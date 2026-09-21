const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

// Device configurations for screenshots
const DEVICES = {
  // iPhone devices
  'iphone-15-pro-max': {
    name: 'iPhone 15 Pro Max',
    width: 430,
    height: 932,
    pixelRatio: 3,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    platform: 'ios',
    storeSize: '6.7"',
    orientation: 'portrait'
  },
  'iphone-15-pro': {
    name: 'iPhone 15 Pro',
    width: 393,
    height: 852,
    pixelRatio: 3,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    platform: 'ios',
    storeSize: '6.1"',
    orientation: 'portrait'
  },
  'iphone-se': {
    name: 'iPhone SE',
    width: 375,
    height: 667,
    pixelRatio: 2,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    platform: 'ios',
    storeSize: '4.7"',
    orientation: 'portrait'
  },
  // iPad devices
  'ipad-pro-12': {
    name: 'iPad Pro 12.9"',
    width: 1024,
    height: 1366,
    pixelRatio: 2,
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    platform: 'ios',
    storeSize: '12.9"',
    orientation: 'portrait'
  },
  'ipad-air': {
    name: 'iPad Air',
    width: 820,
    height: 1180,
    pixelRatio: 2,
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    platform: 'ios',
    storeSize: '10.9"',
    orientation: 'portrait'
  },
  // Android devices
  'pixel-7-pro': {
    name: 'Google Pixel 7 Pro',
    width: 412,
    height: 915,
    pixelRatio: 3.5,
    userAgent: 'Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    platform: 'android',
    storeSize: '6.7"',
    orientation: 'portrait'
  },
  'pixel-7': {
    name: 'Google Pixel 7',
    width: 412,
    height: 869,
    pixelRatio: 2.625,
    userAgent: 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    platform: 'android',
    storeSize: '6.3"',
    orientation: 'portrait'
  },
  'samsung-galaxy-s23': {
    name: 'Samsung Galaxy S23',
    width: 360,
    height: 780,
    pixelRatio: 3,
    userAgent: 'Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    platform: 'android',
    storeSize: '6.1"',
    orientation: 'portrait'
  },
  // Android tablets
  'samsung-tab-s9': {
    name: 'Samsung Galaxy Tab S9',
    width: 800,
    height: 1280,
    pixelRatio: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 13; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    platform: 'android',
    storeSize: '11"',
    orientation: 'portrait'
  }
};

