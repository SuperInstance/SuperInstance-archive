#!/bin/bash
echo "=== ACTIVELOG COMPLETE SYSTEM REPORT ==="
echo "Generated: $(date)"
echo "=" 
echo ""

echo "=== SERVICE COUNT ==="
ls -d ~/activelog/services/*/ | wc -l
echo ""

echo "=== ALL SERVICES ==="
for dir in ~/activelog/services/*/; do
    echo "- $(basename $dir)"
done
echo ""

echo "=== FRONTEND APPS ==="
ls -d ~/activelog/frontend*/ 2>/dev/null
echo ""

echo "=== PORT ALLOCATIONS ==="
grep -r "port.*=" ~/activelog/services/*/main.py 2>/dev/null | grep -oE '8[0-9]{3}' | sort -u
echo ""

echo "=== FEATURES IMPLEMENTED ==="
echo "Payment Systems: $(grep -l "payment\|stripe\|billing" ~/activelog/services/*/main.py 2>/dev/null | wc -l)"
echo "AI Integrations: $(grep -l "ai\|claude\|openai\|gpt" ~/activelog/services/*/main.py 2>/dev/null | wc -l)"
echo "Game Systems: $(grep -l "game\|player\|tycoon" ~/activelog/services/*/main.py 2>/dev/null | wc -l)"
echo "Marine Features: $(grep -l "fishing\|marine\|vessel\|nmea" ~/activelog/services/*/main.py 2>/dev/null | wc -l)"
echo ""

echo "=== DATABASE TABLES ==="
docker exec activelog-postgres-1 psql -U activeloguser -d activelog -c "\dt" 2>/dev/null || echo "Database not accessible"
echo ""

echo "=== TOTAL LINES OF CODE ==="
find ~/activelog -name "*.py" -o -name "*.js" -o -name "*.tsx" | xargs wc -l | tail -1
