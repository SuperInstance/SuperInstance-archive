"""
Prototype-to-Production Pipeline - Automated system for transitioning prototypes to mass production
Handles design validation, manufacturing process optimization, quality assurance, and production scaling.
"""

import asyncio
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiosqlite
import logging
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import tempfile
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    PROTOTYPE_READY = "prototype_ready"
    DESIGN_VALIDATION = "design_validation"
    PROCESS_DEVELOPMENT = "process_development"
    PILOT_PRODUCTION = "pilot_production"
    QUALITY_VALIDATION = "quality_validation"
    PRODUCTION_RAMP = "production_ramp"
    FULL_PRODUCTION = "full_production"
    POST_LAUNCH = "post_launch"

class ValidationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"

class ProcessType(Enum):
    MACHINING = "machining"
    MOLDING = "molding"
    ADDITIVE = "additive"
    ASSEMBLY = "assembly"
    FINISHING = "finishing"
    TESTING = "testing"

class QualityMetric(Enum):
    DIMENSIONAL_ACCURACY = "dimensional_accuracy"
    SURFACE_FINISH = "surface_finish"
    MATERIAL_PROPERTIES = "material_properties"
    FUNCTIONAL_PERFORMANCE = "functional_performance"
    DURABILITY = "durability"
    RELIABILITY = "reliability"

@dataclass
class PrototypeProject:
    id: str
    name: str
    description: str
    created_by: str
    created_at: datetime
    current_stage: PipelineStage
    target_volume: int
    target_cost: float
    timeline: Dict[str, datetime]
    design_files: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationTest:
    id: str
    project_id: str
    test_name: str
    test_type: str
    parameters: Dict[str, Any]
    expected_results: Dict[str, Any]
    actual_results: Optional[Dict[str, Any]]
    status: ValidationStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

@dataclass
class ManufacturingProcess:
    id: str
    project_id: str
    process_name: str
    process_type: ProcessType
    sequence: int
    parameters: Dict[str, Any]
    equipment_requirements: List[str]
    estimated_time: float
    estimated_cost: float
    yield_rate: float
    quality_requirements: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityControl:
    id: str
    project_id: str
    process_id: str
    metric: QualityMetric
    specification: Dict[str, Any]
    measurement_method: str
    frequency: str
    control_limits: Dict[str, float]
    created_at: datetime

@dataclass
class ProductionRun:
    id: str
    project_id: str
    run_type: str  # pilot, ramp, production
    quantity: int
    start_date: datetime
    end_date: Optional[datetime]
    actual_yield: Optional[float]
    quality_results: Dict[str, Any] = field(default_factory=dict)
    cost_analysis: Dict[str, float] = field(default_factory=dict)

@dataclass
class StageGate:
    id: str
    project_id: str
    stage: PipelineStage
    criteria: List[str]
    status: ValidationStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    comments: Optional[str] = None

