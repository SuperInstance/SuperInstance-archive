const fs = require('fs').promises;
const path = require('path');

// App Store metadata configurations
const APP_VARIANTS = {
  'personal-log': {
    name: 'PersonalLog',
    subtitle: 'Your Digital Journal',
    primaryColor: '#6366F1',
    category: 'Lifestyle',
    keywords: ['journal', 'diary', 'personal', 'writing', 'thoughts', 'memories', 'daily', 'reflection'],
    targetAudience: 'individuals seeking personal growth and memory preservation',
    mainBenefit: 'beautifully organized digital journaling',
    screenshots: ['dashboard', 'journal-entry', 'timeline', 'mood-tracking', 'insights']
  },
  'business-log': {
    name: 'BusinessLog',
    subtitle: 'Professional Task Management',
    primaryColor: '#059669',
    category: 'Productivity',
    keywords: ['business', 'tasks', 'productivity', 'team', 'management', 'workflow', 'collaboration', 'enterprise'],
    targetAudience: 'business professionals and teams',
    mainBenefit: 'streamlined business task management',
    screenshots: ['dashboard', 'task-management', 'team-collaboration', 'analytics', 'reports']
  },
  'family-log': {
    name: 'FamilyLog',
    subtitle: 'Family Memories & Planning',
    primaryColor: '#DC2626',
    category: 'Lifestyle',
    keywords: ['family', 'memories', 'photos', 'calendar', 'sharing', 'milestones', 'children', 'relatives'],
    targetAudience: 'families wanting to stay connected and preserve memories',
    mainBenefit: 'bringing families closer together',
    screenshots: ['dashboard', 'shared-calendar', 'photo-albums', 'milestone-tracking', 'memory-sharing']
  },
  'fitness-log': {
    name: 'FitnessLog',
    subtitle: 'Your Personal Fitness Companion',
    primaryColor: '#EA580C',
    category: 'Health & Fitness',
    keywords: ['fitness', 'workout', 'exercise', 'health', 'nutrition', 'goals', 'progress', 'training'],
    targetAudience: 'fitness enthusiasts and health-conscious individuals',
    mainBenefit: 'comprehensive fitness and health tracking',
    screenshots: ['dashboard', 'workout-tracking', 'nutrition-log', 'progress-charts', 'goal-setting']
  },
  'travel-log': {
    name: 'TravelLog',
    subtitle: 'Document Every Adventure',
    primaryColor: '#0891B2',
    category: 'Travel',
    keywords: ['travel', 'trip', 'adventure', 'photos', 'locations', 'itinerary', 'expenses', 'memories'],
    targetAudience: 'travelers and adventure seekers',
    mainBenefit: 'comprehensive travel documentation and planning',
    screenshots: ['dashboard', 'trip-planning', 'location-tracking', 'photo-journal', 'expense-tracking']
  },
  'education-log': {
    name: 'EducationLog',
    subtitle: 'Learn, Track, Achieve',
    primaryColor: '#7C3AED',
    category: 'Education',
    keywords: ['education', 'learning', 'courses', 'grades', 'study', 'progress', 'students', 'academic'],
    targetAudience: 'students and lifelong learners',
    mainBenefit: 'organized educational progress tracking',
    screenshots: ['dashboard', 'course-management', 'grade-tracking', 'study-planner', 'progress-reports']
  }
};

class AppStoreDescriptionGenerator {
  constructor() {
    this.outputDir = path.join(__dirname, '..', 'app-store-metadata');
  }

  async generateAllDescriptions() {
    console.log('📝 Generating App Store descriptions...');
    
    await fs.mkdir(this.outputDir, { recursive: true });
    
    for (const [variantKey, variant] of Object.entries(APP_VARIANTS)) {
      console.log(`\n🎯 Generating descriptions for ${variant.name}...`);
      
      const variantDir = path.join(this.outputDir, variantKey);
      await fs.mkdir(variantDir, { recursive: true });
      
      // Generate all description types
      await this.generateAppStoreDescription(variant, variantDir);
      await this.generateGooglePlayDescription(variant, variantDir);
      await this.generateWebDescription(variant, variantDir);
      await this.generatePressRelease(variant, variantDir);
      await this.generateMetadata(variant, variantDir);
      
      console.log(`  ✅ All descriptions generated for ${variant.name}`);
    }
    
    await this.generateMasterSummary();
    console.log('\n🎉 All App Store descriptions generated successfully!');
  }

  async generateAppStoreDescription(variant, outputDir) {
    const description = this.createAppStoreDescription(variant);
    
    const content = `# ${variant.name} - App Store Description

## App Name
${variant.name}

## Subtitle (30 characters max)
${variant.subtitle}

## Description (4000 characters max)
${description.full}

## Promotional Text (170 characters max)
${description.promotional}

## Keywords (100 characters max)
${variant.keywords.join(', ')}

## What's New (4000 characters max)
${description.whatsNew}

## App Preview and Screenshots Order
1. ${this.getScreenshotDescription(variant, variant.screenshots[0])}
2. ${this.getScreenshotDescription(variant, variant.screenshots[1])}
3. ${this.getScreenshotDescription(variant, variant.screenshots[2])}
4. ${this.getScreenshotDescription(variant, variant.screenshots[3])}
5. ${this.getScreenshotDescription(variant, variant.screenshots[4])}

## App Information
- **Category**: ${variant.category}
- **Content Rating**: 4+ (No objectionable content)
- **Copyright**: © 2024 ActiveLog Technologies
- **Developer Website**: https://activelog.com
- **Support URL**: https://activelog.com/support
- **Privacy Policy URL**: https://activelog.com/privacy

## Review Guidelines Compliance
✅ Follows App Store Review Guidelines
✅ No restricted content
✅ Clear app functionality
✅ Accurate descriptions
✅ Appropriate metadata
`;

    const filepath = path.join(outputDir, 'app-store-description.md');
    await fs.writeFile(filepath, content);
    console.log(`    📱 App Store description saved`);
  }

