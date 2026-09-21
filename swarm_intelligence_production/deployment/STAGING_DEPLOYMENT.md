# Staging Deployment Guide

## Overview

This guide walks you through deploying the Swarm Intelligence Platform to a staging environment for testing and validation before production deployment.

## Prerequisites

### Required Tools

```bash
# Install required tools
kubectl >= 1.28
helm >= 3.13
aws-cli >= 2.13 (or gcloud/az for other clouds)
terraform >= 1.6
docker >= 24.0
```

### Access Requirements

- AWS/GCP/Azure account with appropriate permissions
- kubectl access to staging cluster
- Docker registry access (GitHub Container Registry)
- Domain for staging (e.g., staging.swarm-intelligence.example.com)

## Step 1: Provision Staging Cluster

### AWS EKS

```bash
cd infrastructure/terraform/aws

# Initialize Terraform
terraform init

# Create staging cluster
terraform apply \
  -var="cluster_name=swarm-staging-eks" \
  -var="environment=staging" \
  -var="aws_region=us-east-1" \
  -var="node_instance_type=m6i.2xlarge" \
  -var="min_nodes=3" \
  -var="max_nodes=20" \
  -auto-approve

# Update kubeconfig
aws eks update-kubeconfig \
  --name swarm-staging-eks \
  --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

**Expected Output:**
```
Kubernetes control plane is running at https://XXX.eks.amazonaws.com
CoreDNS is running at https://XXX.eks.amazonaws.com/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

NAME                                          STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.us-east-1.compute.internal     Ready    <none>   5m    v1.28.0
ip-10-0-2-xxx.us-east-1.compute.internal     Ready    <none>   5m    v1.28.0
ip-10-0-3-xxx.us-east-1.compute.internal     Ready    <none>   5m    v1.28.0
```

### GCP GKE

```bash
cd infrastructure/terraform/gcp

# Set project
export GCP_PROJECT="your-project-id"
gcloud config set project $GCP_PROJECT

# Enable APIs
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com

# Deploy cluster
terraform apply \
  -var="project_id=$GCP_PROJECT" \
  -var="environment=staging" \
  -auto-approve

# Get credentials
gcloud container clusters get-credentials \
  swarm-staging-gke \
  --region us-central1

kubectl get nodes
```

### Azure AKS

```bash
cd infrastructure/terraform/azure

# Login
az login

# Deploy cluster
terraform apply \
  -var="environment=staging" \
  -auto-approve

# Get credentials
az aks get-credentials \
  --resource-group swarm-staging-rg \
  --name swarm-staging-aks

kubectl get nodes
```

## Step 2: Deploy Core Services

### Install Storage Class

```bash
kubectl apply -f infrastructure/kubernetes/storage-class.yaml
```

### Deploy PostgreSQL

```bash
# Create namespace
kubectl create namespace swarm-intelligence

# Deploy PostgreSQL
kubectl apply -f infrastructure/kubernetes/postgres-statefulset.yaml

# Wait for ready
kubectl wait --for=condition=ready pod -l app=postgres \
  -n swarm-intelligence --timeout=600s

# Verify
kubectl get pods -n swarm-intelligence -l app=postgres
```

**Expected Output:**
```
NAME         READY   STATUS    RESTARTS   AGE
postgres-0   1/1     Running   0          2m
```

### Deploy Redis

```bash
kubectl apply -f infrastructure/kubernetes/redis-statefulset.yaml

kubectl wait --for=condition=ready pod -l app=redis \
  -n swarm-intelligence --timeout=300s

# Test connection
kubectl exec -n swarm-intelligence redis-0 -- redis-cli ping
# Should output: PONG
```

### Deploy Kafka

```bash
kubectl apply -f infrastructure/kubernetes/kafka-statefulset.yaml

kubectl wait --for=condition=ready pod -l app=kafka \
  -n swarm-intelligence --timeout=600s

# Verify all brokers
kubectl get pods -n swarm-intelligence -l app=kafka
```

**Expected Output:**
```
NAME       READY   STATUS    RESTARTS   AGE
kafka-0    1/1     Running   0          5m
kafka-1    1/1     Running   0          4m
kafka-2    1/1     Running   0          3m
```

## Step 3: Deploy Application Services

### Update Secrets and ConfigMaps

```bash
# Edit secrets for staging environment
kubectl create secret generic swarm-secrets \
  --from-literal=postgres-password='staging-secure-password' \
  --from-literal=redis-password='staging-redis-pass' \
  --from-literal=jwt-secret='staging-jwt-secret-key' \
  --from-literal=api-key='staging-api-key' \
  -n swarm-intelligence \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply configmap
kubectl apply -f infrastructure/kubernetes/configmap.yaml
```

### Deploy Core Engine

```bash
# Deploy
kubectl apply -f infrastructure/kubernetes/core-deployment.yaml

# Wait for ready
kubectl rollout status deployment/swarm-core -n swarm-intelligence

