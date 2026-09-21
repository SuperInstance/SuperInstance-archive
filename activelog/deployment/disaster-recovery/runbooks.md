# ActiveLog Disaster Recovery Runbooks

## Overview

This document contains step-by-step procedures for disaster recovery scenarios in the ActiveLog platform. These runbooks are designed to minimize downtime and data loss during critical incidents.

## Recovery Objectives

- **RTO (Recovery Time Objective)**: 30 minutes
- **RPO (Recovery Point Objective)**: 15 minutes
- **Availability Target**: 99.95% uptime

## Critical Service Priority

1. **Tier 0 (Critical)**: postgres, redis, auth
2. **Tier 1 (High)**: api-gateway, data-manager
3. **Tier 2 (Medium)**: ai-orchestrator, gaming-platform, sync-engine
4. **Tier 3 (Low)**: monitoring, logging, analytics

## Disaster Recovery Scenarios

### 1. Database Corruption/Failure

**Severity**: Critical  
**Estimated RTO**: 15 minutes  
**Estimated RPO**: 5 minutes  

#### Symptoms
- Database connection failures
- Data integrity errors
- PostgreSQL pod crash loops
- Corrupt data files

#### Procedure

1. **Immediate Response**
   ```bash
   # Scale down all applications to prevent further corruption
   kubectl scale deployment --replicas=0 -n activelog --all
   
   # Check database status
   kubectl logs -n activelog postgres-0 --tail=100
   ```

2. **Assessment**
   ```bash
   # Check if database is recoverable
   kubectl exec -n activelog postgres-0 -- pg_ctl status
   
   # Attempt to connect and check data integrity
   kubectl exec -n activelog postgres-0 -- psql -c "SELECT COUNT(*) FROM users;"
   ```

3. **Database Restoration**
   ```bash
   # List available backups
   aws s3 ls s3://activelog-backups/database/ | sort -r
   
   # Create restore job with latest backup
   kubectl create job restore-db-$(date +%Y%m%d-%H%M) \
     --from=job/postgres-restore-template -n activelog
   
   # Monitor restore progress
   kubectl logs -n activelog job/restore-db-$(date +%Y%m%d-%H%M) -f
   ```

4. **Service Recovery**
   ```bash
   # Scale up critical services in order
   kubectl scale deployment postgres --replicas=1 -n activelog
   kubectl wait --for=condition=ready pod -l app=postgres -n activelog --timeout=300s
   
   kubectl scale deployment redis --replicas=1 -n activelog
   kubectl wait --for=condition=ready pod -l app=redis -n activelog --timeout=180s
   
   kubectl scale deployment auth --replicas=2 -n activelog
   kubectl scale deployment api-gateway --replicas=3 -n activelog
   ```

5. **Verification**
   ```bash
   # Health checks
   curl -f http://api-gateway.activelog/health
   
   # Database connectivity test
   kubectl exec -n activelog postgres-0 -- psql -c "SELECT version();"
   
   # Application functionality test
   curl -f http://api-gateway.activelog/api/v1/status
   ```

6. **Scale Up Remaining Services**
   ```bash
   # Use the restoration script
   ./deployment/scripts/restore-all-services.sh
   ```

### 2. Kubernetes Cluster Failure

**Severity**: Critical  
**Estimated RTO**: 45 minutes  
**Estimated RPO**: 15 minutes  

#### Symptoms
- Unable to connect to Kubernetes API
- All nodes unreachable
- Control plane components down
- kubectl commands failing

#### Procedure

1. **Assessment and Communication**
   ```bash
   # Assess cluster state
   kubectl cluster-info
   kubectl get nodes
   
   # Check cloud provider dashboard for infrastructure issues
   # Send initial incident notification to stakeholders
   ```

2. **Attempt Cluster Recovery**
   ```bash
   # Try to recover existing cluster
   # For EKS:
   aws eks describe-cluster --name activelog-production
   
   # For self-managed:
   ssh ubuntu@master-node "sudo systemctl status kubelet"
   ```

