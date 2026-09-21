# ActiveLog Service Deployment Guide

This guide explains how to use the `deploy.sh` script to deploy ActiveLog services to EC2 instances.

## Quick Start

1. **Set up your EC2 host and SSH key:**
   ```bash
   export EC2_HOST=your-ec2-hostname.amazonaws.com
   export EC2_KEY=~/.ssh/your-key.pem
   ```

2. **Deploy a service:**
   ```bash
   ./deploy.sh personallog-backend
   ```

3. **Access your deployed service:**
   - Service URL: `http://personallog-backend.activelog.services`
   - Direct access: `http://your-ec2-hostname.amazonaws.com:8000`

## Features

✅ **Auto-detection** - Automatically detects Python, Node.js, and Docker services  
✅ **Port management** - Automatically assigns unique ports or allows manual override  
✅ **File sync** - Uses rsync for efficient file transfers  
✅ **Systemd integration** - Creates proper systemd services for process management  
✅ **Nginx proxy** - Automatically configures reverse proxy with health checks  
✅ **Service discovery** - Returns URLs for easy testing  
✅ **Error handling** - Comprehensive validation and error messages  

## Prerequisites

### Local Requirements
- `ssh` - SSH client
- `rsync` - File synchronization tool
- `curl` - HTTP client (for testing)

### EC2 Instance Requirements
- Ubuntu/Debian based system
- `nginx` installed and running
- Python 3.8+ (for Python services)
- Node.js 16+ (for Node.js services)
- Docker (for Docker services)
- User account with sudo privileges

### SSH Key Setup
The script requires an SSH key to connect to your EC2 instance:

```bash
# Generate a new key pair (if needed)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/activelog-deploy.pem

# Copy public key to EC2 instance
ssh-copy-id -i ~/.ssh/activelog-deploy.pem.pub ubuntu@your-ec2-host

# Set proper permissions
chmod 600 ~/.ssh/activelog-deploy.pem
```

## Usage Examples

### Basic Deployment
```bash
# Deploy with auto-assigned port
./deploy.sh personallog-backend

# Deploy with specific port
./deploy.sh personallog-backend -p 8500

# Deploy with custom domain
./deploy.sh personallog-backend -d mydomain.com
```

### Environment Variables
```bash
# Set via environment variables
export EC2_HOST=ec2-123-456-789.compute-1.amazonaws.com
export EC2_USER=ubuntu
export EC2_KEY=~/.ssh/my-key.pem
export SERVICE_DOMAIN=mycompany.com

./deploy.sh api-gateway
```

### Testing and Validation
```bash
# Dry run to see what would be deployed
./deploy.sh dmlog-core --dry-run

# Deploy and test
./deploy.sh dmlog-core
curl http://dmlog-core.activelog.services/health
```

## Service Types

The deployment script auto-detects service types based on project files:

### Python Services
**Detection:** `requirements.txt` file present  
**Start command:** `python3 main.py` (or `app.py`, `server.py`)  
**Install:** `pip3 install -r requirements.txt`

Example service structure:
```
services/my-python-service/
├── main.py
├── requirements.txt
└── config.py
```

### Node.js Services
**Detection:** `package.json` file present  
**Start command:** `npm start`  
**Install:** `npm install`

Example service structure:
```
services/my-node-service/
├── package.json
├── server.js
└── src/
```

### Docker Services
**Detection:** `Dockerfile` present  
**Start command:** `docker run`  
**Install:** `docker build`

## Port Management

The script automatically assigns ports starting from 8000:

1. **Auto-assignment** (default): Scans for the next available port
2. **Manual override**: Use `-p` flag to specify a port
3. **Port conflict detection**: Checks if ports are already in use

```bash
# Auto-assigned (finds next available port >= 8000)
./deploy.sh my-service

# Manual port assignment
./deploy.sh my-service -p 8500
```

## Generated Files

When you deploy a service, the script creates several files on the EC2 instance:

### Systemd Service
**Location:** `/etc/systemd/system/activelog-{service-name}.service`  
**Purpose:** Manages service lifecycle (start, stop, restart, auto-start)

```bash
# Service management commands
sudo systemctl status activelog-personallog-backend
sudo systemctl restart activelog-personallog-backend
sudo systemctl logs -f activelog-personallog-backend
```

### Nginx Configuration
**Location:** `/etc/nginx/sites-available/activelog-{service-name}`  
**Purpose:** Reverse proxy configuration with health checks

