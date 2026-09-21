# 📊 Quick Analysis Portal

**Direct URL**: `analysis.activeledger.ai`  
**Easy access financial analysis tools with multiple entry points**

## 🌟 Overview

Quick Analysis Portal provides instant stock analysis through multiple access methods - web portal, PWA, browser extension, mobile widget, and comprehensive APIs. Built for ease of use with keyboard shortcuts, bookmarking support, and tiered access levels.

## 🚀 Quick Start

```bash
# Start the service
cd /home/activeloguser/activelog/services/quick-analysis
./start_service.sh

# Access the portal
open http://localhost:8420
```

## 📱 Access Points

### 1. **Main Web Portal**
- **URL**: `http://localhost:8420`
- **Features**: Full analysis dashboard, search, premium features
- **Keyboard Shortcuts**:
  - `Ctrl + /` - Focus search
  - `Enter` - Search
  - `Esc` - Close results
  - `?` - Show shortcuts

### 2. **Progressive Web App (PWA)**
- **Install**: Click "📱 Install PWA" on main page
- **Features**: 
  - Works offline with cached data
  - Native app-like experience
  - Home screen installation
  - Push notifications (Premium)

### 3. **Browser Extension**
- **Install**: Visit `/extension` page
- **Features**:
  - Right-click any stock symbol for analysis
  - Auto-detect symbols on financial sites
  - Instant overlay with results
  - Keyboard shortcuts (`Ctrl+Shift+A`)

### 4. **Mobile Widget**
- **URL**: `/mobile-widget`
- **Features**:
  - Mobile-optimized interface
  - Add to home screen
  - Touch-friendly design
  - Offline support

### 5. **REST API**
- **Docs**: `/api/docs`
- **Base URL**: `/api/v1`
- **Authentication**: API key required
- **Rate Limits**: Based on tier

### 6. **Bookmark Support**
- **Quick URLs**:
  - `analysis.activeledger.ai?symbol=AAPL`
  - `analysis.activeledger.ai?q=TSLA`
- **Features**: Direct symbol analysis, shareable links

## 💎 Feature Tiers

### 🆓 **Free Tier**
- ✅ Basic stock quotes
- ✅ Simple charts  
- ✅ Key ratios
- ✅ Recent news (3 articles)
- ✅ Analyst consensus
- ✅ **5 searches per day**
- ✅ Watermarked reports
- ✅ Ad supported
- ✅ PWA support
- ✅ Browser extension
- ✅ Basic API (100 calls/hour)

### 💰 **Premium Tier** - $9.99/month
- ✅ **Unlimited searches**
- ✅ Real-time data
- ✅ Advanced charts & indicators
- ✅ Full financial reports
- ✅ Complete news feed
- ✅ **API access (1,000 calls/hour)**
- ✅ No advertisements
- ✅ Priority customer support  
- ✅ Custom alerts & notifications
- ✅ Portfolio tracking
- ✅ Historical data access
- ✅ Batch analysis
- ✅ Export capabilities

### 🏢 **Enterprise Tier** - Contact Sales
- ✅ Everything in Premium
- ✅ **10,000 API calls/hour**
- ✅ White-label options
- ✅ Custom integrations
- ✅ Priority data feeds
- ✅ Advanced analytics
- ✅ Team management
- ✅ SLA guarantees

## 🔌 API Integration

### Authentication
```bash
# Header method
curl -H "X-API-Key: your-api-key" "https://analysis.activeledger.ai/api/v1/quote/AAPL"

# Query parameter method  
curl "https://analysis.activeledger.ai/api/v1/quote/AAPL?api_key=your-api-key"
```

### Key Endpoints

| Endpoint | Method | Description | Tier |
|----------|--------|-------------|------|
| `/quote/{symbol}` | GET | Real-time quote | Free+ |
| `/ratios/{symbol}` | GET | Financial ratios | Free+ |
| `/chart/{symbol}` | GET | Price history | Free+ |
| `/news/{symbol}` | GET | Recent news | Free+ |
| `/analysis/{symbol}` | GET | Complete analysis | Free+ |
| `/batch` | POST | Multiple symbols | Premium+ |
| `/alerts` | POST | Price alerts | Premium+ |
| `/user/usage` | GET | Usage statistics | All |

### Example Integration

#### JavaScript
```javascript
const response = await fetch('https://analysis.activeledger.ai/api/v1/quote/AAPL', {
  headers: { 'X-API-Key': 'your-api-key-here' }
});
const data = await response.json();
console.log(`${data.data.symbol}: $${data.data.current_price}`);
```

