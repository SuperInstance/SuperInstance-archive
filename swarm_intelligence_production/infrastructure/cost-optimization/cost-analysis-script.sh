#!/bin/bash
# Cost Analysis and Optimization Script for Swarm Intelligence Platform

set -e

echo "====================================="
echo "Swarm Intelligence Cost Analysis"
echo "====================================="
echo ""

# Configuration
NAMESPACE="swarm-intelligence"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://prometheus:9090}"
COST_PER_CPU_HOUR="${COST_PER_CPU_HOUR:-0.04}"  # $0.04 per vCPU hour
COST_PER_GB_HOUR="${COST_PER_GB_HOUR:-0.005}"   # $0.005 per GB hour

# Function to query Prometheus
query_prometheus() {
    local query=$1
    curl -s "${PROMETHEUS_URL}/api/v1/query?query=${query}" | jq -r '.data.result[0].value[1]'
}

# Calculate CPU usage and cost
echo "1. CPU Usage and Cost:"
echo "-----------------------------------"
cpu_usage=$(query_prometheus "sum(rate(container_cpu_usage_seconds_total{namespace=\"${NAMESPACE}\"}[24h])) * 24")
cpu_cost=$(echo "$cpu_usage * $COST_PER_CPU_HOUR" | bc)
echo "Total CPU Hours (24h): $cpu_usage"
echo "Estimated Daily CPU Cost: \$$cpu_cost"
echo ""

# Calculate Memory usage and cost
echo "2. Memory Usage and Cost:"
echo "-----------------------------------"
mem_usage_gb=$(query_prometheus "sum(container_memory_working_set_bytes{namespace=\"${NAMESPACE}\"}) / 1024 / 1024 / 1024")
mem_cost=$(echo "$mem_usage_gb * $COST_PER_GB_HOUR * 24" | bc)
echo "Average Memory Usage: ${mem_usage_gb} GB"
echo "Estimated Daily Memory Cost: \$$mem_cost"
echo ""

# Calculate total daily cost
total_daily_cost=$(echo "$cpu_cost + $mem_cost" | bc)
monthly_cost=$(echo "$total_daily_cost * 30" | bc)
annual_cost=$(echo "$total_daily_cost * 365" | bc)

echo "3. Total Cost Estimates:"
echo "-----------------------------------"
echo "Daily Cost: \$$total_daily_cost"
echo "Monthly Cost: \$$monthly_cost"
echo "Annual Cost: \$$annual_cost"
echo ""

# Identify cost optimization opportunities
echo "4. Cost Optimization Opportunities:"
echo "-----------------------------------"

# Check for over-provisioned pods
echo "Checking for over-provisioned pods..."
kubectl top pods -n ${NAMESPACE} --no-headers | awk '{
    if ($3 ~ /%/) {
        cpu_usage = substr($3, 1, length($3)-1)
        if (cpu_usage < 30) {
            print "- Pod " $1 " has low CPU usage: " $3 " - Consider reducing CPU requests"
        }
    }
    if ($5 ~ /%/) {
        mem_usage = substr($5, 1, length($5)-1)
        if (mem_usage < 30) {
            print "- Pod " $1 " has low memory usage: " $5 " - Consider reducing memory requests"
        }
    }
}'
echo ""

# Check for pods running on expensive nodes
echo "Checking for optimization using spot instances..."
spot_eligible=$(kubectl get pods -n ${NAMESPACE} -o json | \
    jq -r '.items[] | select(.spec.nodeSelector."spot" != "true") | select(.metadata.labels.workload | IN("swarm-batch", "swarm-worker")) | .metadata.name')
if [ -n "$spot_eligible" ]; then
    echo "The following pods could run on spot instances for 60-90% cost savings:"
    echo "$spot_eligible"
fi
echo ""

# Check for unused PVCs
echo "Checking for unused storage..."
unused_pvcs=$(kubectl get pvc -n ${NAMESPACE} -o json | \
    jq -r '.items[] | select(.status.phase == "Bound") | select([.metadata.name] | inside(["'$(kubectl get pods -n ${NAMESPACE} -o json | jq -r '.items[].spec.volumes[].persistentVolumeClaim.claimName' | tr '\n' '","')'"] | split(",")) | not) | .metadata.name')