  async generateGooglePlayDescription(variant, outputDir) {
    const description = this.createGooglePlayDescription(variant);
    
    const content = `# ${variant.name} - Google Play Store Description

## App Title (30 characters max)
${variant.name}

## Short Description (80 characters max)
${description.short}

## Full Description (4000 characters max)
${description.full}

## Promotional Video Script
${this.createVideoScript(variant)}

## What's New (500 characters max)
${description.whatsNew}

## App Information
- **Category**: ${this.getGooglePlayCategory(variant.category)}
- **Content Rating**: Everyone
- **Target Age Group**: 13+
- **Contains Ads**: No
- **In-app Products**: Yes (Premium features)

## Store Listing
- **Feature Graphic**: 1024 x 500 px
- **Icon**: 512 x 512 px
- **Screenshots**: At least 2, up to 8
- **Phone Screenshots**: 320-3840 px (16:9 to 9:16 ratio)
- **Tablet Screenshots**: 320-3840 px (16:9 to 9:16 ratio)

## Keywords/Tags
${variant.keywords.join(', ')}

## Developer Information
- **Developer Name**: ActiveLog Technologies
- **Website**: https://activelog.com
- **Email**: support@activelog.com
- **Privacy Policy**: https://activelog.com/privacy
`;

    const filepath = path.join(outputDir, 'google-play-description.md');
    await fs.writeFile(filepath, content);
    console.log(`    🤖 Google Play description saved`);
  }

  async generateWebDescription(variant, outputDir) {
    const description = this.createWebDescription(variant);
    
    const content = `# ${variant.name} - Website & Marketing Copy

## Hero Section
### Headline
${description.headline}

### Subheadline
${description.subheadline}

### Call-to-Action
Download ${variant.name} Today - Free with Premium Options

## About Section
${description.about}

## Key Features (For Landing Page)
${this.getKeyFeatures(variant).map((feature, index) => `
### ${index + 1}. ${feature.title}
${feature.description}
- ${feature.benefits.join('\n- ')}
`).join('\n')}

## Benefits Section
### Why Choose ${variant.name}?
${this.getBenefits(variant).map(benefit => `
**${benefit.title}**
${benefit.description}
`).join('\n')}

## Social Media Copy
### Twitter/X Posts
${this.getSocialMediaPosts(variant).twitter.join('\n\n')}

### Instagram Captions
${this.getSocialMediaPosts(variant).instagram.join('\n\n---\n\n')}

### LinkedIn Posts
${this.getSocialMediaPosts(variant).linkedin.join('\n\n')}

## Email Marketing
### Subject Lines
${this.getEmailSubjects(variant).join('\n')}

### Newsletter Content
${description.newsletter}

## SEO Metadata
- **Title Tag**: ${description.seoTitle}
- **Meta Description**: ${description.seoDescription}
- **Keywords**: ${variant.keywords.join(', ')}
- **Alt Text for Images**: ${variant.name} app screenshots showing ${variant.mainBenefit}
`;

    const filepath = path.join(outputDir, 'web-marketing-copy.md');
    await fs.writeFile(filepath, content);
    console.log(`    🌐 Web marketing copy saved`);
  }

  async generatePressRelease(variant, outputDir) {
    const content = `# Press Release: ${variant.name}

## FOR IMMEDIATE RELEASE

**ActiveLog Technologies Launches ${variant.name}, Revolutionary ${variant.category} App for ${variant.targetAudience}**

*${variant.name} offers ${variant.mainBenefit} with innovative features designed for modern users*

**[City, Date]** - ActiveLog Technologies today announced the launch of ${variant.name}, a groundbreaking ${variant.category.toLowerCase()} application designed specifically for ${variant.targetAudience}. The app delivers ${variant.mainBenefit} through an intuitive interface and powerful features that set new standards in the ${variant.category.toLowerCase()} category.

## Key Innovation Points

${variant.name} addresses the growing need for ${this.getPressReleaseNeed(variant)} with several innovative features:

${this.getKeyFeatures(variant).map(feature => `
**${feature.title}**: ${feature.description} This feature helps users ${feature.benefits[0].toLowerCase()}.`).join('\n')}

## Market Opportunity

The ${variant.category.toLowerCase()} app market continues to grow rapidly, with ${variant.targetAudience} increasingly seeking digital solutions that ${this.getMarketNeed(variant)}. ${variant.name} positions itself uniquely in this space by ${this.getUniquePosition(variant)}.

## Executive Quote

"We created ${variant.name} because we saw a gap in the market for ${variant.mainBenefit}," said [CEO Name], CEO of ActiveLog Technologies. "Our team has spent months perfecting the user experience to ensure that ${variant.targetAudience} have everything they need in one beautifully designed application."

## Product Details

${variant.name} is available for free download on both iOS and Android platforms, with premium features available through in-app purchases. The app includes:

${this.getKeyFeatures(variant).map(feature => `- ${feature.title}: ${feature.description}`).join('\n')}

## Availability

${variant.name} is now available for download on the App Store and Google Play Store. The app is free to download with optional premium features starting at $4.99/month.

## About ActiveLog Technologies

ActiveLog Technologies specializes in creating innovative digital solutions that help people organize and enhance their lives. Founded in 2024, the company is committed to developing user-friendly applications that solve real-world problems through elegant design and powerful functionality.

## Media Contact

**Press Relations**
ActiveLog Technologies
Email: press@activelog.com
Phone: [Phone Number]
Website: https://activelog.com/press

**Product Information**
Support Team
Email: support@activelog.com
Website: https://activelog.com/support

## Download Information

**iOS**: Available on the App Store
**Android**: Available on Google Play
**Website**: https://activelog.com/${variant.name.toLowerCase()}

###

*Note to editors: High-resolution screenshots, app icons, and additional press materials are available at https://activelog.com/press*
`;

    const filepath = path.join(outputDir, 'press-release.md');
    await fs.writeFile(filepath, content);
    console.log(`    📰 Press release saved`);
  }