# Check logs
kubectl logs -f deployment/swarm-core -n swarm-intelligence
```

**Expected Log Output:**
```
[INFO] Swarm Intelligence Core Engine starting...
[INFO] Initializing spatial indexing system...
[INFO] Connected to PostgreSQL
[INFO] Connected to Redis
[INFO] Connected to Kafka
[INFO] Engine ready - listening for tasks
```

### Deploy API

```bash
kubectl apply -f infrastructure/kubernetes/api-deployment.yaml

kubectl rollout status deployment/swarm-api -n swarm-intelligence

# Test API health
kubectl exec -n swarm-intelligence deployment/swarm-core -- \
  curl -s http://swarm-api:8080/health
```

**Expected Output:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-10-14T10:30:00Z",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "messaging": "ok"
  }
}
```

### Deploy Frontend

```bash
kubectl apply -f infrastructure/kubernetes/frontend-deployment.yaml

kubectl rollout status deployment/swarm-frontend -n swarm-intelligence
```

### Deploy Autoscaling

```bash
# Install Metrics Server (if not already installed)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Deploy HPA
kubectl apply -f infrastructure/kubernetes/hpa.yaml

# Verify HPA
kubectl get hpa -n swarm-intelligence
```

**Expected Output:**
```
NAME          REFERENCE              TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
swarm-core    Deployment/swarm-core  45%/70%   5         100       5          1m
swarm-api     Deployment/swarm-api   30%/70%   10        200       10         1m
```

## Step 4: Configure Ingress and SSL

### Install Istio (Recommended)

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.20.0
export PATH=$PWD/bin:$PATH

# Install Istio
istioctl install --set profile=production -y

# Enable sidecar injection
kubectl label namespace swarm-intelligence istio-injection=enabled

# Deploy Istio gateway
kubectl apply -f infrastructure/kubernetes/istio-gateway.yaml
kubectl apply -f infrastructure/kubernetes/istio-policies.yaml
```

### Alternative: NGINX Ingress

```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# Deploy ingress
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

### Get Load Balancer Address

```bash
# For Istio
LB_ADDRESS=$(kubectl get svc istio-ingressgateway -n istio-system \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# For NGINX
LB_ADDRESS=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Load Balancer: $LB_ADDRESS"
```

### Configure DNS

```bash
# Add DNS records (in your DNS provider):
# staging.swarm-intelligence.example.com    -> $LB_ADDRESS
# staging-api.swarm-intelligence.example.com -> $LB_ADDRESS

# Test DNS resolution
nslookup staging.swarm-intelligence.example.com
```

### Install Cert-Manager for SSL

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager pods
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager \
  -n cert-manager --timeout=300s

# Create Let's Encrypt issuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: istio
EOF

# Certificate should be issued automatically
kubectl get certificate -n swarm-intelligence
```

## Step 5: Deploy Monitoring Stack

```bash
# Deploy Prometheus
kubectl apply -f infrastructure/kubernetes/monitoring/prometheus-deployment.yaml
kubectl apply -f infrastructure/kubernetes/monitoring/prometheus-config.yaml
kubectl apply -f monitoring/prometheus-rules.yaml

# Deploy Grafana
kubectl apply -f infrastructure/kubernetes/monitoring/grafana-deployment.yaml

# Deploy Jaeger
kubectl apply -f infrastructure/kubernetes/monitoring/jaeger-deployment.yaml

# Deploy Loki
kubectl apply -f infrastructure/kubernetes/monitoring/loki-deployment.yaml

# Deploy Fluent Bit
kubectl apply -f infrastructure/kubernetes/monitoring/fluent-bit-daemonset.yaml

# Wait for all monitoring pods
kubectl wait --for=condition=ready pod -l app=prometheus \
  -n swarm-intelligence --timeout=300s
kubectl wait --for=condition=ready pod -l app=grafana \
  -n swarm-intelligence --timeout=300s

# Import Grafana dashboards
kubectl port-forward -n swarm-intelligence svc/grafana 3000:3000 &

# Use Grafana UI or API to import dashboards from:
# - monitoring/grafana-dashboards/swarm-overview.json
# - monitoring/grafana-dashboards/api-metrics.json
```

## Step 6: Run Health Checks

### Automated Health Check Script

```bash
# Run the deployment script's health checks
./deployment/deploy.sh -e staging -c aws --dry-run

# Or run manual checks:
```

### Manual Health Checks

```bash
# Check all pods are running
kubectl get pods -n swarm-intelligence

# Should show all pods in Running state:
# - postgres-0
# - redis-0, redis-1, redis-2
# - kafka-0, kafka-1, kafka-2
# - swarm-core-xxx (multiple replicas)
# - swarm-api-xxx (multiple replicas)
# - swarm-frontend-xxx (multiple replicas)
# - prometheus-xxx
# - grafana-xxx
# - jaeger-xxx

