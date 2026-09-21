#!/bin/bash
# Coverage report generation script

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COVERAGE_DIR="$PROJECT_ROOT/tests/coverage"
REPORTS_DIR="$COVERAGE_DIR/reports"
HTML_DIR="$COVERAGE_DIR/html"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Generating Coverage Reports...${NC}"

# Create directories
mkdir -p "$COVERAGE_DIR" "$REPORTS_DIR" "$HTML_DIR"

# Change to project root
cd "$PROJECT_ROOT"

# Run tests with coverage
echo -e "${YELLOW}Running tests with coverage...${NC}"
python -m pytest \
    --cov=activelog \
    --cov=services \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=html:"$HTML_DIR" \
    --cov-report=xml:"$COVERAGE_DIR/coverage.xml" \
    --cov-report=json:"$COVERAGE_DIR/coverage.json" \
    tests/unit/ tests/integration/

# Generate additional reports
echo -e "${YELLOW}Generating additional coverage reports...${NC}"

# Terminal report with details
python -m coverage report --show-missing --precision=2 > "$REPORTS_DIR/terminal_report.txt"

# Detailed line coverage
python -m coverage report --show-missing --precision=2 --format=text > "$REPORTS_DIR/detailed_report.txt"

# Coverage by module
python -c "
import coverage
import json
import sys
import os

# Load coverage data
cov = coverage.Coverage()
try:
    cov.load()
    
    # Get data by module
    data = cov.get_data()
    modules = {}
    
    for filename in data.measured_files():
        # Skip test files and non-Python files
        if '/tests/' in filename or not filename.endswith('.py'):
            continue
            
        # Extract module name
        rel_path = os.path.relpath(filename)
        if rel_path.startswith('activelog/') or rel_path.startswith('services/'):
            module_path = rel_path.replace('/', '.').replace('.py', '')
            
            # Get coverage for this file
            analysis = cov.analysis(filename)
            total_lines = len(analysis[1]) + len(analysis[2])
            covered_lines = len(analysis[1])
            coverage_pct = (covered_lines / total_lines * 100) if total_lines > 0 else 0
            
            modules[module_path] = {
                'file': filename,
                'total_lines': total_lines,
                'covered_lines': covered_lines,
                'missing_lines': len(analysis[2]),
                'coverage_percentage': round(coverage_pct, 2)
            }
    
    # Sort by coverage percentage
    sorted_modules = sorted(modules.items(), key=lambda x: x[1]['coverage_percentage'])
    
    # Write report
    with open('$REPORTS_DIR/module_coverage.json', 'w') as f:
        json.dump(dict(sorted_modules), f, indent=2)
    
    # Write text report
    with open('$REPORTS_DIR/module_coverage.txt', 'w') as f:
        f.write('Module Coverage Report\\n')
        f.write('=' * 50 + '\\n\\n')
        
        for module, data in sorted_modules:
            f.write(f'{module}: {data[\"coverage_percentage\"]}%\\n')
        
        f.write('\\n\\nModules with low coverage (<70%):\\n')
        f.write('-' * 40 + '\\n')
        for module, data in sorted_modules:
            if data['coverage_percentage'] < 70:
                f.write(f'{module}: {data[\"coverage_percentage\"]}% ({data[\"missing_lines\"]} lines missing)\\n')
    
    print('Module coverage analysis complete')
    
except coverage.CoverageException as e:
    print(f'Coverage error: {e}')
    sys.exit(1)
"

# Generate badge data
echo -e "${YELLOW}Generating coverage badge data...${NC}"
python -c "
import coverage
import json
import sys

try:
    cov = coverage.Coverage()
    cov.load()
    
    # Get total coverage
    total = cov.report(show_missing=False, file=sys.stdout)
    
    # Create badge data
    badge_data = {
        'schemaVersion': 1,
        'label': 'coverage',
        'message': f'{total:.1f}%',
        'color': 'brightgreen' if total >= 90 else 'yellow' if total >= 80 else 'orange' if total >= 70 else 'red'
    }
    
    with open('$COVERAGE_DIR/badge.json', 'w') as f:
        json.dump(badge_data, f)
    
    print(f'Coverage badge data generated: {total:.1f}%')
    
except Exception as e:
    print(f'Error generating badge data: {e}')
    sys.exit(1)
