# ActiveLog Quick Launch Deployment

Comprehensive one-click beta deployment system for ActiveLog with advanced features for beta user management, security, and feedback collection.

## 🚀 Quick Start

### Deploy Beta Environment
```bash
cd deployment/quick-launch
./scripts/deploy-beta.sh
```

### Rollback if Needed
```bash
./rollback/rollback-beta.sh --full
```

## 📁 Directory Structure

```
quick-launch/
├── scripts/              # Main deployment scripts
│   ├── deploy-beta.sh     # One-click beta deployment
│   └── data-protection.py # GDPR compliance & data protection
├── configs/               # Configuration files
│   ├── environment.sh     # Environment variables
│   ├── beta-config.yml    # Beta-specific configuration
│   ├── docker-compose.beta.yml # Beta Docker services
│   ├── feature-flags-manager.py # Feature flag management
│   └── beta-feature-flags.json  # Beta feature definitions
├── rollback/              # Rollback procedures
│   ├── rollback-beta.sh   # Quick rollback script
│   └── rollback-manager.py # Advanced rollback management
├── migrations/            # Database migrations
│   ├── migration-runner.py # Safe migration system
│   └── sql/               # SQL migration files
├── beta-management/       # Beta user management
│   ├── beta-user-manager.py # User lifecycle management
│   ├── invite-system.py   # Advanced invite system
│   ├── invite-user.sh     # Quick invite script
│   ├── nda-manager.py     # NDA management system
│   └── nda-manager.sh     # NDA CLI wrapper
├── feedback/              # Feedback system
│   ├── feedback-aggregator.py # Feedback collection & analysis
│   └── view-feedback.sh   # Feedback dashboard
├── monitoring/            # Monitoring configs
├── templates/             # Deployment templates
└── README.md              # This file
```

## 🎯 Core Features

### 1. One-Click Beta Deployment
- **Automated Setup**: Complete beta environment in minutes
- **Environment Isolation**: Separate beta/prod configurations
- **Health Checks**: Automated service validation
- **Monitoring**: Built-in metrics and logging

### 2. Feature Flags System
- **Real-time Toggles**: Enable/disable features without deployment
- **User Segmentation**: Different features for different user groups
- **A/B Testing**: Percentage rollouts for beta features
- **Analytics Integration**: Track feature usage

### 3. Safe Database Migrations
- **Automatic Backups**: Pre-migration database snapshots
- **Rollback Support**: Safe migration rollbacks
- **Integrity Checks**: Validate migrations before and after
- **Zero-downtime**: Migrations don't interrupt service

### 4. Beta User Management
- **Invite System**: Sophisticated invite management with templates
- **User Tiers**: Standard, Premium, and Developer access levels
- **Analytics**: Track user engagement and activity
- **Bulk Operations**: Mass invite and management capabilities

### 5. NDA Management
- **Digital Signatures**: Secure NDA signing process
- **Compliance Tracking**: Monitor NDA status and expiry
- **Automated Reminders**: Email notifications for expiring NDAs
- **Legal Compliance**: Full audit trail for legal requirements

### 6. Feedback Aggregation
- **AI-Powered Analysis**: Automatic sentiment and priority detection
- **Rich Analytics**: Comprehensive feedback insights
- **Auto-categorization**: Smart tagging and classification
- **Response Tracking**: Monitor feedback resolution

### 7. Data Protection (GDPR)
- **User Data Export**: Complete user data export in standard formats
- **Data Anonymization**: GDPR-compliant data anonymization
- **Right to be Forgotten**: Complete user data deletion
- **Encryption**: Data encryption at rest and in transit

### 8. Rollback Procedures
- **Quick Rollback**: One-command rollback to previous state
- **Granular Control**: Service-specific or full rollbacks
- **Safety Checks**: Pre-rollback validation
- **Audit Trail**: Complete rollback history

## 🛠 Usage Guide

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd activelog/deployment/quick-launch

# Configure environment (optional - defaults work for beta)
cp configs/beta-config.yml configs/beta-config.local.yml
# Edit configs/beta-config.local.yml as needed

# Deploy beta environment
./scripts/deploy-beta.sh
```

### Beta User Management
```bash
# Invite a single user
./beta-management/invite-user.sh user@example.com --invited-by admin123

# Invite with premium access
./beta-management/invite-user.sh user@example.com --template premium --invited-by admin123

# Bulk invite from CSV
./beta-management/invite-user.sh --bulk users.csv --invited-by admin123

# List beta users
python3 ./beta-management/beta-user-manager.py list

# Get beta statistics
python3 ./beta-management/beta-user-manager.py stats
```

### NDA Management
```bash
# Check user's NDA status
./beta-management/nda-manager.sh check user-123-456

# Generate compliance report
./beta-management/nda-manager.sh report 30

# Send expiry reminders
./beta-management/nda-manager.sh reminders
```

### Feature Flag Management
```bash
# Deploy feature flags
python3 ./configs/feature-flags-manager.py --action deploy --config ./configs/beta-feature-flags.json

# Get specific feature flag
python3 ./configs/feature-flags-manager.py --action get --flag-key new_dashboard_ui

# Update feature flag
python3 ./configs/feature-flags-manager.py --action update --flag-key ai_powered_search --updates '{"percentage": 75}'

# List all flags
python3 ./configs/feature-flags-manager.py --action list
```

### Feedback Management
```bash
# View feedback summary
./feedback/view-feedback.sh summary 7

