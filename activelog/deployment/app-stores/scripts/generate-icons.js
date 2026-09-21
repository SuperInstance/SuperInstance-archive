const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// App variants with their colors and themes
const APP_VARIANTS = {
  'personal-log': {
    name: 'PersonalLog',
    primaryColor: '#6366F1', // Indigo
    secondaryColor: '#8B5CF6', // Violet
    backgroundColor: '#F8FAFC',
    iconStyle: 'journal'
  },
  'business-log': {
    name: 'BusinessLog', 
    primaryColor: '#059669', // Emerald
    secondaryColor: '#0D9488', // Teal
    backgroundColor: '#F0FDF4',
    iconStyle: 'briefcase'
  },
  'family-log': {
    name: 'FamilyLog',
    primaryColor: '#DC2626', // Red
    secondaryColor: '#EA580C', // Orange
    backgroundColor: '#FEF2F2',
    iconStyle: 'heart'
  },
  'fitness-log': {
    name: 'FitnessLog',
    primaryColor: '#DB2777', // Pink
    secondaryColor: '#C026D3', // Fuchsia
    backgroundColor: '#FDF2F8',
    iconStyle: 'dumbbell'
  },
  'travel-log': {
    name: 'TravelLog',
    primaryColor: '#0284C7', // Sky
    secondaryColor: '#0369A1', // Blue
    backgroundColor: '#F0F9FF',
    iconStyle: 'plane'
  },
  'education-log': {
    name: 'EducationLog',
    primaryColor: '#7C3AED', // Purple
    secondaryColor: '#A855F7', // Purple
    backgroundColor: '#FAF5FF',
    iconStyle: 'book'
  }
};

// Icon sizes for different platforms
const ICON_SIZES = {
  ios: {
    'icon-1024.png': 1024, // App Store
    'icon-20.png': 20,     // iPhone Notification iOS 7-12
    'icon-20@2x.png': 40,  // iPhone Notification iOS 7-12
    'icon-20@3x.png': 60,  // iPhone Notification iOS 7-12
    'icon-29.png': 29,     // iPhone Settings iOS 5-12
    'icon-29@2x.png': 58,  // iPhone Settings iOS 5-12  
    'icon-29@3x.png': 87,  // iPhone Settings iOS 5-12
    'icon-40.png': 40,     // iPhone Spotlight iOS 7-12
    'icon-40@2x.png': 80,  // iPhone Spotlight iOS 7-12
    'icon-40@3x.png': 120, // iPhone Spotlight iOS 7-12
    'icon-60@2x.png': 120, // iPhone App iOS 7-12
    'icon-60@3x.png': 180, // iPhone App iOS 7-12
    'icon-76.png': 76,     // iPad App iOS 7-12
    'icon-76@2x.png': 152, // iPad App iOS 7-12
    'icon-83.5@2x.png': 167, // iPad Pro App
  },
  android: {
    'icon-36.png': 36,     // LDPI
    'icon-48.png': 48,     // MDPI
    'icon-72.png': 72,     // HDPI
    'icon-96.png': 96,     // XHDPI
    'icon-144.png': 144,   // XXHDPI
    'icon-192.png': 192,   // XXXHDPI
    'adaptive-icon-432.png': 432, // Adaptive icon
  },
  web: {
    'favicon-16.png': 16,
    'favicon-32.png': 32,
    'favicon-180.png': 180, // Apple touch icon
    'favicon-192.png': 192, // Android Chrome
    'favicon-512.png': 512, // Android Chrome
  }
};

// Splash screen sizes
const SPLASH_SIZES = {
  ios: [
    { width: 1125, height: 2436, name: 'splash-1125x2436.png' }, // iPhone X/XS/11 Pro
    { width: 1242, height: 2208, name: 'splash-1242x2208.png' }, // iPhone 6+/7+/8+
    { width: 750, height: 1334, name: 'splash-750x1334.png' },   // iPhone 6/7/8
    { width: 1242, height: 2688, name: 'splash-1242x2688.png' }, // iPhone XS Max/11 Pro Max
    { width: 828, height: 1792, name: 'splash-828x1792.png' },   // iPhone XR/11
    { width: 1080, height: 2340, name: 'splash-1080x2340.png' }, // iPhone 12/13/14
    { width: 1170, height: 2532, name: 'splash-1170x2532.png' }, // iPhone 12/13/14 Pro
    { width: 1284, height: 2778, name: 'splash-1284x2778.png' }, // iPhone 12/13/14 Pro Max
    { width: 2048, height: 2732, name: 'splash-2048x2732.png' }, // iPad Pro 12.9"
    { width: 1668, height: 2224, name: 'splash-1668x2224.png' }, // iPad Pro 10.5"
    { width: 1536, height: 2048, name: 'splash-1536x2048.png' }, // iPad
  ],
  android: [
    { width: 320, height: 480, name: 'splash-320x480.png' },    // MDPI
    { width: 480, height: 800, name: 'splash-480x800.png' },    // HDPI
    { width: 720, height: 1280, name: 'splash-720x1280.png' },  // XHDPI
    { width: 1080, height: 1920, name: 'splash-1080x1920.png' }, // XXHDPI
  ]
};

