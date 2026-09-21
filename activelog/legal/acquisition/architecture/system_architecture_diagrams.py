#!/usr/bin/env python3
"""
System Architecture Diagram Generator
ActiveLog Technologies Platform Architecture Visualization

Usage: python system_architecture_diagrams.py
Generates architecture diagrams in ASCII and Mermaid formats
"""

import json
from datetime import datetime

class ArchitectureDiagramGenerator:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def generate_high_level_architecture(self):
        """Generate high-level system architecture diagram"""
        return {
            "title": "ActiveLog Technologies - High-Level System Architecture",
            "mermaid": """
graph TB
    subgraph "Client Layer"
        WEB[Web Application]
        MOBILE[Mobile Apps]
        API_CLIENT[Third-party APIs]
    end
    
    subgraph "Edge Layer"
        CDN[CloudFront CDN]
        WAF[Web Application Firewall]
        LB[Application Load Balancer]
    end
    
    subgraph "API Gateway Layer"
        GATEWAY[Kong API Gateway]
        AUTH[Authentication Service]
        RATE[Rate Limiting]
    end
    
    subgraph "Microservices Mesh"
        CORE[Core Services]
        AI[AI/ML Services] 
        INFRA[Infrastructure Services]
        ISTIO[Istio Service Mesh]
    end
    
    subgraph "Data Layer"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis Cache)]
        ELASTIC[(Elasticsearch)]
        S3[(S3 Storage)]
    end
    
    subgraph "External Services"
        TWILIO[Twilio]
        STRIPE[Stripe]
        AWS_AI[AWS AI Services]
        THIRD_PARTY[Third-party APIs]
    end
    
    WEB --> CDN
    MOBILE --> LB
    API_CLIENT --> GATEWAY
    
    CDN --> WAF
    WAF --> LB
    LB --> GATEWAY
    
    GATEWAY --> AUTH
    GATEWAY --> RATE
    GATEWAY --> ISTIO
    
    ISTIO --> CORE
    ISTIO --> AI
    ISTIO --> INFRA
    
    CORE --> POSTGRES
    CORE --> REDIS
    AI --> ELASTIC
    INFRA --> S3
    
    AI --> AWS_AI
    CORE --> TWILIO
    CORE --> STRIPE
    ISTIO --> THIRD_PARTY
""",
            "components": {
                "client_layer": ["Web App (React/Next.js)", "Mobile Apps (React Native)", "API Clients"],
                "edge_layer": ["CloudFront CDN", "AWS WAF", "Application Load Balancer"],
                "gateway_layer": ["Kong API Gateway", "OAuth 2.0 Auth", "Rate Limiting"],
                "services_layer": ["12 Core Services", "8 AI/ML Services", "6 Infrastructure Services"],
                "data_layer": ["PostgreSQL Clusters", "Redis Cache", "Elasticsearch", "S3 Storage"],
                "external_services": ["Twilio VoIP", "Stripe Billing", "AWS AI/ML", "Partner APIs"]
            }
        }
    
    def generate_microservices_architecture(self):
        """Generate detailed microservices architecture"""
        return {
            "title": "ActiveLog Technologies - Microservices Architecture",
            "mermaid": """
graph LR
    subgraph "Core Business Services"
        AUTH[Auth Service]
        USER[User Management]
        RECEPT[AI Receptionist]
        PHONE[Phone System]
        APPT[Appointment Service]
        DOC[Document AI]
        BILLING[Billing Service]
        NOTIF[Notification Service]
    end
    
    subgraph "AI/ML Services"
        NLP[NLP Engine]
        SPEECH[Speech Processing]
        SENTIMENT[Sentiment Analysis]
        PREDICT[Predictive Analytics]
        RECOMMEND[Recommendation Engine]
        MODEL_MGT[Model Management]
    end
    
    subgraph "Infrastructure Services"
        LOGGING[Logging Service]
        METRICS[Metrics Collector]
        HEALTH[Health Checker]
        CONFIG[Configuration Mgmt]
        BACKUP[Backup Service]
        SECURITY[Security Scanner]
    end
    
    subgraph "Data Stores"
        DB_USER[(User Database)]
        DB_CONV[(Conversation DB)]
        DB_AI[(AI Training DB)]
        CACHE[(Redis Cache)]
        SEARCH[(Search Index)]
        FILES[(File Storage)]
    end
    
    AUTH --> DB_USER
    USER --> DB_USER
    RECEPT --> DB_CONV
    PHONE --> DB_CONV
    APPT --> DB_USER
    DOC --> FILES
    BILLING --> DB_USER
    
    NLP --> DB_AI
    SPEECH --> DB_AI
    SENTIMENT --> DB_CONV
    PREDICT --> DB_AI
    RECOMMEND --> DB_USER
    MODEL_MGT --> DB_AI
    
    LOGGING --> SEARCH
    METRICS --> DB_AI
    HEALTH --> CACHE
    CONFIG --> CACHE
    BACKUP --> FILES
    SECURITY --> SEARCH
""",
            "service_details": {
                "auth_service": {
                    "tech_stack": "Python/FastAPI",
                    "database": "PostgreSQL",
                    "cache": "Redis",
                    "features": ["OAuth 2.0", "JWT Tokens", "MFA", "Session Management"]
                },
                "ai_receptionist": {
                    "tech_stack": "Python/FastAPI + TensorFlow",
                    "database": "PostgreSQL + Elasticsearch", 
                    "features": ["NLP Processing", "Intent Recognition", "Response Generation", "Context Management"]
                },
                "phone_system": {
                    "tech_stack": "Node.js + WebRTC",
                    "integrations": "Twilio, FreeSWITCH",
                    "features": ["VoIP Calling", "Call Routing", "IVR", "Recording"]
                }
            }
        }
    
    def generate_data_architecture(self):
        """Generate data architecture diagram"""
        return {
            "title": "ActiveLog Technologies - Data Architecture",
            "mermaid": """
graph TB
    subgraph "Data Sources"
        APPS[Applications]
        APIS[External APIs]
        FILES[File Uploads]
        VOICE[Voice Data]
    end
    
    subgraph "Data Ingestion"
        KAFKA[Apache Kafka]
        ETL[ETL Pipelines]
        STREAM[Stream Processing]
        BATCH[Batch Processing]
    end
    
    subgraph "Data Storage"
        OLTP[(OLTP Database)]
        OLAP[(Data Warehouse)]
        CACHE[(Cache Layer)]
        LAKE[(Data Lake)]
        SEARCH[(Search Index)]
    end
    
    subgraph "Data Processing"
        ML_PIPELINE[ML Pipelines]
        ANALYTICS[Analytics Engine]
        REPORTS[Report Generator]
        AI_TRAINING[AI Training]
    end
    
    subgraph "Data Access"
        API_LAYER[Data APIs]
        DASHBOARD[Analytics Dashboard]
        BI_TOOLS[BI Tools]
        ML_SERVE[ML Model Serving]
    end
    
    APPS --> KAFKA
    APIS --> ETL
    FILES --> BATCH
    VOICE --> STREAM
    
    KAFKA --> OLTP
    ETL --> OLAP
    STREAM --> CACHE
    BATCH --> LAKE
    
    OLTP --> SEARCH
    OLAP --> ANALYTICS
    CACHE --> ML_PIPELINE
    LAKE --> AI_TRAINING
    
    ML_PIPELINE --> ML_SERVE
    ANALYTICS --> REPORTS
    REPORTS --> DASHBOARD
    AI_TRAINING --> ML_SERVE
    
    API_LAYER --> OLTP
    DASHBOARD --> OLAP
    BI_TOOLS --> OLAP
    ML_SERVE --> API_LAYER
""",
            "data_flows": {
                "real_time": ["User interactions", "Voice processing", "Chat messages"],
                "batch": ["Log processing", "Model training", "Report generation"],
                "streaming": ["Event processing", "Metrics collection", "Alert generation"]
            }
        }
    
    def generate_security_architecture(self):
        """Generate security architecture diagram"""
        return {
            "title": "ActiveLog Technologies - Security Architecture",
            "mermaid": """
graph TB
    subgraph "Perimeter Security"
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
        VPN[VPN Gateway]
    end
    
    subgraph "Network Security"
        VPC[Virtual Private Cloud]
        PRIVATE[Private Subnets]
        PUBLIC[Public Subnets]
        NAT[NAT Gateway]
        SG[Security Groups]
    end
    
    subgraph "Application Security"
        OAUTH[OAuth 2.0]
        JWT[JWT Tokens]
        MFA[Multi-Factor Auth]
        RBAC[Role-Based Access]
        ENCRYPT[Encryption Layer]
    end
    
    subgraph "Data Security"
        FIELD_ENCRYPT[Field-Level Encryption]
        TDE[Transparent Data Encryption]
        KMS[Key Management Service]
        HSM[Hardware Security Module]
    end
    
    subgraph "Infrastructure Security"
        IAM[Identity & Access Management]
        SECRETS[Secrets Manager]
        AUDIT[Audit Logging]
        MONITOR[Security Monitoring]
        SCAN[Vulnerability Scanning]
    end
    
    subgraph "Compliance & Governance"
        SOC2[SOC 2 Type II]
        GDPR[GDPR Compliance]
        HIPAA[HIPAA Ready]
        PCI[PCI DSS Level 1]
    end
    
    WAF --> VPC
    DDoS --> PUBLIC
    VPN --> PRIVATE
    
    PUBLIC --> SG
    PRIVATE --> NAT
    SG --> OAUTH
    
    OAUTH --> JWT
    JWT --> MFA
    MFA --> RBAC
    RBAC --> ENCRYPT
    
    ENCRYPT --> FIELD_ENCRYPT
    FIELD_ENCRYPT --> TDE
    TDE --> KMS
    KMS --> HSM
    
    IAM --> SECRETS
    SECRETS --> AUDIT
    AUDIT --> MONITOR
    MONITOR --> SCAN
    
    OAUTH --> SOC2
    ENCRYPT --> GDPR
    FIELD_ENCRYPT --> HIPAA
    TDE --> PCI
""",
            "security_layers": {
                "network": ["VPC isolation", "Security groups", "NACLs", "Private subnets"],
                "application": ["OAuth 2.0", "JWT tokens", "MFA", "RBAC", "Input validation"],
                "data": ["Field encryption", "TDE", "KMS", "Backup encryption"],
                "infrastructure": ["IAM", "Secrets management", "Audit trails", "Monitoring"]
            }
        }
    
    def generate_deployment_architecture(self):
        """Generate deployment and infrastructure architecture"""
        return {
            "title": "ActiveLog Technologies - Deployment Architecture",
            "mermaid": """
graph TB
    subgraph "Production Environment"
        subgraph "US-East-1 (Primary)"
            EKS1[EKS Cluster Primary]
            RDS1[(RDS Multi-AZ)]
            REDIS1[(ElastiCache Cluster)]
            S31[(S3 Primary)]
        end
        
        subgraph "US-West-2 (DR)"
            EKS2[EKS Cluster DR]
            RDS2[(RDS Read Replica)]
            REDIS2[(ElastiCache Replica)]
            S32[(S3 Cross-Region)]
        end
    end
    
    subgraph "Staging Environment"
        EKS_STAGE[EKS Staging]
        RDS_STAGE[(RDS Staging)]
        REDIS_STAGE[(ElastiCache Staging)]
    end
    
    subgraph "Development Environment"
        LOCAL[Local Development]
        DOCKER[Docker Compose]
        K8S_DEV[Minikube/Kind]
    end
    
    subgraph "CI/CD Pipeline"
        GITHUB[GitHub Repository]
        ACTIONS[GitHub Actions]
        REGISTRY[Container Registry]
        HELM[Helm Charts]
        ARGO[ArgoCD]
    end
    
    subgraph "Monitoring & Observability"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        JAEGER[Jaeger Tracing]
        ELK[ELK Stack]
        ALERTS[AlertManager]
    end
    
    GITHUB --> ACTIONS
    ACTIONS --> REGISTRY
    REGISTRY --> HELM
    HELM --> ARGO
    
    ARGO --> EKS_STAGE
    ARGO --> EKS1
    ARGO --> EKS2
    
    EKS1 --> RDS1
    EKS1 --> REDIS1
    EKS1 --> S31
    
    EKS2 --> RDS2
    EKS2 --> REDIS2
    EKS2 --> S32
    
    RDS1 --> RDS2
    REDIS1 --> REDIS2
    S31 --> S32
    
    EKS1 --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    EKS1 --> JAEGER
    EKS1 --> ELK
    PROMETHEUS --> ALERTS
""",
            "environments": {
                "production": {
                    "clusters": 2,
                    "regions": ["us-east-1", "us-west-2"],
                    "nodes": "10-50 auto-scaling",
                    "databases": "Multi-AZ with read replicas",
                    "uptime_sla": "99.9%"
                },
                "staging": {
                    "purpose": "Pre-production testing",
                    "resources": "50% of production",
                    "data": "Sanitized production data"
                },
                "development": {
                    "local": "Docker compose",
                    "shared": "Kubernetes dev cluster",
                    "data": "Synthetic test data"
                }
            }
        }
    
    def generate_integration_architecture(self):
        """Generate integration architecture diagram"""
        return {
            "title": "ActiveLog Technologies - Integration Architecture",
            "mermaid": """
graph LR
    subgraph "ActiveLog Platform"
        API_GW[API Gateway]
        WEBHOOK[Webhook Handler]
        QUEUE[Message Queue]
        INTEGRATOR[Integration Service]
    end
    
    subgraph "CRM Systems"
        SALESFORCE[Salesforce]
        HUBSPOT[HubSpot]
        PIPEDRIVE[Pipedrive]
    end
    
    subgraph "Communication"
        TWILIO[Twilio]
        SLACK[Slack]
        TEAMS[Microsoft Teams]
        ZOOM[Zoom]
    end
    
    subgraph "Business Tools"
        GOOGLE[Google Workspace]
        OFFICE365[Office 365]
        CALENDAR[Calendar APIs]
    end
    
    subgraph "Payment & Billing"
        STRIPE[Stripe]
        PAYPAL[PayPal]
        CHARGEBEE[Chargebee]
    end
    
    subgraph "AI & Analytics"
        OPENAI[OpenAI]
        AWS_AI[AWS AI Services]
        ANALYTICS[Analytics APIs]
    end
    
    API_GW <--> SALESFORCE
    API_GW <--> HUBSPOT
    API_GW <--> PIPEDRIVE
    
    WEBHOOK <--> TWILIO
    WEBHOOK <--> SLACK
    WEBHOOK <--> TEAMS
    WEBHOOK <--> ZOOM
    
    INTEGRATOR <--> GOOGLE
    INTEGRATOR <--> OFFICE365
    INTEGRATOR <--> CALENDAR
    
    QUEUE --> STRIPE
    QUEUE --> PAYPAL
    QUEUE --> CHARGEBEE
    
    API_GW --> OPENAI
    API_GW --> AWS_AI
    INTEGRATOR --> ANALYTICS
""",
            "integration_patterns": {
                "real_time": ["Webhooks", "WebSockets", "Server-sent events"],
                "batch": ["Scheduled jobs", "Bulk API calls", "File transfers"],
                "event_driven": ["Message queues", "Event streaming", "Pub/sub"]
            }
        }
    
    def generate_ascii_overview(self):
        """Generate ASCII art overview of the system"""
        return """
╭─────────────────────────────────────────────────────────────────────────────╮
│                    ActiveLog Technologies Platform                          │
│                          System Architecture                               │
╰─────────────────────────────────────────────────────────────────────────────╯

┌─ Client Layer ─────────────────────────────────────────────────────────────┐
│  [Web App]  [Mobile Apps]  [API Clients]  [Third-party Integrations]     │
└────────────────────────┬───────────────────────────────────────────────────┘
                         │
┌─ Edge & Gateway ───────▼───────────────────────────────────────────────────┐
│  [CloudFront CDN] → [WAF] → [Load Balancer] → [Kong API Gateway]          │
└────────────────────────┬───────────────────────────────────────────────────┘
                         │
┌─ Microservices Mesh ───▼───────────────────────────────────────────────────┐
│  ┌─ Core Services ────┐  ┌─ AI/ML Services ──┐  ┌─ Infrastructure ────┐    │
│  │ • Auth Service     │  │ • NLP Engine       │  │ • Logging Service   │    │
│  │ • User Management  │  │ • Speech Processing│  │ • Metrics Collector │    │
│  │ • AI Receptionist  │  │ • Sentiment Analysis│ │ • Health Checker    │    │
│  │ • Phone System     │  │ • Predictive AI    │  │ • Config Management │    │
│  │ • Appointments     │  │ • Recommendation   │  │ • Backup Service    │    │
│  │ • Document AI      │  │ • Model Management │  │ • Security Scanner  │    │
│  │ • Analytics        │  │                    │  │                     │    │
│  │ • Notifications    │  │                    │  │                     │    │
│  │ • File Processing  │  │                    │  │                     │    │
│  │ • Integration Hub  │  │                    │  │                     │    │
│  │ • Billing Service  │  │                    │  │                     │    │
│  │ • Admin Portal     │  │                    │  │                     │    │
│  └────────────────────┘  └────────────────────┘  └─────────────────────┘    │
└────────────────────────┬───────────────────────────────────────────────────┘
                         │
┌─ Data Layer ───────────▼───────────────────────────────────────────────────┐
│  [PostgreSQL]  [Redis Cache]  [Elasticsearch]  [S3 Storage]              │
│       │             │              │               │                       │
│   User Data    Session Cache   Search Index    File Storage               │
│  Conversations    API Cache     Log Analysis    Documents                  │
│   AI Training    Real-time      Metrics        Backups                     │
│                   Data                                                     │
└────────────────────────────────────────────────────────────────────────────┘

┌─ External Services ────────────────────────────────────────────────────────┐
│  [Twilio VoIP]  [Stripe Billing]  [AWS AI/ML]  [Partner APIs]            │
└────────────────────────────────────────────────────────────────────────────┘

Key Metrics:
• 47 Microservices          • 99.97% Uptime
• 1.2M Requests/Day         • <200ms P95 Response Time  
• 127 Database Tables       • 94.2% Cache Hit Rate
• 2.4TB Production Data     • 87.3% Code Coverage

Security: SOC 2 Type II | GDPR | HIPAA Ready | PCI DSS Level 1
Infrastructure: AWS Multi-AZ | Kubernetes | Auto-scaling | Blue-green Deployment
"""
    
    def generate_all_diagrams(self):
        """Generate all architecture diagrams"""
        diagrams = {
            "metadata": {
                "generated_at": self.timestamp,
                "version": "2.4",
                "company": "ActiveLog Technologies, Inc."
            },
            "high_level_architecture": self.generate_high_level_architecture(),
            "microservices_architecture": self.generate_microservices_architecture(),
            "data_architecture": self.generate_data_architecture(),
            "security_architecture": self.generate_security_architecture(),
            "deployment_architecture": self.generate_deployment_architecture(),
            "integration_architecture": self.generate_integration_architecture(),
            "ascii_overview": self.generate_ascii_overview()
        }
        
        return diagrams

def main():
    """Generate and save all architecture diagrams"""
    generator = ArchitectureDiagramGenerator()
    diagrams = generator.generate_all_diagrams()
    
    # Save to JSON file
    with open('architecture_diagrams.json', 'w') as f:
        json.dump(diagrams, f, indent=2)
    
    print(f"Architecture diagrams generated at {generator.timestamp}")
    print("\nAvailable diagrams:")
    for key in diagrams.keys():
        if key != "metadata":
            print(f"  - {key}")
    
    # Display ASCII overview
    print("\n" + "="*80)
    print(diagrams["ascii_overview"])
    print("="*80)
    
    return diagrams

if __name__ == "__main__":
    main()