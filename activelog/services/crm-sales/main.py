"""
CRM Sales System
Enterprise customer relationship management with sales automation
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any, List, Optional

# Import CRM components
from contacts.contact_management import ContactManager
from leads.lead_scoring import LeadScoringSystem
from opportunities.opportunity_tracking import OpportunityTracker
from pipeline.pipeline_visualization import PipelineVisualization
from campaigns.email_campaigns import EmailCampaignSystem
from calls.call_logging import CallLoggingSystem
from automation.task_automation import TaskAutomationSystem
from territory.territory_management import TerritoryManagementSystem
from commissions.commission_tracking import CommissionTrackingSystem
from forecasting.sales_forecasting import SalesForecastingSystem
from segmentation.customer_segmentation import CustomerSegmentationSystem
from retention.retention_analytics import RetentionAnalyticsSystem
from config.crm_config import CRMConfig
from database.crm_database import CRMDatabase


class CRMSalesService:
    """Main CRM Sales service orchestrator"""
    
    def __init__(self):
        self.config = CRMConfig()
        self.db = CRMDatabase()
        
        # Initialize database tables
        self.db.initialize_tables()
        
        # Initialize CRM components
        self.contact_manager = ContactManager(self.config, self.db)
        self.lead_scoring = LeadScoringSystem(self.config, self.db)
        self.opportunity_tracker = OpportunityTracker(self.config, self.db)
        self.pipeline_visualizer = PipelineVisualization(self.db.db_path)
        self.email_campaigns = EmailCampaignSystem(self.db.db_path, self.config.get_smtp_config())
        self.call_logging = CallLoggingSystem(self.db.db_path)
        self.task_automation = TaskAutomationSystem(self.db.db_path)
        self.territory_manager = TerritoryManagementSystem(self.db.db_path)
        self.commission_tracker = CommissionTrackingSystem(self.db.db_path)
        self.sales_forecasting = SalesForecastingSystem(self.db.db_path)
        self.customer_segmentation = CustomerSegmentationSystem(self.db.db_path)
        self.retention_analytics = RetentionAnalyticsSystem(self.db.db_path)
        
        # Initialize database
        self.initialize_database()
        
    def initialize_database(self):
        """Initialize CRM database tables"""
        try:
            self.db.initialize_tables()
            print("CRM database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")


# Create Flask application
app = Flask(__name__)
CORS(app)

# Initialize CRM service
crm_service = CRMSalesService()


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'CRM Sales System',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


# Contact Management Endpoints
@app.route('/api/contacts', methods=['POST'])
def create_contact():
    """Create new contact"""
    try:
        contact_data = request.json
        result = crm_service.contact_manager.create_contact(contact_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/contacts', methods=['GET'])
def list_contacts():
    """List contacts with filtering and pagination"""
    try:
        filters = request.args.to_dict()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        result = crm_service.contact_manager.list_contacts(filters, page, limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/contacts/<contact_id>', methods=['GET'])
def get_contact(contact_id):
    """Get contact details"""
    try:
        result = crm_service.contact_manager.get_contact(contact_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/contacts/<contact_id>', methods=['PUT'])
def update_contact(contact_id):
    """Update contact"""
    try:
        update_data = request.json
        result = crm_service.contact_manager.update_contact(contact_id, update_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/contacts/<contact_id>/activities', methods=['GET'])
def get_contact_activities(contact_id):
    """Get contact activity history"""
    try:
        result = crm_service.contact_manager.get_contact_activities(contact_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Lead Scoring Endpoints
@app.route('/api/leads/score', methods=['POST'])
def calculate_lead_score():
    """Calculate lead score"""
    try:
        lead_data = request.json
        result = crm_service.lead_scoring.calculate_lead_score(lead_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/leads/scoring-rules', methods=['GET'])
def get_scoring_rules():
    """Get lead scoring rules"""
    try:
        result = crm_service.lead_scoring.get_scoring_rules()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/leads/scoring-rules', methods=['POST'])
def create_scoring_rule():
    """Create lead scoring rule"""
    try:
        rule_data = request.json
        result = crm_service.lead_scoring.create_scoring_rule(rule_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/leads/hot', methods=['GET'])
def get_hot_leads():
    """Get high-scoring leads"""
    try:
        threshold = float(request.args.get('threshold', 80))
        result = crm_service.lead_scoring.get_hot_leads(threshold)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Opportunity Tracking Endpoints
@app.route('/api/opportunities', methods=['POST'])
def create_opportunity():
    """Create new opportunity"""
    try:
        opportunity_data = request.json
        result = crm_service.opportunity_tracker.create_opportunity(opportunity_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/opportunities', methods=['GET'])
def list_opportunities():
    """List opportunities"""
    try:
        filters = request.args.to_dict()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        result = crm_service.opportunity_tracker.list_opportunities(filters, page, limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/opportunities/<opportunity_id>', methods=['PUT'])
def update_opportunity(opportunity_id):
    """Update opportunity"""
    try:
        update_data = request.json
        result = crm_service.opportunity_tracker.update_opportunity(opportunity_id, update_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/opportunities/<opportunity_id>/stage', methods=['PUT'])
def update_opportunity_stage(opportunity_id):
    """Update opportunity stage"""
    try:
        stage_data = request.json
        result = crm_service.opportunity_tracker.update_opportunity_stage(opportunity_id, stage_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/opportunities/analytics', methods=['GET'])
def get_opportunity_analytics():
    """Get opportunity analytics"""
    try:
        params = request.args.to_dict()
        result = crm_service.opportunity_tracker.get_opportunity_analytics(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Pipeline Visualization Endpoints
@app.route('/api/pipeline/overview', methods=['GET'])
def get_pipeline_overview():
    """Get pipeline overview"""
    try:
        filters = request.args.to_dict()
        result = crm_service.pipeline_visualizer.get_pipeline_overview(filters)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/pipeline/stages', methods=['GET'])
def get_pipeline_stages():
    """Get pipeline stage configuration"""
    try:
        result = crm_service.pipeline_visualizer.get_pipeline_stages()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/pipeline/velocity', methods=['GET'])
def get_pipeline_velocity():
    """Get pipeline velocity metrics"""
    try:
        params = request.args.to_dict()
        result = crm_service.pipeline_visualizer.get_pipeline_velocity(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/pipeline/conversion', methods=['GET'])
def get_conversion_rates():
    """Get stage conversion rates"""
    try:
        params = request.args.to_dict()
        result = crm_service.pipeline_visualizer.get_conversion_rates(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Email Campaign Endpoints
@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    """Create email campaign"""
    try:
        campaign_data = request.json
        result = crm_service.email_campaigns.create_campaign(campaign_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/campaigns', methods=['GET'])
def list_campaigns():
    """List email campaigns"""
    try:
        filters = request.args.to_dict()
        result = crm_service.email_campaigns.list_campaigns(filters)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/campaigns/<campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    """Send email campaign"""
    try:
        send_data = request.json or {}
        result = crm_service.email_campaigns.send_campaign(campaign_id, send_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/campaigns/<campaign_id>/analytics', methods=['GET'])
def get_campaign_analytics(campaign_id):
    """Get campaign analytics"""
    try:
        result = crm_service.email_campaigns.get_campaign_analytics(campaign_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Call Logging Endpoints
@app.route('/api/calls', methods=['POST'])
def log_call():
    """Log call activity"""
    try:
        call_data = request.json
        result = crm_service.call_logging.log_call(call_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/calls', methods=['GET'])
def list_calls():
    """List call logs"""
    try:
        filters = request.args.to_dict()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        result = crm_service.call_logging.list_calls(filters, page, limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/calls/<call_id>', methods=['PUT'])
def update_call_log(call_id):
    """Update call log"""
    try:
        update_data = request.json
        result = crm_service.call_logging.update_call_log(call_id, update_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/calls/analytics', methods=['GET'])
def get_call_analytics():
    """Get call analytics"""
    try:
        params = request.args.to_dict()
        result = crm_service.call_logging.get_call_analytics(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Task Automation Endpoints
@app.route('/api/automation/workflows', methods=['POST'])
def create_workflow():
    """Create automation workflow"""
    try:
        workflow_data = request.json
        result = crm_service.task_automation.create_workflow(workflow_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/automation/workflows', methods=['GET'])
def list_workflows():
    """List automation workflows"""
    try:
        result = crm_service.task_automation.list_workflows()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/automation/triggers', methods=['POST'])
def execute_trigger():
    """Execute automation trigger"""
    try:
        trigger_data = request.json
        result = crm_service.task_automation.execute_trigger(trigger_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """List tasks"""
    try:
        filters = request.args.to_dict()
        result = crm_service.task_automation.list_tasks(filters)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Territory Management Endpoints
@app.route('/api/territories', methods=['POST'])
def create_territory():
    """Create sales territory"""
    try:
        territory_data = request.json
        result = crm_service.territory_manager.create_territory(territory_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/territories', methods=['GET'])
def list_territories():
    """List territories"""
    try:
        result = crm_service.territory_manager.list_territories()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/territories/<territory_id>/assign', methods=['POST'])
def assign_territory():
    """Assign territory to sales rep"""
    try:
        assignment_data = request.json
        result = crm_service.territory_manager.assign_territory(territory_id, assignment_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/territories/<territory_id>/performance', methods=['GET'])
def get_territory_performance(territory_id):
    """Get territory performance metrics"""
    try:
        params = request.args.to_dict()
        result = crm_service.territory_manager.get_territory_performance(territory_id, params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Commission Tracking Endpoints
@app.route('/api/commissions/calculate', methods=['POST'])
def calculate_commission():
    """Calculate commission"""
    try:
        calculation_data = request.json
        result = crm_service.commission_tracker.calculate_commission(calculation_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/commissions/plans', methods=['GET'])
def get_commission_plans():
    """Get commission plans"""
    try:
        result = crm_service.commission_tracker.get_commission_plans()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/commissions/statements', methods=['GET'])
def get_commission_statements():
    """Get commission statements"""
    try:
        params = request.args.to_dict()
        result = crm_service.commission_tracker.get_commission_statements(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/commissions/reports', methods=['GET'])
def get_commission_reports():
    """Get commission reports"""
    try:
        params = request.args.to_dict()
        result = crm_service.commission_tracker.get_commission_reports(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Sales Forecasting Endpoints
@app.route('/api/forecasting/generate', methods=['POST'])
def generate_forecast():
    """Generate sales forecast"""
    try:
        forecast_params = request.json
        result = crm_service.sales_forecasting.generate_forecast(forecast_params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/forecasting/models', methods=['GET'])
def get_forecasting_models():
    """Get available forecasting models"""
    try:
        result = crm_service.sales_forecasting.get_forecasting_models()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/forecasting/accuracy', methods=['GET'])
def get_forecast_accuracy():
    """Get forecast accuracy metrics"""
    try:
        params = request.args.to_dict()
        result = crm_service.sales_forecasting.get_forecast_accuracy(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/forecasting/scenarios', methods=['POST'])
def create_forecast_scenario():
    """Create forecast scenario"""
    try:
        scenario_data = request.json
        result = crm_service.sales_forecasting.create_forecast_scenario(scenario_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Customer Segmentation Endpoints
@app.route('/api/segmentation/segments', methods=['GET'])
def get_customer_segments():
    """Get customer segments"""
    try:
        result = crm_service.customer_segmentation.get_customer_segments()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/segmentation/create', methods=['POST'])
def create_segment():
    """Create customer segment"""
    try:
        segment_data = request.json
        result = crm_service.customer_segmentation.create_segment(segment_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/segmentation/analyze', methods=['POST'])
def analyze_segmentation():
    """Analyze customer segmentation"""
    try:
        analysis_params = request.json
        result = crm_service.customer_segmentation.analyze_segmentation(analysis_params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/segmentation/recommendations', methods=['GET'])
def get_segment_recommendations():
    """Get segment-based recommendations"""
    try:
        params = request.args.to_dict()
        result = crm_service.customer_segmentation.get_segment_recommendations(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Retention Analytics Endpoints
@app.route('/api/retention/analysis', methods=['GET'])
def get_retention_analysis():
    """Get customer retention analysis"""
    try:
        params = request.args.to_dict()
        result = crm_service.retention_analytics.get_retention_analysis(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/retention/cohort', methods=['GET'])
def get_cohort_analysis():
    """Get cohort retention analysis"""
    try:
        params = request.args.to_dict()
        result = crm_service.retention_analytics.get_cohort_analysis(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/retention/churn', methods=['GET'])
def get_churn_analysis():
    """Get churn risk analysis"""
    try:
        params = request.args.to_dict()
        result = crm_service.retention_analytics.get_churn_analysis(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/retention/interventions', methods=['GET'])
def get_retention_interventions():
    """Get retention intervention recommendations"""
    try:
        params = request.args.to_dict()
        result = crm_service.retention_analytics.get_retention_interventions(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Dashboard and Reporting Endpoints
@app.route('/api/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """Get CRM dashboard overview"""
    try:
        # Combine data from multiple components for dashboard
        overview = {
            'contacts': crm_service.contact_manager.get_contact_summary(),
            'opportunities': crm_service.opportunity_tracker.get_opportunity_summary(),
            'pipeline': crm_service.pipeline_visualizer.get_pipeline_summary(),
            'campaigns': crm_service.email_campaigns.get_campaign_summary(),
            'activities': {
                'calls_today': crm_service.call_logging.get_daily_call_count(),
                'tasks_pending': crm_service.task_automation.get_pending_task_count(),
            },
            'performance': {
                'revenue_forecast': crm_service.sales_forecasting.get_current_forecast(),
                'top_territories': crm_service.territory_manager.get_top_performing_territories(),
            }
        }
        
        return jsonify({
            'success': True,
            'overview': overview,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/reports/<report_type>', methods=['GET'])
def generate_report(report_type):
    """Generate various CRM reports"""
    try:
        params = request.args.to_dict()
        
        if report_type == 'sales_performance':
            result = crm_service.opportunity_tracker.get_sales_performance_report(params)
        elif report_type == 'pipeline_health':
            result = crm_service.pipeline_visualizer.get_pipeline_health_report(params)
        elif report_type == 'territory_analysis':
            result = crm_service.territory_manager.get_territory_analysis_report(params)
        elif report_type == 'commission_summary':
            result = crm_service.commission_tracker.get_commission_summary_report(params)
        elif report_type == 'customer_retention':
            result = crm_service.retention_analytics.get_retention_report(params)
        else:
            return jsonify({'error': 'Unknown report type'}), 400
            
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8356))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting CRM Sales System on port {port}")
    print("Available endpoints:")
    print("  - Contact Management: /api/contacts")
    print("  - Lead Scoring: /api/leads")
    print("  - Opportunity Tracking: /api/opportunities")
    print("  - Pipeline Visualization: /api/pipeline")
    print("  - Email Campaigns: /api/campaigns")
    print("  - Call Logging: /api/calls")
    print("  - Task Automation: /api/automation")
    print("  - Territory Management: /api/territories")
    print("  - Commission Tracking: /api/commissions")
    print("  - Sales Forecasting: /api/forecasting")
    print("  - Customer Segmentation: /api/segmentation")
    print("  - Retention Analytics: /api/retention")
    print("  - Dashboard: /api/dashboard")
    print("  - Reports: /api/reports")
    
    app.run(host='0.0.0.0', port=port, debug=debug)