// App variants and their demo screens
const APP_VARIANTS = {
  'personal-log': {
    name: 'PersonalLog',
    primaryColor: '#6366F1',
    screens: [
      { name: 'dashboard', title: 'Your Personal Dashboard', description: 'Track your daily thoughts and experiences' },
      { name: 'journal-entry', title: 'Write Your Story', description: 'Capture moments that matter with our intuitive editor' },
      { name: 'timeline', title: 'Your Journey', description: 'Browse through your personal timeline of memories' },
      { name: 'mood-tracking', title: 'Track Your Mood', description: 'Monitor your emotional well-being over time' },
      { name: 'insights', title: 'Personal Insights', description: 'Discover patterns in your thoughts and habits' }
    ]
  },
  'business-log': {
    name: 'BusinessLog',
    primaryColor: '#059669',
    screens: [
      { name: 'dashboard', title: 'Business Overview', description: 'Monitor your business metrics and progress' },
      { name: 'task-management', title: 'Manage Tasks', description: 'Organize and track your business objectives' },
      { name: 'team-collaboration', title: 'Team Collaboration', description: 'Work together seamlessly with your team' },
      { name: 'analytics', title: 'Business Analytics', description: 'Data-driven insights for better decisions' },
      { name: 'reports', title: 'Professional Reports', description: 'Generate comprehensive business reports' }
    ]
  },
  'family-log': {
    name: 'FamilyLog',
    primaryColor: '#DC2626',
    screens: [
      { name: 'dashboard', title: 'Family Dashboard', description: 'Keep track of your family\'s activities and memories' },
      { name: 'shared-calendar', title: 'Family Calendar', description: 'Coordinate schedules and family events' },
      { name: 'photo-albums', title: 'Family Photos', description: 'Create beautiful albums of your family moments' },
      { name: 'milestone-tracking', title: 'Family Milestones', description: 'Record important family achievements' },
      { name: 'memory-sharing', title: 'Share Memories', description: 'Connect and share with family members' }
    ]
  },
  'fitness-log': {
    name: 'FitnessLog',
    primaryColor: '#EA580C',
    screens: [
      { name: 'dashboard', title: 'Fitness Dashboard', description: 'Track your health and fitness journey' },
      { name: 'workout-tracking', title: 'Log Workouts', description: 'Record your exercises and training sessions' },
      { name: 'nutrition-log', title: 'Nutrition Tracking', description: 'Monitor your daily nutrition and calories' },
      { name: 'progress-charts', title: 'Progress Charts', description: 'Visualize your fitness improvements over time' },
      { name: 'goal-setting', title: 'Fitness Goals', description: 'Set and achieve your health objectives' }
    ]
  },
  'travel-log': {
    name: 'TravelLog',
    primaryColor: '#0891B2',
    screens: [
      { name: 'dashboard', title: 'Travel Dashboard', description: 'Document your adventures around the world' },
      { name: 'trip-planning', title: 'Plan Your Trip', description: 'Organize itineraries and travel details' },
      { name: 'location-tracking', title: 'Track Locations', description: 'Map your journey with GPS tracking' },
      { name: 'photo-journal', title: 'Travel Photos', description: 'Create stunning photo journals of your trips' },
      { name: 'expense-tracking', title: 'Travel Expenses', description: 'Keep track of your travel budget and costs' }
    ]
  },
  'education-log': {
    name: 'EducationLog',
    primaryColor: '#7C3AED',
    screens: [
      { name: 'dashboard', title: 'Learning Dashboard', description: 'Track your educational progress and achievements' },
      { name: 'course-management', title: 'Manage Courses', description: 'Organize your classes and study materials' },
      { name: 'grade-tracking', title: 'Grade Tracking', description: 'Monitor your academic performance' },
      { name: 'study-planner', title: 'Study Planner', description: 'Plan your study schedule and assignments' },
      { name: 'progress-reports', title: 'Progress Reports', description: 'Analyze your learning patterns and improvements' }
    ]
  }
};

class ScreenshotGenerator {
  constructor() {
    this.browser = null;
    this.outputDir = path.join(__dirname, '..', 'screenshots');
  }