#### Python
```python
import requests

headers = {'X-API-Key': 'your-api-key-here'}
response = requests.get('https://analysis.activeledger.ai/api/v1/quote/AAPL', headers=headers)
data = response.json()
print(f"{data['data']['symbol']}: ${data['data']['current_price']}")
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + /` | Focus search input |
| `Enter` | Execute search |
| `Esc` | Close results/overlays |
| `?` | Show shortcuts help |
| `Ctrl + Shift + A` | Open portal (extension) |
| `Ctrl + Shift + S` | Quick search (extension) |

## 🔧 Browser Extension

### Installation
1. Visit `/extension` page
2. Download extension package
3. Open Chrome → Extensions → Developer mode
4. Click "Load unpacked" → Select folder
5. Extension ready!

### Features
- **Right-click analysis**: Select any stock symbol → right-click → "Analyze with Quick Analysis Portal"
- **Auto-enhancement**: Adds quick analysis buttons to financial websites
- **Instant overlay**: Results appear without leaving the page
- **Keyboard shortcuts**: Quick access from any page

## 📱 Mobile Features

### PWA Installation
**iOS Safari**:
1. Tap Share button
2. "Add to Home Screen"  
3. Tap "Add"

**Android Chrome**:
1. Tap menu (⋮)
2. "Add to Home screen"
3. Tap "Add"

### Mobile Widget
- Touch-optimized interface
- Swipe gestures
- Offline caching
- Fast search suggestions
- One-tap popular symbols

## 🏗️ Architecture

```
Quick Analysis Portal
├── Main Application (main.py)
├── Analysis Engine (yfinance integration)
├── User Management (tiers, limits, API keys)
├── Browser Extension (Chrome/Firefox)
├── PWA Support (service worker, manifest)
├── Mobile Widget (responsive design)
├── REST API (comprehensive endpoints)
└── Database (SQLite with user data, caching)
```

## 📊 Data Sources

- **Primary**: Yahoo Finance (yfinance)
- **Backup**: Alpha Vantage API (planned)
- **News**: Yahoo Finance News Feed
- **Real-time**: WebSocket connections (Premium)

## 🔒 Security Features

- API key authentication
- Rate limiting by tier
- Input validation & sanitization
- SQL injection protection
- XSS prevention
- CSRF tokens
- Secure session management

## 🚀 Performance

- **Response Time**: < 500ms average
- **Caching**: Intelligent data caching
- **CDN**: Static asset delivery
- **Compression**: Gzip compression
- **Minification**: CSS/JS optimization
- **Lazy Loading**: Progressive content loading

## 🛠️ Development

### Local Setup
```bash
# Clone and setup
cd /home/activeloguser/activelog/services/quick-analysis
pip install -r requirements.txt

# Run development server
python main.py

# Run with debugging
FLASK_DEBUG=true python main.py
```

### Testing
```bash
# Test API endpoints
curl http://localhost:8420/health

# Test stock analysis
curl -X POST http://localhost:8420/api/quick-analysis \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL"}'
```

## 🌐 Deployment

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Configure reverse proxy (nginx)
- [ ] Enable SSL certificates
- [ ] Set up monitoring (health checks)
- [ ] Configure log rotation
- [ ] Database backups
- [ ] CDN configuration
- [ ] Domain DNS (analysis.activeledger.ai)

### Environment Variables
```bash
export FLASK_APP=main.py
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
export DATABASE_URL=sqlite:///quick_analysis.db
```

## 🎯 Quick Access Summary

| Method | URL/Action | Best For |
|--------|------------|----------|
| **Direct URL** | `analysis.activeledger.ai` | Bookmarks, sharing |
| **PWA** | Install from main page | Mobile, offline use |
| **Extension** | Right-click any symbol | Browsing web |
| **Widget** | `/mobile-widget` | Mobile quick access |
| **API** | `/api/v1/*` | App integration |
| **Shortcuts** | `Ctrl+/`, `Enter` | Power users |

## 🔗 Links

- **Main Portal**: http://localhost:8420
- **API Documentation**: http://localhost:8420/api/docs
- **Mobile Widget**: http://localhost:8420/mobile-widget
- **Browser Extension**: http://localhost:8420/extension
- **Premium Upgrade**: http://localhost:8420/premium
- **Health Check**: http://localhost:8420/health

## 📞 Support

- **Issues**: Create GitHub issue
- **API Help**: Check `/api/docs`
- **Feature Requests**: Contact support
- **Premium Support**: priority@activeledger.ai

---

**🎉 Easy Access Financial Analysis - Made Simple!**

*Built for speed, designed for accessibility, optimized for every device.*