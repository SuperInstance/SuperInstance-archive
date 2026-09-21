#!/bin/bash
# HTTPS/TLS Deployment Script for ActiveLog
# Generated on 2025-08-22 09:56:16

set -e

echo "🔒 Deploying HTTPS/TLS configuration for localhost..."

# Create necessary directories
mkdir -p ./docker/nginx/ssl
mkdir -p ./logs/nginx

# Copy certificates
echo "📋 Copying certificates..."
cp ./security-audit/configs/certificates/localhost.crt ./docker/nginx/ssl/
cp ./security-audit/configs/certificates/localhost.key ./docker/nginx/ssl/
cp ./security-audit/configs/certificates/dhparam.pem ./docker/nginx/ssl/

# Set proper permissions
chmod 644 ./docker/nginx/ssl/localhost.crt
chmod 600 ./docker/nginx/ssl/localhost.key
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
if curl -k -s -o /dev/null -w "%{http_code}" https://localhost | grep -q "200\|301\|302"; then
    echo "✅ HTTPS endpoint is accessible"
else
    echo "❌ HTTPS endpoint test failed"
    echo "Check logs: docker-compose logs nginx"
fi

# Test HTTP to HTTPS redirect
echo "🔄 Testing HTTP to HTTPS redirect..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "301\|302"; then
    echo "✅ HTTP to HTTPS redirect is working"
else
    echo "❌ HTTP to HTTPS redirect test failed"
fi

# Display certificate information
echo "📜 Certificate information:"
openssl x509 -in ./docker/nginx/ssl/localhost.crt -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After :)"

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
echo "Access your application at: https://localhost"
