# Data Flow Architecture

This document describes how data flows through the ActiveLog system, including ingestion, processing, storage, and retrieval patterns.

## File Upload and Processing Flow

```mermaid
flowchart TD
    USER[User Client] --> CDN[CDN/Upload Endpoint]
    CDN --> S3[File Storage<br/>S3/MinIO]
    
    S3 --> WATCHER[File Watcher<br/>Event Trigger]
    WATCHER --> QUEUE1[Processing Queue]
    
    QUEUE1 --> META_EXTRACT[Metadata Extraction]
    QUEUE1 --> THUMB[Thumbnail Generation]
    QUEUE1 --> VIRUS[Virus Scanning]
    
    META_EXTRACT --> META_DB[(Metadata DB)]
    META_EXTRACT --> SEARCH[Search Index]
    META_EXTRACT --> VECTOR[Vector Database]
    
    THUMB --> S3
    VIRUS --> QUARANTINE{Virus Found?}
    
    QUARANTINE -->|Clean| PROCESS_QUEUE[AI Processing Queue]
    QUARANTINE -->|Infected| ALERT[Security Alert]
    
    PROCESS_QUEUE --> DOC_AI[Document AI]
    PROCESS_QUEUE --> VIDEO_AI[Video Processing]
    PROCESS_QUEUE --> IMAGE_AI[Image Analysis]
    
    DOC_AI --> FEATURES[Feature Extraction]
    VIDEO_AI --> TRANSCRIPTION[Video Transcription]
    IMAGE_AI --> RECOGNITION[Object Recognition]
    
    FEATURES --> VECTOR
    TRANSCRIPTION --> SEARCH
    RECOGNITION --> META_DB
    
    VECTOR --> SMART[Smart Folder<br/>Classification]
    SMART --> COLLAB[Collaboration<br/>Notifications]
    
    COLLAB --> NOTIF[Notification Service]
    NOTIF --> WEBSOCKET[WebSocket]
    NOTIF --> EMAIL[Email Service]
    NOTIF --> PUSH[Push Notifications]
    
    WEBSOCKET --> USER
    EMAIL --> USER
    PUSH --> USER

    %% Styling
    classDef storage fill:#E1F5FE,stroke:#01579B
    classDef processing fill:#FFF3E0,stroke:#E65100
    classDef ai fill:#F3E5F5,stroke:#4A148C
    classDef notification fill:#E8F5E8,stroke:#1B5E20
    classDef user fill:#FFEBEE,stroke:#C62828

    class S3,META_DB,SEARCH,VECTOR storage
    class META_EXTRACT,THUMB,VIRUS,FEATURES,TRANSCRIPTION,RECOGNITION processing
    class DOC_AI,VIDEO_AI,IMAGE_AI,SMART ai
    class NOTIF,WEBSOCKET,EMAIL,PUSH notification
    class USER,CDN user
```

## Search and Retrieval Flow

```mermaid
flowchart TD
    SEARCH_REQ[Search Request] --> GATEWAY[API Gateway]
    GATEWAY --> AUTH[Authentication]
    AUTH --> METADATA[Metadata Service]
    
    METADATA --> QUERY_PARSER[Query Parser]
    QUERY_PARSER --> SEARCH_TYPE{Search Type?}
    
    SEARCH_TYPE -->|Text Search| ELASTIC[Elasticsearch<br/>Full-text Search]
    SEARCH_TYPE -->|Semantic Search| VECTOR_SEARCH[Vector Database<br/>Similarity Search]
    SEARCH_TYPE -->|Filter Search| SQL_SEARCH[PostgreSQL<br/>Structured Query]
    
    ELASTIC --> RESULTS1[Text Results]
    VECTOR_SEARCH --> RESULTS2[Semantic Results]
    SQL_SEARCH --> RESULTS3[Filtered Results]
    
    RESULTS1 --> MERGER[Result Merger<br/>& Ranker]
    RESULTS2 --> MERGER
    RESULTS3 --> MERGER
    
    MERGER --> PERMISSION[Permission Filter]
    PERMISSION --> CACHE{Cache Hit?}
    
    CACHE -->|Hit| CACHE_RETURN[Return Cached]
    CACHE -->|Miss| ENRICHER[Result Enricher]
    
    ENRICHER --> FILE_META[File Metadata]
    ENRICHER --> PREVIEW[Preview Generation]
    ENRICHER --> RELATED[Related Documents]
    
    FILE_META --> FINAL_RESULTS[Final Results]
    PREVIEW --> FINAL_RESULTS
    RELATED --> FINAL_RESULTS
    
    FINAL_RESULTS --> RESPONSE_CACHE[Update Cache]
    FINAL_RESULTS --> CLIENT[Return to Client]
    
    CACHE_RETURN --> CLIENT
    RESPONSE_CACHE --> CLIENT

    %% Analytics tracking
    CLIENT --> ANALYTICS[Analytics Tracking]
    ANALYTICS --> METRICS_DB[(Metrics Database)]
```