class PrototypePipelineManager:
    def __init__(self, db_path: str = "prototype_pipeline.db", storage_path: str = "pipeline_files"):
        self.db_path = db_path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.ml_model = None
        self.scaler = StandardScaler()
        
    async def initialize_database(self):
        """Initialize the database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Prototype projects table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS prototype_projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP,
                    current_stage TEXT,
                    target_volume INTEGER,
                    target_cost REAL,
                    timeline TEXT,
                    design_files TEXT,
                    requirements TEXT,
                    constraints TEXT
                )
            """)
            
            # Validation tests table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS validation_tests (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    test_name TEXT,
                    test_type TEXT,
                    parameters TEXT,
                    expected_results TEXT,
                    actual_results TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    notes TEXT
                )
            """)
            
            # Manufacturing processes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS manufacturing_processes (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    process_name TEXT,
                    process_type TEXT,
                    sequence INTEGER,
                    parameters TEXT,
                    equipment_requirements TEXT,
                    estimated_time REAL,
                    estimated_cost REAL,
                    yield_rate REAL,
                    quality_requirements TEXT
                )
            """)
            
            # Quality control table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quality_control (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    process_id TEXT,
                    metric TEXT,
                    specification TEXT,
                    measurement_method TEXT,
                    frequency TEXT,
                    control_limits TEXT,
                    created_at TIMESTAMP
                )
            """)
            
            # Production runs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS production_runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    run_type TEXT,
                    quantity INTEGER,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    actual_yield REAL,
                    quality_results TEXT,
                    cost_analysis TEXT
                )
            """)
            
            # Stage gates table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stage_gates (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    stage TEXT,
                    criteria TEXT,
                    status TEXT,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    comments TEXT
                )
            """)
            
            await db.commit()

    async def create_prototype_project(self, name: str, description: str, created_by: str,
                                     target_volume: int, target_cost: float,
                                     requirements: Dict[str, Any] = None) -> str:
        """Create a new prototype-to-production project"""
        project_id = str(uuid.uuid4())
        now = datetime.now()
        requirements = requirements or {}
        
        # Create initial timeline
        timeline = {
            "design_validation": (now + timedelta(days=30)).isoformat(),
            "process_development": (now + timedelta(days=60)).isoformat(),
            "pilot_production": (now + timedelta(days=90)).isoformat(),
            "quality_validation": (now + timedelta(days=120)).isoformat(),
            "production_ramp": (now + timedelta(days=150)).isoformat(),
            "full_production": (now + timedelta(days=180)).isoformat()
        }
        
        project = PrototypeProject(
            id=project_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=now,
            current_stage=PipelineStage.PROTOTYPE_READY,
            target_volume=target_volume,
            target_cost=target_cost,
            timeline={k: datetime.fromisoformat(v) for k, v in timeline.items()},
            requirements=requirements
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO prototype_projects 
                (id, name, description, created_by, created_at, current_stage,
                 target_volume, target_cost, timeline, design_files, requirements, constraints)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id, project.name, project.description, project.created_by,
                project.created_at, project.current_stage.value,
                project.target_volume, project.target_cost,
                json.dumps(timeline), json.dumps(project.design_files),
                json.dumps(project.requirements), json.dumps(project.constraints)
            ))
            await db.commit()
        
        # Create initial stage gates
        await self._create_stage_gates(project_id)
        
        logger.info(f"Created prototype project: {project_id}")
        return project_id

    async def _create_stage_gates(self, project_id: str):
        """Create stage gate criteria for project"""
        stage_criteria = {
            PipelineStage.DESIGN_VALIDATION: [
                "Design requirements verified",
                "CAD models validated",
                "Materials selected",
                "Performance simulations completed"
            ],
            PipelineStage.PROCESS_DEVELOPMENT: [
                "Manufacturing processes defined",
                "Equipment requirements identified",
                "Process parameters optimized",
                "Cost estimates validated"
            ],
            PipelineStage.PILOT_PRODUCTION: [
                "Pilot run completed successfully",
                "Quality metrics achieved",
                "Process stability demonstrated",
                "Yield targets met"
            ],
            PipelineStage.QUALITY_VALIDATION: [
                "Quality control systems implemented",
                "Statistical process control established",
                "Customer acceptance criteria met",
                "Regulatory compliance verified"
            ],
            PipelineStage.PRODUCTION_RAMP: [
                "Production capacity available",
                "Supply chain established",
                "Quality systems scaled",
                "Cost targets achieved"
            ],
            PipelineStage.FULL_PRODUCTION: [
                "Full volume capability demonstrated",
                "All quality metrics stable",
                "Customer delivery requirements met",
                "Profitability targets achieved"
            ]
        }
        
        async with aiosqlite.connect(self.db_path) as db:
            for stage, criteria in stage_criteria.items():
                gate_id = str(uuid.uuid4())
                await db.execute("""
                    INSERT INTO stage_gates (id, project_id, stage, criteria, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (gate_id, project_id, stage.value, json.dumps(criteria), ValidationStatus.PENDING.value))
            await db.commit()

    async def add_validation_test(self, project_id: str, test_name: str, test_type: str,
                                parameters: Dict[str, Any], expected_results: Dict[str, Any]) -> str:
        """Add a validation test to the project"""
        test_id = str(uuid.uuid4())
        now = datetime.now()
        
        test = ValidationTest(
            id=test_id,
            project_id=project_id,
            test_name=test_name,
            test_type=test_type,
            parameters=parameters,
            expected_results=expected_results,
            status=ValidationStatus.PENDING,
            created_at=now
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO validation_tests
                (id, project_id, test_name, test_type, parameters, expected_results,
                 actual_results, status, created_at, completed_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test.id, test.project_id, test.test_name, test.test_type,
                json.dumps(test.parameters), json.dumps(test.expected_results),
                json.dumps(test.actual_results) if test.actual_results else None,
                test.status.value, test.created_at, test.completed_at, test.notes
            ))
            await db.commit()
        
        logger.info(f"Added validation test {test_id} to project {project_id}")
        return test_id

    async def define_manufacturing_process(self, project_id: str, process_name: str,
                                         process_type: ProcessType, sequence: int,
                                         parameters: Dict[str, Any], equipment: List[str],
                                         time_estimate: float, cost_estimate: float,
                                         yield_rate: float) -> str:
        """Define a manufacturing process for the project"""
        process_id = str(uuid.uuid4())
        
        process = ManufacturingProcess(
            id=process_id,
            project_id=project_id,
            process_name=process_name,
            process_type=process_type,
            sequence=sequence,
            parameters=parameters,
            equipment_requirements=equipment,
            estimated_time=time_estimate,
            estimated_cost=cost_estimate,
            yield_rate=yield_rate
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO manufacturing_processes
                (id, project_id, process_name, process_type, sequence, parameters,
                 equipment_requirements, estimated_time, estimated_cost, yield_rate, quality_requirements)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                process.id, process.project_id, process.process_name, process.process_type.value,
                process.sequence, json.dumps(process.parameters),
                json.dumps(process.equipment_requirements), process.estimated_time,
                process.estimated_cost, process.yield_rate,
                json.dumps(process.quality_requirements)
            ))
            await db.commit()
        
        logger.info(f"Defined manufacturing process {process_id} for project {project_id}")
        return process_id

    async def create_quality_control(self, project_id: str, process_id: str,
                                   metric: QualityMetric, specification: Dict[str, Any],
                                   measurement_method: str, frequency: str,
                                   control_limits: Dict[str, float]) -> str:
        """Create quality control specification"""
        qc_id = str(uuid.uuid4())
        now = datetime.now()
        
        qc = QualityControl(
            id=qc_id,
            project_id=project_id,
            process_id=process_id,
            metric=metric,
            specification=specification,
            measurement_method=measurement_method,
            frequency=frequency,
            control_limits=control_limits,
            created_at=now
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO quality_control
                (id, project_id, process_id, metric, specification, measurement_method,
                 frequency, control_limits, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                qc.id, qc.project_id, qc.process_id, qc.metric.value,
                json.dumps(qc.specification), qc.measurement_method,
                qc.frequency, json.dumps(qc.control_limits), qc.created_at
            ))
            await db.commit()
        
        logger.info(f"Created quality control {qc_id} for project {project_id}")
        return qc_id

    async def run_production_batch(self, project_id: str, run_type: str, quantity: int) -> str:
        """Execute a production run (pilot, ramp, or production)"""
        run_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Simulate production run
        processes = await self._get_manufacturing_processes(project_id)
        
        # Calculate actual yield and costs
        total_yield = 1.0
        total_cost = 0.0
        
        for process in processes:
            # Simulate some variation in yield
            process_yield = process.yield_rate * (0.9 + 0.2 * np.random.random())
            total_yield *= process_yield
            total_cost += process.estimated_cost * quantity
        
        # Add variation based on run type
        if run_type == "pilot":
            total_yield *= 0.85  # Lower yield for pilot runs
            total_cost *= 1.2    # Higher costs for pilot
        elif run_type == "ramp":
            total_yield *= 0.95  # Moderate yield for ramp
            total_cost *= 1.1    # Slightly higher costs
        
        # Quality simulation
        quality_results = await self._simulate_quality_results(project_id, quantity)
        
        run = ProductionRun(
            id=run_id,
            project_id=project_id,
            run_type=run_type,
            quantity=quantity,
            start_date=now,
            end_date=now + timedelta(days=1),  # Simplified timeline
            actual_yield=total_yield,
            quality_results=quality_results,
            cost_analysis={
                "total_cost": total_cost,
                "cost_per_unit": total_cost / quantity,
                "labor_cost": total_cost * 0.3,
                "material_cost": total_cost * 0.5,
                "overhead_cost": total_cost * 0.2
            }
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO production_runs
                (id, project_id, run_type, quantity, start_date, end_date,
                 actual_yield, quality_results, cost_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.id, run.project_id, run.run_type, run.quantity,
                run.start_date, run.end_date, run.actual_yield,
                json.dumps(run.quality_results), json.dumps(run.cost_analysis)
            ))
            await db.commit()
        
        logger.info(f"Completed production run {run_id} for project {project_id}")
        return run_id

    async def _simulate_quality_results(self, project_id: str, quantity: int) -> Dict[str, Any]:
        """Simulate quality test results for production run"""
        qc_specs = await self._get_quality_controls(project_id)
        
        results = {}
        for qc in qc_specs:
            metric_name = qc.metric.value
            
            # Simulate measurements based on control limits
            if "upper_limit" in qc.control_limits and "lower_limit" in qc.control_limits:
                target = (qc.control_limits["upper_limit"] + qc.control_limits["lower_limit"]) / 2
                std_dev = (qc.control_limits["upper_limit"] - target) / 3
                
                measurements = np.random.normal(target, std_dev, min(quantity, 100))
                
                results[metric_name] = {
                    "measurements": measurements.tolist(),
                    "mean": float(np.mean(measurements)),
                    "std_dev": float(np.std(measurements)),
                    "pass_rate": float(np.sum(
                        (measurements >= qc.control_limits["lower_limit"]) &
                        (measurements <= qc.control_limits["upper_limit"])
                    ) / len(measurements)),
                    "cpk": self._calculate_cpk(measurements, qc.control_limits)
                }
        
        return results

    def _calculate_cpk(self, measurements: np.ndarray, control_limits: Dict[str, float]) -> float:
        """Calculate process capability index (Cpk)"""
        if "upper_limit" not in control_limits or "lower_limit" not in control_limits:
            return 0.0
        
        mean_val = np.mean(measurements)
        std_val = np.std(measurements)
        
        if std_val == 0:
            return float('inf')
        
        usl = control_limits["upper_limit"]
        lsl = control_limits["lower_limit"]
        
        cpu = (usl - mean_val) / (3 * std_val)
        cpl = (mean_val - lsl) / (3 * std_val)
        
        return float(min(cpu, cpl))

    async def advance_stage(self, project_id: str, reviewer_id: str, comments: str = None) -> bool:
        """Advance project to next stage if gate criteria are met"""
        project = await self.get_project(project_id)
        if not project:
            return False
        
        current_stage = project.current_stage
        stage_mapping = {
            PipelineStage.PROTOTYPE_READY: PipelineStage.DESIGN_VALIDATION,
            PipelineStage.DESIGN_VALIDATION: PipelineStage.PROCESS_DEVELOPMENT,
            PipelineStage.PROCESS_DEVELOPMENT: PipelineStage.PILOT_PRODUCTION,
            PipelineStage.PILOT_PRODUCTION: PipelineStage.QUALITY_VALIDATION,
            PipelineStage.QUALITY_VALIDATION: PipelineStage.PRODUCTION_RAMP,
            PipelineStage.PRODUCTION_RAMP: PipelineStage.FULL_PRODUCTION,
            PipelineStage.FULL_PRODUCTION: PipelineStage.POST_LAUNCH
        }
        
        if current_stage not in stage_mapping:
            return False
        
        next_stage = stage_mapping[current_stage]
        
        # Update stage gate
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE stage_gates 
                SET status = ?, reviewed_by = ?, reviewed_at = ?, comments = ?
                WHERE project_id = ? AND stage = ?
            """, (
                ValidationStatus.PASSED.value, reviewer_id, datetime.now(),
                comments, project_id, current_stage.value
            ))
            
            # Update project stage
            await db.execute("""
                UPDATE prototype_projects SET current_stage = ? WHERE id = ?
            """, (next_stage.value, project_id))
            
            await db.commit()
        
        logger.info(f"Advanced project {project_id} from {current_stage.value} to {next_stage.value}")
        return True

    async def get_project(self, project_id: str) -> Optional[PrototypeProject]:
        """Get project by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM prototype_projects WHERE id = ?
            """, (project_id,))
            result = await cursor.fetchone()
            
            if result:
                timeline_data = json.loads(result[8])
                return PrototypeProject(
                    id=result[0],
                    name=result[1],
                    description=result[2],
                    created_by=result[3],
                    created_at=datetime.fromisoformat(result[4]),
                    current_stage=PipelineStage(result[5]),
                    target_volume=result[6],
                    target_cost=result[7],
                    timeline={k: datetime.fromisoformat(v) for k, v in timeline_data.items()},
                    design_files=json.loads(result[9]),
                    requirements=json.loads(result[10]),
                    constraints=json.loads(result[11])
                )
        return None

    async def _get_manufacturing_processes(self, project_id: str) -> List[ManufacturingProcess]:
        """Get manufacturing processes for project"""
        processes = []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM manufacturing_processes 
                WHERE project_id = ? ORDER BY sequence
            """, (project_id,))
            results = await cursor.fetchall()
            
            for result in results:
                processes.append(ManufacturingProcess(
                    id=result[0],
                    project_id=result[1],
                    process_name=result[2],
                    process_type=ProcessType(result[3]),
                    sequence=result[4],
                    parameters=json.loads(result[5]),
                    equipment_requirements=json.loads(result[6]),
                    estimated_time=result[7],
                    estimated_cost=result[8],
                    yield_rate=result[9],
                    quality_requirements=json.loads(result[10])
                ))
        
        return processes

    async def _get_quality_controls(self, project_id: str) -> List[QualityControl]:
        """Get quality controls for project"""
        qcs = []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM quality_control WHERE project_id = ?
            """, (project_id,))
            results = await cursor.fetchall()
            
            for result in results:
                qcs.append(QualityControl(
                    id=result[0],
                    project_id=result[1],
                    process_id=result[2],
                    metric=QualityMetric(result[3]),
                    specification=json.loads(result[4]),
                    measurement_method=result[5],
                    frequency=result[6],
                    control_limits=json.loads(result[7]),
                    created_at=datetime.fromisoformat(result[8])
                ))
        
        return qcs

class PipelineAnalyzer:
    def __init__(self, manager: PrototypePipelineManager):
        self.manager = manager
    
    async def generate_pipeline_dashboard(self, project_id: str) -> Dict[str, Any]:
        """Generate comprehensive pipeline dashboard"""
        project = await self.manager.get_project(project_id)
        if not project:
            return {}
        
        # Get production runs
        production_runs = await self._get_production_runs(project_id)
        
        # Calculate key metrics
        total_runs = len(production_runs)
        
        if production_runs:
            avg_yield = np.mean([run.actual_yield for run in production_runs if run.actual_yield])
            total_produced = sum(run.quantity for run in production_runs)
            
            # Cost trends
            cost_trend = []
            for run in production_runs:
                if run.cost_analysis:
                    cost_trend.append({
                        "date": run.start_date.isoformat(),
                        "cost_per_unit": run.cost_analysis.get("cost_per_unit", 0),
                        "run_type": run.run_type
                    })
            
            # Quality trends
            quality_trend = []
            for run in production_runs:
                if run.quality_results:
                    avg_pass_rate = np.mean([
                        metrics.get("pass_rate", 0) 
                        for metrics in run.quality_results.values()
                        if isinstance(metrics, dict) and "pass_rate" in metrics
                    ])
                    quality_trend.append({
                        "date": run.start_date.isoformat(),
                        "pass_rate": avg_pass_rate,
                        "run_type": run.run_type
                    })
        else:
            avg_yield = 0
            total_produced = 0
            cost_trend = []
            quality_trend = []
        
        # Timeline analysis
        timeline_status = {}
        for milestone, target_date in project.timeline.items():
            is_overdue = datetime.now() > target_date
            timeline_status[milestone] = {
                "target_date": target_date.isoformat(),
                "is_overdue": is_overdue,
                "days_until": (target_date - datetime.now()).days
            }
        
        return {
            "project_info": {
                "name": project.name,
                "current_stage": project.current_stage.value,
                "target_volume": project.target_volume,
                "target_cost": project.target_cost
            },
            "production_metrics": {
                "total_runs": total_runs,
                "average_yield": float(avg_yield),
                "total_produced": total_produced,
                "cost_trend": cost_trend,
                "quality_trend": quality_trend
            },
            "timeline_status": timeline_status,
            "stage_progress": await self._get_stage_progress(project_id)
        }

    async def _get_production_runs(self, project_id: str) -> List[ProductionRun]:
        """Get production runs for project"""
        runs = []
        async with aiosqlite.connect(self.manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM production_runs WHERE project_id = ? ORDER BY start_date
            """, (project_id,))
            results = await cursor.fetchall()
            
            for result in results:
                runs.append(ProductionRun(
                    id=result[0],
                    project_id=result[1],
                    run_type=result[2],
                    quantity=result[3],
                    start_date=datetime.fromisoformat(result[4]),
                    end_date=datetime.fromisoformat(result[5]) if result[5] else None,
                    actual_yield=result[6],
                    quality_results=json.loads(result[7]) if result[7] else {},
                    cost_analysis=json.loads(result[8]) if result[8] else {}
                ))
        
        return runs

    async def _get_stage_progress(self, project_id: str) -> Dict[str, Any]:
        """Get stage gate progress"""
        progress = {}
        async with aiosqlite.connect(self.manager.db_path) as db:
            cursor = await db.execute("""
                SELECT stage, status, criteria FROM stage_gates WHERE project_id = ?
            """, (project_id,))
            results = await cursor.fetchall()
            
            for result in results:
                stage = result[0]
                status = result[1]
                criteria = json.loads(result[2])
                
                progress[stage] = {
                    "status": status,
                    "criteria": criteria,
                    "completion_rate": 1.0 if status == "passed" else 0.0
                }
        
        return progress