  async generateMetadata(variant, outputDir) {
    const metadata = {
      app_name: variant.name,
      subtitle: variant.subtitle,
      bundle_id: `com.activelog.${variant.name.toLowerCase()}`,
      version: '1.0.0',
      build_number: '1',
      category: variant.category,
      keywords: variant.keywords,
      primary_color: variant.primaryColor,
      target_audience: variant.targetAudience,
      main_benefit: variant.mainBenefit,
      screenshots: variant.screenshots,
      supported_devices: ['iPhone', 'iPad', 'Android Phone', 'Android Tablet'],
      minimum_os: {
        ios: '13.0',
        android: '21 (Android 5.0)'
      },
      localization: ['en-US'],
      pricing: {
        base: 'Free',
        premium: '$4.99/month',
        annual: '$49.99/year'
      },
      app_store_rating: '4+',
      google_play_rating: 'Everyone',
      file_sizes: {
        ios: 'Varies by device',
        android: 'Varies by device'
      },
      features: this.getKeyFeatures(variant).map(f => f.title),
      release_notes: this.getReleaseNotes(variant),
      support_info: {
        website: 'https://activelog.com',
        support_url: 'https://activelog.com/support',
        privacy_policy: 'https://activelog.com/privacy',
        terms_of_service: 'https://activelog.com/terms'
      }
    };

    const filepath = path.join(outputDir, 'metadata.json');
    await fs.writeFile(filepath, JSON.stringify(metadata, null, 2));
    console.log(`    📋 Metadata JSON saved`);
  }

  createAppStoreDescription(variant) {
    const features = this.getKeyFeatures(variant);
    const benefits = this.getBenefits(variant);
    
    const full = `Transform your ${this.getDescriptionContext(variant)} with ${variant.name} - the ultimate ${variant.category.toLowerCase()} app designed for ${variant.targetAudience}.

🌟 WHY CHOOSE ${variant.name.toUpperCase()}?

${variant.name} isn't just another ${variant.category.toLowerCase()} app. It's your personal companion that understands what ${variant.targetAudience} really need. With ${variant.mainBenefit}, you'll discover a new level of organization and efficiency that fits perfectly into your lifestyle.

✨ POWERFUL FEATURES

${features.map(feature => `${this.getEmoji(feature.title)} ${feature.title}
${feature.description}
${feature.benefits.map(b => `• ${b}`).join('\n')}
`).join('\n')}

🎯 PERFECT FOR YOU IF:
${this.getTargetUserTypes(variant).map(type => `• ${type}`).join('\n')}

🏆 WHY USERS LOVE ${variant.name}:
${benefits.map(benefit => `• ${benefit.title}: ${benefit.description}`).join('\n')}

💎 PREMIUM FEATURES
Unlock the full potential of ${variant.name} with premium features including advanced analytics, unlimited storage, priority support, and exclusive tools designed for power users.

🔒 PRIVACY & SECURITY
Your data is precious to us. ${variant.name} uses end-to-end encryption and follows strict privacy policies to ensure your information stays secure and private.

📱 CROSS-PLATFORM SYNC
Start on your iPhone, continue on your iPad, and access everything from the web. Your data syncs seamlessly across all your devices.

🆓 FREE TO START
Download ${variant.name} today and start with our generous free tier. Upgrade to premium when you're ready for advanced features.

Join thousands of satisfied users who have already transformed their ${this.getDescriptionContext(variant)} with ${variant.name}.

Download now and experience the difference!`;

    const promotional = `Transform your ${this.getDescriptionContext(variant)} with ${variant.name} - ${variant.mainBenefit} that users love. Start free today!`;
    
    const whatsNew = `🎉 Welcome to ${variant.name} v1.0!

We're excited to introduce ${variant.name}, featuring:

${features.slice(0, 3).map(feature => `• ${feature.title}: ${feature.description.split('.')[0]}`).join('\n')}

• Beautiful, intuitive interface designed for ${variant.targetAudience}
• Cross-platform synchronization
• Premium features with free trial
• Enterprise-grade security and privacy

This is just the beginning! We have exciting updates planned based on your feedback.

Thank you for choosing ${variant.name}!`;

    return { full, promotional, whatsNew };
  }