" 2>/dev/null

# Check coverage thresholds
echo -e "${YELLOW}Checking coverage thresholds...${NC}"
python -c "
import coverage
import sys

try:
    cov = coverage.Coverage()
    cov.load()
    
    total = cov.report(show_missing=False, file=open('/dev/null', 'w'))
    
    print(f'Total coverage: {total:.2f}%')
    
    # Define thresholds
    thresholds = {
        'excellent': 95,
        'good': 85,
        'acceptable': 75,
        'poor': 60
    }
    
    if total >= thresholds['excellent']:
        print('✅ Excellent coverage!')
        status = 'excellent'
    elif total >= thresholds['good']:
        print('✅ Good coverage')
        status = 'good'  
    elif total >= thresholds['acceptable']:
        print('⚠️  Acceptable coverage')
        status = 'acceptable'
    elif total >= thresholds['poor']:
        print('⚠️  Poor coverage - needs improvement')
        status = 'poor'
    else:
        print('❌ Very poor coverage - immediate action needed')
        status = 'very_poor'
        sys.exit(1)
    
    # Write status file
    with open('$COVERAGE_DIR/status.txt', 'w') as f:
        f.write(f'{total:.2f}\\n{status}')
    
except Exception as e:
    print(f'Error checking coverage: {e}')
    sys.exit(1)
"

# Generate summary
echo -e "${YELLOW}Generating coverage summary...${NC}"
cat > "$COVERAGE_DIR/summary.md" << EOF
# Coverage Report Summary

Generated on: $(date)

## Overall Statistics

$(python -c "
import coverage
cov = coverage.Coverage()
cov.load()
total = cov.report(show_missing=False, file=open('/dev/null', 'w'))
print(f'- **Total Coverage:** {total:.2f}%')
")

## Reports Available

- **HTML Report:** Open \`tests/coverage/html/index.html\` in your browser
- **XML Report:** \`tests/coverage/coverage.xml\` (for CI/CD integration)
- **JSON Report:** \`tests/coverage/coverage.json\` (for programmatic access)
- **Terminal Report:** \`tests/coverage/reports/terminal_report.txt\`
- **Module Analysis:** \`tests/coverage/reports/module_coverage.txt\`

## Quick Access

\`\`\`bash
# View HTML report
open tests/coverage/html/index.html

# View terminal report
cat tests/coverage/reports/terminal_report.txt

# Check modules with low coverage
grep -A 20 "low coverage" tests/coverage/reports/module_coverage.txt
\`\`\`

## Recommendations

$(python -c "
import json
import sys
try:
    with open('tests/coverage/reports/module_coverage.json', 'r') as f:
        modules = json.load(f)
    
    low_coverage = [m for m, data in modules.items() if data['coverage_percentage'] < 70]
    
    if low_coverage:
        print('### Modules needing attention (< 70% coverage):')
        for module in low_coverage[:5]:  # Show top 5
            print(f'- \`{module}\`: {modules[module][\"coverage_percentage\"]}%')
        
        if len(low_coverage) > 5:
            print(f'- ... and {len(low_coverage) - 5} more modules')
    else:
        print('### ✅ All modules have good coverage!')
except:
    print('### Analysis data not available')
")
EOF

# Print summary
echo -e "${GREEN}✅ Coverage reports generated successfully!${NC}"
echo ""
echo "📁 Reports available at:"
echo "   HTML: $HTML_DIR/index.html"
echo "   XML:  $COVERAGE_DIR/coverage.xml"
echo "   JSON: $COVERAGE_DIR/coverage.json"
echo ""
echo "📊 Quick stats:"
cat "$COVERAGE_DIR/status.txt" | head -1 | xargs -I {} echo "   Coverage: {}%"
echo ""
echo "🔍 To view HTML report:"
echo "   open $HTML_DIR/index.html"
echo ""

# Optional: Open HTML report if running on macOS/Linux with desktop
if command -v open >/dev/null 2>&1; then
    read -p "Open HTML report in browser? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$HTML_DIR/index.html"
    fi
elif command -v xdg-open >/dev/null 2>&1; then
    read -p "Open HTML report in browser? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        xdg-open "$HTML_DIR/index.html"
    fi
fi

echo -e "${BLUE}🎉 Coverage report generation complete!${NC}"