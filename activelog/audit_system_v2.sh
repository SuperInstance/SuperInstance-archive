#!/bin/bash
echo "=== ActiveLog System Audit v2 ==="
echo "Date: $(date)"
echo ""

# Check all services
echo "SERVICES STATUS:"
for service in ~/activelog/services/*/; do
    if [ -f "$service/main.py" ]; then
        echo "✓ $(basename $service)"
    else
        echo "✗ $(basename $service) - Missing main.py"
    fi
done

# Check all frontends
echo ""
echo "FRONTEND APPS:"
ls -la ~/activelog/frontend*/ 2>/dev/null | grep "^d"

# Check critical features
echo ""
echo "CRITICAL FEATURES:"
grep -l "Compute.*Capital\|CC\|CCC" ~/activelog/services/*/main.py 2>/dev/null | wc -l
echo "Services with CC integration: $(grep -l "Compute.*Capital\|CC\|CCC" ~/activelog/services/*/main.py 2>/dev/null | wc -l)"

# Generate detailed report
echo ""
echo "Generating detailed report..."