### Deployment Metadata
**Location:** `/tmp/activelog-deploy-{service-name}.json`  
**Purpose:** Contains deployment information (port, URL, timestamp)

```json
{
  "service_name": "personallog-backend",
  "port": 8000,
  "url": "http://personallog-backend.activelog.services",
  "direct_url": "http://ec2-host:8000",
  "systemd_service": "activelog-personallog-backend.service",
  "deployed_at": "2025-01-15T10:30:00Z",
  "ec2_host": "ec2-123.amazonaws.com"
}
```

## Nginx Configuration

The script generates production-ready nginx configurations with:

- **Load balancing** - Single upstream server with failover settings
- **Health checks** - Automatic retry on backend failures
- **Proper headers** - X-Real-IP, X-Forwarded-For, etc.
- **Timeouts** - Reasonable connect, send, and read timeouts
- **Security** - Basic security headers and settings

## Monitoring and Logs

### Service Status
```bash
# Check if service is running
ssh -i ~/.ssh/key.pem ubuntu@ec2-host 'sudo systemctl status activelog-my-service'

# View real-time logs
ssh -i ~/.ssh/key.pem ubuntu@ec2-host 'sudo journalctl -fu activelog-my-service'

# View nginx logs
ssh -i ~/.ssh/key.pem ubuntu@ec2-host 'sudo tail -f /var/log/nginx/access.log'
```

### Health Checks
```bash
# Check service directly
curl http://ec2-host:8000/health

# Check via nginx proxy
curl http://my-service.activelog.services/health
```

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   ```bash
   # Check EC2_HOST is reachable
   ping $EC2_HOST
   
   # Test SSH connection
   ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'echo connected'
   ```

2. **Service Won't Start**
   ```bash
   # Check systemd logs
   ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'sudo journalctl -u activelog-my-service -n 50'
   
   # Check service dependencies
   ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'cd /opt/activelog/services/my-service && ls -la'
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using the port
   ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'sudo lsof -i :8000'
   
   # Use a different port
   ./deploy.sh my-service -p 8001
   ```

4. **Nginx Configuration Error**
   ```bash
   # Test nginx configuration
   ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'sudo nginx -t'
   
   # Reload nginx
   ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'sudo systemctl reload nginx'
   ```

### Debug Mode

For detailed debugging, modify the script to add `set -x` for verbose output:

```bash
# Edit the script temporarily
sed -i '3i set -x' deploy.sh
./deploy.sh my-service --dry-run
```

## Security Considerations

- **SSH Key Protection**: Ensure SSH private keys have 600 permissions
- **User Isolation**: Services run as dedicated `activelog` user, not root
- **Systemd Security**: NoNewPrivileges, ProtectSystem, PrivateTmp enabled
- **Nginx Security**: Rate limiting and security headers configured
- **Network Security**: Consider using VPC and security groups

## Advanced Usage

### Custom Start Commands

For services that need custom start commands, modify the service detection logic:

```bash
# Edit the detect_service_config function in deploy.sh
# Add custom logic for your service type
```

### Multiple Environments

Deploy to different environments using different domains:

```bash
# Development
./deploy.sh my-service -d dev.activelog.com

# Staging  
./deploy.sh my-service -d staging.activelog.com

# Production
./deploy.sh my-service -d activelog.com
```

### Load Balancing

For high-traffic services, deploy to multiple instances and configure nginx upstream:

```bash
# Deploy to multiple hosts
EC2_HOST=web1.example.com ./deploy.sh my-service -p 8000
EC2_HOST=web2.example.com ./deploy.sh my-service -p 8000

# Configure load balancer manually or use script enhancement
```

## Script Maintenance

The deployment script is designed to be:

- **Self-contained** - No external dependencies beyond standard Unix tools
- **Idempotent** - Can be run multiple times safely  
- **Extensible** - Easy to add new service types or deployment targets
- **Testable** - Includes dry-run mode for safe testing

For script updates or customization, key areas to modify:

1. **Service detection** - `detect_service_config()` function
2. **Port allocation** - `get_next_port()` function  
3. **Nginx templates** - `create_nginx_config()` function
4. **Systemd templates** - `create_systemd_service()` function

---

## Support

For issues with the deployment script:

1. Run with `--dry-run` to test configuration
2. Check EC2 instance logs: `/var/log/nginx/error.log`
3. Check systemd service logs: `journalctl -u activelog-service-name`
4. Verify network connectivity and SSH access
5. Review this documentation for common solutions