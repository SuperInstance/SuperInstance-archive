#!/usr/bin/env python3
"""
DNS Configuration Automation Manager
Manages Route 53 DNS configuration, domain setup, and subdomain management
"""

import os
import json
import boto3
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class DNSRecord:
    name: str
    record_type: str
    value: str
    ttl: int = 300
    weight: Optional[int] = None
    set_identifier: Optional[str] = None
    health_check_id: Optional[str] = None

@dataclass
class DomainConfig:
    domain_name: str
    hosted_zone_id: str
    subdomains: List[str]
    load_balancer_dns: str
    cloudfront_dns: str
    verification_records: List[DNSRecord]

class DNSManager:
    """Comprehensive DNS management and automation"""
    
    def __init__(self, domain_name: str = "activelog.com"):
        self.domain_name = domain_name
        self.route53 = boto3.client('route53')
        self.acm = boto3.client('acm')
        self.cloudfront = boto3.client('cloudfront')
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'/home/activeloguser/activelog/logs/dns-manager-{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_dns_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Complete DNS setup and configuration"""
        try:
            self.logger.info(f"Setting up DNS configuration for {self.domain_name}")
            
            results = {
                'domain': self.domain_name,
                'setup_started': datetime.now().isoformat(),
                'steps_completed': [],
                'errors': [],
                'dns_records': []
            }
            
            # Step 1: Create or get hosted zone
            hosted_zone_result = self._create_or_get_hosted_zone()
            if hosted_zone_result['success']:
                results['hosted_zone_id'] = hosted_zone_result['hosted_zone_id']
                results['steps_completed'].append('hosted_zone')
                self.logger.info(f"✓ Hosted zone ready: {hosted_zone_result['hosted_zone_id']}")
            else:
                results['errors'].append(f"Hosted zone setup failed: {hosted_zone_result['error']}")
                return results
            
            # Step 2: Setup main domain records
            main_records_result = self._setup_main_domain_records(
                hosted_zone_result['hosted_zone_id'],
                config.get('load_balancer_dns', ''),
                config.get('cloudfront_dns', '')
            )
            if main_records_result['success']:
                results['dns_records'].extend(main_records_result['records'])
                results['steps_completed'].append('main_domain_records')
                self.logger.info("✓ Main domain records configured")
            
            # Step 3: Setup subdomain records
            subdomains = config.get('subdomains', [
                'api', 'www', 'app', 'admin', 'docs', 'cdn', 'files'
            ])
            
            for subdomain in subdomains:
                subdomain_result = self._setup_subdomain(
                    hosted_zone_result['hosted_zone_id'],
                    subdomain,
                    config.get('load_balancer_dns', ''),
                    config.get('cloudfront_dns', '')
                )
                if subdomain_result['success']:
                    results['dns_records'].extend(subdomain_result['records'])
                    self.logger.info(f"✓ Subdomain configured: {subdomain}")
            
            results['steps_completed'].append('subdomain_records')
            
            # Step 4: Setup email records (MX, SPF, DKIM)
            email_result = self._setup_email_records(hosted_zone_result['hosted_zone_id'])
            if email_result['success']:
                results['dns_records'].extend(email_result['records'])
                results['steps_completed'].append('email_records')
                self.logger.info("✓ Email records configured")
            
            # Step 5: Setup security records (CAA)
            security_result = self._setup_security_records(hosted_zone_result['hosted_zone_id'])
            if security_result['success']:
                results['dns_records'].extend(security_result['records'])
                results['steps_completed'].append('security_records')
                self.logger.info("✓ Security records configured")
            
            # Step 6: Setup health checks
            health_check_result = self._setup_health_checks(config)
            if health_check_result['success']:
                results['health_checks'] = health_check_result['health_checks']
                results['steps_completed'].append('health_checks')
                self.logger.info("✓ Health checks configured")
            
            # Step 7: Verify DNS propagation
            verification_result = self._verify_dns_propagation(results['dns_records'])
            if verification_result['success']:
                results['steps_completed'].append('dns_verification')
                results['propagation_status'] = verification_result['status']
                self.logger.info("✓ DNS propagation verified")
            
            results['setup_completed'] = datetime.now().isoformat()
            results['success'] = len(results['errors']) == 0
            
            return results
            
        except Exception as e:
            self.logger.error(f"DNS setup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'domain': self.domain_name
            }
    
    def _create_or_get_hosted_zone(self) -> Dict[str, Any]:
        """Create or get existing hosted zone"""
        try:
            # Check if hosted zone already exists
            response = self.route53.list_hosted_zones_by_name(DNSName=self.domain_name)
            
            existing_zone = None
            for zone in response['HostedZones']:
                if zone['Name'].rstrip('.') == self.domain_name:
                    existing_zone = zone
                    break
            
            if existing_zone:
                return {
                    'success': True,
                    'hosted_zone_id': existing_zone['Id'].split('/')[-1],
                    'existing': True
                }
            
            # Create new hosted zone
            create_response = self.route53.create_hosted_zone(
                Name=self.domain_name,
                CallerReference=str(int(time.time())),
                HostedZoneConfig={
                    'Comment': f'Hosted zone for {self.domain_name} - ActiveLog Production',
                    'PrivateZone': False
                }
            )
            
            hosted_zone_id = create_response['HostedZone']['Id'].split('/')[-1]
            
            # Get name servers
            ns_response = self.route53.get_hosted_zone(Id=hosted_zone_id)
            name_servers = ns_response['DelegationSet']['NameServers']
            
            return {
                'success': True,
                'hosted_zone_id': hosted_zone_id,
                'existing': False,
                'name_servers': name_servers
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _setup_main_domain_records(self, hosted_zone_id: str, 
                                 load_balancer_dns: str, cloudfront_dns: str) -> Dict[str, Any]:
        """Setup main domain DNS records"""
        try:
            records_created = []
            
            # Root domain A record (apex) - points to CloudFront or ALB
            if cloudfront_dns:
                # Use ALIAS record for CloudFront
                change_batch = {
                    'Comment': 'Root domain ALIAS to CloudFront',
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': self.domain_name,
                            'Type': 'A',
                            'AliasTarget': {
                                'DNSName': cloudfront_dns,
                                'EvaluateTargetHealth': False,
                                'HostedZoneId': 'Z2FDTNDATAQYW2'  # CloudFront hosted zone ID
                            }
                        }
                    }]
                }
            elif load_balancer_dns:
                # Use ALIAS record for ALB
                change_batch = {
                    'Comment': 'Root domain ALIAS to ALB',
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': self.domain_name,
                            'Type': 'A',
                            'AliasTarget': {
                                'DNSName': load_balancer_dns,
                                'EvaluateTargetHealth': True,
                                'HostedZoneId': self._get_alb_zone_id()
                            }
                        }
                    }]
                }
            else:
                return {'success': False, 'error': 'No target DNS provided'}
            
            response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch
            )
            
            records_created.append({
                'name': self.domain_name,
                'type': 'A',
                'target': cloudfront_dns or load_balancer_dns,
                'change_id': response['ChangeInfo']['Id']
            })
            
            return {
                'success': True,
                'records': records_created
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _setup_subdomain(self, hosted_zone_id: str, subdomain: str, 
                        load_balancer_dns: str, cloudfront_dns: str) -> Dict[str, Any]:
        """Setup individual subdomain"""
        try:
            full_domain = f"{subdomain}.{self.domain_name}"
            records_created = []
            
            # Determine target based on subdomain type
            if subdomain in ['cdn', 'files', 'assets']:
                # Static content subdomains -> CloudFront
                target_dns = cloudfront_dns
                zone_id = 'Z2FDTNDATAQYW2'  # CloudFront
            else:
                # API and app subdomains -> ALB
                target_dns = load_balancer_dns
                zone_id = self._get_alb_zone_id()
            
            if not target_dns:
                # Fallback to CNAME to main domain
                change_batch = {
                    'Comment': f'CNAME record for {subdomain}',
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': full_domain,
                            'Type': 'CNAME',
                            'TTL': 300,
                            'ResourceRecords': [{'Value': self.domain_name}]
                        }
                    }]
                }
            else:
                # ALIAS record
                change_batch = {
                    'Comment': f'ALIAS record for {subdomain}',
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': full_domain,
                            'Type': 'A',
                            'AliasTarget': {
                                'DNSName': target_dns,
                                'EvaluateTargetHealth': True,
                                'HostedZoneId': zone_id
                            }
                        }
                    }]
                }
            
            response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch
            )
            
            records_created.append({
                'name': full_domain,
                'type': 'A' if target_dns else 'CNAME',
                'target': target_dns or self.domain_name,
                'change_id': response['ChangeInfo']['Id']
            })
            
            return {
                'success': True,
                'records': records_created
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _setup_email_records(self, hosted_zone_id: str) -> Dict[str, Any]:
        """Setup email-related DNS records"""
        try:
            records_created = []
            
            # MX Records for email
            mx_change = {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': self.domain_name,
                    'Type': 'MX',
                    'TTL': 3600,
                    'ResourceRecords': [
                        {'Value': '10 mail.activelog.com'},
                        {'Value': '20 mail2.activelog.com'}
                    ]
                }
            }
            
            # SPF Record
            spf_change = {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': self.domain_name,
                    'Type': 'TXT',
                    'TTL': 3600,
                    'ResourceRecords': [
                        {'Value': '"v=spf1 include:_spf.google.com include:mailgun.org ~all"'}
                    ]
                }
            }
            
            # DMARC Record
            dmarc_change = {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': f'_dmarc.{self.domain_name}',
                    'Type': 'TXT',
                    'TTL': 3600,
                    'ResourceRecords': [
                        {'Value': '"v=DMARC1; p=quarantine; rua=mailto:dmarc@activelog.com"'}
                    ]
                }
            }
            
            # Apply all email records
            change_batch = {
                'Comment': 'Email DNS records',
                'Changes': [mx_change, spf_change, dmarc_change]
            }
            
            response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch
            )
            
            records_created.extend([
                {'name': self.domain_name, 'type': 'MX', 'description': 'Mail exchange'},
                {'name': self.domain_name, 'type': 'TXT', 'description': 'SPF record'},
                {'name': f'_dmarc.{self.domain_name}', 'type': 'TXT', 'description': 'DMARC policy'}
            ])
            
            return {
                'success': True,
                'records': records_created,
                'change_id': response['ChangeInfo']['Id']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _setup_security_records(self, hosted_zone_id: str) -> Dict[str, Any]:
        """Setup security-related DNS records"""
        try:
            records_created = []
            
            # CAA Records for certificate authority authorization
            caa_changes = []
            
            # Allow Let's Encrypt
            caa_changes.append({
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': self.domain_name,
                    'Type': 'CAA',
                    'TTL': 3600,
                    'ResourceRecords': [
                        {'Value': '0 issue "letsencrypt.org"'},
                        {'Value': '0 issue "amazon.com"'},
                        {'Value': '0 iodef "mailto:security@activelog.com"'}
                    ]
                }
            })
            
            change_batch = {
                'Comment': 'Security DNS records (CAA)',
                'Changes': caa_changes
            }
            
            response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch
            )
            
            records_created.append({
                'name': self.domain_name,
                'type': 'CAA',
                'description': 'Certificate authority authorization'
            })
            
            return {
                'success': True,
                'records': records_created,
                'change_id': response['ChangeInfo']['Id']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _setup_health_checks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Setup Route 53 health checks"""
        try:
            health_checks_created = []
            
            # Health check for main domain
            if config.get('load_balancer_dns'):
                health_check = self.route53.create_health_check(
                    Type='HTTPS',
                    ResourcePath='/health',
                    FullyQualifiedDomainName=config['load_balancer_dns'],
                    Port=443,
                    RequestInterval=30,
                    FailureThreshold=3,
                    CloudWatchAlarmRegion='us-east-1'
                )
                
                health_checks_created.append({
                    'id': health_check['HealthCheck']['Id'],
                    'type': 'HTTPS',
                    'target': config['load_balancer_dns'],
                    'path': '/health'
                })
            
            # Health check for API subdomain
            if config.get('api_endpoint'):
                api_health_check = self.route53.create_health_check(
                    Type='HTTPS',
                    ResourcePath='/api/health',
                    FullyQualifiedDomainName=f"api.{self.domain_name}",
                    Port=443,
                    RequestInterval=30,
                    FailureThreshold=3
                )
                
                health_checks_created.append({
                    'id': api_health_check['HealthCheck']['Id'],
                    'type': 'HTTPS',
                    'target': f"api.{self.domain_name}",
                    'path': '/api/health'
                })
            
            return {
                'success': True,
                'health_checks': health_checks_created
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _verify_dns_propagation(self, dns_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify DNS record propagation"""
        try:
            propagation_results = []
            
            for record in dns_records[:5]:  # Check first 5 records
                record_name = record['name']
                record_type = record['type']
                
                try:
                    # Use dig command to check DNS resolution
                    import subprocess
                    result = subprocess.run(
                        ['dig', '+short', record_name, record_type],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    propagation_results.append({
                        'name': record_name,
                        'type': record_type,
                        'resolved': len(result.stdout.strip()) > 0,
                        'response': result.stdout.strip()
                    })
                    
                except subprocess.TimeoutExpired:
                    propagation_results.append({
                        'name': record_name,
                        'type': record_type,
                        'resolved': False,
                        'error': 'Timeout'
                    })
                except Exception as e:
                    propagation_results.append({
                        'name': record_name,
                        'type': record_type,
                        'resolved': False,
                        'error': str(e)
                    })
            
            successful_propagations = sum(1 for result in propagation_results if result['resolved'])
            
            return {
                'success': True,
                'status': {
                    'total_checked': len(propagation_results),
                    'successful': successful_propagations,
                    'propagation_percentage': (successful_propagations / max(len(propagation_results), 1)) * 100
                },
                'results': propagation_results
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_alb_zone_id(self) -> str:
        """Get ALB hosted zone ID based on region"""
        # AWS ALB hosted zone IDs by region
        alb_zone_ids = {
            'us-east-1': 'Z35SXDOTRQ7X7K',
            'us-west-2': 'Z1D633PJN98FT9',
            'eu-west-1': 'Z32O12XQLNTSW2',
            'ap-southeast-1': 'Z1LMS91P8CMLE5'
        }
        return alb_zone_ids.get('us-east-1', 'Z35SXDOTRQ7X7K')  # Default to us-east-1
    
    def export_dns_configuration(self, output_file: str) -> Dict[str, Any]:
        """Export current DNS configuration"""
        try:
            # Get hosted zone
            zones = self.route53.list_hosted_zones_by_name(DNSName=self.domain_name)
            
            if not zones['HostedZones']:
                return {'success': False, 'error': 'No hosted zone found'}
            
            hosted_zone_id = zones['HostedZones'][0]['Id'].split('/')[-1]
            
            # Get all records
            records_response = self.route53.list_resource_record_sets(HostedZoneId=hosted_zone_id)
            
            dns_config = {
                'domain': self.domain_name,
                'hosted_zone_id': hosted_zone_id,
                'exported_at': datetime.now().isoformat(),
                'records': []
            }
            
            for record in records_response['ResourceRecordSets']:
                dns_config['records'].append({
                    'name': record['Name'],
                    'type': record['Type'],
                    'ttl': record.get('TTL'),
                    'values': [rr['Value'] for rr in record.get('ResourceRecords', [])],
                    'alias_target': record.get('AliasTarget')
                })
            
            # Save to file
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(dns_config, f, indent=2)
            
            return {
                'success': True,
                'config_file': output_file,
                'records_count': len(dns_config['records'])
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_dns_setup(self) -> Dict[str, Any]:
        """Validate DNS configuration"""
        validation_results = {
            'domain': self.domain_name,
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'overall_status': 'unknown'
        }
        
        checks = [
            ('Hosted Zone Exists', self._check_hosted_zone),
            ('Root Domain Resolution', self._check_root_domain),
            ('WWW Subdomain', self._check_www_subdomain),
            ('API Subdomain', self._check_api_subdomain),
            ('Email Records (MX)', self._check_mx_records),
            ('SPF Record', self._check_spf_record),
            ('Security Records (CAA)', self._check_caa_records)
        ]
        
        passed_checks = 0
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                validation_results['checks'].append({
                    'name': check_name,
                    'status': 'passed' if result['passed'] else 'failed',
                    'details': result.get('details', ''),
                    'recommendations': result.get('recommendations', [])
                })
                
                if result['passed']:
                    passed_checks += 1
                    
            except Exception as e:
                validation_results['checks'].append({
                    'name': check_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        validation_results['passed_checks'] = passed_checks
        validation_results['total_checks'] = len(checks)
        validation_results['overall_status'] = 'passed' if passed_checks == len(checks) else 'failed'
        
        return validation_results
    
    def _check_hosted_zone(self) -> Dict[str, Any]:
        """Check if hosted zone exists"""
        try:
            zones = self.route53.list_hosted_zones_by_name(DNSName=self.domain_name)
            return {
                'passed': len(zones['HostedZones']) > 0,
                'details': f"Found {len(zones['HostedZones'])} hosted zones"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}
    
    def _check_root_domain(self) -> Dict[str, Any]:
        """Check root domain resolution"""
        try:
            import subprocess
            result = subprocess.run(['dig', '+short', self.domain_name, 'A'], 
                                  capture_output=True, text=True, timeout=10)
            
            return {
                'passed': len(result.stdout.strip()) > 0,
                'details': f"Root domain resolves to: {result.stdout.strip()}"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}
    
    def _check_www_subdomain(self) -> Dict[str, Any]:
        """Check www subdomain resolution"""
        try:
            import subprocess
            result = subprocess.run(['dig', '+short', f'www.{self.domain_name}', 'A'], 
                                  capture_output=True, text=True, timeout=10)
            
            return {
                'passed': len(result.stdout.strip()) > 0,
                'details': f"WWW subdomain resolves to: {result.stdout.strip()}"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}
    
    def _check_api_subdomain(self) -> Dict[str, Any]:
        """Check API subdomain resolution"""
        try:
            import subprocess
            result = subprocess.run(['dig', '+short', f'api.{self.domain_name}', 'A'], 
                                  capture_output=True, text=True, timeout=10)
            
            return {
                'passed': len(result.stdout.strip()) > 0,
                'details': f"API subdomain resolves to: {result.stdout.strip()}"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}
    
    def _check_mx_records(self) -> Dict[str, Any]:
        """Check MX records"""
        try:
            import subprocess
            result = subprocess.run(['dig', '+short', self.domain_name, 'MX'], 
                                  capture_output=True, text=True, timeout=10)
            
            return {
                'passed': len(result.stdout.strip()) > 0,
                'details': f"MX records: {result.stdout.strip()}"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}
    
    def _check_spf_record(self) -> Dict[str, Any]:
        """Check SPF record"""
        try:
            import subprocess
            result = subprocess.run(['dig', '+short', self.domain_name, 'TXT'], 
                                  capture_output=True, text=True, timeout=10)
            
            spf_found = any('v=spf1' in line for line in result.stdout.splitlines())
            
            return {
                'passed': spf_found,
                'details': f"SPF record {'found' if spf_found else 'not found'}"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}
    
    def _check_caa_records(self) -> Dict[str, Any]:
        """Check CAA records"""
        try:
            import subprocess
            result = subprocess.run(['dig', '+short', self.domain_name, 'CAA'], 
                                  capture_output=True, text=True, timeout=10)
            
            return {
                'passed': len(result.stdout.strip()) > 0,
                'details': f"CAA records: {result.stdout.strip()}"
            }
        except Exception as e:
            return {'passed': False, 'details': str(e)}

def main():
    """Main function for DNS setup"""
    dns_manager = DNSManager("activelog.com")
    
    print("🌐 Starting ActiveLog DNS Configuration")
    print("=" * 50)
    
    # Example configuration
    config = {
        'load_balancer_dns': 'activelog-production-alb-123456789.us-east-1.elb.amazonaws.com',
        'cloudfront_dns': 'd123456789.cloudfront.net',
        'subdomains': ['api', 'www', 'app', 'admin', 'docs', 'cdn'],
        'api_endpoint': 'api.activelog.com'
    }
    
    # Setup DNS configuration
    result = dns_manager.setup_dns_configuration(config)
    
    if result['success']:
        print("✅ DNS configuration completed successfully!")
        print(f"Records created: {len(result.get('dns_records', []))}")
        for step in result['steps_completed']:
            print(f"  ✓ {step}")
    else:
        print("❌ DNS configuration failed!")
        for error in result.get('errors', []):
            print(f"  - {error}")
    
    # Validate DNS setup
    print("\n🔍 Validating DNS configuration...")
    validation = dns_manager.validate_dns_setup()
    
    print(f"Validation: {validation['passed_checks']}/{validation['total_checks']} checks passed")
    
    for check in validation['checks']:
        status_emoji = "✅" if check['status'] == 'passed' else "❌"
        print(f"{status_emoji} {check['name']}: {check.get('details', check.get('error', ''))}")

if __name__ == "__main__":
    main()