if [ -n "$unused_pvcs" ]; then
    echo "The following PVCs are not mounted by any pod:"
    echo "$unused_pvcs"
fi
echo ""

# Check cluster autoscaler efficiency
echo "Checking autoscaler efficiency..."
node_count=$(kubectl get nodes --no-headers | wc -l)
avg_node_utilization=$(kubectl top nodes --no-headers | awk '{sum+=$3} END {print sum/NR}' | sed 's/%//')
echo "Total Nodes: $node_count"
echo "Average Node Utilization: ${avg_node_utilization}%"
if (( $(echo "$avg_node_utilization < 60" | bc -l) )); then
    echo "⚠️  Low node utilization detected. Consider adjusting autoscaler thresholds."
fi
echo ""

# Storage cost analysis
echo "5. Storage Cost Analysis:"
echo "-----------------------------------"
total_storage=$(kubectl get pvc -n ${NAMESPACE} -o json | \
    jq -r '[.items[].spec.resources.requests.storage | rtrimstr("Gi") | tonumber] | add')
storage_cost=$(echo "$total_storage * 0.10 / 30" | bc)  # $0.10 per GB-month
echo "Total Storage: ${total_storage} GB"
echo "Daily Storage Cost: \$$storage_cost"
echo ""

# Network cost estimation
echo "6. Network Cost Estimation:"
echo "-----------------------------------"
egress_gb=$(query_prometheus "sum(rate(container_network_transmit_bytes_total{namespace=\"${NAMESPACE}\"}[24h])) * 24 / 1024 / 1024 / 1024")
network_cost=$(echo "$egress_gb * 0.09" | bc)  # $0.09 per GB egress
echo "Egress Traffic (24h): ${egress_gb} GB"
echo "Daily Network Cost: \$$network_cost"
echo ""

# Recommendations
echo "7. Cost Optimization Recommendations:"
echo "-----------------------------------"
echo "✓ Enable cluster autoscaler to scale down during low usage"
echo "✓ Use spot instances for non-critical workloads (60-90% savings)"
echo "✓ Implement pod disruption budgets to allow safe node consolidation"
echo "✓ Set up HPA and VPA for right-sizing workloads"
echo "✓ Use KEDA for event-driven scaling"
echo "✓ Schedule batch jobs during off-peak hours"
echo "✓ Implement caching to reduce database costs"
echo "✓ Use lifecycle policies for storage to delete old data"
echo "✓ Monitor and optimize network egress"
echo "✓ Use reserved capacity for baseline workloads (40-60% savings)"
echo ""

# Potential savings
echo "8. Estimated Potential Savings:"
echo "-----------------------------------"
spot_savings=$(echo "$total_daily_cost * 0.3 * 0.7" | bc)  # 30% spot, 70% savings
reserved_savings=$(echo "$total_daily_cost * 0.5 * 0.5" | bc)  # 50% reserved, 50% savings
total_savings=$(echo "$spot_savings + $reserved_savings" | bc)
echo "By using Spot Instances: \$$spot_savings/day"
echo "By using Reserved Capacity: \$$reserved_savings/day"
echo "Total Potential Savings: \$$total_savings/day (\$$(echo "$total_savings * 365" | bc)/year)"
echo ""

# Generate report
REPORT_FILE="cost-report-$(date +%Y%m%d).txt"
{
    echo "Swarm Intelligence Cost Report"
    echo "Generated: $(date)"
    echo ""
    echo "Daily Cost: \$$total_daily_cost"
    echo "Monthly Cost: \$$monthly_cost"
    echo "Annual Cost: \$$annual_cost"
    echo ""
    echo "Potential Annual Savings: \$$(echo "$total_savings * 365" | bc)"
} > "$REPORT_FILE"

echo "Report saved to: $REPORT_FILE"
echo ""
echo "====================================="
echo "Cost Analysis Complete"
echo "====================================="