  createGooglePlayDescription(variant) {
    const features = this.getKeyFeatures(variant);
    
    const short = `${variant.mainBenefit} for ${variant.targetAudience} - Start free!`;
    
    const full = `🌟 Transform Your ${this.getDescriptionContext(variant)} with ${variant.name}

${variant.name} is the ultimate ${variant.category.toLowerCase()} app designed specifically for ${variant.targetAudience}. Experience ${variant.mainBenefit} with features that actually work for your lifestyle.

🚀 KEY FEATURES

${features.map(feature => `📌 ${feature.title}
${feature.description}
${feature.benefits.slice(0, 2).map(b => `  ✓ ${b}`).join('\n')}
`).join('\n')}

🎯 WHO IS THIS FOR?
${this.getTargetUserTypes(variant).map(type => `• ${type}`).join('\n')}

💡 WHY CHOOSE ${variant.name}?
${this.getBenefits(variant).slice(0, 4).map(benefit => `✅ ${benefit.title} - ${benefit.description}`).join('\n')}

🔒 PRIVACY FIRST
Your data is encrypted and secure. We never sell your personal information and follow strict privacy policies.

💎 FREE & PREMIUM
• Free version includes core features
• Premium subscription unlocks advanced tools
• 7-day free trial for premium features
• Cancel anytime

📱 SYNC EVERYWHERE
Works seamlessly across Android phones, tablets, and web browsers.

⭐ JOIN THOUSANDS OF HAPPY USERS
"${this.getTestimonial(variant)}"

Download ${variant.name} now and start your journey toward ${variant.mainBenefit}!

For support, visit: https://activelog.com/support`;
    
    const whatsNew = `🎉 New ${variant.name} v1.0 features: Enhanced ${features[0].title.toLowerCase()}, improved sync, and premium trial!`;

    return { short, full, whatsNew };
  }

  createWebDescription(variant) {
    return {
      headline: `${variant.name}: ${variant.subtitle}`,
      subheadline: `The ultimate ${variant.category.toLowerCase()} app for ${variant.targetAudience} who want ${variant.mainBenefit}`,
      about: `${variant.name} revolutionizes how ${variant.targetAudience} approach ${this.getDescriptionContext(variant)}. Our innovative platform combines powerful features with intuitive design, making it easier than ever to ${this.getMainAction(variant)}. Whether you're just starting out or you're a power user, ${variant.name} adapts to your needs and grows with you.`,
      newsletter: `Discover how ${variant.name} can transform your ${this.getDescriptionContext(variant)}. Our ${variant.category.toLowerCase()} app offers ${variant.mainBenefit} with features designed specifically for ${variant.targetAudience}. Join thousands of users who have already improved their ${this.getDescriptionContext(variant)} with ${variant.name}. Download free today and see the difference!`,
      seoTitle: `${variant.name} - ${variant.subtitle} | ${variant.category} App`,
      seoDescription: `${variant.mainBenefit} with ${variant.name}. Perfect for ${variant.targetAudience}. Free download with premium features. Start today!`
    };
  }

  getKeyFeatures(variant) {
    const featureMap = {
      'PersonalLog': [
        {
          title: 'Rich Writing Experience',
          description: 'Express your thoughts with our powerful text editor featuring formatting, photos, and voice notes.',
          benefits: ['Format text with bold, italic, and lists', 'Add photos and voice recordings', 'Tag entries with moods and topics']
        },
        {
          title: 'Personal Insights',
          description: 'Discover patterns in your thoughts and mood with intelligent analytics and beautiful visualizations.',
          benefits: ['Track mood changes over time', 'Identify writing patterns', 'Get personalized insights']
        },
        {
          title: 'Secure & Private',
          description: 'Your thoughts are protected with end-to-end encryption and advanced privacy controls.',
          benefits: ['End-to-end encryption', 'Biometric lock options', 'Private cloud sync']
        }
      ],
      'BusinessLog': [
        {
          title: 'Smart Task Management',
          description: 'Organize projects with intelligent task prioritization, deadlines, and team collaboration.',
          benefits: ['AI-powered task prioritization', 'Deadline tracking and reminders', 'Team collaboration tools']
        },
        {
          title: 'Business Analytics',
          description: 'Make data-driven decisions with comprehensive reports and performance metrics.',
          benefits: ['Real-time performance dashboards', 'Custom report generation', 'ROI tracking and analysis']
        },
        {
          title: 'Team Collaboration',
          description: 'Work seamlessly with your team using shared workspaces, comments, and real-time updates.',
          benefits: ['Shared project workspaces', 'Real-time commenting system', 'Team activity feeds']
        }
      ],
      'FamilyLog': [
        {
          title: 'Family Memory Sharing',
          description: 'Create beautiful family albums and share precious moments with loved ones.',
          benefits: ['Collaborative photo albums', 'Family timeline creation', 'Memory sharing with relatives']
        },
        {
          title: 'Shared Family Calendar',
          description: 'Keep everyone on the same page with shared calendars, events, and reminders.',
          benefits: ['Synchronized family calendar', 'Event planning tools', 'Shared reminders and notifications']
        },
        {
          title: 'Milestone Tracking',
          description: 'Never forget important family moments with milestone tracking and celebration reminders.',
          benefits: ['Birthday and anniversary tracking', 'Growth milestone recording', 'Achievement celebrations']
        }
      ],
      'FitnessLog': [
        {
          title: 'Comprehensive Workout Tracking',
          description: 'Log every workout with detailed exercise tracking, progress photos, and performance analytics.',
          benefits: ['Exercise database with 1000+ workouts', 'Progress photo tracking', 'Strength and cardio analytics']
        },
        {
          title: 'Nutrition Management',
          description: 'Track your nutrition with barcode scanning, meal planning, and macro tracking.',
          benefits: ['Barcode scanning for food items', 'Meal planning and prep tools', 'Macro and calorie tracking']
        },
        {
          title: 'Goal Achievement',
          description: 'Set fitness goals and track your progress with motivating charts and achievement badges.',
          benefits: ['Customizable fitness goals', 'Progress visualization charts', 'Achievement badge system']
        }
      ],
      'TravelLog': [
        {
          title: 'Trip Planning & Organization',
          description: 'Plan perfect trips with itinerary management, booking tracking, and travel checklists.',
          benefits: ['Visual itinerary planning', 'Booking and reservation tracking', 'Travel checklist templates']
        },
        {
          title: 'Location & Photo Journaling',
          description: 'Document your adventures with GPS tracking, photo journals, and travel stories.',
          benefits: ['GPS location tracking', 'Photo journal creation', 'Travel story writing tools']
        },
        {
          title: 'Expense Tracking',
          description: 'Stay within budget with currency conversion, expense categorization, and spending analytics.',
          benefits: ['Multi-currency expense tracking', 'Budget planning and alerts', 'Spending analytics and reports']
        }
      ],
      'EducationLog': [
        {
          title: 'Course & Grade Management',
          description: 'Organize your academic life with course tracking, grade monitoring, and GPA calculation.',
          benefits: ['Course schedule management', 'Grade tracking and GPA calculation', 'Academic progress reports']
        },
        {
          title: 'Study Planning',
          description: 'Optimize your study time with smart scheduling, assignment tracking, and exam preparation.',
          benefits: ['Smart study schedule creation', 'Assignment and deadline tracking', 'Exam preparation tools']
        },
        {
          title: 'Learning Analytics',
          description: 'Understand your learning patterns with study time analysis and performance insights.',
          benefits: ['Study time tracking and analysis', 'Learning pattern identification', 'Performance improvement suggestions']
        }
      ]
    };

    return featureMap[variant.name] || featureMap['PersonalLog'];
  }

