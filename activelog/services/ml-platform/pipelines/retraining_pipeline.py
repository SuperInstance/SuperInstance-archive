import time
import sqlite3
import pickle
import json
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import subprocess
import os


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(Enum):
    SCHEDULE = "schedule"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DATA_DRIFT = "data_drift"
    MANUAL = "manual"
    DATA_VOLUME = "data_volume"


@dataclass
class RetrainingConfig:
    model_id: str
    model_version: str
    trigger_type: TriggerType
    schedule_cron: Optional[str] = None
    performance_threshold: Optional[float] = None
    data_drift_threshold: Optional[float] = None
    min_samples_required: Optional[int] = None
    training_script_path: str = ""
    training_data_query: str = ""
    validation_split: float = 0.2
    hyperparameters: Dict[str, Any] = None
    environment_variables: Dict[str, str] = None
    max_training_time_hours: int = 24
    auto_deploy: bool = False


@dataclass
class PipelineRun:
    run_id: str
    config: RetrainingConfig
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    trigger_reason: str = ""
    metrics: Dict[str, float] = None
    logs: List[str] = None
    error_message: str = ""
    artifacts_path: str = ""
    new_model_version: str = ""


class DataCollector:
    def __init__(self, db_path: str = "ml_platform.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                features TEXT NOT NULL,
                target TEXT,
                metadata TEXT,
                used_in_training BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_training_sample(self, model_id: str, features: Dict[str, Any],
                          target: Optional[Any] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO training_data (model_id, timestamp, features, target, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            model_id,
            datetime.now().isoformat(),
            json.dumps(features),
            json.dumps(target) if target is not None else None,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_training_data(self, model_id: str, start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         unused_only: bool = True) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM training_data WHERE model_id = ?"
        params = [model_id]
        
        if unused_only:
            query += " AND used_in_training = FALSE"
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "model_id": row[1],
                "timestamp": row[2],
                "features": json.loads(row[3]),
                "target": json.loads(row[4]) if row[4] else None,
                "metadata": json.loads(row[5]) if row[5] else {},
                "used_in_training": row[6]
            })
        
        return data
    
    def mark_data_as_used(self, data_ids: List[int]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ",".join(["?" for _ in data_ids])
        cursor.execute(f'''
            UPDATE training_data 
            SET used_in_training = TRUE 
            WHERE id IN ({placeholders})
        ''', data_ids)
        
        conn.commit()
        conn.close()


class ModelTrainer:
    def __init__(self, base_models_dir: str = "/home/activeloguser/activelog/services/ml-platform/models"):
        self.base_models_dir = base_models_dir
        self.logger = logging.getLogger(__name__)
    
    def train_model(self, run: PipelineRun, data_collector: DataCollector) -> Tuple[bool, str, Dict[str, float]]:
        try:
            # Get training data
            training_data = data_collector.get_training_data(
                run.config.model_id,
                unused_only=True
            )
            
            if len(training_data) < (run.config.min_samples_required or 100):
                return False, f"Insufficient training data: {len(training_data)} samples", {}
            
            # Create training directory
            training_dir = os.path.join(self.base_models_dir, "training", run.run_id)
            os.makedirs(training_dir, exist_ok=True)
            
            # Prepare training data file
            training_file = os.path.join(training_dir, "training_data.json")
            with open(training_file, 'w') as f:
                json.dump(training_data, f)
            
            # Execute training script
            if run.config.training_script_path:
                success, output, metrics = self._execute_training_script(
                    run, training_dir, training_file
                )
            else:
                success, output, metrics = self._default_training_process(
                    run, training_data
                )
            
            # Mark data as used if training successful
            if success:
                data_ids = [item["id"] for item in training_data]
                data_collector.mark_data_as_used(data_ids)
            
            return success, output, metrics
            
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return False, str(e), {}
    
    def _execute_training_script(self, run: PipelineRun, training_dir: str,
                               training_file: str) -> Tuple[bool, str, Dict[str, float]]:
        env = os.environ.copy()
        if run.config.environment_variables:
            env.update(run.config.environment_variables)
        
        # Add common environment variables
        env.update({
            "MODEL_ID": run.config.model_id,
            "MODEL_VERSION": run.config.model_version,
            "TRAINING_DATA_FILE": training_file,
            "OUTPUT_DIR": training_dir,
            "HYPERPARAMETERS": json.dumps(run.config.hyperparameters or {})
        })
        
        try:
            result = subprocess.run(
                ["python", run.config.training_script_path],
                cwd=training_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=run.config.max_training_time_hours * 3600
            )
            
            # Try to read metrics file if it exists
            metrics_file = os.path.join(training_dir, "metrics.json")
            metrics = {}
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
            
            return result.returncode == 0, result.stdout + result.stderr, metrics
            
        except subprocess.TimeoutExpired:
            return False, "Training timeout exceeded", {}
        except Exception as e:
            return False, f"Script execution failed: {e}", {}
    
    def _default_training_process(self, run: PipelineRun,
                                training_data: List[Dict[str, Any]]) -> Tuple[bool, str, Dict[str, float]]:
        # Simple default training process using sklearn
        try:
            from sklearn.model_selection import train_test_split
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import accuracy_score, precision_score, recall_score
            import numpy as np
            
            # Extract features and targets
            features = []
            targets = []
            
            for sample in training_data:
                if sample["target"] is not None:
                    # Convert features dict to list (simple approach)
                    feature_values = list(sample["features"].values())
                    features.append(feature_values)
                    targets.append(sample["target"])
            
            if not features:
                return False, "No labeled training data available", {}
            
            X = np.array(features)
            y = np.array(targets)
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=run.config.validation_split, random_state=42
            )
            
            # Train model
            model = RandomForestClassifier(**(run.config.hyperparameters or {}))
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_val)
            metrics = {
                "accuracy": accuracy_score(y_val, y_pred),
                "precision": precision_score(y_val, y_pred, average='weighted'),
                "recall": recall_score(y_val, y_pred, average='weighted'),
                "training_samples": len(X_train),
                "validation_samples": len(X_val)
            }
            
            # Save model
            model_dir = os.path.join(self.base_models_dir, run.config.model_id)
            os.makedirs(model_dir, exist_ok=True)
            
            new_version = f"{run.config.model_version}.retrain.{int(time.time())}"
            model_path = os.path.join(model_dir, f"model_{new_version}.pkl")
            
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            run.new_model_version = new_version
            run.artifacts_path = model_path
            
            return True, f"Training completed successfully. New version: {new_version}", metrics
            
        except ImportError:
            return False, "Default training requires sklearn", {}
        except Exception as e:
            return False, f"Default training failed: {e}", {}