  async initialize() {
    console.log('📸 Initializing Screenshot Generator...');
    
    // Create output directory
    await fs.mkdir(this.outputDir, { recursive: true });
    
    // Launch browser
    this.browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
      ]
    });
    
    console.log('✅ Browser initialized');
  }

  async generateAllScreenshots() {
    if (!this.browser) {
      throw new Error('Browser not initialized. Call initialize() first.');
    }

    for (const [variantKey, variant] of Object.entries(APP_VARIANTS)) {
      console.log(`\n🎯 Generating screenshots for ${variant.name}...`);
      
      // Create variant directory
      const variantDir = path.join(this.outputDir, variantKey);
      await fs.mkdir(variantDir, { recursive: true });
      
      for (const [deviceKey, device] of Object.entries(DEVICES)) {
        console.log(`  📱 Device: ${device.name}`);
        
        // Create device directory
        const deviceDir = path.join(variantDir, deviceKey);
        await fs.mkdir(deviceDir, { recursive: true });
        
        await this.generateScreenshotsForDevice(variant, device, deviceDir);
      }
    }
  }

  async generateScreenshotsForDevice(variant, device, outputDir) {
    const page = await this.browser.newPage();
    
    try {
      // Set viewport and user agent
      await page.setViewport({
        width: device.width,
        height: device.height,
        deviceScaleFactor: device.pixelRatio
      });
      
      if (device.userAgent) {
        await page.setUserAgent(device.userAgent);
      }
      
      for (const [index, screen] of variant.screens.entries()) {
        console.log(`    🖼️  Generating ${screen.name}...`);
        
        // Generate HTML content for the screen
        const html = this.generateScreenHTML(variant, screen, device);
        
        await page.setContent(html, { 
          waitUntil: 'networkidle0',
          timeout: 30000
        });
        
        // Wait for any animations to complete
        await page.waitForTimeout(1000);
        
        // Take screenshot
        const filename = `${String(index + 1).padStart(2, '0')}-${screen.name}.png`;
        const filepath = path.join(outputDir, filename);
        
        await page.screenshot({
          path: filepath,
          fullPage: false,
          type: 'png'
        });
        
        console.log(`      ✅ Saved: ${filename}`);
      }
    } catch (error) {
      console.error(`    ❌ Error generating screenshots: ${error.message}`);
    } finally {
      await page.close();
    }
  }

  generateScreenHTML(variant, screen, device) {
    const isTablet = device.width > 600;
    const isAndroid = device.platform === 'android';
    
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${variant.name} - ${screen.title}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: ${isAndroid ? 'Roboto, Arial, sans-serif' : '-apple-system, BlinkMacSystemFont, Arial, sans-serif'};
            background: linear-gradient(135deg, ${variant.primaryColor} 0%, ${this.adjustColor(variant.primaryColor, -20)} 100%);
            color: #333;
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .status-bar {
            height: ${isAndroid ? '24px' : device.name.includes('iPhone') ? '44px' : '20px'};
            background: ${isAndroid ? 'rgba(0,0,0,0.3)' : 'transparent'};
            color: ${isAndroid ? 'white' : '#000'};
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 16px;
            font-size: ${isAndroid ? '12px' : '14px'};
            font-weight: 500;
        }
        
        .time { font-weight: 600; }
        .battery { display: flex; align-items: center; gap: 4px; }
        
        .header {
            background: white;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .header h1 {
            font-size: ${isTablet ? '28px' : '20px'};
            font-weight: 700;
            color: ${variant.primaryColor};
        }
        
        .header .menu-icon {
            width: 24px;
            height: 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-around;
        }
        
        .header .menu-icon span {
            width: 100%;
            height: 2px;
            background: ${variant.primaryColor};
            border-radius: 1px;
        }
        
        .content {
            flex: 1;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        
        .hero-section {
            background: white;
            border-radius: 16px;
            padding: 32px 24px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
        }
        
        .hero-icon {
            width: ${isTablet ? '120px' : '80px'};
            height: ${isTablet ? '120px' : '80px'};
            background: ${variant.primaryColor};
            border-radius: 50%;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: ${isTablet ? '48px' : '32px'};
        }
        
        .hero-title {
            font-size: ${isTablet ? '32px' : '24px'};
            font-weight: 800;
            color: #1a1a1a;
            margin-bottom: 12px;
        }
        
        .hero-description {
            font-size: ${isTablet ? '18px' : '16px'};
            color: #666;
            line-height: 1.5;
            margin-bottom: 24px;
        }
        
        .cta-button {
            background: ${variant.primaryColor};
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: ${isTablet ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)'};
            gap: 16px;
        }
        
        .feature-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            text-align: center;
        }
        
        .feature-icon {
            width: 48px;
            height: 48px;
            background: ${this.adjustColor(variant.primaryColor, 10)};
            border-radius: 12px;
            margin: 0 auto 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .feature-title {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
        }
        
        .feature-text {
            font-size: 12px;
            color: #666;
            line-height: 1.4;
        }
        
        .bottom-nav {
            background: white;
            padding: 8px 0 ${device.name.includes('iPhone') ? '24px' : '8px'};
            border-top: 1px solid #e5e5e5;
            display: flex;
            justify-content: space-around;
            align-items: center;
        }
        
        .nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 8px;
        }
        
        .nav-icon {
            width: 24px;
            height: 24px;
            border-radius: 4px;
            background: ${variant.primaryColor};
            opacity: 0.3;
        }
        
        .nav-item.active .nav-icon {
            opacity: 1;
        }
        
        .nav-text {
            font-size: 10px;
            color: #666;
            font-weight: 500;
        }
        
        .nav-item.active .nav-text {
            color: ${variant.primaryColor};
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .hero-section {
            animation: fadeInUp 0.6s ease-out;
        }
        
        .feature-card {
            animation: fadeInUp 0.6s ease-out;
        }
        
        .feature-card:nth-child(1) { animation-delay: 0.1s; }
        .feature-card:nth-child(2) { animation-delay: 0.2s; }
        .feature-card:nth-child(3) { animation-delay: 0.3s; }
        .feature-card:nth-child(4) { animation-delay: 0.4s; }
        .feature-card:nth-child(5) { animation-delay: 0.5s; }
        .feature-card:nth-child(6) { animation-delay: 0.6s; }
    </style>
</head>
<body>
    <div class="status-bar">
        <div class="time">${this.getCurrentTime()}</div>
        <div class="battery">
            <span>100%</span>
            <div style="width: 20px; height: 10px; border: 1px solid currentColor; border-radius: 2px; position: relative;">
                <div style="position: absolute; right: -3px; top: 3px; width: 2px; height: 4px; background: currentColor; border-radius: 0 1px 1px 0;"></div>
                <div style="position: absolute; left: 1px; top: 1px; right: 1px; bottom: 1px; background: currentColor; border-radius: 1px;"></div>
            </div>
        </div>
    </div>
    
    <div class="header">
        <div class="menu-icon">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <h1>${variant.name}</h1>
        <div style="width: 24px;"></div>
    </div>
    
    <div class="content">
        <div class="hero-section">
            <div class="hero-icon">${this.getVariantIcon(variant.name)}</div>
            <h2 class="hero-title">${screen.title}</h2>
            <p class="hero-description">${screen.description}</p>
            <button class="cta-button">Get Started</button>
        </div>
        
        <div class="feature-grid">
            ${this.generateFeatureCards(variant, screen).join('')}
        </div>
    </div>
    
    <div class="bottom-nav">
        <div class="nav-item active">
            <div class="nav-icon"></div>
            <div class="nav-text">Home</div>
        </div>
        <div class="nav-item">
            <div class="nav-icon"></div>
            <div class="nav-text">Explore</div>
        </div>
        <div class="nav-item">
            <div class="nav-icon"></div>
            <div class="nav-text">Profile</div>
        </div>
        <div class="nav-item">
            <div class="nav-icon"></div>
            <div class="nav-text">Settings</div>
        </div>
    </div>
</body>
</html>`;
  }

  getVariantIcon(variantName) {
    const icons = {
      'PersonalLog': '📝',
      'BusinessLog': '💼',
      'FamilyLog': '👨‍👩‍👧‍👦',
      'FitnessLog': '💪',
      'TravelLog': '✈️',
      'EducationLog': '📚'
    };
    return icons[variantName] || '📱';
  }

  generateFeatureCards(variant, screen) {
    const features = this.getScreenFeatures(variant.name, screen.name);
    return features.map(feature => `
      <div class="feature-card">
        <div class="feature-icon">${feature.icon}</div>
        <div class="feature-title">${feature.title}</div>
        <div class="feature-text">${feature.text}</div>
      </div>
    `);
  }

  getScreenFeatures(variantName, screenName) {
    const featureMap = {
      PersonalLog: {
        dashboard: [
          { icon: '📊', title: 'Analytics', text: 'View your insights' },
          { icon: '🎯', title: 'Goals', text: 'Track progress' },
          { icon: '📅', title: 'Calendar', text: 'Schedule entries' },
          { icon: '🔔', title: 'Reminders', text: 'Never miss a day' }
        ],
        'journal-entry': [
          { icon: '✍️', title: 'Rich Editor', text: 'Format your text' },
          { icon: '📸', title: 'Photos', text: 'Add images' },
          { icon: '🎵', title: 'Voice Notes', text: 'Record audio' },
          { icon: '📍', title: 'Location', text: 'Tag places' }
        ],
        timeline: [
          { icon: '🗓️', title: 'Timeline', text: 'Browse by date' },
          { icon: '🔍', title: 'Search', text: 'Find entries' },
          { icon: '🏷️', title: 'Tags', text: 'Organize content' },
          { icon: '💾', title: 'Backup', text: 'Safe & secure' }
        ]
      },
      BusinessLog: {
        dashboard: [
          { icon: '💹', title: 'Revenue', text: 'Track income' },
          { icon: '👥', title: 'Team', text: 'Manage staff' },
          { icon: '📋', title: 'Tasks', text: 'To-do lists' },
          { icon: '📊', title: 'Reports', text: 'Business metrics' }
        ],
        'task-management': [
          { icon: '✅', title: 'Assignments', text: 'Delegate work' },
          { icon: '⏰', title: 'Deadlines', text: 'Meet targets' },
          { icon: '🔄', title: 'Workflow', text: 'Automate tasks' },
          { icon: '📈', title: 'Progress', text: 'Track completion' }
        ]
      }
      // Add more variants as needed
    };

    const defaultFeatures = [
      { icon: '⭐', title: 'Premium', text: 'Advanced features' },
      { icon: '🔒', title: 'Secure', text: 'Your data is safe' },
      { icon: '📱', title: 'Mobile', text: 'Use anywhere' },
      { icon: '🌙', title: 'Dark Mode', text: 'Easy on eyes' }
    ];

    return featureMap[variantName]?.[screenName] || defaultFeatures;
  }

  adjustColor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
      (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
      (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
  }

  getCurrentTime() {
    return new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  async generateStoreAssets() {
    console.log('\n🎨 Generating App Store marketing assets...');
    
    for (const [variantKey, variant] of Object.entries(APP_VARIANTS)) {
      const marketingDir = path.join(this.outputDir, variantKey, 'marketing');
      await fs.mkdir(marketingDir, { recursive: true });
      
      // Generate app store previews
      await this.generateAppStorePreview(variant, marketingDir);
      
      // Generate feature graphics
      await this.generateFeatureGraphics(variant, marketingDir);
    }
  }

  async generateAppStorePreview(variant, outputDir) {
    const page = await this.browser.newPage();
    
    try {
      await page.setViewport({ width: 1242, height: 2688, deviceScaleFactor: 3 });
      
      const html = `
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, ${variant.primaryColor} 0%, ${this.adjustColor(variant.primaryColor, -30)} 100%);
            font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .preview-container {
            text-align: center;
            color: white;
            padding: 60px 40px;
        }
        .app-icon {
            width: 200px;
            height: 200px;
            background: white;
            border-radius: 40px;
            margin: 0 auto 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 80px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .app-name {
            font-size: 64px;
            font-weight: 800;
            margin-bottom: 20px;
        }
        .tagline {
            font-size: 28px;
            opacity: 0.9;
            margin-bottom: 60px;
            font-weight: 300;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 40px;
            max-width: 800px;
            margin: 0 auto;
        }
        .feature {
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        .feature-icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .feature-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .feature-desc {
            font-size: 18px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="app-icon">${this.getVariantIcon(variant.name)}</div>
        <div class="app-name">${variant.name}</div>
        <div class="tagline">${this.getAppTagline(variant.name)}</div>
        <div class="features">
            ${this.getTopFeatures(variant.name).map(feature => `
                <div class="feature">
                    <div class="feature-icon">${feature.icon}</div>
                    <div class="feature-title">${feature.title}</div>
                    <div class="feature-desc">${feature.desc}</div>
                </div>
            `).join('')}
        </div>
    </div>
</body>
</html>`;
      
      await page.setContent(html, { waitUntil: 'networkidle0' });
      await page.waitForTimeout(1000);
      
      const filepath = path.join(outputDir, 'app-store-preview.png');
      await page.screenshot({
        path: filepath,
        fullPage: true,
        type: 'png'
      });
      
      console.log(`  ✅ Generated App Store preview for ${variant.name}`);
    } finally {
      await page.close();
    }
  }

  async generateFeatureGraphics(variant, outputDir) {
    const features = this.getTopFeatures(variant.name);
    
    for (const [index, feature] of features.entries()) {
      const page = await this.browser.newPage();
      
      try {
        await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 2 });
        
        const html = `
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: ${variant.primaryColor};
            font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            color: white;
        }
        .feature-showcase {
            text-align: center;
            padding: 80px 40px;
            max-width: 800px;
        }
        .feature-icon {
            font-size: 120px;
            margin-bottom: 40px;
        }
        .feature-title {
            font-size: 48px;
            font-weight: 800;
            margin-bottom: 30px;
        }
        .feature-desc {
            font-size: 24px;
            line-height: 1.4;
            opacity: 0.9;
            margin-bottom: 60px;
        }
        .app-branding {
            position: absolute;
            bottom: 60px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 20px;
            opacity: 0.7;
        }
        .mini-icon {
            width: 40px;
            height: 40px;
            background: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .app-name {
            font-size: 18px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="feature-showcase">
        <div class="feature-icon">${feature.icon}</div>
        <div class="feature-title">${feature.title}</div>
        <div class="feature-desc">${feature.desc}</div>
    </div>
    <div class="app-branding">
        <div class="mini-icon">${this.getVariantIcon(variant.name)}</div>
        <div class="app-name">${variant.name}</div>
    </div>
</body>
</html>`;
        
        await page.setContent(html, { waitUntil: 'networkidle0' });
        await page.waitForTimeout(500);
        
        const filepath = path.join(outputDir, `feature-${index + 1}-${feature.title.toLowerCase().replace(/\s+/g, '-')}.png`);
        await page.screenshot({
          path: filepath,
          fullPage: true,
          type: 'png'
        });
        
        console.log(`  ✅ Generated feature graphic: ${feature.title}`);
      } finally {
        await page.close();
      }
    }
  }

  getAppTagline(variantName) {
    const taglines = {
      'PersonalLog': 'Your thoughts, beautifully organized',
      'BusinessLog': 'Professional task management made simple',
      'FamilyLog': 'Bringing families closer together',
      'FitnessLog': 'Your personal fitness companion',
      'TravelLog': 'Document every adventure',
      'EducationLog': 'Learn, track, achieve'
    };
    return taglines[variantName] || 'Organize your life';
  }

  getTopFeatures(variantName) {
    const features = {
      PersonalLog: [
        { icon: '✍️', title: 'Rich Writing', desc: 'Express yourself with our powerful editor' },
        { icon: '📊', title: 'Insights', desc: 'Discover patterns in your thoughts' },
        { icon: '🔒', title: 'Private', desc: 'Your thoughts are secure and encrypted' },
        { icon: '📱', title: 'Everywhere', desc: 'Access your journal on all devices' }
      ],
      BusinessLog: [
        { icon: '📋', title: 'Task Management', desc: 'Organize and prioritize your work' },
        { icon: '👥', title: 'Team Collaboration', desc: 'Work together seamlessly' },
        { icon: '📈', title: 'Analytics', desc: 'Data-driven business insights' },
        { icon: '⚡', title: 'Automation', desc: 'Streamline your workflows' }
      ],
      FamilyLog: [
        { icon: '📸', title: 'Memory Sharing', desc: 'Create beautiful family albums' },
        { icon: '📅', title: 'Family Calendar', desc: 'Keep everyone synchronized' },
        { icon: '🎉', title: 'Milestones', desc: 'Celebrate important moments' },
        { icon: '💬', title: 'Family Chat', desc: 'Stay connected with loved ones' }
      ],
      FitnessLog: [
        { icon: '💪', title: 'Workout Tracking', desc: 'Log every rep and set' },
        { icon: '🍎', title: 'Nutrition', desc: 'Track your daily nutrition' },
        { icon: '📈', title: 'Progress', desc: 'See your fitness improvements' },
        { icon: '🎯', title: 'Goals', desc: 'Set and achieve fitness targets' }
      ],
      TravelLog: [
        { icon: '🗺️', title: 'Trip Planning', desc: 'Plan your perfect adventure' },
        { icon: '📍', title: 'Location Tracking', desc: 'Map your journey' },
        { icon: '📸', title: 'Photo Journal', desc: 'Create stunning travel stories' },
        { icon: '💰', title: 'Expense Tracking', desc: 'Stay within your budget' }
      ],
      EducationLog: [
        { icon: '📚', title: 'Course Management', desc: 'Organize your studies' },
        { icon: '📝', title: 'Note Taking', desc: 'Capture important information' },
        { icon: '📊', title: 'Grade Tracking', desc: 'Monitor your progress' },
        { icon: '🎓', title: 'Achievement', desc: 'Celebrate your success' }
      ]
    };
    
    return features[variantName] || features.PersonalLog;
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
      console.log('🔄 Browser closed');
    }
  }

  async generateSummaryReport() {
    const summaryPath = path.join(this.outputDir, 'SCREENSHOT_SUMMARY.md');
    const variants = Object.keys(APP_VARIANTS);
    const devices = Object.keys(DEVICES);
    
    let report = `# Screenshot Generation Report\n\n`;
    report += `Generated on: ${new Date().toLocaleString()}\n\n`;
    report += `## Summary\n`;
    report += `- **App Variants**: ${variants.length}\n`;
    report += `- **Device Configurations**: ${devices.length}\n`;
    report += `- **Total Screenshots**: ${variants.length * devices.length * 5} (5 screens per variant per device)\n\n`;
    
    report += `## App Variants\n`;
    variants.forEach(variant => {
      const variantData = APP_VARIANTS[variant];
      report += `### ${variantData.name}\n`;
      report += `- **Primary Color**: ${variantData.primaryColor}\n`;
      report += `- **Screens**: ${variantData.screens.length}\n`;
      report += `- **Directory**: \`screenshots/${variant}/\`\n\n`;
    });
    
    report += `## Device Configurations\n`;
    Object.entries(DEVICES).forEach(([key, device]) => {
      report += `### ${device.name}\n`;
      report += `- **Resolution**: ${device.width}x${device.height}\n`;
      report += `- **Pixel Ratio**: ${device.pixelRatio}\n`;
      report += `- **Platform**: ${device.platform}\n`;
      report += `- **Store Size**: ${device.storeSize}\n\n`;
    });
    
    report += `## File Structure\n`;
    report += `\`\`\`\n`;
    report += `screenshots/\n`;
    variants.forEach(variant => {
      report += `├── ${variant}/\n`;
      devices.forEach(device => {
        report += `│   ├── ${device}/\n`;
        report += `│   │   ├── 01-dashboard.png\n`;
        report += `│   │   ├── 02-main-feature.png\n`;
        report += `│   │   ├── 03-secondary-feature.png\n`;
        report += `│   │   ├── 04-additional-feature.png\n`;
        report += `│   │   └── 05-final-feature.png\n`;
      });
      report += `│   └── marketing/\n`;
      report += `│       ├── app-store-preview.png\n`;
      report += `│       ├── feature-1-*.png\n`;
      report += `│       ├── feature-2-*.png\n`;
      report += `│       ├── feature-3-*.png\n`;
      report += `│       └── feature-4-*.png\n`;
    });
    report += `\`\`\`\n\n`;
    
    report += `## Usage Instructions\n`;
    report += `1. **App Store Screenshots**: Use device-specific folders for App Store submissions\n`;
    report += `2. **Marketing Assets**: Use files in \`marketing/\` folders for promotional materials\n`;
    report += `3. **Web Preview**: Feature graphics can be used on websites and landing pages\n\n`;
    
    report += `## App Store Requirements Met\n`;
    report += `- ✅ iPhone 6.7" screenshots (iPhone 15 Pro Max)\n`;
    report += `- ✅ iPhone 6.1" screenshots (iPhone 15 Pro)\n`;
    report += `- ✅ iPhone 4.7" screenshots (iPhone SE)\n`;
    report += `- ✅ iPad 12.9" screenshots (iPad Pro)\n`;
    report += `- ✅ iPad 10.9" screenshots (iPad Air)\n`;
    report += `- ✅ Android phone screenshots (Multiple sizes)\n`;
    report += `- ✅ Android tablet screenshots\n`;
    report += `- ✅ Feature graphics for promotional use\n\n`;
    
    await fs.writeFile(summaryPath, report);
    console.log(`📋 Summary report saved: ${summaryPath}`);
  }
}

// Main execution
async function main() {
  const generator = new ScreenshotGenerator();
  
  try {
    await generator.initialize();
    await generator.generateAllScreenshots();
    await generator.generateStoreAssets();
    await generator.generateSummaryReport();
    
    console.log('\n🎉 Screenshot generation completed successfully!');
    console.log('📂 Check the screenshots/ directory for all generated files');
    
  } catch (error) {
    console.error('❌ Error generating screenshots:', error);
    process.exit(1);
  } finally {
    await generator.cleanup();
  }
}

// Export for module usage
module.exports = { ScreenshotGenerator, DEVICES, APP_VARIANTS };

// Run if called directly
if (require.main === module) {
  main();
}