  getBenefits(variant) {
    const benefitMap = {
      'PersonalLog': [
        { title: 'Improve Self-Awareness', description: 'Gain deeper insights into your thoughts and emotions' },
        { title: 'Never Lose Memories', description: 'All your entries are safely backed up and searchable' },
        { title: 'Build Healthy Habits', description: 'Consistent journaling promotes mental wellness' },
        { title: 'Express Creativity', description: 'Multiple formats let you capture thoughts your way' }
      ],
      'BusinessLog': [
        { title: 'Increase Productivity', description: 'Smart task management helps you focus on what matters' },
        { title: 'Make Better Decisions', description: 'Data-driven insights guide strategic choices' },
        { title: 'Improve Team Communication', description: 'Collaboration tools keep everyone aligned' },
        { title: 'Scale Your Business', description: 'Organized workflows support business growth' }
      ],
      'FamilyLog': [
        { title: 'Strengthen Family Bonds', description: 'Shared experiences bring families closer together' },
        { title: 'Preserve Precious Moments', description: 'Never lose important family memories again' },
        { title: 'Stay Organized Together', description: 'Coordinated planning reduces family stress' },
        { title: 'Create Lasting Legacy', description: 'Build a digital family heritage for future generations' }
      ],
      'FitnessLog': [
        { title: 'Achieve Fitness Goals Faster', description: 'Tracking and analytics accelerate progress' },
        { title: 'Stay Motivated Daily', description: 'Visual progress and achievements keep you going' },
        { title: 'Optimize Your Workouts', description: 'Data insights help you train more effectively' },
        { title: 'Build Lasting Habits', description: 'Consistent tracking creates sustainable routines' }
      ],
      'TravelLog': [
        { title: 'Travel with Confidence', description: 'Organized planning reduces travel stress' },
        { title: 'Maximize Your Adventures', description: 'Never miss must-see attractions or experiences' },
        { title: 'Preserve Travel Memories', description: 'Create beautiful records of every journey' },
        { title: 'Stay Within Budget', description: 'Expense tracking helps control travel costs' }
      ],
      'EducationLog': [
        { title: 'Improve Academic Performance', description: 'Organized study habits lead to better grades' },
        { title: 'Reduce Academic Stress', description: 'Clear planning eliminates last-minute panic' },
        { title: 'Optimize Study Time', description: 'Analytics show you how to study more effectively' },
        { title: 'Achieve Learning Goals', description: 'Structured tracking keeps you on target' }
      ]
    };

    return benefitMap[variant.name] || benefitMap['PersonalLog'];
  }