async def main():
    """Demonstration of the prototype-to-production pipeline system"""
    manager = PrototypePipelineManager()
    analyzer = PipelineAnalyzer(manager)
    
    # Initialize database
    await manager.initialize_database()
    
    print("=== Prototype-to-Production Pipeline Demo ===")
    
    # Create a prototype project
    project_id = await manager.create_prototype_project(
        name="Smart Thermostat v2",
        description="Next generation smart thermostat with improved sensors",
        created_by="engineer_001",
        target_volume=10000,
        target_cost=45.0,
        requirements={
            "temperature_accuracy": "±0.1°C",
            "wifi_connectivity": "802.11n minimum",
            "battery_life": "2 years",
            "operating_temp": "-20°C to 60°C"
        }
    )
    print(f"Created project: {project_id}")
    
    # Add validation tests
    test_id = await manager.add_validation_test(
        project_id=project_id,
        test_name="Temperature Accuracy Test",
        test_type="performance",
        parameters={"test_duration": 24, "temp_range": [-20, 60], "humidity": [20, 80]},
        expected_results={"accuracy": 0.1, "stability": 0.05}
    )
    print(f"Added validation test: {test_id}")
    
    # Define manufacturing processes
    machining_id = await manager.define_manufacturing_process(
        project_id=project_id,
        process_name="Housing Machining",
        process_type=ProcessType.MACHINING,
        sequence=1,
        parameters={"material": "ABS", "tolerance": "±0.05mm"},
        equipment=["CNC_Mill_001", "Drill_Press_002"],
        time_estimate=15.0,
        cost_estimate=8.50,
        yield_rate=0.98
    )
    
    assembly_id = await manager.define_manufacturing_process(
        project_id=project_id,
        process_name="PCB Assembly",
        process_type=ProcessType.ASSEMBLY,
        sequence=2,
        parameters={"components": 45, "solder_type": "lead_free"},
        equipment=["Pick_Place_001", "Reflow_Oven_001"],
        time_estimate=8.0,
        cost_estimate=15.75,
        yield_rate=0.95
    )
    print(f"Defined processes: {machining_id}, {assembly_id}")
    
    # Create quality controls
    qc_id = await manager.create_quality_control(
        project_id=project_id,
        process_id=assembly_id,
        metric=QualityMetric.FUNCTIONAL_PERFORMANCE,
        specification={"temp_accuracy": 0.1, "response_time": 5.0},
        measurement_method="automated_test_fixture",
        frequency="every_unit",
        control_limits={"upper_limit": 0.15, "lower_limit": 0.05}
    )
    print(f"Created quality control: {qc_id}")
    
    # Run pilot production
    pilot_run_id = await manager.run_production_batch(
        project_id=project_id,
        run_type="pilot",
        quantity=50
    )
    print(f"Completed pilot run: {pilot_run_id}")
    
    # Advance through stages
    await manager.advance_stage(project_id, "reviewer_001", "Pilot run successful, proceed to ramp")
    await manager.advance_stage(project_id, "reviewer_001", "Quality validation complete")
    print("Advanced through pipeline stages")
    
    # Run production ramp
    ramp_run_id = await manager.run_production_batch(
        project_id=project_id,
        run_type="ramp",
        quantity=500
    )
    print(f"Completed ramp run: {ramp_run_id}")
    
    # Generate dashboard
    dashboard = await analyzer.generate_pipeline_dashboard(project_id)
    
    print(f"\n=== Pipeline Dashboard ===")
    print(f"Project: {dashboard['project_info']['name']}")
    print(f"Current Stage: {dashboard['project_info']['current_stage']}")
    print(f"Production Runs: {dashboard['production_metrics']['total_runs']}")
    print(f"Average Yield: {dashboard['production_metrics']['average_yield']:.2%}")
    print(f"Total Produced: {dashboard['production_metrics']['total_produced']} units")
    
    print(f"\nTimeline Status:")
    for milestone, status in dashboard['timeline_status'].items():
        overdue = " (OVERDUE)" if status['is_overdue'] else ""
        print(f"- {milestone}: {status['days_until']} days{overdue}")
    
    print(f"\nStage Progress:")
    for stage, progress in dashboard['stage_progress'].items():
        print(f"- {stage}: {progress['status']} ({len(progress['criteria'])} criteria)")
    
    print("\n=== Demo completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(main())