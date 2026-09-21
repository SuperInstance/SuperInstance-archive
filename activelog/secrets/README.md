# ActiveLog Secrets Management

This directory contains sensitive configuration data for production deployment.

## Setup

Run the setup script to generate secure secrets:

```bash
./setup-secrets.sh
```

## Manual Configuration Required

After running the setup script, update these files with your actual values:

### 1. OpenAI API Key
```bash
echo "sk-your-actual-openai-api-key" > openai_api_key.txt
```

### 2. AWS Credentials
```bash
echo "AKIA..." > aws_access_key.txt
echo "your-secret-key" > aws_secret_key.txt
```

### 3. SMTP Configuration
```bash
echo "smtp.your-provider.com" > smtp_host.txt
echo "your-email@domain.com" > smtp_user.txt
echo "your-smtp-password" > smtp_password.txt
```

## Security Best Practices

1. **File Permissions**: All secret files have 600 permissions (read/write for owner only)
2. **Directory Permissions**: The secrets directory has 700 permissions
3. **Version Control**: All `.txt` files are excluded from git via `.gitignore`
4. **Rotation**: Regularly rotate passwords and API keys
5. **Access Control**: Limit who has access to production secrets

## Production Deployment

1. Run `./setup-secrets.sh` on the production server
2. Update placeholder values with real credentials
3. Verify file permissions are correct
4. Start the application with `docker-compose -f docker-compose.prod.yml up -d`

## Secret Files

| File | Description | Example |
|------|-------------|---------|
| `database_url.txt` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `redis_url.txt` | Redis connection string | `redis://:pass@host:6379/0` |
| `jwt_secret.txt` | JWT signing secret | 64-character hex string |
| `openai_api_key.txt` | OpenAI API key | `sk-...` |
| `aws_access_key.txt` | AWS access key ID | `AKIA...` |
| `aws_secret_key.txt` | AWS secret access key | Base64 string |
| `smtp_host.txt` | SMTP server hostname | `smtp.gmail.com` |
| `smtp_user.txt` | SMTP username | `user@domain.com` |
| `smtp_password.txt` | SMTP password | App-specific password |
| `grafana_admin_password.txt` | Grafana admin password | Auto-generated |

## Troubleshooting

### Permission Denied Errors
```bash
chmod 700 .
chmod 600 *.txt
```

### Missing Secret Files
```bash
./setup-secrets.sh
```

### Invalid Credentials
Check logs: `docker-compose -f docker-compose.prod.yml logs`

## Emergency Access

If you lose access to secrets:

1. **Database**: Use PostgreSQL recovery procedures
2. **JWT**: Users will need to re-authenticate
3. **API Keys**: Regenerate from provider dashboards
4. **Grafana**: Reset admin password via CLI

## Backup

Create encrypted backups of secrets:

```bash
tar -czf secrets-backup.tar.gz *.txt
gpg -c secrets-backup.tar.gz
rm secrets-backup.tar.gz
```

Store `secrets-backup.tar.gz.gpg` securely.