  getTargetUserTypes(variant) {
    const typeMap = {
      'PersonalLog': [
        'You want to develop a consistent journaling habit',
        'You\'re interested in personal growth and self-reflection',
        'You have thoughts and experiences you want to preserve',
        'You prefer digital tools over paper journals'
      ],
      'BusinessLog': [
        'You\'re a business owner or manager looking to improve productivity',
        'You work with a team and need collaboration tools',
        'You want to make data-driven business decisions',
        'You need to track projects and deadlines effectively'
      ],
      'FamilyLog': [
        'You want to stay better connected with family members',
        'You love preserving and sharing family memories',
        'You need help coordinating family schedules and events',
        'You want to create a digital legacy for your family'
      ],
      'FitnessLog': [
        'You\'re committed to improving your health and fitness',
        'You like tracking your progress and seeing results',
        'You want to optimize your workouts and nutrition',
        'You need motivation to stick to your fitness goals'
      ],
      'TravelLog': [
        'You love to travel and want to document your adventures',
        'You need help planning and organizing trips',
        'You want to keep track of travel expenses and budgets',
        'You enjoy sharing travel experiences with others'
      ],
      'EducationLog': [
        'You\'re a student looking to improve academic performance',
        'You want to better organize your study schedule',
        'You need help tracking assignments and deadlines',
        'You\'re interested in analyzing your learning patterns'
      ]
    };

    return typeMap[variant.name] || typeMap['PersonalLog'];
  }

  getSocialMediaPosts(variant) {
    return {
      twitter: [
        `✨ Just launched ${variant.name}! Perfect for ${variant.targetAudience} who want ${variant.mainBenefit} 🚀 #${variant.name} #${variant.category} #ProductivityApp`,
        `${this.getEmoji(variant.name)} ${variant.name} makes ${this.getDescriptionContext(variant)} so much easier! Try it free today 📱 Download link in bio`,
        `Why struggle with ${this.getDescriptionContext(variant)}? ${variant.name} has everything ${variant.targetAudience} need in one beautiful app 💫 #AppLaunch`
      ],
      instagram: [
        `🌟 Introducing ${variant.name}! 
        
Transform your ${this.getDescriptionContext(variant)} with our beautifully designed app. Perfect for ${variant.targetAudience} who want ${variant.mainBenefit}.

✨ What makes us different:
${this.getKeyFeatures(variant).slice(0, 3).map(f => `• ${f.title}`).join('\n')}

Download free today! Link in bio 📱

#${variant.name} #${variant.category} #AppLaunch #Productivity #DigitalWellness`,

        `📱 ${variant.name} User Spotlight!
        
"This app has completely transformed my ${this.getDescriptionContext(variant)}. I can't imagine going back to the old way!" - Sarah M.

See why thousands of ${variant.targetAudience} are choosing ${variant.name} for ${variant.mainBenefit}.

Try it free today! 🚀

#UserTestimonial #${variant.name} #${variant.category}Success`
      ],
      linkedin: [
        `🚀 Excited to announce the launch of ${variant.name}!
        
After months of development, we've created the ultimate ${variant.category.toLowerCase()} solution for ${variant.targetAudience}.

Key innovations:
${this.getKeyFeatures(variant).slice(0, 2).map(f => `• ${f.title}: ${f.description.split('.')[0]}`).join('\n')}

Available now on iOS and Android. What features are most important to you in a ${variant.category.toLowerCase()} app?

#ProductLaunch #${variant.category} #Innovation #MobileApp`,

        `The future of ${this.getDescriptionContext(variant)} is here. ${variant.name} represents a new approach to ${variant.category.toLowerCase()} apps - one that actually understands what ${variant.targetAudience} need.

With ${variant.mainBenefit}, we're helping users achieve more than they thought possible.

Ready to transform your ${this.getDescriptionContext(variant)}? Download ${variant.name} today.

#Innovation #${variant.category} #DigitalTransformation`
      ]
    };
  }

  getEmailSubjects(variant) {
    return [
      `🎉 ${variant.name} is here! Transform your ${this.getDescriptionContext(variant)} today`,
      `The ${variant.category.toLowerCase()} app ${variant.targetAudience} have been waiting for`,
      `${variant.name}: ${variant.mainBenefit} made simple`,
      `Download ${variant.name} free - perfect for ${variant.targetAudience}`,
      `Why ${variant.name} is different from every other ${variant.category.toLowerCase()} app`
    ];
  }

  createVideoScript(variant) {
    return `# ${variant.name} - App Preview Video Script (30 seconds)

**SCENE 1** (0-3s)
- Show app icon animation
- Text overlay: "${variant.name}"
- Voiceover: "Introducing ${variant.name}"

**SCENE 2** (3-8s)
- Show main dashboard screen
- Highlight key interface elements
- Voiceover: "The ultimate ${variant.category.toLowerCase()} app for ${variant.targetAudience}"

**SCENE 3** (8-15s)
- Demonstrate first key feature
- Show smooth interactions
- Voiceover: "${this.getKeyFeatures(variant)[0].description.split('.')[0]}"

**SCENE 4** (15-22s)
- Show second key feature
- Demonstrate ease of use
- Voiceover: "${this.getKeyFeatures(variant)[1].description.split('.')[0]}"

**SCENE 5** (22-27s)
- Show results/benefits screen
- Display success metrics
- Voiceover: "Join thousands achieving ${variant.mainBenefit}"

**SCENE 6** (27-30s)
- Show download screens (App Store/Google Play)
- Text overlay: "Download Free Today"
- Voiceover: "Download ${variant.name} - free today!"

**Music**: Upbeat, modern, inspiring
**Style**: Clean, modern animations with smooth transitions
**Colors**: Primary brand color ${variant.primaryColor} with white/light backgrounds`;
  }