## Real-time Collaboration Flow

```mermaid
sequenceDiagram
    participant User1
    participant WebSocket1
    participant CollabService
    participant CRDT
    participant Database
    participant WebSocket2
    participant User2

    User1->>WebSocket1: Edit Document
    WebSocket1->>CollabService: Operation Delta
    CollabService->>CRDT: Apply Operation
    CRDT->>CRDT: Conflict Resolution
    CRDT->>Database: Persist Changes
    CollabService->>WebSocket2: Broadcast Delta
    WebSocket2->>User2: Live Update
    
    Note over User1, User2: Concurrent Editing
    
    User2->>WebSocket2: Simultaneous Edit
    WebSocket2->>CollabService: Operation Delta
    CollabService->>CRDT: Apply Operation
    CRDT->>CRDT: Merge Conflicting Ops
    CRDT->>Database: Persist Merged State
    CollabService->>WebSocket1: Broadcast Merged Delta
    WebSocket1->>User1: Conflict Resolution
```

## Data Synchronization Flow

```mermaid
flowchart TD
    subgraph "Device A"
        LOCAL_A[Local Storage]
        SYNC_A[Sync Agent]
        APP_A[ActiveLog App]
    end
    
    subgraph "Cloud Infrastructure"
        SYNC_SERVICE[Sync Service]
        CONFLICT_RESOLVER[Conflict Resolver]
        MERGE_ENGINE[3-Way Merge]
        CLOUD_STORAGE[(Cloud Storage)]
        VERSION_CONTROL[Version Control]
    end
    
    subgraph "Device B" 
        LOCAL_B[Local Storage]
        SYNC_B[Sync Agent]
        APP_B[ActiveLog App]
    end
    
    APP_A --> LOCAL_A
    LOCAL_A --> SYNC_A
    SYNC_A -->|Push Changes| SYNC_SERVICE
    
    SYNC_SERVICE --> CONFLICT_RESOLVER
    CONFLICT_RESOLVER -->|Conflict Detected| MERGE_ENGINE
    CONFLICT_RESOLVER -->|No Conflict| CLOUD_STORAGE
    
    MERGE_ENGINE -->|Auto-Resolve| CLOUD_STORAGE
    MERGE_ENGINE -->|Manual Required| VERSION_CONTROL
    
    CLOUD_STORAGE --> VERSION_CONTROL
    VERSION_CONTROL -->|Pull Changes| SYNC_B
    
    SYNC_B --> LOCAL_B
    LOCAL_B --> APP_B
    
    SYNC_SERVICE -->|Notify| SYNC_A
    SYNC_SERVICE -->|Notify| SYNC_B
```

## ML Pipeline Data Flow

