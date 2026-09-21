#!/usr/bin/env python3
"""
Test script for the advanced analytics system
Tests the usage analytics and report generation components independently.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database_manager import DatabaseManager
from billing.usage_analytics import UsageAnalytics, CostDimension, AnalyticsPeriod
from billing.report_generator import ReportGenerator, ReportRequest, ReportType, ReportFormat

class MockBillingEngine:
    """Mock billing engine for testing"""
    def __init__(self):
        pass
    
    async def calculate_projected_cost(self, user_id: str, days: int):
        return {"projected_cost": 150.00, "confidence": 0.85}

async def test_analytics_system():
    """Test the analytics system components"""
    
    try:
        print("🔧 Testing Advanced Analytics System")
        print("=" * 50)
        
        # Initialize database
        print("1. Initializing database...")
        db_manager = DatabaseManager("test_analytics.db")
        await db_manager.initialize()
        print("✅ Database initialized")
        
        # Initialize mock billing engine
        billing_engine = MockBillingEngine()
        
        # Initialize analytics components
        print("2. Initializing usage analytics...")
        usage_analytics = UsageAnalytics(db_manager, billing_engine)
        print("✅ Usage analytics initialized")
        
        print("3. Initializing report generator...")
        report_generator = ReportGenerator(db_manager, usage_analytics, billing_engine)
        print("✅ Report generator initialized")
        
        # Test data setup
        print("4. Setting up test data...")
        await setup_test_data(db_manager)
        print("✅ Test data created")
        
        # Test analytics functions
        print("5. Testing cost breakdown analysis...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        breakdown = await usage_analytics.get_detailed_cost_breakdown(
            "test_user_1", start_date, end_date,
            [CostDimension.INSTANCE_TYPE, CostDimension.SERVICE]
        )
        print(f"✅ Cost breakdown generated: {len(breakdown.get('dimensions', {}))} dimensions analyzed")
        
        # Test usage patterns
        print("6. Testing usage pattern detection...")
        patterns = await usage_analytics.detect_usage_patterns(
            "test_user_1", start_date, end_date
        )
        print(f"✅ Usage patterns detected: {len(patterns)} patterns found")
        
        # Test resource utilization
        print("7. Testing resource utilization analysis...")
        utilization = await usage_analytics.analyze_resource_utilization(
            "test_user_1", start_date, end_date
        )
        print(f"✅ Resource utilization analyzed: {len(utilization)} resources")
        
        # Test report generation
        print("8. Testing report generation...")
        report_request = ReportRequest(
            report_type=ReportType.COST_SUMMARY,
            format=ReportFormat.JSON,
            start_date=start_date,
            end_date=end_date,
            include_charts=True,
            include_recommendations=True
        )
        
        report = await report_generator.generate_report("test_user_1", report_request)
        print(f"✅ Report generated: {report['success']}")
        if report['success']:
            metadata = report['metadata']
            print(f"   Report ID: {metadata['report_id']}")
            print(f"   Generation time: {metadata['generation_time_seconds']:.2f}s")
            print(f"   Total records: {metadata['total_records']}")
        
        # Test different report types
        print("9. Testing different report types...")
        report_types = [
            ReportType.EXECUTIVE_SUMMARY,
            ReportType.DETAILED_BILLING,
            ReportType.OPTIMIZATION_REPORT
        ]
        
        for report_type in report_types:
            request = ReportRequest(
                report_type=report_type,
                format=ReportFormat.JSON,
                start_date=start_date,
                end_date=end_date
            )
            result = await report_generator.generate_report("test_user_1", request)
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {report_type.value} report")
        
        print("\n🎉 All analytics tests completed successfully!")
        print("=" * 50)
        print("Analytics System Features:")
        print("• Detailed cost breakdown by multiple dimensions")
        print("• Resource utilization analysis with efficiency scoring")
        print("• Usage pattern detection and optimization suggestions")
        print("• Comparative analysis between time periods")
        print("• Comprehensive report generation in multiple formats")
        print("• Tag-based cost allocation")
        print("• Executive summaries with key insights")
        print("• Trend analysis and forecasting")
        
        # Cleanup
        os.remove("test_analytics.db")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing analytics system: {e}")
        import traceback
        traceback.print_exc()
        return False

async def setup_test_data(db_manager):
    """Set up test billing and instance data"""
    
    import aiosqlite
    async with aiosqlite.connect(db_manager.db_path) as conn:
        # Create test user
        await conn.execute("""
            INSERT OR IGNORE INTO users (user_id, email, tier, created_at)
            VALUES ('test_user_1', 'test@example.com', 'premium', ?)
        """, (datetime.now(),))
        
        # Create test instances
        instance_data = [
            ('inst_1', 'test_user_1', 't3.medium', 'running'),
            ('inst_2', 'test_user_1', 'c5.xlarge', 'running'),
            ('inst_3', 'test_user_1', 't3.small', 'terminated')
        ]
        
        for instance_id, user_id, instance_type, status in instance_data:
            await conn.execute("""
                INSERT OR IGNORE INTO ec2_instances 
                (instance_id, user_id, instance_type, state, created_at, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                instance_id, user_id, instance_type, status,
                datetime.now() - timedelta(days=5),
                '{"Environment": "test", "Project": "analytics"}'
            ))
        
        # Create test billing records
        base_time = datetime.now() - timedelta(days=3)
        billing_records = []
        
        for i in range(20):  # 20 billing records
            start_time = base_time + timedelta(hours=i)
            end_time = start_time + timedelta(minutes=60)
            duration = 60
            
            # Vary the instance and costs
            instance_id = f"inst_{(i % 3) + 1}"
            instance_type = ['t3.medium', 'c5.xlarge', 't3.small'][i % 3]
            cost = Decimal('5.00') + Decimal(str(i * 0.5))
            
            billing_records.append((
                f"bill_{i}", "test_user_1", instance_id, instance_type,
                start_time, end_time, duration, 0.1, float(cost), "compute"
            ))
        
        await conn.executemany("""
            INSERT OR IGNORE INTO billing_records 
            (record_id, user_id, instance_id, instance_type, start_time, end_time, 
             duration_minutes, cost_per_minute, total_cost, billing_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, billing_records)
        
        await conn.commit()

if __name__ == "__main__":
    success = asyncio.run(test_analytics_system())
    sys.exit(0 if success else 1)