  getScreenshotDescription(variant, screenName) {
    const descriptions = {
      dashboard: `Main dashboard showing overview of ${this.getMainAction(variant)} activities`,
      'journal-entry': 'Rich text editor with formatting options and media attachments',
      timeline: 'Chronological view of entries with search and filtering options',
      'mood-tracking': 'Mood tracking interface with visual analytics',
      insights: 'Personal insights dashboard with charts and trends',
      'task-management': 'Task organization interface with priorities and deadlines',
      'team-collaboration': 'Team workspace showing collaborative features',
      analytics: 'Business analytics dashboard with key metrics',
      reports: 'Professional report generation and export options',
      'shared-calendar': 'Family calendar with shared events and reminders',
      'photo-albums': 'Photo album creation and sharing interface',
      'milestone-tracking': 'Family milestone tracking with celebration features',
      'memory-sharing': 'Memory sharing interface with family connections',
      'workout-tracking': 'Workout logging with exercise selection and tracking',
      'nutrition-log': 'Nutrition tracking with food database and macros',
      'progress-charts': 'Fitness progress visualization with charts and graphs',
      'goal-setting': 'Goal creation and tracking interface',
      'trip-planning': 'Trip planning interface with itinerary management',
      'location-tracking': 'Location-based journaling with map integration',
      'photo-journal': 'Travel photo journal with location tagging',
      'expense-tracking': 'Travel expense tracking with currency conversion',
      'course-management': 'Course organization with schedule and materials',
      'grade-tracking': 'Grade tracking interface with GPA calculation',
      'study-planner': 'Study schedule planning with time blocking',
      'progress-reports': 'Academic progress reports with analytics'
    };

    return descriptions[screenName] || `${screenName.replace('-', ' ')} interface`;
  }

  async generateMasterSummary() {
    const variants = Object.keys(APP_VARIANTS);
    const summary = `# App Store Metadata Master Summary

Generated: ${new Date().toLocaleString()}

## Overview
This document contains App Store descriptions, metadata, and marketing copy for all ${variants.length} app variants in the ActiveLog family.

## App Variants Summary

${Object.entries(APP_VARIANTS).map(([key, variant]) => `
### ${variant.name}
- **Subtitle**: ${variant.subtitle}
- **Category**: ${variant.category}  
- **Primary Color**: ${variant.primaryColor}
- **Target Audience**: ${variant.targetAudience}
- **Main Benefit**: ${variant.mainBenefit}
- **Keywords**: ${variant.keywords.join(', ')}
- **Directory**: \`app-store-metadata/${key}/\`
`).join('')}

## Files Generated Per Variant

