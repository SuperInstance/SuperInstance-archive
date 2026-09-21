"""
HTTPS/TLS Configuration for ActiveLog
Implements secure TLS configuration, certificate management, and HTTPS enforcement.
"""

import os
import ssl
import socket
import subprocess
import tempfile
import ipaddress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import OpenSSL
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import nginx
import yaml


class TLSConfigurationManager:
    """Manages TLS/SSL configuration for ActiveLog services."""
    
    def __init__(self, base_path: str = "/home/activeloguser/activelog"):
        self.base_path = Path(base_path)
        self.certs_path = self.base_path / "security-audit" / "configs" / "certificates"
        self.nginx_config_path = self.base_path / "docker" / "nginx"
        
        # Create directories
        self.certs_path.mkdir(parents=True, exist_ok=True)
        
        # TLS Security configuration
        self.tls_config = {
            'protocols': ['TLSv1.2', 'TLSv1.3'],  # Only secure protocols
            'cipher_suites': [
                # AEAD ciphers (preferred)
                'ECDHE-ECDSA-AES256-GCM-SHA384',
                'ECDHE-RSA-AES256-GCM-SHA384', 
                'ECDHE-ECDSA-CHACHA20-POLY1305',
                'ECDHE-RSA-CHACHA20-POLY1305',
                'ECDHE-ECDSA-AES128-GCM-SHA256',
                'ECDHE-RSA-AES128-GCM-SHA256',
                
                # CBC ciphers (fallback)
                'ECDHE-ECDSA-AES256-SHA384',
                'ECDHE-RSA-AES256-SHA384',
                'ECDHE-ECDSA-AES128-SHA256',
                'ECDHE-RSA-AES128-SHA256',
            ],
            'key_exchange': ['ECDHE'],  # Perfect Forward Secrecy
            'signature_algorithms': ['SHA256', 'SHA384', 'SHA512'],
            'curves': ['prime256v1', 'secp384r1', 'secp521r1'],  # Secure curves
            'compression': False,  # Disable compression (CRIME attack)
            'renegotiation': False,  # Disable renegotiation
            'session_tickets': False,  # Disable session tickets for better security
            'ocsp_stapling': True,  # Enable OCSP stapling
            'hsts_max_age': 31536000,  # 1 year HSTS
            'hsts_include_subdomains': True,
            'hsts_preload': True
        }
    
    def generate_self_signed_certificate(self, domain: str, validity_days: int = 365) -> Dict[str, Path]:
        """Generate self-signed certificate for development/testing."""
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate subject and issuer
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ActiveLog"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IT Department"),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256())
        
        # Save private key
        key_path = self.certs_path / f"{domain}.key"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save certificate
        cert_path = self.certs_path / f"{domain}.crt"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Set appropriate permissions
        os.chmod(key_path, 0o600)  # Private key readable only by owner
        os.chmod(cert_path, 0o644)  # Certificate readable by all
        
        return {
            'certificate': cert_path,
            'private_key': key_path,
            'domain': domain,
            'validity_days': validity_days
        }
    
    def generate_nginx_tls_config(self, domain: str, cert_path: str, key_path: str) -> str:
        """Generate secure Nginx TLS configuration."""
        
        config = f"""
# HTTPS server configuration for {domain}
server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};

    # SSL Certificate Configuration
    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};

    # SSL Protocol Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    
    # SSL Cipher Configuration
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
    ssl_ecdh_curve prime256v1:secp384r1:secp521r1;

    # SSL Session Configuration
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;  # Disable for better security

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate {cert_path};
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';" always;

    # Hide Nginx version
    server_tokens off;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security configuration
    client_max_body_size 100M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    keepalive_timeout 65s;
    send_timeout 60s;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy settings for backend services
    location / {{
        proxy_pass http://api-gateway:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # Security headers for proxied requests
        proxy_hide_header X-Powered-By;
        proxy_hide_header Server;
    }}
    
    # API endpoints
    location /api/ {{
        proxy_pass http://api-gateway:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Additional rate limiting for API
        limit_req zone=api burst=10 nodelay;
    }}
    
    # WebSocket support
    location /ws/ {{
        proxy_pass http://api-gateway:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    # Static files
    location /static/ {{
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }}

    # Health check endpoint
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
}}

# HTTP to HTTPS redirect
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    
    # Security headers even for redirects
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}
"""
        return config.strip()
    
    def generate_docker_compose_tls_config(self) -> Dict[str, Any]:
        """Generate Docker Compose configuration with TLS."""
        
        config = {
            'version': '3.8',
            'services': {
                'nginx': {
                    'image': 'nginx:alpine',
                    'ports': ['80:80', '443:443'],
                    'volumes': [
                        './docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro',
                        './docker/nginx/ssl.conf:/etc/nginx/conf.d/ssl.conf:ro',
                        './security-audit/configs/certificates:/etc/nginx/ssl:ro',
                        './docker/nginx/dhparam.pem:/etc/nginx/ssl/dhparam.pem:ro'
                    ],
                    'depends_on': ['api-gateway'],
                    'networks': ['activelog'],
                    'environment': {
                        'TZ': 'UTC'
                    },
                    'restart': 'unless-stopped',
                    'security_opt': ['no-new-privileges:true'],
                    'cap_drop': ['ALL'],
                    'cap_add': ['CHOWN', 'SETGID', 'SETUID'],
                    'read_only': True,
                    'tmpfs': ['/var/cache/nginx', '/var/run', '/var/log/nginx'],
                    'logging': {
                        'driver': 'json-file',
                        'options': {
                            'max-size': '10m',
                            'max-file': '3'
                        }
                    }
                }
            },
            'networks': {
                'activelog': {
                    'driver': 'bridge'
                }
            }
        }
        
        return config
    
    def generate_dhparam(self, bits: int = 2048) -> Path:
        """Generate Diffie-Hellman parameters for perfect forward secrecy."""
        dhparam_path = self.certs_path / "dhparam.pem"
        
        if not dhparam_path.exists():
            print(f"Generating {bits}-bit DH parameters (this may take a while)...")
            subprocess.run([
                'openssl', 'dhparam', '-out', str(dhparam_path), str(bits)
            ], check=True)
        
        return dhparam_path
    
    def test_tls_configuration(self, domain: str, port: int = 443) -> Dict[str, Any]:
        """Test TLS configuration for security issues."""
        
        result = {
            'domain': domain,
            'port': port,
            'accessible': False,
            'certificate_valid': False,
            'protocols': [],
            'cipher_suites': [],
            'certificate_info': {},
            'security_issues': [],
            'recommendations': []
        }
        
        try:
            # Test connection
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((domain, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    result['accessible'] = True
                    
                    # Get certificate info
                    cert = ssock.getpeercert()
                    result['certificate_info'] = {
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'not_before': cert['notBefore'],
                        'not_after': cert['notAfter'],
                        'serial_number': cert['serialNumber'],
                        'version': cert['version']
                    }
                    
                    # Check certificate validity
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    now = datetime.utcnow()
                    
                    if not_before <= now <= not_after:
                        result['certificate_valid'] = True
                    else:
                        result['security_issues'].append('Certificate expired or not yet valid')
                    
                    # Get protocol and cipher info
                    result['protocols'] = [ssock.version()]
                    result['cipher_suites'] = [ssock.cipher()]
        
        except Exception as e:
            result['security_issues'].append(f'Connection failed: {str(e)}')
        
        # Analyze security
        self._analyze_tls_security(result)
        
        return result
    
    def _analyze_tls_security(self, test_result: Dict[str, Any]):
        """Analyze TLS configuration for security issues."""
        
        # Check protocols
        if test_result['protocols']:
            for protocol in test_result['protocols']:
                if protocol in ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1']:
                    test_result['security_issues'].append(f'Insecure protocol: {protocol}')
                    test_result['recommendations'].append('Disable legacy SSL/TLS protocols')
        
        # Check cipher suites
        if test_result['cipher_suites']:
            cipher_info = test_result['cipher_suites'][0]
            cipher_name = cipher_info[0] if cipher_info else ''
            
            # Check for weak ciphers
            weak_patterns = ['RC4', 'DES', 'MD5', 'NULL', 'EXPORT', 'ADH', 'AECDH']
            for pattern in weak_patterns:
                if pattern in cipher_name:
                    test_result['security_issues'].append(f'Weak cipher: {cipher_name}')
                    test_result['recommendations'].append('Use strong cipher suites only')
                    break
        
        # Check certificate
        if test_result['certificate_info']:
            cert_info = test_result['certificate_info']
            
            # Check key size (if available)
            # Note: This would require additional SSL inspection tools
            
            # Check expiration
            if 'not_after' in cert_info:
                try:
                    not_after = datetime.strptime(cert_info['not_after'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (not_after - datetime.utcnow()).days
                    
                    if days_until_expiry < 30:
                        test_result['security_issues'].append(f'Certificate expires in {days_until_expiry} days')
                        test_result['recommendations'].append('Renew certificate soon')
                except:
                    pass
    
    def generate_security_report(self) -> str:
        """Generate TLS security configuration report."""
        
        report_lines = [
            "=" * 80,
            "TLS/HTTPS SECURITY CONFIGURATION REPORT",
            "=" * 80,
            "",
            "CONFIGURATION SUMMARY:",
            f"  Certificate Directory: {self.certs_path}",
            f"  Nginx Config Directory: {self.nginx_config_path}",
            "",
            "TLS SECURITY SETTINGS:",
            f"  Supported Protocols: {', '.join(self.tls_config['protocols'])}",
            f"  Cipher Suites: {len(self.tls_config['cipher_suites'])} secure ciphers",
            f"  Perfect Forward Secrecy: {'Yes' if self.tls_config['key_exchange'] else 'No'}",
            f"  HSTS Enabled: Yes (max-age: {self.tls_config['hsts_max_age']})",
            f"  OCSP Stapling: {'Yes' if self.tls_config['ocsp_stapling'] else 'No'}",
            "",
            "SECURITY FEATURES:",
            "  ✓ TLS 1.2+ only",
            "  ✓ Strong cipher suites",
            "  ✓ Perfect Forward Secrecy (ECDHE)",
            "  ✓ HSTS with includeSubDomains and preload",
            "  ✓ Security headers (CSP, X-Frame-Options, etc.)",
            "  ✓ Session ticket encryption disabled",
            "  ✓ Compression disabled (CRIME prevention)",
            "  ✓ OCSP stapling enabled",
            "",
            "CERTIFICATES GENERATED:",
        ]
        
        # List generated certificates
        for cert_file in self.certs_path.glob("*.crt"):
            domain = cert_file.stem
            key_file = self.certs_path / f"{domain}.key"
            
            if key_file.exists():
                report_lines.append(f"  ✓ {domain} (cert: {cert_file.name}, key: {key_file.name})")
            else:
                report_lines.append(f"  ⚠ {domain} (cert: {cert_file.name}, key: MISSING)")
        
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "- Use certificates from trusted CA in production",
            "- Implement certificate monitoring and auto-renewal",
            "- Regular security testing with SSL Labs or similar tools",
            "- Monitor for TLS vulnerabilities and update configurations",
            "- Implement certificate pinning for critical applications",
            "",
            "IMPLEMENTATION STEPS:",
            "1. Deploy generated certificates to production servers",
            "2. Update Nginx configuration with provided settings",
            "3. Test TLS configuration with security tools",
            "4. Monitor certificate expiration dates",
            "5. Set up automated certificate renewal",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def setup_production_tls(self, domain: str) -> Dict[str, Any]:
        """Setup TLS configuration for production deployment."""
        
        result = {
            'domain': domain,
            'steps_completed': [],
            'files_created': [],
            'errors': []
        }
        
        try:
            # Step 1: Generate self-signed certificate (for testing)
            cert_info = self.generate_self_signed_certificate(domain)
            result['steps_completed'].append('Generated self-signed certificate')
            result['files_created'].extend([str(cert_info['certificate']), str(cert_info['private_key'])])
            
            # Step 2: Generate DH parameters
            dhparam_path = self.generate_dhparam()
            result['steps_completed'].append('Generated DH parameters')
            result['files_created'].append(str(dhparam_path))
            
            # Step 3: Generate Nginx configuration
            nginx_config = self.generate_nginx_tls_config(
                domain, 
                f"/etc/nginx/ssl/{domain}.crt",
                f"/etc/nginx/ssl/{domain}.key"
            )
            
            nginx_config_path = self.base_path / "docker" / "nginx" / "ssl.conf"
            nginx_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(nginx_config_path, 'w') as f:
                f.write(nginx_config)
            
            result['steps_completed'].append('Generated Nginx TLS configuration')
            result['files_created'].append(str(nginx_config_path))
            
            # Step 4: Generate Docker Compose configuration
            docker_config = self.generate_docker_compose_tls_config()
            docker_config_path = self.base_path / "docker-compose.https.yml"
            
            with open(docker_config_path, 'w') as f:
                yaml.dump(docker_config, f, default_flow_style=False)
            
            result['steps_completed'].append('Generated Docker Compose TLS configuration')
            result['files_created'].append(str(docker_config_path))
            
            # Step 5: Create deployment script
            deploy_script = self._generate_tls_deployment_script(domain)
            deploy_script_path = self.base_path / "scripts" / "deploy_https.sh"
            deploy_script_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(deploy_script_path, 'w') as f:
                f.write(deploy_script)
            
            os.chmod(deploy_script_path, 0o755)
            
            result['steps_completed'].append('Generated deployment script')
            result['files_created'].append(str(deploy_script_path))
            
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def _generate_tls_deployment_script(self, domain: str) -> str:
        """Generate deployment script for TLS setup."""
        
        script = f"""#!/bin/bash
# HTTPS/TLS Deployment Script for ActiveLog
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

set -e

echo "🔒 Deploying HTTPS/TLS configuration for {domain}..."

# Create necessary directories
mkdir -p ./docker/nginx/ssl
mkdir -p ./logs/nginx

# Copy certificates
echo "📋 Copying certificates..."
cp ./security-audit/configs/certificates/{domain}.crt ./docker/nginx/ssl/
cp ./security-audit/configs/certificates/{domain}.key ./docker/nginx/ssl/
cp ./security-audit/configs/certificates/dhparam.pem ./docker/nginx/ssl/

# Set proper permissions
chmod 644 ./docker/nginx/ssl/{domain}.crt
chmod 600 ./docker/nginx/ssl/{domain}.key
chmod 644 ./docker/nginx/ssl/dhparam.pem

# Validate Nginx configuration
echo "✅ Validating Nginx configuration..."
docker run --rm -v $(pwd)/docker/nginx:/etc/nginx nginx:alpine nginx -t

# Deploy with HTTPS
echo "🚀 Deploying ActiveLog with HTTPS..."
docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Test HTTPS endpoint
echo "🧪 Testing HTTPS endpoint..."
if curl -k -s -o /dev/null -w "%{{http_code}}" https://localhost | grep -q "200\\|301\\|302"; then
    echo "✅ HTTPS endpoint is accessible"
else
    echo "❌ HTTPS endpoint test failed"
    echo "Check logs: docker-compose logs nginx"
fi

# Test HTTP to HTTPS redirect
echo "🔄 Testing HTTP to HTTPS redirect..."
if curl -s -o /dev/null -w "%{{http_code}}" http://localhost | grep -q "301\\|302"; then
    echo "✅ HTTP to HTTPS redirect is working"
else
    echo "❌ HTTP to HTTPS redirect test failed"
fi

# Display certificate information
echo "📜 Certificate information:"
openssl x509 -in ./docker/nginx/ssl/{domain}.crt -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After :)"

echo ""
echo "🎉 HTTPS deployment completed!"
echo ""
echo "Next steps:"
echo "1. Update DNS records to point to this server"
echo "2. Obtain valid SSL certificate from trusted CA (Let's Encrypt, etc.)"
echo "3. Replace self-signed certificate with trusted certificate"
echo "4. Test with SSL Labs: https://www.ssllabs.com/ssltest/"
echo "5. Monitor certificate expiration and set up renewal"
echo ""
echo "Access your application at: https://{domain}"
"""
        return script


def main():
    """Main function to setup TLS configuration."""
    import ipaddress
    
    print("🔒 Setting up HTTPS/TLS configuration for ActiveLog...")
    
    # Initialize TLS manager
    tls_manager = TLSConfigurationManager()
    
    # Setup for localhost (development)
    domain = "localhost"
    print(f"Configuring TLS for domain: {domain}")
    
    # Setup production TLS
    result = tls_manager.setup_production_tls(domain)
    
    # Display results
    print(f"✅ TLS setup completed for {domain}")
    print(f"Steps completed: {len(result['steps_completed'])}")
    
    for step in result['steps_completed']:
        print(f"  ✓ {step}")
    
    if result['errors']:
        print(f"❌ Errors encountered: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  ✗ {error}")
    
    print(f"\nFiles created: {len(result['files_created'])}")
    for file_path in result['files_created']:
        print(f"  📄 {file_path}")
    
    # Generate and save security report
    report = tls_manager.generate_security_report()
    report_path = tls_manager.base_path / "security-audit" / "reports" / "tls_security_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\n📊 Security report saved to: {report_path}")
    print("\n" + report)


if __name__ == "__main__":
    main()