async function generateIcon(variant, size, outputPath, iconStyle) {
  const canvas = sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 255, g: 255, b: 255, alpha: 0 }
    }
  });

  // Create icon based on style
  let iconSvg = '';
  
  switch (iconStyle) {
    case 'journal':
      iconSvg = createJournalIcon(variant, size);
      break;
    case 'briefcase':
      iconSvg = createBriefcaseIcon(variant, size);
      break;
    case 'heart':
      iconSvg = createHeartIcon(variant, size);
      break;
    case 'dumbbell':
      iconSvg = createDumbbellIcon(variant, size);
      break;
    case 'plane':
      iconSvg = createPlaneIcon(variant, size);
      break;
    case 'book':
      iconSvg = createBookIcon(variant, size);
      break;
    default:
      iconSvg = createDefaultIcon(variant, size);
  }

  try {
    await canvas
      .composite([{
        input: Buffer.from(iconSvg),
        top: 0,
        left: 0
      }])
      .png({ quality: 100 })
      .toFile(outputPath);
    
    console.log(`✅ Generated icon: ${outputPath}`);
  } catch (error) {
    console.error(`❌ Failed to generate icon ${outputPath}:`, error);
  }
}

function createJournalIcon(variant, size) {
  const padding = size * 0.15;
  const innerSize = size - (padding * 2);
  
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg-${variant.name}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.primaryColor};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:1" />
        </linearGradient>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <dropShadow dx="2" dy="4" stdDeviation="3" flood-color="#000" flood-opacity="0.2"/>
        </filter>
      </defs>
      
      <!-- Background circle -->
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="url(#bg-${variant.name})" filter="url(#shadow)"/>
      
      <!-- Journal book -->
      <rect x="${padding * 1.2}" y="${padding * 1.5}" width="${innerSize * 0.6}" height="${innerSize * 0.7}" 
            fill="white" rx="${size * 0.02}" stroke="${variant.backgroundColor}" stroke-width="2"/>
      
      <!-- Journal lines -->
      <line x1="${padding * 1.5}" y1="${padding * 2.2}" x2="${padding * 1.5 + innerSize * 0.4}" y2="${padding * 2.2}" 
            stroke="${variant.primaryColor}" stroke-width="1" opacity="0.6"/>
      <line x1="${padding * 1.5}" y1="${padding * 2.6}" x2="${padding * 1.5 + innerSize * 0.4}" y2="${padding * 2.6}" 
            stroke="${variant.primaryColor}" stroke-width="1" opacity="0.6"/>
      <line x1="${padding * 1.5}" y1="${padding * 3.0}" x2="${padding * 1.5 + innerSize * 0.3}" y2="${padding * 3.0}" 
            stroke="${variant.primaryColor}" stroke-width="1" opacity="0.6"/>
      
      <!-- Pen -->
      <line x1="${size * 0.65}" y1="${size * 0.35}" x2="${size * 0.75}" y2="${size * 0.25}" 
            stroke="white" stroke-width="3" stroke-linecap="round"/>
      <circle cx="${size * 0.77}" cy="${size * 0.23}" r="3" fill="white"/>
    </svg>
  `;
}

function createBriefcaseIcon(variant, size) {
  const padding = size * 0.15;
  
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg-${variant.name}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.primaryColor};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="url(#bg-${variant.name})"/>
      
      <!-- Briefcase body -->
      <rect x="${padding * 1.5}" y="${size * 0.45}" width="${size * 0.5}" height="${size * 0.35}" 
            fill="white" rx="${size * 0.02}"/>
      
      <!-- Briefcase handle -->
      <rect x="${size * 0.42}" y="${size * 0.35}" width="${size * 0.16}" height="${size * 0.12}" 
            fill="none" stroke="white" stroke-width="3" rx="${size * 0.02}"/>
      
      <!-- Lock -->
      <rect x="${size * 0.47}" y="${size * 0.52}" width="${size * 0.06}" height="${size * 0.08}" 
            fill="${variant.secondaryColor}"/>
    </svg>
  `;
}