Each variant directory contains:
- \`app-store-description.md\` - Complete App Store listing content
- \`google-play-description.md\` - Google Play Store listing content  
- \`web-marketing-copy.md\` - Website and social media content
- \`press-release.md\` - Press release template
- \`metadata.json\` - Structured app metadata

## Usage Instructions

### For App Store Submissions
1. Use content from \`app-store-description.md\`
2. Follow character limits specified in each section
3. Use provided keywords for ASO optimization
4. Reference screenshot order and descriptions

### For Google Play Submissions  
1. Use content from \`google-play-description.md\`
2. Adapt promotional video script as needed
3. Follow Google Play content policies
4. Use specified content ratings

### For Marketing & PR
1. Use \`web-marketing-copy.md\` for website content
2. Use \`press-release.md\` template for media outreach
3. Social media posts are ready to use
4. Email subject lines provided for campaigns

### For Development
1. Reference \`metadata.json\` for app configuration
2. Use specified bundle IDs and version numbers
3. Follow minimum OS requirements
4. Implement specified app features

## ASO (App Store Optimization) Strategy

### Common Keywords Across Variants
${this.getCommonKeywords()} 

### Category Distribution
${this.getCategoryDistribution()}

### Localization Notes
All variants currently support English (en-US) only. Future localization recommended for major markets (Spanish, French, German, Japanese, Chinese).

## Brand Consistency

### Color Palette
${Object.entries(APP_VARIANTS).map(([key, variant]) => `- ${variant.name}: ${variant.primaryColor}`).join('\n')}

### Messaging Framework
All variants follow consistent messaging:
1. Problem identification
2. Solution presentation  
3. Feature highlights
4. Benefit emphasis
5. Call to action

### Voice & Tone
- Professional yet approachable
- User-focused and benefit-driven
- Clear and concise
- Encouraging and motivational

## Next Steps

1. **Review Content**: Review all generated content for accuracy
2. **Customize**: Adapt content for specific markets if needed
3. **Translate**: Prepare translations for target markets  
4. **Test**: A/B test different descriptions for optimization
5. **Monitor**: Track ASO performance and iterate

## Support

For questions about this metadata:
- Technical: development@activelog.com
- Marketing: marketing@activelog.com  
- Press: press@activelog.com

---

*This summary was auto-generated on ${new Date().toISOString()}*
`;

    const summaryPath = path.join(this.outputDir, 'MASTER_SUMMARY.md');
    await fs.writeFile(summaryPath, summary);
    console.log(`📋 Master summary saved: ${summaryPath}`);
  }

  // Helper methods
  getDescriptionContext(variant) {
    const contexts = {
      'PersonalLog': 'personal journaling',
      'BusinessLog': 'business productivity',
      'FamilyLog': 'family coordination',
      'FitnessLog': 'fitness journey',
      'TravelLog': 'travel planning',
      'EducationLog': 'learning experience'
    };
    return contexts[variant.name] || 'digital organization';
  }

  getMainAction(variant) {
    const actions = {
      'PersonalLog': 'journaling and reflection',
      'BusinessLog': 'business task management',
      'FamilyLog': 'family memory sharing',
      'FitnessLog': 'fitness tracking',
      'TravelLog': 'travel documentation',
      'EducationLog': 'learning progress tracking'
    };
    return actions[variant.name] || 'organizing';
  }

  getEmoji(title) {
    const emojis = {
      'Rich Writing': '✍️',
      'Personal Insights': '📊',
      'Secure': '🔒',
      'Smart Task': '🎯',
      'Business Analytics': '📈',
      'Team Collaboration': '👥',
      'Family Memory': '📸',
      'Shared Family': '📅',
      'Milestone': '🎉',
      'Comprehensive Workout': '💪',
      'Nutrition': '🍎',
      'Goal': '🏆',
      'Trip Planning': '🗺️',
      'Location': '📍',
      'Expense': '💰',
      'Course': '📚',
      'Study': '📝',
      'Learning': '🎓'
    };
    
    const key = Object.keys(emojis).find(k => title.includes(k));
    return emojis[key] || '⭐';
  }

  getGooglePlayCategory(appStoreCategory) {
    const mapping = {
      'Lifestyle': 'Lifestyle',
      'Productivity': 'Productivity',
      'Health & Fitness': 'Health & Fitness',
      'Travel': 'Travel & Local',
      'Education': 'Education'
    };
    return mapping[appStoreCategory] || 'Lifestyle';
  }

  getPressReleaseNeed(variant) {
    const needs = {
      'PersonalLog': 'effective digital journaling and personal reflection tools',
      'BusinessLog': 'streamlined business task management and team collaboration',
      'FamilyLog': 'better family coordination and memory preservation',
      'FitnessLog': 'comprehensive fitness and health tracking solutions',
      'TravelLog': 'organized travel planning and memory documentation',
      'EducationLog': 'structured learning progress tracking and study organization'
    };
    return needs[variant.name] || 'digital organization solutions';
  }

  getMarketNeed(variant) {
    const needs = {
      'PersonalLog': 'help them maintain consistent journaling habits and gain personal insights',
      'BusinessLog': 'improve productivity and streamline team collaboration',
      'FamilyLog': 'stay connected with family and preserve precious memories',
      'FitnessLog': 'track their fitness progress and maintain healthy habits',
      'TravelLog': 'plan amazing trips and document their adventures',
      'EducationLog': 'improve their learning outcomes and stay organized academically'
    };
    return needs[variant.name] || 'organize their digital lives more effectively';
  }

  getUniquePosition(variant) {
    const positions = {
      'PersonalLog': 'combining powerful writing tools with intelligent personal insights',
      'BusinessLog': 'integrating task management with team collaboration and business analytics',
      'FamilyLog': 'focusing specifically on family coordination and memory preservation',
      'FitnessLog': 'offering comprehensive tracking for both fitness and nutrition in one app',
      'TravelLog': 'combining trip planning, documentation, and expense tracking seamlessly',
      'EducationLog': 'providing academic-focused tools with learning analytics and study optimization'
    };
    return positions[variant.name] || 'offering a uniquely tailored user experience';
  }

  getTestimonial(variant) {
    const testimonials = {
      'PersonalLog': 'This app has transformed my daily reflection practice. I love the insights it provides!',
      'BusinessLog': 'Our team productivity has increased 40% since we started using BusinessLog.',
      'FamilyLog': 'Finally, an app that helps our whole family stay connected and organized.',
      'FitnessLog': 'I\'ve never been more motivated to stick to my fitness goals. The tracking is incredible!',
      'TravelLog': 'TravelLog made our last vacation so much better organized and more memorable.',
      'EducationLog': 'My grades have improved significantly since I started using this for study planning.'
    };
    return testimonials[variant.name] || 'This app has completely changed how I stay organized!';
  }

  getReleaseNotes(variant) {
    return [
      `🎉 Welcome to ${variant.name} v1.0!`,
      `• Introducing ${variant.mainBenefit}`,
      `• Beautiful, intuitive interface designed for ${variant.targetAudience}`,
      '• Cross-device synchronization',
      '• Premium features with free trial',
      '• Enterprise-grade security and privacy',
      '',
      'Thank you for choosing ' + variant.name + '! We have exciting updates planned.'
    ];
  }

  getCommonKeywords() {
    const allKeywords = Object.values(APP_VARIANTS).flatMap(v => v.keywords);
    const frequency = {};
    allKeywords.forEach(keyword => {
      frequency[keyword] = (frequency[keyword] || 0) + 1;
    });
    
    return Object.entries(frequency)
      .filter(([, count]) => count > 1)
      .sort(([, a], [, b]) => b - a)
      .map(([keyword, count]) => `- ${keyword} (used in ${count} apps)`)
      .join('\n');
  }

  getCategoryDistribution() {
    const categories = {};
    Object.values(APP_VARIANTS).forEach(variant => {
      categories[variant.category] = (categories[variant.category] || 0) + 1;
    });
    
    return Object.entries(categories)
      .map(([category, count]) => `- ${category}: ${count} app${count > 1 ? 's' : ''}`)
      .join('\n');
  }
}

// Main execution
async function main() {
  const generator = new AppStoreDescriptionGenerator();
  
  try {
    await generator.generateAllDescriptions();
  } catch (error) {
    console.error('❌ Error generating descriptions:', error);
    process.exit(1);
  }
}

// Export for module usage
module.exports = { AppStoreDescriptionGenerator, APP_VARIANTS };

// Run if called directly
if (require.main === module) {
  main();
}