# ☁️ Cloud Deployment Guide - AI Society Portal

## Quick Answer: YES! Access from Anywhere 🌍

You can absolutely run this on EC2 (or other cloud platforms) and access it from your phone, laptop, or anywhere. Rooms will keep running in the cloud even when you're not watching!

---

## 🎯 Deployment Options Compared

| Option | Difficulty | Cost/Month | Best For | WebSocket Support |
|--------|-----------|------------|----------|-------------------|
| **Railway** | ⭐ Easiest | $5-20 | Quick start, hobby | ✅ Yes |
| **Render** | ⭐ Easy | $7-25 | Simple, reliable | ✅ Yes |
| **Fly.io** | ⭐⭐ Moderate | $5-15 | Low cost, global | ✅ Yes |
| **EC2** | ⭐⭐⭐ Advanced | $10-30 | Full control | ✅ Yes |
| **DigitalOcean** | ⭐⭐ Moderate | $12-25 | Balanced | ✅ Yes |
| **AWS ECS/Fargate** | ⭐⭐⭐⭐ Complex | $20-50 | Production scale | ✅ Yes |

---

## 🚀 Option 1: Railway (RECOMMENDED - Easiest)

**Perfect for: Getting started quickly, accessing from anywhere**

### Why Railway?
- 🎯 Deploy with one click
- 🔄 Auto-deploys from GitHub
- 💰 $5 free credit, then ~$5-10/month
- 📱 Access from phone/laptop anywhere
- ✅ WebSocket support built-in
- 🔒 HTTPS automatic

### Deploy to Railway (5 Minutes)

1. **Push to GitHub**
```bash
cd ai_society_portal
git init
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Deploy on Railway**
- Go to [railway.app](https://railway.app)
- Click "New Project" → "Deploy from GitHub"
- Select your repo
- Railway auto-detects Docker Compose
- Add environment variables:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
- Click Deploy!

3. **Access Your Portal**
- Railway gives you a URL like: `your-app.railway.app`
- Open on phone: ✅
- Open on laptop: ✅
- Rooms keep running: ✅

**That's it!** Your AI Society is now in the cloud.

---

## 🚀 Option 2: AWS EC2 (What You Asked About)

**Perfect for: Full control, custom configuration**

### EC2 Setup (15 Minutes)

#### Step 1: Launch EC2 Instance

1. **Go to AWS Console** → EC2
2. **Launch Instance**:
   - AMI: Ubuntu 22.04 LTS
   - Instance type: `t3.medium` (2 vCPU, 4 GB RAM)
   - Storage: 30 GB
   - Security Group: Open ports 80, 443, 22, 8000

3. **Configure Security Group**:
```
Port 22 (SSH) - Your IP only
Port 80 (HTTP) - Anywhere (0.0.0.0/0)
Port 443 (HTTPS) - Anywhere (0.0.0.0/0)
Port 8000 (API) - Anywhere (0.0.0.0/0) [temporary, will close after nginx]
```

#### Step 2: SSH into Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

#### Step 3: Install Docker & Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Logout and login again for docker group to take effect
exit
ssh -i your-key.pem ubuntu@your-ec2-ip
```

#### Step 4: Deploy Your App

```bash
# Clone your repo (or upload files)
git clone your-repo-url
cd ai_society_portal

# Create .env file
cat > backend/.env << EOF
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
QDRANT_URL=qdrant:6333
EOF

# Start everything
docker-compose up -d

# Check it's running
docker-compose ps
```

#### Step 5: Access Your Portal

- Open: `http://your-ec2-ip`
- Or set up domain: `your-domain.com` → EC2 IP

**Access from anywhere:**
- Phone: ✅ (open browser, go to your-ec2-ip)
- Laptop: ✅
- Rooms run 24/7: ✅

#### Step 6: (Optional) Add SSL/HTTPS

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

### EC2 Costs

- **t3.medium**: ~$30/month
- **t3.small**: ~$15/month (might be tight)
- **t3.micro**: ~$7.50/month (free tier, very limited)

**Pro tip**: Use AWS Lightsail instead - simpler, fixed pricing ($12-20/month)

---

## 🚀 Option 3: Render (Great Balance)

**Perfect for: Easy deployment, good performance**

### Deploy to Render (10 Minutes)

1. **Push to GitHub** (if not already)