function createHeartIcon(variant, size) {
  const padding = size * 0.15;
  
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg-${variant.name}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.primaryColor};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="url(#bg-${variant.name})"/>
      
      <!-- Heart shape -->
      <path d="M${size * 0.5},${size * 0.7} C${size * 0.3},${size * 0.5} ${size * 0.2},${size * 0.3} ${size * 0.35},${size * 0.25} 
               C${size * 0.4},${size * 0.2} ${size * 0.5},${size * 0.3} ${size * 0.5},${size * 0.3} 
               C${size * 0.5},${size * 0.3} ${size * 0.6},${size * 0.2} ${size * 0.65},${size * 0.25} 
               C${size * 0.8},${size * 0.3} ${size * 0.7},${size * 0.5} ${size * 0.5},${size * 0.7} Z" 
            fill="white"/>
    </svg>
  `;
}

function createDumbbellIcon(variant, size) {
  const padding = size * 0.15;
  
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg-${variant.name}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.primaryColor};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="url(#bg-${variant.name})"/>
      
      <!-- Dumbbell bar -->
      <rect x="${size * 0.25}" y="${size * 0.47}" width="${size * 0.5}" height="${size * 0.06}" 
            fill="white" rx="${size * 0.03}"/>
      
      <!-- Left weight -->
      <rect x="${size * 0.2}" y="${size * 0.4}" width="${size * 0.08}" height="${size * 0.2}" 
            fill="white" rx="${size * 0.01}"/>
      
      <!-- Right weight -->
      <rect x="${size * 0.72}" y="${size * 0.4}" width="${size * 0.08}" height="${size * 0.2}" 
            fill="white" rx="${size * 0.01}"/>
    </svg>
  `;
}

function createPlaneIcon(variant, size) {
  const padding = size * 0.15;
  
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg-${variant.name}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.primaryColor};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="url(#bg-${variant.name})"/>
      
      <!-- Plane body -->
      <path d="M${size * 0.3},${size * 0.5} L${size * 0.7},${size * 0.4} L${size * 0.75},${size * 0.45} 
               L${size * 0.7},${size * 0.5} L${size * 0.75},${size * 0.55} L${size * 0.7},${size * 0.6} 
               L${size * 0.3},${size * 0.5} Z" fill="white"/>
      
      <!-- Wings -->
      <path d="M${size * 0.35},${size * 0.5} L${size * 0.2},${size * 0.35} L${size * 0.25},${size * 0.32} 
               L${size * 0.4},${size * 0.47} Z" fill="white"/>
      <path d="M${size * 0.35},${size * 0.5} L${size * 0.2},${size * 0.65} L${size * 0.25},${size * 0.68} 
               L${size * 0.4},${size * 0.53} Z" fill="white"/>
    </svg>
  `;
}

function createBookIcon(variant, size) {
  const padding = size * 0.15;
  
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg-${variant.name}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.primaryColor};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="url(#bg-${variant.name})"/>
      
      <!-- Book -->
      <rect x="${size * 0.25}" y="${size * 0.25}" width="${size * 0.5}" height="${size * 0.5}" 
            fill="white" rx="${size * 0.02}"/>
      
      <!-- Book spine -->
      <rect x="${size * 0.25}" y="${size * 0.25}" width="${size * 0.05}" height="${size * 0.5}" 
            fill="${variant.secondaryColor}"/>
      
      <!-- Pages -->
      <line x1="${size * 0.35}" y1="${size * 0.35}" x2="${size * 0.65}" y2="${size * 0.35}" 
            stroke="${variant.primaryColor}" stroke-width="1" opacity="0.6"/>
      <line x1="${size * 0.35}" y1="${size * 0.42}" x2="${size * 0.65}" y2="${size * 0.42}" 
            stroke="${variant.primaryColor}" stroke-width="1" opacity="0.6"/>
      <line x1="${size * 0.35}" y1="${size * 0.49}" x2="${size * 0.6}" y2="${size * 0.49}" 
            stroke="${variant.primaryColor}" stroke-width="1" opacity="0.6"/>
    </svg>
  `;
}

function createDefaultIcon(variant, size) {
  return createJournalIcon(variant, size);
}

async function generateSplashScreen(variant, width, height, outputPath) {
  const canvas = sharp({
    create: {
      width,
      height,
      channels: 4,
      background: variant.backgroundColor
    }
  });

  // Create a simple splash design
  const logoSize = Math.min(width, height) * 0.3;
  const logoX = (width - logoSize) / 2;
  const logoY = (height - logoSize) / 2;

  const splashSvg = `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="splash-bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${variant.backgroundColor};stop-opacity:1" />
          <stop offset="50%" style="stop-color:${variant.primaryColor};stop-opacity:0.1" />
          <stop offset="100%" style="stop-color:${variant.secondaryColor};stop-opacity:0.2" />
        </linearGradient>
      </defs>
      
      <rect width="${width}" height="${height}" fill="url(#splash-bg)"/>
      
      <!-- Logo circle -->
      <circle cx="${width/2}" cy="${height/2}" r="${logoSize/2}" fill="${variant.primaryColor}" opacity="0.9"/>
      
      <!-- App name -->
      <text x="${width/2}" y="${height/2 + logoSize/2 + 40}" 
            text-anchor="middle" 
            font-family="Arial, sans-serif" 
            font-size="${Math.max(width, height) * 0.05}" 
            font-weight="bold" 
            fill="${variant.primaryColor}">
        ${variant.name}
      </text>
      
      <!-- Tagline -->
      <text x="${width/2}" y="${height/2 + logoSize/2 + 80}" 
            text-anchor="middle" 
            font-family="Arial, sans-serif" 
            font-size="${Math.max(width, height) * 0.025}" 
            fill="${variant.secondaryColor}"
            opacity="0.8">
        Your Digital Log Companion
      </text>
    </svg>
  `;

  try {
    await canvas
      .composite([{
        input: Buffer.from(splashSvg),
        top: 0,
        left: 0
      }])
      .png({ quality: 100 })
      .toFile(outputPath);
    
    console.log(`✅ Generated splash: ${outputPath}`);
  } catch (error) {
    console.error(`❌ Failed to generate splash ${outputPath}:`, error);
  }
}

