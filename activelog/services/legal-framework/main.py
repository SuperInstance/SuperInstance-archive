#!/usr/bin/env python3
"""
ActiveLog Legal Framework Service
Comprehensive legal management system providing IP protection, licensing, compliance,
and contract management for ActiveLog ecosystem
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import legal framework components
from core.legal_manager import LegalManager
from ip.ip_protection import IPProtectionManager
from licensing.license_manager import LicenseManager
from templates.document_generator import DocumentGenerator
from gdpr.compliance_manager import GDPRComplianceManager
from partnerships.partnership_manager import PartnershipManager
from acquisition.acquisition_manager import AcquisitionManager
from revenue.revenue_sharing import RevenueSharingManager
from trademark.trademark_manager import TrademarkManager
from patents.patent_manager import PatentManager
from escrow.escrow_manager import EscrowManager
from compliance.audit_manager import ComplianceAuditManager
from config.settings import LegalFrameworkConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/legal-framework.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class LegalFrameworkService:
    """Main legal framework service orchestrating all legal tools and compliance systems"""
    
    def __init__(self):
        self.config = LegalFrameworkConfig()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize core components
        self.legal_manager = LegalManager(self.config)
        self.ip_protection = IPProtectionManager(self.config)
        self.license_manager = LicenseManager(self.config)
        self.document_generator = DocumentGenerator(self.config)
        self.gdpr_compliance = GDPRComplianceManager(self.config)
        self.partnership_manager = PartnershipManager(self.config)
        self.acquisition_manager = AcquisitionManager(self.config)
        self.revenue_sharing = RevenueSharingManager(self.config)
        self.trademark_manager = TrademarkManager(self.config)
        self.patent_manager = PatentManager(self.config)
        self.escrow_manager = EscrowManager(self.config)
        self.compliance_audit = ComplianceAuditManager(self.config)
        
        self._setup_routes()
        logger.info("Legal Framework Service initialized")

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'legal-framework',
                    'version': '1.0.0',
                    'port': 8343
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503

        # Intellectual Property routes
        @self.app.route('/ip/protect', methods=['POST'])
        def protect_ip():
            """Protect intellectual property"""
            try:
                data = request.get_json()
                result = self.ip_protection.protect_asset(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to protect IP: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/ip/assets', methods=['GET'])
        def list_ip_assets():
            """List protected IP assets"""
            try:
                assets = self.ip_protection.list_assets()
                return jsonify(assets)
            except Exception as e:
                logger.error(f"Failed to list IP assets: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/ip/assets/<asset_id>', methods=['GET'])
        def get_ip_asset(asset_id: str):
            """Get specific IP asset details"""
            try:
                asset = self.ip_protection.get_asset(asset_id)
                return jsonify(asset)
            except Exception as e:
                logger.error(f"Failed to get IP asset {asset_id}: {e}")
                return jsonify({'error': str(e)}), 500

        # Licensing routes
        @self.app.route('/licensing/create', methods=['POST'])
        def create_license():
            """Create new license"""
            try:
                data = request.get_json()
                result = self.license_manager.create_license(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to create license: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/licensing/licenses', methods=['GET'])
        def list_licenses():
            """List all licenses"""
            try:
                licenses = self.license_manager.list_licenses()
                return jsonify(licenses)
            except Exception as e:
                logger.error(f"Failed to list licenses: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/licensing/validate/<license_key>', methods=['GET'])
        def validate_license(license_key: str):
            """Validate license key"""
            try:
                validation = self.license_manager.validate_license(license_key)
                return jsonify(validation)
            except Exception as e:
                logger.error(f"Failed to validate license {license_key}: {e}")
                return jsonify({'error': str(e)}), 500

        # Document generation routes
        @self.app.route('/documents/generate', methods=['POST'])
        def generate_document():
            """Generate legal document"""
            try:
                data = request.get_json()
                result = self.document_generator.generate_document(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to generate document: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/documents/templates', methods=['GET'])
        def list_templates():
            """List available document templates"""
            try:
                templates = self.document_generator.list_templates()
                return jsonify(templates)
            except Exception as e:
                logger.error(f"Failed to list templates: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/documents/tos/generate', methods=['POST'])
        def generate_tos():
            """Generate terms of service"""
            try:
                data = request.get_json()
                result = self.document_generator.generate_terms_of_service(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to generate ToS: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/documents/privacy/generate', methods=['POST'])
        def generate_privacy_policy():
            """Generate privacy policy"""
            try:
                data = request.get_json()
                result = self.document_generator.generate_privacy_policy(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to generate privacy policy: {e}")
                return jsonify({'error': str(e)}), 500

        # GDPR compliance routes
        @self.app.route('/gdpr/assess', methods=['POST'])
        def assess_gdpr_compliance():
            """Assess GDPR compliance"""
            try:
                data = request.get_json()
                assessment = self.gdpr_compliance.assess_compliance(data)
                return jsonify(assessment)
            except Exception as e:
                logger.error(f"Failed to assess GDPR compliance: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/gdpr/data-request', methods=['POST'])
        def handle_data_request():
            """Handle GDPR data request"""
            try:
                data = request.get_json()
                result = self.gdpr_compliance.handle_data_request(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to handle data request: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/gdpr/consent', methods=['POST'])
        def manage_consent():
            """Manage GDPR consent"""
            try:
                data = request.get_json()
                result = self.gdpr_compliance.manage_consent(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to manage consent: {e}")
                return jsonify({'error': str(e)}), 500

        # Partnership routes
        @self.app.route('/partnerships/create', methods=['POST'])
        def create_partnership():
            """Create partnership agreement"""
            try:
                data = request.get_json()
                result = self.partnership_manager.create_partnership(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to create partnership: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/partnerships', methods=['GET'])
        def list_partnerships():
            """List partnerships"""
            try:
                partnerships = self.partnership_manager.list_partnerships()
                return jsonify(partnerships)
            except Exception as e:
                logger.error(f"Failed to list partnerships: {e}")
                return jsonify({'error': str(e)}), 500

        # Acquisition routes
        @self.app.route('/acquisition/prepare', methods=['POST'])
        def prepare_acquisition():
            """Prepare acquisition package"""
            try:
                data = request.get_json()
                result = self.acquisition_manager.prepare_package(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to prepare acquisition: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/acquisition/due-diligence', methods=['POST'])
        def conduct_due_diligence():
            """Conduct due diligence"""
            try:
                data = request.get_json()
                result = self.acquisition_manager.conduct_due_diligence(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to conduct due diligence: {e}")
                return jsonify({'error': str(e)}), 500

        # Revenue sharing routes
        @self.app.route('/revenue/create-contract', methods=['POST'])
        def create_revenue_contract():
            """Create revenue sharing contract"""
            try:
                data = request.get_json()
                result = self.revenue_sharing.create_contract(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to create revenue contract: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/revenue/calculate', methods=['POST'])
        def calculate_revenue_share():
            """Calculate revenue sharing"""
            try:
                data = request.get_json()
                calculation = self.revenue_sharing.calculate_share(data)
                return jsonify(calculation)
            except Exception as e:
                logger.error(f"Failed to calculate revenue share: {e}")
                return jsonify({'error': str(e)}), 500

        # Trademark routes
        @self.app.route('/trademark/register', methods=['POST'])
        def register_trademark():
            """Register trademark"""
            try:
                data = request.get_json()
                result = self.trademark_manager.register_trademark(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to register trademark: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/trademark/search', methods=['POST'])
        def search_trademarks():
            """Search existing trademarks"""
            try:
                data = request.get_json()
                results = self.trademark_manager.search_trademarks(data)
                return jsonify(results)
            except Exception as e:
                logger.error(f"Failed to search trademarks: {e}")
                return jsonify({'error': str(e)}), 500

        # Patent routes
        @self.app.route('/patents/file', methods=['POST'])
        def file_patent():
            """File patent application"""
            try:
                data = request.get_json()
                result = self.patent_manager.file_patent(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to file patent: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/patents/prior-art', methods=['POST'])
        def search_prior_art():
            """Search prior art"""
            try:
                data = request.get_json()
                results = self.patent_manager.search_prior_art(data)
                return jsonify(results)
            except Exception as e:
                logger.error(f"Failed to search prior art: {e}")
                return jsonify({'error': str(e)}), 500

        # Code escrow routes
        @self.app.route('/escrow/create', methods=['POST'])
        def create_escrow():
            """Create code escrow agreement"""
            try:
                data = request.get_json()
                result = self.escrow_manager.create_escrow(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to create escrow: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/escrow/deposit', methods=['POST'])
        def deposit_code():
            """Deposit code to escrow"""
            try:
                data = request.get_json()
                result = self.escrow_manager.deposit_code(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to deposit code: {e}")
                return jsonify({'error': str(e)}), 500

        # Compliance audit routes
        @self.app.route('/compliance/audit', methods=['POST'])
        def conduct_audit():
            """Conduct compliance audit"""
            try:
                data = request.get_json()
                result = self.compliance_audit.conduct_audit(data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to conduct audit: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/compliance/report', methods=['GET'])
        def get_compliance_report():
            """Get compliance report"""
            try:
                report_type = request.args.get('type', 'full')
                report = self.compliance_audit.generate_report(report_type)
                return jsonify(report)
            except Exception as e:
                logger.error(f"Failed to get compliance report: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/legal/dashboard', methods=['GET'])
        def get_legal_dashboard():
            """Get legal dashboard overview"""
            try:
                dashboard = self.legal_manager.get_dashboard()
                return jsonify(dashboard)
            except Exception as e:
                logger.error(f"Failed to get legal dashboard: {e}")
                return jsonify({'error': str(e)}), 500

    def run(self):
        """Run the legal framework service"""
        try:
            logger.info("Starting Legal Framework Service on port 8343")
            self.app.run(
                host='0.0.0.0',
                port=8343,
                debug=self.config.is_development(),
                threaded=True
            )
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            logger.info("Legal Framework Service stopped")


def main():
    """Main entry point"""
    try:
        # Ensure required directories exist
        os.makedirs('/home/activeloguser/activelog/logs', exist_ok=True)
        os.makedirs('/home/activeloguser/activelog/data/legal-framework', exist_ok=True)
        
        # Initialize and run service
        service = LegalFrameworkService()
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()