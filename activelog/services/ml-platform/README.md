# ML Platform

A comprehensive Machine Learning platform providing model registry, A/B testing, performance monitoring, automated retraining, feature store, explainability, drift detection, and governance capabilities.

## Features

- **Model Registry**: Version control and lifecycle management for ML models
- **A/B Testing**: Statistical testing framework for model comparisons
- **Performance Monitoring**: Real-time model performance tracking and alerting
- **Automated Retraining**: Scheduled and trigger-based model retraining pipelines
- **Feature Store**: Centralized feature management and serving
- **Model Explainability**: SHAP, LIME, and feature importance explanations
- **Drift Detection**: Data and concept drift monitoring
- **Model Governance**: Compliance, approval workflows, and audit trails

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python ml_platform_server.py
```

3. The API will be available at `http://localhost:8109`

## API Endpoints

### Model Registry
- `POST /models` - Register a new model
- `GET /models` - List all models
- `GET /models/{model_id}` - Get model details
- `POST /models/{model_id}/predict` - Make predictions

### A/B Testing
- `POST /experiments` - Create new experiment
- `POST /experiments/{experiment_id}/start` - Start experiment
- `POST /experiments/{experiment_id}/assign` - Assign variant to user

### Monitoring
- `GET /models/{model_id}/health` - Get model health status
- `GET /models/{model_id}/metrics` - Get performance metrics
- `GET /monitoring/alerts` - Get active alerts

### Feature Store
- `POST /feature-groups` - Create feature group
- `POST /feature-groups/{group_id}/ingest` - Ingest features
- `GET /features/online` - Get online features

### Governance
- `POST /models/{model_id}/governance/evaluate` - Evaluate compliance
- `POST /models/{model_id}/approval` - Request deployment approval

## Architecture

The platform is built with a modular architecture:

```
ml-platform/
├── registry/           # Model registry and versioning
├── testing/           # A/B testing framework
├── monitoring/        # Performance monitoring
├── pipelines/         # Retraining pipelines
├── feature_store/     # Feature management
├── explainability/    # Model explanations
├── drift/             # Drift detection
├── governance/        # Model governance
└── ml_platform_server.py  # Main API server
```

## Usage Examples

### Register a Model
```python
import requests

response = requests.post("http://localhost:8109/models", json={
    "name": "Credit Risk Model",
    "description": "Predicts loan default risk",
    "version": "1.0",
    "format": "sklearn"
})
```

### Create A/B Test
```python
response = requests.post("http://localhost:8109/experiments", json={
    "experiment_id": "credit_model_test",
    "name": "Credit Model A/B Test",
    "variants": [
        {
            "variant_id": "control",
            "name": "Current Model",
            "model_id": "credit_model_v1",
            "model_version": "1.0",
            "traffic_allocation": 0.5
        },
        {
            "variant_id": "treatment",
            "name": "New Model",
            "model_id": "credit_model_v2",
            "model_version": "1.0", 
            "traffic_allocation": 0.5
        }
    ],
    "success_metric": "conversion_rate"
})
```

### Monitor Model Health
```python
response = requests.get("http://localhost:8109/models/credit_model_v1/health")
health = response.json()
print(f"Model health: {health['health_status']}")
```

## Configuration

The platform uses SQLite by default for storage. To configure different database or settings, modify the initialization parameters in `ml_platform_server.py`.

## License

MIT License