async function generateAssetsForVariant(variantKey) {
  const variant = APP_VARIANTS[variantKey];
  console.log(`\n🎨 Generating assets for ${variant.name}...`);

  // Create directories
  const variantDir = path.join(__dirname, '..', 'assets', variantKey);
  const iosDir = path.join(variantDir, 'ios');
  const androidDir = path.join(variantDir, 'android');
  const webDir = path.join(variantDir, 'web');
  const splashDir = path.join(variantDir, 'splash');

  [variantDir, iosDir, androidDir, webDir, splashDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  // Generate iOS icons
  console.log('📱 Generating iOS icons...');
  for (const [filename, size] of Object.entries(ICON_SIZES.ios)) {
    const outputPath = path.join(iosDir, filename);
    await generateIcon(variant, size, outputPath, variant.iconStyle);
  }

  // Generate Android icons
  console.log('🤖 Generating Android icons...');
  for (const [filename, size] of Object.entries(ICON_SIZES.android)) {
    const outputPath = path.join(androidDir, filename);
    await generateIcon(variant, size, outputPath, variant.iconStyle);
  }

  // Generate Web icons
  console.log('🌐 Generating Web icons...');
  for (const [filename, size] of Object.entries(ICON_SIZES.web)) {
    const outputPath = path.join(webDir, filename);
    await generateIcon(variant, size, outputPath, variant.iconStyle);
  }

  // Generate splash screens
  console.log('💫 Generating splash screens...');
  
  // iOS splash screens
  for (const splash of SPLASH_SIZES.ios) {
    const outputPath = path.join(splashDir, 'ios', splash.name);
    if (!fs.existsSync(path.dirname(outputPath))) {
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    }
    await generateSplashScreen(variant, splash.width, splash.height, outputPath);
  }

  // Android splash screens
  for (const splash of SPLASH_SIZES.android) {
    const outputPath = path.join(splashDir, 'android', splash.name);
    if (!fs.existsSync(path.dirname(outputPath))) {
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    }
    await generateSplashScreen(variant, splash.width, splash.height, outputPath);
  }

  // Generate main app icon and splash for Expo
  await generateIcon(variant, 1024, path.join(variantDir, 'icon.png'), variant.iconStyle);
  await generateIcon(variant, 432, path.join(variantDir, 'adaptive-icon.png'), variant.iconStyle);
  await generateSplashScreen(variant, 1080, 1920, path.join(variantDir, 'splash.png'));

  console.log(`✅ Completed assets for ${variant.name}`);
}

async function generateAllAssets() {
  console.log('🚀 Starting icon and splash generation for all app variants...\n');

  const startTime = Date.now();

  try {
    // Generate assets for each variant
    for (const variantKey of Object.keys(APP_VARIANTS)) {
      await generateAssetsForVariant(variantKey);
    }

    const duration = (Date.now() - startTime) / 1000;
    console.log(`\n✅ All assets generated successfully in ${duration.toFixed(2)}s!`);
    
    console.log('\n📁 Generated assets structure:');
    console.log('assets/');
    Object.keys(APP_VARIANTS).forEach(variant => {
      console.log(`  └── ${variant}/`);
      console.log('      ├── ios/          (iOS icons)');
      console.log('      ├── android/      (Android icons)');
      console.log('      ├── web/          (Web icons)');
      console.log('      ├── splash/       (Splash screens)');
      console.log('      ├── icon.png      (Main app icon)');
      console.log('      ├── adaptive-icon.png');
      console.log('      └── splash.png    (Main splash)');
    });

  } catch (error) {
    console.error('❌ Failed to generate assets:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  generateAllAssets();
}

module.exports = {
  generateAllAssets,
  generateAssetsForVariant,
  APP_VARIANTS,
  ICON_SIZES,
  SPLASH_SIZES
};