class RetrainingPipeline:
    def __init__(self, db_path: str = "ml_platform.db"):
        self.db_path = db_path
        self.data_collector = DataCollector(db_path)
        self.model_trainer = ModelTrainer()
        self.configurations = {}
        self.active_runs = {}
        self.scheduler_thread = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retraining_configs (
                model_id TEXT,
                model_version TEXT,
                config TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                PRIMARY KEY (model_id, model_version)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                trigger_reason TEXT,
                metrics TEXT,
                logs TEXT,
                error_message TEXT,
                artifacts_path TEXT,
                new_model_version TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Load existing configurations
        self._load_configurations()
    
    def _load_configurations(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT model_id, model_version, config 
            FROM retraining_configs 
            WHERE active = TRUE
        ''')
        
        for row in cursor.fetchall():
            model_id, model_version, config_json = row
            config_dict = json.loads(config_json)
            config = RetrainingConfig(**config_dict)
            key = f"{model_id}:{model_version}"
            self.configurations[key] = config
        
        conn.close()
    
    def add_retraining_config(self, config: RetrainingConfig):
        key = f"{config.model_id}:{config.model_version}"
        self.configurations[key] = config
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO retraining_configs 
            (model_id, model_version, config, active)
            VALUES (?, ?, ?, TRUE)
        ''', (config.model_id, config.model_version, json.dumps(asdict(config))))
        
        conn.commit()
        conn.close()
        
        # Set up scheduling if needed
        if config.trigger_type == TriggerType.SCHEDULE and config.schedule_cron:
            self._setup_scheduled_retraining(config)
    
    def remove_retraining_config(self, model_id: str, model_version: str):
        key = f"{model_id}:{model_version}"
        if key in self.configurations:
            del self.configurations[key]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE retraining_configs 
            SET active = FALSE 
            WHERE model_id = ? AND model_version = ?
        ''', (model_id, model_version))
        
        conn.commit()
        conn.close()
    
    def trigger_retraining(self, model_id: str, model_version: str,
                         trigger_reason: str = "manual",
                         async_execution: bool = True) -> str:
        key = f"{model_id}:{model_version}"
        if key not in self.configurations:
            raise ValueError(f"No retraining configuration found for {key}")
        
        config = self.configurations[key]
        run_id = f"run_{model_id}_{model_version}_{int(time.time())}"
        
        run = PipelineRun(
            run_id=run_id,
            config=config,
            status=PipelineStatus.PENDING,
            start_time=datetime.now(),
            trigger_reason=trigger_reason,
            logs=[]
        )
        
        self.active_runs[run_id] = run
        self._store_pipeline_run(run)
        
        if async_execution:
            thread = threading.Thread(target=self._execute_pipeline_run, args=(run,))
            thread.daemon = True
            thread.start()
        else:
            self._execute_pipeline_run(run)
        
        return run_id
    
    def _execute_pipeline_run(self, run: PipelineRun):
        try:
            run.status = PipelineStatus.RUNNING
            self._store_pipeline_run(run)
            self.logger.info(f"Starting retraining run {run.run_id}")
            
            # Execute training
            success, output, metrics = self.model_trainer.train_model(run, self.data_collector)
            
            run.end_time = datetime.now()
            run.metrics = metrics
            run.logs.append(output)
            
            if success:
                run.status = PipelineStatus.COMPLETED
                self.logger.info(f"Retraining run {run.run_id} completed successfully")
                
                # Auto-deploy if configured
                if run.config.auto_deploy:
                    self._auto_deploy_model(run)
            else:
                run.status = PipelineStatus.FAILED
                run.error_message = output
                self.logger.error(f"Retraining run {run.run_id} failed: {output}")
            
        except Exception as e:
            run.status = PipelineStatus.FAILED
            run.error_message = str(e)
            run.end_time = datetime.now()
            self.logger.error(f"Retraining run {run.run_id} failed with exception: {e}")
        
        finally:
            self._store_pipeline_run(run)
    
    def _auto_deploy_model(self, run: PipelineRun):
        # Integration with model registry for auto-deployment
        self.logger.info(f"Auto-deploying model {run.new_model_version}")
        # This would integrate with the model registry to promote the model
    
    def _store_pipeline_run(self, run: PipelineRun):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO pipeline_runs 
            (run_id, model_id, model_version, status, start_time, end_time,
             trigger_reason, metrics, logs, error_message, artifacts_path, new_model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run.run_id,
            run.config.model_id,
            run.config.model_version,
            run.status.value,
            run.start_time.isoformat(),
            run.end_time.isoformat() if run.end_time else None,
            run.trigger_reason,
            json.dumps(run.metrics) if run.metrics else None,
            json.dumps(run.logs) if run.logs else None,
            run.error_message,
            run.artifacts_path,
            run.new_model_version
        ))
        
        conn.commit()
        conn.close()
    
    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM pipeline_runs WHERE run_id = ?
        ''', (run_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct config
        key = f"{row[1]}:{row[2]}"  # model_id:model_version
        config = self.configurations.get(key)
        
        return PipelineRun(
            run_id=row[0],
            config=config,
            status=PipelineStatus(row[3]),
            start_time=datetime.fromisoformat(row[4]),
            end_time=datetime.fromisoformat(row[5]) if row[5] else None,
            trigger_reason=row[6] or "",
            metrics=json.loads(row[7]) if row[7] else {},
            logs=json.loads(row[8]) if row[8] else [],
            error_message=row[9] or "",
            artifacts_path=row[10] or "",
            new_model_version=row[11] or ""
        )
    
    def get_recent_runs(self, model_id: Optional[str] = None,
                       limit: int = 50) -> List[PipelineRun]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM pipeline_runs"
        params = []
        
        if model_id:
            query += " WHERE model_id = ?"
            params.append(model_id)
        
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        runs = []
        for row in rows:
            key = f"{row[1]}:{row[2]}"
            config = self.configurations.get(key)
            
            runs.append(PipelineRun(
                run_id=row[0],
                config=config,
                status=PipelineStatus(row[3]),
                start_time=datetime.fromisoformat(row[4]),
                end_time=datetime.fromisoformat(row[5]) if row[5] else None,
                trigger_reason=row[6] or "",
                metrics=json.loads(row[7]) if row[7] else {},
                logs=json.loads(row[8]) if row[8] else [],
                error_message=row[9] or "",
                artifacts_path=row[10] or "",
                new_model_version=row[11] or ""
            ))
        
        return runs
    
    def start_scheduler(self):
        if not self.is_running:
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
    
    def stop_scheduler(self):
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
    
    def _run_scheduler(self):
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _setup_scheduled_retraining(self, config: RetrainingConfig):
        def job():
            try:
                self.trigger_retraining(
                    config.model_id, 
                    config.model_version, 
                    f"scheduled: {config.schedule_cron}"
                )
            except Exception as e:
                self.logger.error(f"Scheduled retraining failed: {e}")
        
        # Simple scheduling - in production, use proper cron parsing
        if config.schedule_cron == "daily":
            schedule.every().day.at("02:00").do(job)
        elif config.schedule_cron == "weekly":
            schedule.every().week.do(job)
        elif config.schedule_cron.startswith("every_"):
            hours = int(config.schedule_cron.split("_")[1])
            schedule.every(hours).hours.do(job)


# Usage example
if __name__ == "__main__":
    pipeline = RetrainingPipeline()
    
    # Create retraining configuration
    config = RetrainingConfig(
        model_id="sentiment_model",
        model_version="1.0",
        trigger_type=TriggerType.SCHEDULE,
        schedule_cron="daily",
        min_samples_required=1000,
        training_script_path="/path/to/train_sentiment.py",
        validation_split=0.2,
        hyperparameters={"n_estimators": 100, "max_depth": 10},
        auto_deploy=True
    )
    
    pipeline.add_retraining_config(config)
    pipeline.start_scheduler()
    
    # Add some training data
    data_collector = pipeline.data_collector
    data_collector.add_training_sample(
        "sentiment_model",
        {"text": "This is great!", "length": 13},
        "positive"
    )
    
    # Manually trigger retraining
    run_id = pipeline.trigger_retraining("sentiment_model", "1.0", "manual_test")
    print(f"Started retraining run: {run_id}")
    
    # Check run status
    time.sleep(2)
    run = pipeline.get_pipeline_run(run_id)
    print(f"Run status: {run.status}")