3. **Provision New Cluster (if recovery fails)**
   ```bash
   # Using Terraform
   cd infrastructure/terraform
   terraform plan -var="cluster_name=activelog-recovery-$(date +%Y%m%d)"
   terraform apply -auto-approve
   
   # Configure kubectl context
   aws eks update-kubeconfig --name activelog-recovery-$(date +%Y%m%d)
   ```

4. **Install Base Infrastructure**
   ```bash
   # Install Istio
   kubectl apply -f deployment/istio/
   
   # Install monitoring
   kubectl apply -f deployment/monitoring/namespace-exporters.yaml
   kubectl apply -f deployment/monitoring/prometheus.yaml
   
   # Install logging
   kubectl apply -f deployment/logging/namespace-rbac.yaml
   ```

5. **Restore Application State**
   ```bash
   # Restore Kubernetes manifests
   BACKUP_FILE=$(aws s3 ls s3://activelog-backups/k8s-state/ | sort -r | head -1 | awk '{print $4}')
   aws s3 cp "s3://activelog-backups/k8s-state/${BACKUP_FILE}" /tmp/
   tar -xzf "/tmp/${BACKUP_FILE}" -C /tmp/
   
   # Apply restored manifests
   kubectl apply -f /tmp/k8s-state-*/
   ```

6. **Restore Data**
   ```bash
   # Restore database
   kubectl create job restore-db-recovery --from=job/postgres-restore-template -n activelog
   
   # Restore file storage from backup
   kubectl create job restore-files --from=cronjob/filesystem-backup -n activelog
   ```

7. **DNS and Traffic Routing**
   ```bash
   # Update DNS records to point to new cluster
   aws route53 change-resource-record-sets --hosted-zone-id Z123456789 \
     --change-batch file://dns-update.json
   
   # Verify DNS propagation
   nslookup api.activelog.com
   ```

### 3. Regional Outage

**Severity**: Critical  
**Estimated RTO**: 60 minutes  
**Estimated RPO**: 30 minutes  

#### Symptoms
- Entire AWS/cloud region unavailable
- All services in primary region unreachable
- Regional DNS failures
- Cross-region backups still accessible

#### Procedure

1. **Activate DR Region**
   ```bash
   # Switch to DR region
   export AWS_DEFAULT_REGION=us-east-1
   aws eks update-kubeconfig --name activelog-dr-cluster
   ```

2. **Scale Up DR Infrastructure**
   ```bash
   # Activate standby cluster
   kubectl scale deployment --replicas=1 -n activelog postgres
   kubectl scale deployment --replicas=1 -n activelog redis
   
   # Wait for storage systems
   kubectl wait --for=condition=ready pod -l app=postgres -n activelog --timeout=600s
   ```

3. **Sync Latest Data**
   ```bash
   # Restore from latest cross-region backup
   LATEST_BACKUP=$(aws s3 ls s3://activelog-backups-dr/database/ | sort -r | head -1 | awk '{print $4}')
   
   # Create restore job in DR region
   kubectl create job restore-dr-$(date +%Y%m%d) \
     --from=job/postgres-restore-template -n activelog
   ```

4. **Update Global Load Balancer**
   ```bash
   # Update Route53 health checks and routing
   aws route53 change-resource-record-sets --hosted-zone-id Z123456789 \
     --change-batch '{
       "Changes": [{
         "Action": "UPSERT",
         "ResourceRecordSet": {
           "Name": "api.activelog.com",
           "Type": "A",
           "AliasTarget": {
             "DNSName": "dr-loadbalancer.us-east-1.elb.amazonaws.com",
             "EvaluateTargetHealth": true
           }
         }
       }]
     }'
   ```

5. **Scale Up Applications**
   ```bash
   # Scale critical services
   kubectl scale deployment api-gateway --replicas=3 -n activelog
   kubectl scale deployment auth --replicas=2 -n activelog
   
   # Scale remaining services gradually
   for deployment in $(kubectl get deployments -n activelog -o name); do
     kubectl scale $deployment --replicas=1 -n activelog
     sleep 30
   done
   ```

### 4. Single Service Failure

**Severity**: Medium  
**Estimated RTO**: 5 minutes  
**Estimated RPO**: 0 minutes  

