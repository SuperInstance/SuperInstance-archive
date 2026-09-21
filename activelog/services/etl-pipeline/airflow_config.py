"""
Apache Airflow Configuration for ETL Pipeline
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Airflow Configuration
AIRFLOW_CONFIG = {
    # Core settings
    'core': {
        'dags_folder': '/home/activeloguser/activelog/services/etl-pipeline/dags',
        'plugins_folder': '/home/activeloguser/activelog/services/etl-pipeline/plugins',
        'base_log_folder': '/home/activeloguser/activelog/services/etl-pipeline/logs',
        'remote_logging': False,
        'executor': 'LocalExecutor',
        'sql_alchemy_conn': 'postgresql://airflow:airflow@localhost:5432/airflow',
        'parallelism': 32,
        'dag_concurrency': 16,
        'max_active_runs_per_dag': 16,
        'load_examples': False,
        'load_default_connections': False,
        'donot_pickle': True,
        'dagbag_import_timeout': 30.0,
        'dag_file_processor_timeout': 50,
        'task_runner': 'StandardTaskRunner',
        'default_task_retries': 0,
        'killed_task_cleanup_time': 60,
        'dag_run_conf_overrides_params': False,
        'enable_xcom_pickling': True,
        'check_slas': True,
        'xcom_backend': 'airflow.models.xcom.BaseXCom',
        'lazy_load_plugins': True,
        'lazy_discover_providers': True
    },
    
    # Scheduler settings
    'scheduler': {
        'job_heartbeat_sec': 5,
        'scheduler_heartbeat_sec': 5,
        'run_duration': -1,
        'min_file_process_interval': 0,
        'dag_dir_list_interval': 300,
        'print_stats_interval': 30,
        'pool_metrics_interval': 5.0,
        'scheduler_health_check_threshold': 30,
        'orphaned_tasks_check_interval': 300.0,
        'child_process_log_directory': '/home/activeloguser/activelog/services/etl-pipeline/logs/scheduler',
        'schedule_after_task_execution': True,
        'parsing_processes': 2,
        'file_parsing_sort_mode': 'modified_time',
        'use_row_level_locking': True,
        'max_dagruns_to_create_per_loop': 10,
        'max_dagruns_per_loop_to_schedule': 20,
        'scheduler_idle_sleep_time': 1,
        'num_runs': -1,
        'processor_poll_interval': 1,
        'min_serialized_dag_update_interval': 30,
        'min_serialized_dag_fetch_interval': 10,
        'max_callbacks_per_loop': 20,
        'dag_stale_not_seen_duration': 600,
        'auto_refresh_interval': 30,
        'task_queued_timeout': 600.0
    },
    
    # Webserver settings
    'webserver': {
        'base_url': 'http://localhost:8080',
        'default_ui_timezone': 'UTC',
        'web_server_host': '0.0.0.0',
        'web_server_port': 8080,
        'web_server_ssl_cert': '',
        'web_server_ssl_key': '',
        'web_server_master_timeout': 120,
        'web_server_worker_timeout': 120,
        'worker_refresh_batch_size': 1,
        'worker_refresh_interval': 6000,
        'secret_key': 'temporary_key_for_development',
        'workers': 4,
        'worker_class': 'sync',
        'access_logfile': '-',
        'error_logfile': '-',
        'access_logformat': '',
        'expose_config': True,
        'expose_hostname': True,
        'expose_stacktrace': True,
        'dag_default_view': 'tree',
        'dag_orientation': 'LR',
        'log_fetch_timeout_sec': 5,
        'log_fetch_delay_sec': 2,
        'log_auto_tailing_offset': 30,
        'log_animation_speed': 1000,
        'hide_paused_dags_by_default': False,
        'page_size': 100,
        'navbar_color': '#007A87',
        'default_dag_run_display_number': 25,
        'enable_proxy_fix': False,
        'cookie_secure': False,
        'cookie_samesite': 'Lax',
        'default_wrap': False,
        'x_frame_enabled': True,
        'show_recent_stats_for_completed_runs': True,
        'update_fab_perms': True
    },
    
    # Celery settings (for distributed execution)
    'celery': {
        'celery_app_name': 'airflow.executors.celery_executor',
        'worker_concurrency': 16,
        'worker_log_server_port': 8793,
        'broker_url': 'redis://localhost:6379/0',
        'result_backend': 'db+postgresql://airflow:airflow@localhost:5432/airflow',
        'flower_host': '0.0.0.0',
        'flower_url_prefix': '',
        'flower_port': 5555,
        'flower_basic_auth': '',
        'default_queue': 'default',
        'celery_config_options': 'airflow.config_templates.default_celery.DEFAULT_CELERY_CONFIG',
        'ssl_active': False,
        'ssl_key': '',
        'ssl_cert': '',
        'ssl_cacert': '',
        'pool': 'prefork',
        'operation_timeout': 1.0
    },
    
    # Logging settings
    'logging': {
        'logging_level': 'INFO',
        'fab_logging_level': 'WARN',
        'logging_config_class': '',
        'colored_console_log': True,
        'colored_log_format': '[%%(blue)s%%(asctime)s%%(reset)s] {{%%(blue)s%%(filename)s:%%(reset)s%%(lineno)d}} %%(log_color)s%%(levelname)s%%(reset)s - %%(log_color)s%%(message)s%%(reset)s',
        'colored_formatter_class': 'airflow.utils.log.colored_log.CustomTTYColoredFormatter',
        'log_format': '[%%(asctime)s] {{%%(filename)s:%%(lineno)d}} %%(levelname)s - %%(message)s',
        'simple_log_format': '%%(levelname)s - %%(message)s',
        'task_log_prefix_template': '',
        'log_filename_template': '{{ ti.dag_id }}/{{ ti.task_id }}/{{ ts }}/{{ try_number }}.log',
        'log_processor_filename_template': '{{ filename }}.log',
        'dag_processor_manager_log_location': '/home/activeloguser/activelog/services/etl-pipeline/logs/dag_processor_manager/dag_processor_manager.log',
        'task_log_reader': 'task',
        'extra_logger_names': '',
        'encrypt_s3_logs': False
    },
    
    # Metrics settings
    'metrics': {
        'statsd_on': True,
        'statsd_host': 'localhost',
        'statsd_port': 8125,
        'statsd_prefix': 'airflow',
        'statsd_allow_list': '',
        'stat_name_handler': '',
        'statsd_datadog_enabled': False,
        'statsd_datadog_tags': '',
        'statsd_custom_client_path': ''
    },
    
    # Lineage settings
    'lineage': {
        'backend': 'airflow.lineage.backend.atlas.AtlasBackend'
    },
    
    # Atlas settings
    'atlas': {
        'sasl_enabled': False,
        'host': '',
        'port': 21000,
        'username': '',
        'password': ''
    },
    
    # Operators
    'operators': {
        'default_owner': 'airflow',
        'default_cpus': 1,
        'default_ram': 512,
        'default_disk': 512,
        'default_gpus': 0,
        'allow_illegal_arguments': False
    },
    
    # Hive settings
    'hive': {
        'default_hive_mapred_queue': ''
    },
    
    # Email settings
    'email': {
        'email_backend': 'airflow.utils.email.send_email_smtp',
        'email_conn_id': 'smtp_default',
        'default_email_on_retry': True,
        'default_email_on_failure': True,
        'subject_template': '/home/activeloguser/activelog/services/etl-pipeline/config/airflow_email_subject_template.txt',
        'html_content_template': '/home/activeloguser/activelog/services/etl-pipeline/config/airflow_email_template.html'
    },
    
    # SMTP settings
    'smtp': {
        'smtp_host': 'localhost',
        'smtp_starttls': True,
        'smtp_ssl': False,
        'smtp_user': '',
        'smtp_password': '',
        'smtp_port': 587,
        'smtp_mail_from': 'airflow@example.com',
        'smtp_timeout': 30,
        'smtp_retry_limit': 5
    },
    
    # Sensors settings
    'sensors': {
        'default_timeout': 60 * 60 * 24 * 7,
        'min_file_process_interval': 0,
        'dag_dir_list_interval': 300,
        'print_stats_interval': 30
    },
    
    # Smart sensors
    'smart_sensor': {
        'use_smart_sensor': False,
        'shard_code_upper_limit': 10000,
        'shards': 5,
        'sensors_enabled': 'NamedHivePartitionSensor'
    }
}

# Default DAG arguments
DEFAULT_DAG_ARGS = {
    'owner': 'etl-pipeline',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
    'max_active_runs': 1,
    'tags': ['etl', 'data-pipeline']
}

# Connection configurations for data sources
DATA_SOURCE_CONNECTIONS = {
    'postgres_default': {
        'conn_type': 'postgres',
        'host': 'localhost',
        'schema': 'activelog',
        'login': 'postgres',
        'password': 'postgres',
        'port': 5432
    },
    
    'mysql_default': {
        'conn_type': 'mysql',
        'host': 'localhost',
        'schema': 'activelog',
        'login': 'mysql',
        'password': 'mysql',
        'port': 3306
    },
    
    'redis_default': {
        'conn_type': 'redis',
        'host': 'localhost',
        'port': 6379,
        'extra': '{"db": 0}'
    },
    
    'mongodb_default': {
        'conn_type': 'mongo',
        'host': 'localhost',
        'port': 27017,
        'schema': 'activelog',
        'login': 'mongo',
        'password': 'mongo'
    },
    
    'elasticsearch_default': {
        'conn_type': 'elasticsearch',
        'host': 'localhost',
        'port': 9200,
        'extra': '{"http_auth": ["elastic", "elastic"]}'
    },
    
    'kafka_default': {
        'conn_type': 'kafka',
        'host': 'localhost',
        'port': 9092,
        'extra': '{"bootstrap.servers": "localhost:9092"}'
    },
    
    'minio_default': {
        'conn_type': 'aws',
        'host': 'localhost:9000',
        'login': 'minioadmin',
        'password': 'minioadmin',
        'extra': '{"endpoint_url": "http://localhost:9000", "aws_access_key_id": "minioadmin", "aws_secret_access_key": "minioadmin"}'
    },
    
    'http_api_default': {
        'conn_type': 'http',
        'host': 'localhost',
        'port': 8080,
        'extra': '{"timeout": 30}'
    }
}

# Task pools configuration
TASK_POOLS = {
    'db_pool': {
        'description': 'Pool for database operations',
        'slots': 10
    },
    'api_pool': {
        'description': 'Pool for API calls',
        'slots': 20
    },
    'heavy_computation_pool': {
        'description': 'Pool for heavy computation tasks',
        'slots': 5
    },
    'file_processing_pool': {
        'description': 'Pool for file processing tasks',
        'slots': 15
    },
    'stream_processing_pool': {
        'description': 'Pool for stream processing tasks',
        'slots': 8
    }
}

# Variables configuration
AIRFLOW_VARIABLES = {
    'etl_data_path': '/data/etl',
    'backup_path': '/data/backup',
    'temp_path': '/tmp/etl',
    'max_file_size': '1GB',
    'batch_size': '10000',
    'parallel_workers': '4',
    'data_retention_days': '90',
    'error_threshold': '0.05',
    'notification_email': 'admin@activelog.com',
    'monitoring_enabled': 'true',
    'debug_mode': 'false'
}

def get_airflow_config() -> Dict[str, Any]:
    """Get Airflow configuration dictionary"""
    return AIRFLOW_CONFIG

def get_default_dag_args() -> Dict[str, Any]:
    """Get default DAG arguments"""
    return DEFAULT_DAG_ARGS.copy()

def get_data_source_connections() -> Dict[str, Dict[str, Any]]:
    """Get data source connections configuration"""
    return DATA_SOURCE_CONNECTIONS

def get_task_pools() -> Dict[str, Dict[str, Any]]:
    """Get task pools configuration"""
    return TASK_POOLS

def get_airflow_variables() -> Dict[str, str]:
    """Get Airflow variables configuration"""
    return AIRFLOW_VARIABLES

def setup_airflow_environment():
    """Setup Airflow environment with required directories and configurations"""
    import os
    
    # Create required directories
    directories = [
        '/home/activeloguser/activelog/services/etl-pipeline/dags',
        '/home/activeloguser/activelog/services/etl-pipeline/plugins',
        '/home/activeloguser/activelog/services/etl-pipeline/logs',
        '/home/activeloguser/activelog/services/etl-pipeline/logs/scheduler',
        '/home/activeloguser/activelog/services/etl-pipeline/config',
        '/data/etl',
        '/data/backup',
        '/tmp/etl'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Set environment variables
    os.environ.update({
        'AIRFLOW_HOME': '/home/activeloguser/activelog/services/etl-pipeline',
        'AIRFLOW__CORE__DAGS_FOLDER': '/home/activeloguser/activelog/services/etl-pipeline/dags',
        'AIRFLOW__CORE__PLUGINS_FOLDER': '/home/activeloguser/activelog/services/etl-pipeline/plugins',
        'AIRFLOW__CORE__BASE_LOG_FOLDER': '/home/activeloguser/activelog/services/etl-pipeline/logs',
        'AIRFLOW__CORE__SQL_ALCHEMY_CONN': 'postgresql://airflow:airflow@localhost:5432/airflow',
        'AIRFLOW__CORE__EXECUTOR': 'LocalExecutor',
        'AIRFLOW__WEBSERVER__EXPOSE_CONFIG': 'True',
        'AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL': '30',
        'AIRFLOW__CORE__LOAD_EXAMPLES': 'False'
    })
    
    logger.info("Airflow environment setup completed")

class AirflowDagBuilder:
    """Helper class for building Airflow DAGs with common patterns"""
    
    @staticmethod
    def create_data_pipeline_dag(
        dag_id: str,
        description: str,
        schedule_interval: str,
        source_configs: List[Dict[str, Any]],
        transformation_configs: List[Dict[str, Any]],
        destination_configs: List[Dict[str, Any]],
        dag_args: Dict[str, Any] = None
    ):
        """Create a standard data pipeline DAG"""
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        from airflow.operators.bash import BashOperator
        from airflow.utils.task_group import TaskGroup
        
        dag_args = dag_args or get_default_dag_args()
        
        dag = DAG(
            dag_id=dag_id,
            description=description,
            schedule_interval=schedule_interval,
            default_args=dag_args,
            catchup=False,
            tags=['etl', 'data-pipeline', 'auto-generated']
        )
        
        return dag
    
    @staticmethod
    def create_monitoring_tasks(dag):
        """Add monitoring tasks to a DAG"""
        from airflow.operators.python import PythonOperator
        from airflow.utils.task_group import TaskGroup
        
        with TaskGroup('monitoring', dag=dag) as monitoring_group:
            data_quality_check = PythonOperator(
                task_id='data_quality_check',
                python_callable=lambda: print("Data quality check"),
                dag=dag
            )
            
            lineage_tracking = PythonOperator(
                task_id='lineage_tracking',
                python_callable=lambda: print("Lineage tracking"),
                dag=dag
            )
            
            metrics_collection = PythonOperator(
                task_id='metrics_collection',
                python_callable=lambda: print("Metrics collection"),
                dag=dag
            )
            
            data_quality_check >> [lineage_tracking, metrics_collection]
        
        return monitoring_group

if __name__ == "__main__":
    setup_airflow_environment()
    print("Airflow configuration setup completed")