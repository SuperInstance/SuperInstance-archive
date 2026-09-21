#!/bin/bash

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

# Install Python 3.9
yum install -y python3 python3-pip

# Install Git
yum install -y git

# Create application directory
mkdir -p /opt/activelog
cd /opt/activelog

# Set environment variables
echo "export DOMAIN_NAME=${domain_name}" >> /etc/environment
echo "export ENVIRONMENT=${environment}" >> /etc/environment
echo "export AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)" >> /etc/environment

# Download application from S3 (placeholder)
# aws s3 cp s3://activelog-artifacts/${domain_name}/ /opt/activelog/ --recursive

# Create a simple health check endpoint
cat > /opt/activelog/health_check.py << 'EOF'
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'healthy', 'domain': '${domain_name}', 'environment': '${environment}'}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    server.serve_forever()
EOF

chmod +x /opt/activelog/health_check.py

# Create systemd service for health check
cat > /etc/systemd/system/activelog-health.service << EOF
[Unit]
Description=ActiveLog Health Check Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/activelog
ExecStart=/usr/bin/python3 /opt/activelog/health_check.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the health check service
systemctl daemon-reload
systemctl enable activelog-health
systemctl start activelog-health

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "metrics": {
        "namespace": "ActiveLog/${domain_name}",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 60
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/ec2/activelog/${domain_name}",
                        "log_stream_name": "{instance_id}/messages"
                    },
                    {
                        "file_path": "/opt/activelog/logs/*.log",
                        "log_group_name": "/aws/ec2/activelog/${domain_name}",
                        "log_stream_name": "{instance_id}/application"
                    }
                ]
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Log successful completion
echo "User data script completed successfully for ${domain_name} in ${environment}" >> /var/log/user-data.log