#### Common Issues

**API Gateway Down**
```bash
# Check pod status
kubectl get pods -n activelog -l app=api-gateway

# Check logs
kubectl logs -n activelog -l app=api-gateway --tail=100

# Restart deployment
kubectl rollout restart deployment/api-gateway -n activelog

# Verify health
curl -f http://api-gateway.activelog/health
```

**Auth Service Issues**
```bash
# Check authentication flows
kubectl logs -n activelog -l app=auth --tail=50

# Check database connectivity
kubectl exec -n activelog deploy/auth -- nc -zv postgres 5432

# Restart if needed
kubectl rollout restart deployment/auth -n activelog
```

**Gaming Platform Performance**
```bash
# Check active sessions
kubectl exec -n activelog deploy/gaming-platform -- curl -s localhost:8070/metrics | grep active_sessions

# Check resource usage
kubectl top pods -n activelog -l app=gaming-platform

# Scale up if needed
kubectl scale deployment gaming-platform --replicas=5 -n activelog
```

## Recovery Verification Checklist

### Database Recovery
- [ ] Database pod is running and ready
- [ ] Can connect to database from application pods
- [ ] User count matches expected range
- [ ] Critical tables are intact and accessible
- [ ] Database backup job completes successfully

### Application Recovery
- [ ] All critical services (Tier 0) are healthy
- [ ] API Gateway responds to health checks
- [ ] Authentication flows work correctly
- [ ] Gaming platform sessions can be created
- [ ] AI services respond to inference requests
- [ ] File sync operations work

### Infrastructure Recovery
- [ ] All nodes are in Ready state
- [ ] Persistent volumes are mounted correctly
- [ ] Network policies allow required traffic
- [ ] DNS resolution works for all services
- [ ] Load balancer health checks pass

### Monitoring and Alerting
- [ ] Prometheus is scraping all targets
- [ ] Grafana dashboards load correctly
- [ ] AlertManager is receiving alerts
- [ ] Log aggregation is functioning
- [ ] Metrics show normal patterns

## Post-Incident Actions

1. **Immediate Stabilization**
   - Ensure all services are scaled to normal levels
   - Verify monitoring and alerting is fully functional
   - Check that all backup jobs are scheduled and running

2. **Communication**
   - Update incident status page
   - Send recovery notification to stakeholders
   - Schedule post-mortem meeting within 24 hours

3. **Data Integrity Verification**
   - Run data consistency checks
   - Verify recent transactions are present
   - Check for any data corruption or loss

4. **Performance Monitoring**
   - Monitor system performance for next 24 hours
   - Watch for any degraded performance or errors
   - Scale resources if needed for recovery load

5. **Backup Verification**
   - Ensure next backup cycle completes successfully
   - Verify backup integrity and accessibility
   - Update backup retention if needed

## Contact Information

### Incident Response Team
- **Primary On-Call**: +1-555-0123
- **Secondary On-Call**: +1-555-0124  
- **Engineering Manager**: engineering-manager@activelog.com
- **DevOps Lead**: devops@activelog.com

### Escalation
- **CTO**: cto@activelog.com
- **CEO**: ceo@activelog.com (for major incidents only)

### External Resources
- **AWS Support**: Case creation through AWS Console
- **Cloud Provider**: Support ticket through provider portal
- **Database Vendor**: PostgreSQL community or enterprise support

## Tools and Resources

### Monitoring Dashboards
- Grafana: http://grafana.activelog.com
- Prometheus: http://prometheus.activelog.com
- AlertManager: http://alertmanager.activelog.com

### Backup Locations
- Database Backups: s3://activelog-backups/database/
- K8s State: s3://activelog-backups/k8s-state/
- File Storage: s3://activelog-backups/filesystem/

### Documentation
- Architecture Diagrams: https://wiki.activelog.com/architecture
- Service Dependencies: https://wiki.activelog.com/services
- Network Topology: https://wiki.activelog.com/network

---

**Last Updated**: $(date)  
**Version**: 1.0  
**Next Review Date**: $(date -d '+3 months')