2. **Go to [render.com](https://render.com)**

3. **Create New Web Service**
   - Connect GitHub
   - Select Docker
   - Point to `backend/Dockerfile`
   - Add environment variables

4. **Create Static Site**
   - Select `frontend/`
   - Build command: `npm install && npm run build`
   - Publish directory: `build`

**Cost**: ~$7/month for backend, ~$0 for frontend

---

## 🚀 Option 4: DigitalOcean App Platform

**Perfect for: Simple, reliable, good documentation**

### Deploy to DigitalOcean (10 Minutes)

1. **Create Droplet** or use **App Platform**
2. **App Platform** (easier):
   - Connect GitHub
   - Auto-detects Dockerfile
   - Deploy!

**Cost**: $12-25/month

---

## 🚀 Option 5: Docker Anywhere (Universal)

Use Docker Compose on **any** cloud provider:

```bash
# On your cloud VM
git clone your-repo
cd ai_society_portal

# Create .env
echo "OPENAI_API_KEY=your-key" > backend/.env
echo "ANTHROPIC_API_KEY=your-key" >> backend/.env

# Deploy
docker-compose up -d

# Check logs
docker-compose logs -f
```

Works on:
- ✅ AWS EC2
- ✅ Google Cloud Compute
- ✅ Azure VMs
- ✅ DigitalOcean Droplets
- ✅ Linode
- ✅ Vultr
- ✅ Your own server

---

## 📱 Mobile Access

Once deployed to any cloud option, access from phone:

1. **Open browser** (Chrome, Safari, etc.)
2. **Go to your URL**:
   - `http://your-ec2-ip` (if EC2)
   - `https://your-app.railway.app` (if Railway)
   - `https://your-domain.com` (if custom domain)

3. **Use the portal**:
   - ✅ Create characters
   - ✅ Create rooms
   - ✅ Start conversations
   - ✅ Watch live feeds
   - ✅ Pause/resume
   - ✅ Inject messages

**The interface is responsive** - works great on phone!

---

## 🔥 Persistent Rooms (Keep Running)

### How to Keep Conversations Running While Away

**Option A: Long-Running Sessions**
```bash
# When creating room, set long duration
{
  "duration_minutes": 1440  // 24 hours
}
```

**Option B: Background Process**
```python
# In backend, modify to run indefinitely
while room.session.is_active:
    await conversation_engine.run_round()
    await asyncio.sleep(room.conversation_pace_seconds)
```

**Option C: Scheduled Tasks**
- Use cron jobs or celery to restart sessions
- Characters continue working at home
- Conversations resume periodically

---

## 💰 Cost Comparison (Monthly)

### Budget Setup (~$10-20/month)
```
Railway: $10/month
- Backend + Frontend + Qdrant
- 500 hours compute
- Perfect for hobby use
```

### Standard Setup (~$25-40/month)
```
EC2 t3.medium: $30/month
+ Storage: $3/month
+ Data transfer: $5/month
= ~$38/month total
```

### Production Setup (~$50-100/month)
```
AWS ECS Fargate: $40/month
+ RDS Database: $20/month
+ S3 Storage: $5/month
+ CloudFront CDN: $10/month
= ~$75/month total
```

---

## 🛡️ Security Considerations

### Essential Security Steps

1. **Environment Variables**
   - Never commit API keys
   - Use cloud provider's secrets management

2. **HTTPS/SSL**
   - Required for production
   - Free with Let's Encrypt
   - Auto-configured on Railway/Render

3. **Firewall**
   - Restrict SSH to your IP
   - Only open necessary ports
   - Use security groups (AWS) or firewalls

4. **Authentication** (Future Addition)
   - Add user login system
   - Protect API endpoints
   - Use JWT tokens

5. **Rate Limiting**
   - Prevent API abuse
   - Add to FastAPI endpoints

---

## 📊 Storage Considerations

### Where Character/Room Data Lives

**Development**: Local file system
**Cloud**: Several options

#### Option 1: Docker Volumes (Simple)
```yaml
volumes:
  - ./ai_society_data:/app/ai_society_data
```
- ✅ Simple
- ❌ Lost if container restarts (unless mounted)

#### Option 2: Cloud Storage (Better)
```python
# Modify to use S3 instead of local files
import boto3
s3 = boto3.client('s3')

# Save character
s3.put_object(
    Bucket='ai-society-characters',
    Key=f'characters/{char_id}/character.json',
    Body=json.dumps(character.to_dict())
)
```

#### Option 3: Database (Best for Production)
- Use PostgreSQL (AWS RDS)
- Store characters/rooms in DB
- File attachments in S3

---

## 🚦 Monitoring & Maintenance

### Keep Your Portal Healthy

**Check Status**:
```bash
# Docker
docker-compose ps
docker-compose logs

# System resources
htop
df -h
```

**Restart Services**:
```bash
docker-compose restart
```

**Update Application**:
```bash
git pull
docker-compose down
docker-compose up -d --build
```

**Backup Data**:
```bash
# Backup character/room data
tar -czf backup.tar.gz ai_society_data/

# Or use cloud backups
aws s3 sync ai_society_data/ s3://your-bucket/backups/
```

---

## 🎯 Recommended Setup for You

Based on your use case (access from anywhere, check on rooms):

### 🥇 Best Choice: Railway
**Why:**
- Deploy in 5 minutes
- Access from anywhere instantly
- Auto HTTPS
- $5-15/month
- Perfect for personal use

### 🥈 Second Choice: EC2 with Docker
**Why:**
- Full control
- Can optimize costs
- Good for learning
- ~$20-30/month

### 🥉 Third Choice: DigitalOcean App Platform
**Why:**
- Good balance
- Simple interface
- Reliable
- $12-25/month

---

## 🆘 Troubleshooting Cloud Deployment

**Problem**: WebSocket not connecting
**Solution**: Ensure proxy config has upgrade headers (nginx.conf provided)

**Problem**: CORS errors
**Solution**: Set proper API URL in frontend env vars

**Problem**: Out of memory
**Solution**: Increase instance size or add swap

**Problem**: Can't access from phone
**Solution**: Check security group allows port 80/443 from anywhere

---

## 📞 Next Steps

1. **Choose your deployment method**
2. **Follow the guide above**
3. **Test from your phone**
4. **Create characters and rooms**
5. **Let conversations run while you work**
6. **Check in from anywhere!**

---

## 🎓 Advanced: Multi-Region Setup

For ultra-low latency worldwide:
- Deploy to multiple AWS regions
- Use CloudFront for global CDN
- Route53 for geographic routing

But for personal use, single region is perfect!

---

**Ready to deploy?** Start with Railway for the easiest experience, or EC2 if you want full control!

Your AI Society can live in the cloud and you can check on your characters from anywhere 🌍✨