# Generate detailed report
./feedback/view-feedback.sh report 30

# Export feedback data
./feedback/view-feedback.sh export csv 30

# Live dashboard
./feedback/view-feedback.sh dashboard

# Update feedback status
./feedback/view-feedback.sh update feedback-123 resolved
```

### Database Migrations
```bash
# Run pending migrations
python3 ./migrations/migration-runner.py --action migrate

# Check migration status
python3 ./migrations/migration-runner.py --action status

# Rollback last migration
python3 ./migrations/migration-runner.py --action rollback
```

### Data Protection Operations
```bash
# Export user data (GDPR)
python3 ./scripts/data-protection.py --action export --user-id user-123

# Anonymize user data
python3 ./scripts/data-protection.py --action anonymize --user-id user-123

# Delete user data (Right to be forgotten)
python3 ./scripts/data-protection.py --action delete --user-id user-123

# Clean up expired data
python3 ./scripts/data-protection.py --action cleanup
```

### Rollback Operations
```bash
# Quick rollback (last stable version)
./rollback/rollback-beta.sh --full

# Rollback to specific version
./rollback/rollback-beta.sh --to-version v1.2.0

# Rollback only services
./rollback/rollback-beta.sh --services-only

# List available backups
./rollback/rollback-beta.sh --list-backups

# Dry run (see what would happen)
./rollback/rollback-beta.sh --dry-run
```

## 🔧 Configuration

### Environment Configuration
Edit `configs/environment.sh` to customize:
- Database settings
- API endpoints
- Feature flag defaults
- Security settings
- Resource limits

### Beta-Specific Settings
Modify `configs/beta-config.yml`:
- User limits
- Feature enablements
- Email settings
- Monitoring configuration

### Feature Flags
Update `configs/beta-feature-flags.json`:
- Add new feature flags
- Set rollout percentages
- Define user segments
- Configure A/B tests

## 🔍 Monitoring & Observability

### Access Points
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8080
- **Admin Panel**: http://localhost:3000/admin
- **Grafana Dashboard**: http://localhost:3001
- **Prometheus Metrics**: http://localhost:9090

### Key Metrics
- User registration and activation rates
- Feature adoption metrics
- Feedback sentiment analysis
- System performance metrics
- Error rates and availability

### Log Locations
- **Application Logs**: `/var/log/activelog/beta.log`
- **Migration Logs**: `./migrations/migration.log`
- **Beta Management**: `./beta-management/beta-management.log`
- **Feedback System**: `./feedback/feedback-aggregator.log`

## 🚨 Troubleshooting

### Common Issues

**Deployment Fails**
```bash
# Check system requirements
./scripts/deploy-beta.sh --dry-run

# View detailed logs
docker-compose logs -f
```

**Database Connection Issues**
```bash
# Check database status
docker ps | grep postgres

# Reset database
docker-compose restart postgres
```

**Feature Flags Not Working**
```bash
# Check Redis connection
docker ps | grep redis

# Redeploy feature flags
python3 ./configs/feature-flags-manager.py --action deploy --config ./configs/beta-feature-flags.json
```

**Rollback Issues**
```bash
# Check available backups
./rollback/rollback-beta.sh --list-backups

# Force rollback (skip confirmations)
./rollback/rollback-beta.sh --force --full
```

### Getting Help
1. Check logs in respective component directories
2. Use `--dry-run` flags to see what would happen
3. Verify database and Redis connectivity
4. Check Docker container status
5. Review configuration files for typos

## 🔒 Security Considerations

### Data Protection
- All sensitive data encrypted at rest
- GDPR compliance built-in
- Automatic data anonymization
- Secure user data export

### Authentication & Authorization
- JWT-based authentication
- Role-based access control
- NDA requirement enforcement
- Session management

### Network Security
- HTTPS enforcement in production
- Rate limiting
- CORS protection
- Security headers

### Audit & Compliance
- Complete audit logging
- NDA compliance tracking
- User activity monitoring
- Data access logging

## 🚀 Production Deployment

### Pre-Production Checklist
- [ ] All tests passing
- [ ] Security review completed
- [ ] Database migrations tested
- [ ] Rollback procedures validated
- [ ] Monitoring configured
- [ ] SSL certificates configured
- [ ] Backup procedures tested

### Production Configuration
Update environment variables for production:
```bash
export ENVIRONMENT=production
export DEBUG_MODE=false
export HTTPS_ENABLED=true
export DB_CONNECTIONS=200
export REDIS_MAXMEMORY=2gb
```

### Scaling Considerations
- Use multiple API workers
- Implement database connection pooling
- Configure Redis clustering
- Set up CDN for static assets
- Enable horizontal pod autoscaling

## 📈 Future Enhancements

### Planned Features
- [ ] Advanced A/B testing framework
- [ ] Machine learning feedback analysis
- [ ] Automated user onboarding
- [ ] Integration with external tools
- [ ] Mobile app support
- [ ] Advanced analytics dashboard

### Integration Roadmap
- Slack/Discord notifications
- Jira/GitHub issue creation
- Zapier webhook support
- Analytics platform integration
- Customer support tools

---

## 📞 Support

For technical support or questions:
- **Beta Support**: beta-support@activelog.dev
- **Documentation**: Check logs and configuration files
- **Issues**: Create detailed issue reports with logs

---

**Happy Beta Testing! 🎉**