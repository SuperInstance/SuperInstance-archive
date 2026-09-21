#!/usr/bin/env python3
"""
ActiveLog Membership Migration Service
Comprehensive membership management with cross-frontend transfers, billing consolidation,
and advanced discount systems
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import membership migration components
from core.membership_manager import MembershipManager
from transfer.cross_frontend_transfer import CrossFrontendTransfer
from credits.compute_credits_manager import ComputeCreditsManager
from migration.data_migration_engine import DataMigrationEngine
from preferences.preference_manager import PreferenceManager
from billing.subscription_consolidator import SubscriptionConsolidator
from billing.multi_app_billing import MultiAppBilling
from family.family_plan_manager import FamilyPlanManager
from discounts.student_discount_manager import StudentDiscountManager
from discounts.senior_discount_manager import SeniorDiscountManager
from corporate.bulk_transfer_manager import BulkTransferManager
from config.settings import MembershipMigrationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/membership-migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MembershipMigrationService:
    """Main service orchestrating all membership migration components"""
    
    def __init__(self):
        self.config = MembershipMigrationConfig()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize core components
        self.membership_manager = MembershipManager(self.config)
        self.cross_frontend_transfer = CrossFrontendTransfer(self.config)
        self.compute_credits_manager = ComputeCreditsManager(self.config)
        self.data_migration_engine = DataMigrationEngine(self.config)
        self.preference_manager = PreferenceManager(self.config)
        self.subscription_consolidator = SubscriptionConsolidator(self.config)
        self.multi_app_billing = MultiAppBilling(self.config)
        self.family_plan_manager = FamilyPlanManager(self.config)
        self.student_discount_manager = StudentDiscountManager(self.config)
        self.senior_discount_manager = SeniorDiscountManager(self.config)
        self.bulk_transfer_manager = BulkTransferManager(self.config)
        
        self._setup_routes()
        logger.info("Membership Migration Service initialized")

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'membership-migration',
                    'version': '1.0.0',
                    'port': 8336
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503

        @self.app.route('/membership/<user_id>', methods=['GET'])
        def get_membership_info(user_id: str):
            """Get comprehensive membership information"""
            try:
                membership_info = self.membership_manager.get_membership_info(user_id)
                return jsonify(membership_info)
            except Exception as e:
                logger.error(f"Failed to get membership info for {user_id}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/transfer/cross-frontend', methods=['POST'])
        def initiate_cross_frontend_transfer():
            """Initiate cross-frontend membership transfer"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                source_app = data.get('source_app')
                target_app = data.get('target_app')
                transfer_options = data.get('transfer_options', {})
                
                result = self.cross_frontend_transfer.initiate_transfer(
                    user_id, source_app, target_app, transfer_options
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to initiate cross-frontend transfer: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/transfer/status/<transfer_id>', methods=['GET'])
        def get_transfer_status(transfer_id: str):
            """Get transfer status"""
            try:
                status = self.cross_frontend_transfer.get_transfer_status(transfer_id)
                return jsonify(status)
            except Exception as e:
                logger.error(f"Failed to get transfer status for {transfer_id}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/credits/preserve', methods=['POST'])
        def preserve_compute_credits():
            """Preserve compute credits during migration"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                source_app = data.get('source_app')
                target_app = data.get('target_app')
                
                result = self.compute_credits_manager.preserve_credits(
                    user_id, source_app, target_app
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to preserve compute credits: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/credits/balance/<user_id>', methods=['GET'])
        def get_credits_balance(user_id: str):
            """Get user's compute credits balance across all apps"""
            try:
                balance = self.compute_credits_manager.get_credits_balance(user_id)
                return jsonify(balance)
            except Exception as e:
                logger.error(f"Failed to get credits balance for {user_id}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/migration/data', methods=['POST'])
        def migrate_user_data():
            """Migrate user data and history"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                source_app = data.get('source_app')
                target_app = data.get('target_app')
                migration_options = data.get('migration_options', {})
                
                result = self.data_migration_engine.migrate_data(
                    user_id, source_app, target_app, migration_options
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to migrate user data: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/preferences/transfer', methods=['POST'])
        def transfer_preferences():
            """Transfer user preferences between apps"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                source_app = data.get('source_app')
                target_app = data.get('target_app')
                
                result = self.preference_manager.transfer_preferences(
                    user_id, source_app, target_app
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to transfer preferences: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/billing/consolidate', methods=['POST'])
        def consolidate_subscriptions():
            """Consolidate multiple subscriptions"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                subscription_ids = data.get('subscription_ids', [])
                consolidation_plan = data.get('consolidation_plan', 'optimal')
                
                result = self.subscription_consolidator.consolidate_subscriptions(
                    user_id, subscription_ids, consolidation_plan
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to consolidate subscriptions: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/billing/multi-app', methods=['POST'])
        def setup_multi_app_billing():
            """Setup multi-app single billing"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                apps = data.get('apps', [])
                billing_preferences = data.get('billing_preferences', {})
                
                result = self.multi_app_billing.setup_unified_billing(
                    user_id, apps, billing_preferences
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to setup multi-app billing: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/family/create', methods=['POST'])
        def create_family_plan():
            """Create family plan"""
            try:
                data = request.get_json()
                organizer_id = data.get('organizer_id')
                plan_type = data.get('plan_type', 'standard')
                initial_members = data.get('initial_members', [])
                
                result = self.family_plan_manager.create_family_plan(
                    organizer_id, plan_type, initial_members
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to create family plan: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/family/<family_id>/members', methods=['POST'])
        def add_family_member():
            """Add member to family plan"""
            try:
                family_id = request.view_args['family_id']
                data = request.get_json()
                member_email = data.get('member_email')
                role = data.get('role', 'member')
                
                result = self.family_plan_manager.add_member(family_id, member_email, role)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to add family member: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/discounts/student/verify', methods=['POST'])
        def verify_student_discount():
            """Verify student discount eligibility"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                verification_data = data.get('verification_data', {})
                
                result = self.student_discount_manager.verify_student_status(
                    user_id, verification_data
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to verify student discount: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/discounts/senior/verify', methods=['POST'])
        def verify_senior_discount():
            """Verify senior discount eligibility"""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                verification_data = data.get('verification_data', {})
                
                result = self.senior_discount_manager.verify_senior_status(
                    user_id, verification_data
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to verify senior discount: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/corporate/bulk-transfer', methods=['POST'])
        def initiate_bulk_corporate_transfer():
            """Initiate bulk corporate transfer"""
            try:
                data = request.get_json()
                corporate_id = data.get('corporate_id')
                user_list = data.get('user_list', [])
                transfer_options = data.get('transfer_options', {})
                
                result = self.bulk_transfer_manager.initiate_bulk_transfer(
                    corporate_id, user_list, transfer_options
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to initiate bulk corporate transfer: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/corporate/transfer-status/<transfer_batch_id>', methods=['GET'])
        def get_bulk_transfer_status(transfer_batch_id: str):
            """Get bulk transfer status"""
            try:
                status = self.bulk_transfer_manager.get_transfer_status(transfer_batch_id)
                return jsonify(status)
            except Exception as e:
                logger.error(f"Failed to get bulk transfer status: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/analytics/migration-stats', methods=['GET'])
        def get_migration_analytics():
            """Get migration analytics and statistics"""
            try:
                time_range = request.args.get('time_range', '30d')
                stats = self.membership_manager.get_migration_analytics(time_range)
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Failed to get migration analytics: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/dashboard', methods=['GET'])
        def get_dashboard_data():
            """Get dashboard metrics and status"""
            try:
                dashboard_data = self.membership_manager.get_dashboard_metrics()
                return jsonify(dashboard_data)
            except Exception as e:
                logger.error(f"Failed to get dashboard data: {e}")
                return jsonify({'error': str(e)}), 500

    def run(self):
        """Run the service"""
        try:
            logger.info("Starting Membership Migration Service on port 8336")
            self.app.run(
                host='0.0.0.0',
                port=8336,
                debug=self.config.is_development(),
                threaded=True
            )
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            logger.info("Membership Migration Service stopped")

def main():
    """Main entry point"""
    try:
        # Ensure required directories exist
        os.makedirs('/home/activeloguser/activelog/logs', exist_ok=True)
        os.makedirs('/home/activeloguser/activelog/data/membership-migration', exist_ok=True)
        
        # Initialize and run service
        service = MembershipMigrationService()
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()