# Check services
kubectl get svc -n swarm-intelligence

# Check ingress
kubectl get ingress -n swarm-intelligence

# Test API endpoint
curl https://staging-api.swarm-intelligence.example.com/health

# Expected: {"status":"healthy",...}

# Test frontend
curl -I https://staging.swarm-intelligence.example.com

# Expected: HTTP/2 200
```

### Smoke Tests

```bash
# Create a test swarm via API
curl -X POST https://staging-api.swarm-intelligence.example.com/api/swarms \
  -H "Content-Type: application/json" \
  -d '{
    "name": "staging-test-swarm",
    "agent_count": 1000,
    "behavior": "foraging"
  }'

# Should return swarm_id

# Check metrics
curl https://staging-api.swarm-intelligence.example.com/metrics

# Should show Prometheus metrics including swarm_agents_total
```

## Step 7: Access URLs and Credentials

### Application URLs

```
Frontend:    https://staging.swarm-intelligence.example.com
API:         https://staging-api.swarm-intelligence.example.com
API Docs:    https://staging-api.swarm-intelligence.example.com/docs
GraphQL:     https://staging-api.swarm-intelligence.example.com/graphql
```

### Monitoring URLs

Use `kubectl port-forward` to access monitoring tools:

```bash
# Grafana
kubectl port-forward -n swarm-intelligence svc/grafana 3000:3000
# Access: http://localhost:3000
# Username: admin
# Password: (check secrets)

# Prometheus
kubectl port-forward -n swarm-intelligence svc/prometheus 9090:9090
# Access: http://localhost:9090

# Jaeger
kubectl port-forward -n swarm-intelligence svc/jaeger-query 16686:16686
# Access: http://localhost:16686
```

### Get Credentials

```bash
# Grafana admin password
kubectl get secret swarm-secrets -n swarm-intelligence \
  -o jsonpath='{.data.grafana-password}' | base64 -d

# Database connection string
kubectl get secret swarm-secrets -n swarm-intelligence \
  -o jsonpath='{.data.postgres-password}' | base64 -d
```

## Step 8: Verify Performance

### Basic Performance Test

```bash
# Install Python test dependencies
pip install requests psutil

# Run performance test
python tests/e2e/test_full_workflow.py --target staging --agents 10000

# Expected output:
# ✓ Created swarm with 10,000 agents
# ✓ FPS: 58.3 (target: >30)
# ✓ Latency p99: 45ms (target: <100ms)
# ✓ Memory: 640MB (0.064MB per agent)
# ✓ All tests passed
```

### Load Test

```bash
# Install K6
brew install k6  # macOS
# or
sudo apt install k6  # Ubuntu

# Run load test
k6 run tests/e2e/load_test.js \
  --vus 100 \
  --duration 5m \
  --env BASE_URL=https://staging-api.swarm-intelligence.example.com

# Expected results:
# http_req_duration: avg=85ms p95=150ms
# http_req_failed: <1%
# checks: 100% passed
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n swarm-intelligence

# Check logs
kubectl logs <pod-name> -n swarm-intelligence

# Common issues:
# 1. Image pull errors -> Check registry credentials
# 2. Resource limits -> Increase node capacity
# 3. Failed health checks -> Check application logs
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
kubectl exec -n swarm-intelligence postgres-0 -- \
  psql -U swarm_user -d swarm_intelligence -c "SELECT 1"

# Test Redis connection
kubectl exec -n swarm-intelligence redis-0 -- redis-cli ping

# Check connection strings in configmap
kubectl get configmap swarm-config -n swarm-intelligence -o yaml
```

### High Latency

```bash
# Check pod resources
kubectl top pods -n swarm-intelligence

# Check node resources
kubectl top nodes

# Scale up if needed
kubectl scale deployment swarm-core --replicas=10 -n swarm-intelligence
```

### SSL Certificate Issues

```bash
# Check certificate status
kubectl describe certificate -n swarm-intelligence

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Force renewal
kubectl delete certificate <cert-name> -n swarm-intelligence
# Will be automatically recreated
```

## Cleanup

To tear down the staging environment:

```bash
# Delete Kubernetes resources
kubectl delete namespace swarm-intelligence

# Destroy infrastructure
cd infrastructure/terraform/aws  # or gcp/azure
terraform destroy -auto-approve
```

## Next Steps

1. **Run full test suite**: `pytest tests/ -v`
2. **Performance testing**: See tests/e2e/README.md
3. **Security scan**: Run vulnerability scans
4. **Load testing**: Simulate production traffic
5. **Documentation**: Update any environment-specific configs
6. **Production deployment**: See deployment/production-deploy.yaml

## Support

For issues or questions:
- Check logs: `kubectl logs -f deployment/swarm-core -n swarm-intelligence`
- View dashboards: Grafana at http://localhost:3000
- Review alerts: Prometheus at http://localhost:9090
- Contact: devops@example.com