```mermaid
flowchart TD
    RAW_DATA[Raw Data<br/>Files/Docs/Images] --> INGESTION[Data Ingestion]
    INGESTION --> PREPROCESSING[Data Preprocessing]
    
    PREPROCESSING --> FEATURE_EXTRACTION[Feature Extraction]
    FEATURE_EXTRACTION --> FEATURE_STORE[(Feature Store)]
    
    FEATURE_STORE --> TRAINING[Model Training]
    TRAINING --> MODEL_VALIDATION[Model Validation]
    MODEL_VALIDATION --> MODEL_REGISTRY[(Model Registry)]
    
    MODEL_REGISTRY --> DEPLOYMENT[Model Deployment]
    DEPLOYMENT --> INFERENCE_ENDPOINT[Inference API]
    
    INFERENCE_ENDPOINT --> PREDICTION[Predictions]
    PREDICTION --> FEEDBACK[Feedback Loop]
    FEEDBACK --> FEATURE_STORE
    
    subgraph "Model Monitoring"
        DRIFT_DETECTION[Data Drift Detection]
        PERFORMANCE_MONITOR[Performance Monitor]
        ALERT_SYSTEM[Alert System]
    end
    
    PREDICTION --> DRIFT_DETECTION
    PREDICTION --> PERFORMANCE_MONITOR
    PERFORMANCE_MONITOR --> ALERT_SYSTEM
    DRIFT_DETECTION --> ALERT_SYSTEM
    
    ALERT_SYSTEM --> RETRAINING[Model Retraining]
    RETRAINING --> TRAINING
```

## Analytics Data Pipeline

```mermaid
flowchart TD
    subgraph "Data Sources"
        APPS[Application Logs]
        APIS[API Access Logs] 
        EVENTS[User Events]
        SYSTEM[System Metrics]
    end
    
    subgraph "Ingestion Layer"
        KAFKA[Kafka Streams]
        FLUENTD[Fluentd Collectors]
    end
    
    subgraph "Processing Layer"
        SPARK[Apache Spark<br/>Batch Processing]
        STORM[Apache Storm<br/>Stream Processing]
    end
    
    subgraph "Storage Layer"
        WAREHOUSE[(Data Warehouse<br/>BigQuery/Redshift)]
        TIMESERIES[(Time Series DB<br/>InfluxDB)]
        OLAP[(OLAP Cube<br/>ClickHouse)]
    end
    
    subgraph "Analytics Layer"
        DASHBOARDS[Real-time Dashboards]
        REPORTS[Scheduled Reports] 
        ML_ANALYTICS[ML Analytics]
        ALERTS[Alert Engine]
    end
    
    APPS --> FLUENTD
    APIS --> KAFKA
    EVENTS --> KAFKA
    SYSTEM --> FLUENTD
    
    KAFKA --> STORM
    FLUENTD --> SPARK
    
    STORM --> TIMESERIES
    STORM --> OLAP
    SPARK --> WAREHOUSE
    
    TIMESERIES --> DASHBOARDS
    OLAP --> REPORTS
    WAREHOUSE --> ML_ANALYTICS
    WAREHOUSE --> ALERTS
    
    ML_ANALYTICS --> PREDICTIONS[Predictive Analytics]
    ALERTS --> NOTIFICATIONS[Alert Notifications]
```

## Backup and Recovery Flow

```mermaid
flowchart TD
    PRIMARY_DB[(Primary Database)] --> REPLICATION[(Read Replicas)]
    PRIMARY_DB --> WAL_SHIPPING[WAL Shipping]
    
    WAL_SHIPPING --> HOT_STANDBY[(Hot Standby)]
    
    subgraph "Backup Strategy"
        FULL_BACKUP[Full Backup<br/>Weekly]
        INCREMENTAL[Incremental<br/>Daily]
        CONTINUOUS[Continuous WAL<br/>Real-time]
    end
    
    PRIMARY_DB --> FULL_BACKUP
    PRIMARY_DB --> INCREMENTAL
    WAL_SHIPPING --> CONTINUOUS
    
    subgraph "Storage Tiers"
        HOT_STORAGE[Hot Storage<br/>SSD/NVMe]
        WARM_STORAGE[Warm Storage<br/>Standard HDD]
        COLD_STORAGE[Cold Storage<br/>Glacier/Archive]
    end
    
    FULL_BACKUP --> HOT_STORAGE
    INCREMENTAL --> WARM_STORAGE
    CONTINUOUS --> HOT_STORAGE
    
    HOT_STORAGE -->|30 days| WARM_STORAGE
    WARM_STORAGE -->|90 days| COLD_STORAGE
    
    subgraph "Recovery Scenarios"
        POINT_IN_TIME[Point-in-Time Recovery]
        DISASTER_RECOVERY[Disaster Recovery]
        CROSS_REGION[Cross-Region Restore]
    end
    
    HOT_STORAGE --> POINT_IN_TIME
    HOT_STANDBY --> DISASTER_RECOVERY
    COLD_STORAGE --> CROSS_REGION
```

## Data Governance Flow

```mermaid
flowchart TD
    DATA_INGESTION[Data Ingestion] --> CLASSIFICATION[Data Classification]
    CLASSIFICATION --> PII_DETECTION[PII Detection]
    PII_DETECTION --> ENCRYPTION[Encryption at Rest]
    
    ENCRYPTION --> ACCESS_CONTROL[Access Control]
    ACCESS_CONTROL --> AUDIT_LOG[Audit Logging]
    
    subgraph "Data Lifecycle"
        RETENTION[Retention Policy]
        ARCHIVAL[Data Archival]
        DELETION[Secure Deletion]
    end
    
    AUDIT_LOG --> RETENTION
    RETENTION --> ARCHIVAL
    ARCHIVAL --> DELETION
    
    subgraph "Compliance"
        GDPR[GDPR Compliance]
        HIPAA[HIPAA Compliance]
        SOX[SOX Compliance]
    end
    
    ACCESS_CONTROL --> GDPR
    ENCRYPTION --> HIPAA
    AUDIT_LOG --> SOX
    
    subgraph "Data Quality"
        VALIDATION[Data Validation]
        PROFILING[Data Profiling] 
        LINEAGE[Data Lineage]
    end
    
    DATA_INGESTION --> VALIDATION
    CLASSIFICATION --> PROFILING
    AUDIT_LOG --> LINEAGE
```

## Performance Optimization Patterns

### Caching Strategy
```mermaid
flowchart LR
    REQUEST[Request] --> L1[L1 Cache<br/>Application Memory]
    L1 -->|Miss| L2[L2 Cache<br/>Redis]
    L2 -->|Miss| L3[L3 Cache<br/>CDN]
    L3 -->|Miss| DATABASE[(Database)]
    
    DATABASE --> L3
    L3 --> L2
    L2 --> L1
    L1 --> RESPONSE[Response]
```

### Data Partitioning
```mermaid
graph TB
    QUERY[Query] --> ROUTER[Query Router]
    
    ROUTER --> SHARD1[(Shard 1<br/>Users A-F)]
    ROUTER --> SHARD2[(Shard 2<br/>Users G-M)]
    ROUTER --> SHARD3[(Shard 3<br/>Users N-S)]
    ROUTER --> SHARD4[(Shard 4<br/>Users T-Z)]
    
    SHARD1 --> AGGREGATOR[Result Aggregator]
    SHARD2 --> AGGREGATOR
    SHARD3 --> AGGREGATOR
    SHARD4 --> AGGREGATOR
    
    AGGREGATOR --> RESPONSE[Response]
```

## Error Handling and Circuit Breakers

```mermaid
stateDiagram-v2
    [*] --> Healthy
    Healthy --> Degraded: Error rate > 5%
    Degraded --> Healthy: Error rate < 1%
    Degraded --> Failing: Error rate > 20%
    Failing --> CircuitOpen: Consecutive failures > 10
    CircuitOpen --> HalfOpen: Timeout (30s)
    HalfOpen --> Healthy: Success
    HalfOpen --> CircuitOpen: Failure
    
    note right of Healthy
        Normal operation
        All requests processed
    end note
    
    note right of Degraded
        Increased latency
        Some retries
    end note
    
    note right of Failing
        High error rate
        Aggressive retries
    end note
    
    note right of CircuitOpen
        Fast failures
        No downstream calls
    end note
```