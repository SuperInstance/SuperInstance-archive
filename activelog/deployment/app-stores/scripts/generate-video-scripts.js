const fs = require('fs').promises;
const path = require('path');

// Video script configurations for different types and variants
const APP_VARIANTS = {
  'personal-log': {
    name: 'PersonalLog',
    subtitle: 'Your Digital Journal',
    primaryColor: '#6366F1',
    icon: '📝',
    tagline: 'Your thoughts, beautifully organized',
    targetAudience: 'individuals seeking personal growth',
    mainBenefit: 'beautifully organized digital journaling'
  },
  'business-log': {
    name: 'BusinessLog',
    subtitle: 'Professional Task Management',
    primaryColor: '#059669',
    icon: '💼',
    tagline: 'Professional task management made simple',
    targetAudience: 'business professionals and teams',
    mainBenefit: 'streamlined business task management'
  },
  'family-log': {
    name: 'FamilyLog',
    subtitle: 'Family Memories & Planning',
    primaryColor: '#DC2626',
    icon: '👨‍👩‍👧‍👦',
    tagline: 'Bringing families closer together',
    targetAudience: 'families wanting to stay connected',
    mainBenefit: 'bringing families closer together'
  },
  'fitness-log': {
    name: 'FitnessLog',
    subtitle: 'Your Personal Fitness Companion',
    primaryColor: '#EA580C',
    icon: '💪',
    tagline: 'Your personal fitness companion',
    targetAudience: 'fitness enthusiasts',
    mainBenefit: 'comprehensive fitness and health tracking'
  },
  'travel-log': {
    name: 'TravelLog',
    subtitle: 'Document Every Adventure',
    primaryColor: '#0891B2',
    icon: '✈️',
    tagline: 'Document every adventure',
    targetAudience: 'travelers and adventure seekers',
    mainBenefit: 'comprehensive travel documentation'
  },
  'education-log': {
    name: 'EducationLog',
    subtitle: 'Learn, Track, Achieve',
    primaryColor: '#7C3AED',
    icon: '📚',
    tagline: 'Learn, track, achieve',
    targetAudience: 'students and lifelong learners',
    mainBenefit: 'organized educational progress tracking'
  }
};

// Video types and their purposes
const VIDEO_TYPES = {
  'app-preview': {
    name: 'App Preview',
    duration: 30,
    purpose: 'App Store preview video',
    format: 'Portrait (9:16)',
    description: 'Short showcase for app store listings'
  },
  'promotional': {
    name: 'Promotional Video',
    duration: 60,
    purpose: 'Marketing and advertising',
    format: 'Landscape (16:9)',
    description: 'Detailed feature demonstration'
  },
  'explainer': {
    name: 'Explainer Video',
    duration: 90,
    purpose: 'Website and onboarding',
    format: 'Landscape (16:9)',
    description: 'Comprehensive product explanation'
  },
  'social-media': {
    name: 'Social Media',
    duration: 15,
    purpose: 'Social media advertising',
    format: 'Square (1:1)',
    description: 'Quick attention-grabbing content'
  },
  'demo': {
    name: 'Product Demo',
    duration: 120,
    purpose: 'Sales presentations',
    format: 'Landscape (16:9)',
    description: 'In-depth feature walkthrough'
  }
};

class VideoScriptGenerator {
  constructor() {
    this.outputDir = path.join(__dirname, '..', 'video-scripts');
  }

  async generateAllScripts() {
    console.log('🎬 Generating video scripts for all variants...');
    
    await fs.mkdir(this.outputDir, { recursive: true });
    
    for (const [variantKey, variant] of Object.entries(APP_VARIANTS)) {
      console.log(`\n🎯 Generating scripts for ${variant.name}...`);
      
      const variantDir = path.join(this.outputDir, variantKey);
      await fs.mkdir(variantDir, { recursive: true });
      
      // Generate scripts for each video type
      for (const [typeKey, type] of Object.entries(VIDEO_TYPES)) {
        console.log(`  🎥 Creating ${type.name} script...`);
        await this.generateVideoScript(variant, type, typeKey, variantDir);
      }
      
      // Generate additional specialized scripts
      await this.generateTeaser(variant, variantDir);
      await this.generateTestimonial(variant, variantDir);
      await this.generateTutorial(variant, variantDir);
      
      console.log(`  ✅ All scripts generated for ${variant.name}`);
    }
    
    await this.generateProductionGuide();
    await this.generateMasterIndex();
    
    console.log('\n🎉 All video scripts generated successfully!');
  }

  async generateVideoScript(variant, type, typeKey, outputDir) {
    let script;
    
    switch (typeKey) {
      case 'app-preview':
        script = this.createAppPreviewScript(variant, type);
        break;
      case 'promotional':
        script = this.createPromotionalScript(variant, type);
        break;
      case 'explainer':
        script = this.createExplainerScript(variant, type);
        break;
      case 'social-media':
        script = this.createSocialMediaScript(variant, type);
        break;
      case 'demo':
        script = this.createDemoScript(variant, type);
        break;
      default:
        script = this.createGenericScript(variant, type);
    }
    
    const filepath = path.join(outputDir, `${typeKey}-script.md`);
    await fs.writeFile(filepath, script);
  }

  createAppPreviewScript(variant, type) {
    const features = this.getTopFeatures(variant);
    
    return `# ${variant.name} - App Preview Script (30 seconds)

## Video Specifications
- **Duration**: ${type.duration} seconds
- **Format**: ${type.format}
- **Purpose**: ${type.purpose}
- **Resolution**: 1080x1920 (Portrait)
- **Frame Rate**: 30fps
- **Audio**: Voiceover + Background Music

## Scene Breakdown

### SCENE 1: Hook (0-3 seconds)
**Visual**: 
- App icon animation with subtle bounce
- Clean background gradient (${variant.primaryColor})
- App name appears with smooth typography animation

**Text Overlay**: 
\`\`\`
${variant.name}
${variant.subtitle}
\`\`\`

**Voiceover**: 
"Introducing ${variant.name}..."

**Music**: Upbeat, modern intro

---

### SCENE 2: Problem Statement (3-8 seconds)
**Visual**:
- Split screen showing "before" frustration
- Scattered papers, multiple apps, confusion
- Smooth transition to clean, organized solution

**Text Overlay**:
\`\`\`
Tired of messy ${this.getContextArea(variant)}?
\`\`\`

**Voiceover**: 
"Stop struggling with ${this.getProblemStatement(variant)}"

**Animation**: Subtle shake effect on "before" side, smooth slide to solution

---

### SCENE 3: Solution Introduction (8-15 seconds)
**Visual**:
- Main dashboard screen with smooth parallax scroll
- Key UI elements highlighted with gentle pulses
- Clean, modern interface showcase

**Text Overlay**:
\`\`\`
Meet ${variant.name}
${variant.mainBenefit}
\`\`\`

**Voiceover**: 
"${variant.name} brings you ${variant.mainBenefit}, designed specifically for ${variant.targetAudience}"

**Animation**: Dashboard elements animate in sequence, smooth navigation demonstration

---

### SCENE 4: Feature Highlight (15-22 seconds)
**Visual**:
- Quick montage of top 3 features
- Smooth transitions between screens
- User interactions with tap animations
- Data visualizations and results

**Text Overlay**:
\`\`\`
${features[0].title}
${features[1].title} 
${features[2].title}
\`\`\`

**Voiceover**: 
"With ${features[0].title.toLowerCase()}, ${features[1].title.toLowerCase()}, and ${features[2].title.toLowerCase()}"

**Animation**: Feature-specific micro-animations, progress indicators, success states

---

### SCENE 5: Social Proof (22-27 seconds)
**Visual**:
- User avatars with satisfaction indicators
- Star ratings animation
- Growth/success metrics
- Community/sharing elements

**Text Overlay**:
\`\`\`
Join 10,000+ Happy Users
⭐⭐⭐⭐⭐ 4.8/5 Rating
\`\`\`

**Voiceover**: 
"Join thousands of ${variant.targetAudience} who've already transformed their ${this.getContextArea(variant)}"

**Animation**: Counter animations, star ratings filling, user testimonial quotes

---

### SCENE 6: Call to Action (27-30 seconds)
**Visual**:
- App Store and Google Play download buttons
- Final app icon with brand colors
- Download animation sequence

**Text Overlay**:
\`\`\`
Download FREE Today
Start Your Journey
\`\`\`

**Voiceover**: 
"Download ${variant.name} free today and start your journey!"

**Animation**: Download buttons with hover effects, final logo animation

## Production Notes

### Visual Style
- **Color Palette**: Primary ${variant.primaryColor}, White (#FFFFFF), Light Gray (#F8F9FA)
- **Typography**: San Francisco/Roboto, clean and modern
- **Animation Style**: Smooth, purposeful, not distracting
- **Transitions**: Fade, slide, and scale - keep it elegant

### Audio Guidelines
- **Voiceover**: Professional, friendly, confident tone
- **Background Music**: Upbeat but not overwhelming (volume at 30%)
- **Sound Effects**: Subtle UI sounds, success chimes
- **Audio Mix**: Voice clear and prominent

### Technical Requirements
- **Export Format**: MP4, H.264 codec
- **Resolution**: 1080x1920 (App Store requirement)
- **File Size**: Under 500MB
- **Subtitles**: Include SRT file for accessibility

### Brand Guidelines
- Always show actual app interface (no mockups)
- Maintain consistent color usage
- Include app icon prominently
- Show real functionality, not fake data

### App Store Compliance
- No fake testimonials or reviews
- Actual app functionality only
- Clear representation of features
- No misleading claims
- Include age rating if required

## Shot List for Production

1. **App Icon Animation** - 3 seconds of logo reveal
2. **Problem Scenario** - 5 seconds of "before" state  
3. **Dashboard Overview** - 7 seconds of main interface
4. **Feature Demo 1** - ${features[0].title} in action (3 seconds)
5. **Feature Demo 2** - ${features[1].title} workflow (3 seconds)  
6. **Feature Demo 3** - ${features[2].title} results (3 seconds)
7. **Social Proof Graphics** - 5 seconds of ratings/users
8. **Download CTA** - 3 seconds of store buttons

## Additional Deliverables Needed
- [ ] High-resolution app screenshots
- [ ] App icon files (PNG, various sizes)
- [ ] Brand color palette and fonts
- [ ] Background music track (royalty-free)
- [ ] Professional voiceover recording
- [ ] Legal compliance review
- [ ] Multiple format exports (Square, Landscape versions)
`;
  }

  createPromotionalScript(variant, type) {
    const features = this.getTopFeatures(variant);
    const benefits = this.getBenefits(variant);
    
    return `# ${variant.name} - Promotional Video Script (60 seconds)

## Video Specifications
- **Duration**: ${type.duration} seconds
- **Format**: ${type.format} 
- **Purpose**: ${type.purpose}
- **Resolution**: 1920x1080 (Landscape)
- **Frame Rate**: 30fps
- **Audio**: Voiceover + Background Music + SFX

## Detailed Scene Breakdown

### SCENE 1: Opening Hook (0-8 seconds)
**Concept**: Start with relatable problem/frustration

**Visual**:
- Real person struggling with ${this.getProblemScenario(variant)}
- Quick cuts showing frustration, scattered items, inefficiency
- Subtle color grading (slightly desaturated)

**Text Overlay**:
\`\`\`
Sound Familiar?
\`\`\`

**Voiceover**: 
"We've all been there. ${this.getProblemNarrative(variant)} But what if there was a better way?"

**Music**: Soft, slightly tense intro building to resolution

**Props/Setting**: ${this.getProblemProps(variant)}

---

### SCENE 2: Solution Reveal (8-18 seconds)
**Concept**: Dramatic transformation/reveal of the app

**Visual**:
- Smooth transition from problem to solution
- App icon materializes with particle effects
- Color shifts to warmer, more vibrant palette
- Clean, modern device showcase

**Text Overlay**:
\`\`\`
Introducing ${variant.name}
${variant.tagline}
\`\`\`

**Voiceover**: 
"Introducing ${variant.name} - ${variant.tagline}. Finally, ${variant.mainBenefit} that actually works for ${variant.targetAudience}."

**Music**: Uplifting transition, energy building

**Animation**: Logo reveal with brand colors, device rotation

---

### SCENE 3: Feature Demonstration (18-38 seconds)
**Concept**: Show key features in action with real benefits

#### Feature 1: ${features[0].title} (18-25 seconds)
**Visual**:
- Clean interface showcase
- User performing key action
- Immediate positive result/feedback

**Text Overlay**:
\`\`\`
${features[0].title}
${features[0].benefit}
\`\`\`

**Voiceover**: 
"${features[0].description}"

#### Feature 2: ${features[1].title} (25-32 seconds)
**Visual**:
- Different angle/device showing versatility
- Data visualization or progress indication
- User satisfaction moment

**Text Overlay**:
\`\`\`
${features[1].title}
${features[1].benefit}
\`\`\`

**Voiceover**: 
"${features[1].description}"

#### Feature 3: ${features[2].title} (32-38 seconds)
**Visual**:
- Results screen or achievement
- Multiple devices showing sync
- Community/sharing aspect if applicable

**Text Overlay**:
\`\`\`
${features[2].title}
${features[2].benefit}
\`\`\`

**Voiceover**: 
"${features[2].description}"

---

### SCENE 4: Benefits & Transformation (38-48 seconds)
**Concept**: Show the transformation and life improvement

**Visual**:
- Split screen: before vs. after
- Happy users in real environments
- Success metrics, progress indicators
- Multiple use cases/scenarios

**Text Overlay**:
\`\`\`
Transform Your ${this.getContextArea(variant)}
Join 10,000+ Success Stories
\`\`\`

**Voiceover**: 
"Whether you're ${this.getUserScenarios(variant).join(', or you're ')}, ${variant.name} adapts to your needs. Join over 10,000 users who've already transformed their ${this.getContextArea(variant)}."

**Music**: Peak emotional moment, inspiring

---

### SCENE 5: Social Proof & Trust (48-55 seconds)
**Concept**: Build credibility and trust

**Visual**:
- App store ratings animation
- User testimonial quotes (text)
- Security/privacy badges
- Awards or recognition (if applicable)

**Text Overlay**:
\`\`\`
⭐⭐⭐⭐⭐ 4.8/5 Stars
"Game-changing app!"
Secure & Private
\`\`\`

**Voiceover**: 
"With a 4.8-star rating and thousands of satisfied users, ${variant.name} is the trusted choice for ${variant.targetAudience}."

**Animation**: Star ratings filling up, testimonial quotes sliding in

---

### SCENE 6: Call to Action (55-60 seconds)
**Concept**: Strong, clear call to action

**Visual**:
- App store buttons prominently displayed
- Final app icon with brand animation
- Pricing information (if needed)
- Download animation sequence

**Text Overlay**:
\`\`\`
Download FREE
Premium features available
Start your transformation today
\`\`\`

**Voiceover**: 
"Ready to transform your ${this.getContextArea(variant)}? Download ${variant.name} free today. Premium features available with 7-day free trial."

**Music**: Crescendo finish, call to action energy

## Extended Production Requirements

### Casting Requirements
- **Primary Actor**: ${this.getCastingRequirements(variant)}
- **Age Range**: 25-45
- **Diversity**: Multiple ethnicities represented
- **Wardrobe**: ${this.getWardrobeGuide(variant)}

### Location Requirements
${this.getLocationRequirements(variant)}

### Props & Equipment
${this.getPropsRequirements(variant)}

### Post-Production Elements
- Color grading to match brand palette
- Motion graphics for text overlays
- App interface screen recordings
- Music licensing for commercial use
- Multiple aspect ratio exports (16:9, 1:1, 9:16)

### Alternative Versions to Create
1. **30-second cut** - Remove middle feature demonstration
2. **15-second social media version** - Hook + Solution + CTA only
3. **Silent version** - Enhanced text overlays for autoplay
4. **Testimonial version** - Include real user interviews

## Budget Considerations
- **Production**: $5,000 - $15,000
- **Talent**: $500 - $2,000
- **Location**: $200 - $1,000
- **Equipment**: $1,000 - $3,000 (if renting)
- **Post-Production**: $2,000 - $5,000
- **Music/SFX**: $200 - $500

## Success Metrics to Track
- Click-through rate from video to app store
- Conversion rate from view to download
- Engagement time (% watched)
- Social shares and comments
- Brand awareness lift
`;
  }

  createExplainerScript(variant, type) {
    const features = this.getTopFeatures(variant);
    const useCases = this.getUseCases(variant);
    
    return `# ${variant.name} - Explainer Video Script (90 seconds)

## Video Specifications
- **Duration**: ${type.duration} seconds
- **Format**: ${type.format}
- **Purpose**: ${type.purpose}
- **Target**: Website visitors, new users, onboarding
- **Style**: Educational, comprehensive, welcoming

## Complete Scene Structure

### ACT 1: PROBLEM IDENTIFICATION (0-20 seconds)

#### SCENE 1: The Universal Problem (0-10 seconds)
**Concept**: Everyone can relate to this frustration

**Visual**:
- Montage of people struggling with ${this.getProblemContext(variant)}
- Multiple scenarios, different ages/demographics
- Subtle animation showing chaos/inefficiency

**Narration**: 
"Every day, millions of ${variant.targetAudience} struggle with ${this.getUniversalProblem(variant)}. Sound familiar?"

#### SCENE 2: The Cost of This Problem (10-20 seconds)
**Concept**: What happens when this problem isn't solved

**Visual**:
- Time wasting visualization
- Stress indicators
- Missed opportunities or goals

**Narration**: 
"Without the right tools, you end up ${this.getProblemConsequences(variant)}. There's got to be a better solution."

### ACT 2: SOLUTION INTRODUCTION (20-35 seconds)

#### SCENE 3: Meet the Solution (20-30 seconds)
**Visual**:
- Smooth transition from chaos to order
- ${variant.name} logo animation
- Clean, modern interface preview

**Narration**: 
"Meet ${variant.name} - the ${variant.category.toLowerCase()} app designed specifically for ${variant.targetAudience}. We built ${variant.name} to solve exactly these problems."

#### SCENE 4: Core Philosophy (30-35 seconds)
**Visual**:
- Brand values visualization
- User-centered design principles
- Simple, elegant interface elements

**Narration**: 
"Our philosophy is simple: ${this.getCorePhilosophy(variant)}"

### ACT 3: HOW IT WORKS (35-65 seconds)

#### SCENE 5: Feature Walkthrough - Primary Feature (35-45 seconds)
**Feature**: ${features[0].title}

**Visual**:
- Step-by-step demonstration
- User journey from start to success
- Interface closeups with annotations

**Narration**: 
"Here's how it works. First, ${features[0].walkthrough}. This solves the problem of ${features[0].problemSolved}."

#### SCENE 6: Feature Walkthrough - Secondary Feature (45-55 seconds)
**Feature**: ${features[1].title}

**Visual**:
- Different user scenario
- Integration with first feature
- Data flow and results

**Narration**: 
"But that's not all. ${features[1].walkthrough}. This means ${features[1].benefit}."

#### SCENE 7: Feature Walkthrough - Advanced Feature (55-65 seconds)
**Feature**: ${features[2].title}

**Visual**:
- Power user scenario
- Advanced capabilities
- Long-term value demonstration

**Narration**: 
"For advanced users, ${features[2].walkthrough}. This gives you ${features[2].advancedBenefit}."

### ACT 4: BENEFITS & TRANSFORMATION (65-80 seconds)

#### SCENE 8: User Success Stories (65-75 seconds)
**Visual**:
- Real user scenarios (illustrated or animated)
- Before/after transformations
- Success metrics and achievements

**Narration**: 
"Our users report ${this.getSuccessMetrics(variant)}. Like Sarah, who ${this.getUserStoryExample(variant)}."

#### SCENE 9: Why Choose ${variant.name} (75-80 seconds)
**Visual**:
- Comparison with alternatives
- Unique value propositions
- Award or recognition graphics

**Narration**: 
"What makes ${variant.name} different? ${this.getUniqueValueProps(variant)}"

### ACT 5: CALL TO ACTION (80-90 seconds)

#### SCENE 10: Getting Started (80-85 seconds)
**Visual**:
- Download process
- First-time user experience
- Support and onboarding

**Narration**: 
"Getting started is easy. Download ${variant.name} free from the App Store or Google Play. Our onboarding process will have you up and running in minutes."

#### SCENE 11: Final CTA (85-90 seconds)
**Visual**:
- Strong visual call-to-action
- App store badges
- Brand reinforcement

**Narration**: 
"Ready to transform your ${this.getContextArea(variant)}? Join thousands of satisfied users. Download ${variant.name} today."

## Character Development

### Primary Persona: The Relatable User
- **Name**: Jordan (gender-neutral)
- **Age**: 32
- **Background**: ${this.getPersonaBackground(variant)}
- **Goals**: ${this.getPersonaGoals(variant)}
- **Pain Points**: ${this.getPersonaPainPoints(variant)}

### Character Arc
1. **Struggling** - Jordan faces daily challenges
2. **Discovering** - Jordan finds ${variant.name}
3. **Learning** - Jordan explores features
4. **Succeeding** - Jordan achieves goals
5. **Thriving** - Jordan becomes a power user

## Visual Design System

### Color Palette
- **Primary**: ${variant.primaryColor}
- **Secondary**: ${this.getSecondaryColor(variant.primaryColor)}
- **Neutral**: #F8F9FA, #6C757D
- **Accent**: #28A745 (success), #FFC107 (highlight)

### Typography
- **Headlines**: Bold, sans-serif
- **Body Text**: Clean, readable
- **UI Elements**: Match app typography

### Animation Principles
- **Purposeful**: Every animation serves a function
- **Smooth**: 60fps minimum for screen recordings
- **Branded**: Consistent with app's motion design
- **Accessible**: Not too fast, no strobing effects

## Interactive Elements

### Clickable Hotspots (Web Version)
1. **Feature deep-dives**: Click to see extended demos
2. **User testimonials**: Click for full stories
3. **Pricing information**: Click for details
4. **Download options**: Direct links to app stores

### Chapter Markers
1. The Problem (0:00)
2. The Solution (0:20)
3. How It Works (0:35)
4. Success Stories (1:05)
5. Get Started (1:20)

## Accessibility Features
- **Closed Captions**: Full transcript available
- **Audio Descriptions**: For visually impaired users  
- **Keyboard Navigation**: For interactive elements
- **High Contrast**: Option for better visibility
- **Playback Speed**: Adjustable 0.5x to 2x

## Localization Considerations
- **Script Translation**: Prepare for 5 major languages
- **Cultural Adaptation**: Adjust scenarios for different markets
- **Voice Talent**: Native speakers for each market
- **Visual Elements**: Culturally appropriate imagery

## Success Metrics
- **Completion Rate**: Target 70%+ watch-through
- **Engagement**: Comments, shares, likes
- **Conversion**: Video view to app download
- **Retention**: Users who watch and stay active
- **Support Reduction**: Fewer onboarding questions

## Production Timeline
- **Pre-Production**: 2 weeks
- **Production**: 1 week
- **Post-Production**: 3 weeks
- **Review & Revisions**: 1 week
- **Final Delivery**: 1 week
- **Total**: 8 weeks

## Deliverables Package
1. **Master Video** - 90 seconds, 1920x1080
2. **Short Version** - 60 seconds for attention spans
3. **Micro Version** - 30 seconds for social media
4. **Chapter Clips** - Individual feature demos
5. **Audio Track** - For podcast/radio use
6. **Subtitle Files** - SRT format, multiple languages
7. **Storyboard** - Frame-by-frame visual guide
8. **Asset Package** - All graphics, logos, fonts used
`;
  }

  createSocialMediaScript(variant, type) {
    return `# ${variant.name} - Social Media Video Script (15 seconds)

## Video Specifications
- **Duration**: ${type.duration} seconds
- **Format**: ${type.format} (1080x1080)
- **Purpose**: ${type.purpose}
- **Platforms**: Instagram, Facebook, TikTok, Twitter
- **Style**: High-energy, attention-grabbing

## Ultra-Fast Paced Script

### SCENE 1: Instant Hook (0-2 seconds)
**Visual**: 
- Bold text animation: "STOP SCROLLING!"
- Eye-catching color flash in ${variant.primaryColor}
- Quick app icon bounce

**Text Overlay**: 
\`\`\`
STOP SCROLLING! ✋
This will change everything
\`\`\`

**Audio**: Strong sound effect, no voiceover yet

### SCENE 2: Problem Flash (2-5 seconds)
**Visual**:
- Rapid montage of frustration (3 quick cuts)
- Exaggerated expressions
- "X" marks over failed solutions

**Text Overlay**:
\`\`\`
Tired of ${this.getShortProblem(variant)}?
❌ Messy  ❌ Stressful  ❌ Time-wasting
\`\`\`

**Audio**: Quick, punchy music starts

### SCENE 3: Solution Reveal (5-8 seconds)
**Visual**:
- ${variant.name} logo animation
- App interface quick showcase
- Smooth transitions between 3 key screens

**Text Overlay**:
\`\`\`
Meet ${variant.name} ${variant.icon}
${variant.tagline}
\`\`\`

**Audio**: Music builds, satisfying "ding" sound

### SCENE 4: Feature Speed Run (8-12 seconds)
**Visual**:
- Ultra-fast feature demonstrations
- Success animations and checkmarks
- Happy user reactions

**Text Overlay**:
\`\`\`
✅ ${this.getKeyFeatures(variant)[0].title}
✅ ${this.getKeyFeatures(variant)[1].title}  
✅ ${this.getKeyFeatures(variant)[2].title}
\`\`\`

**Audio**: Achievement sounds, upbeat rhythm

### SCENE 5: Social Proof (12-13 seconds)
**Visual**:
- Star ratings animation
- User count ticker
- Hearts/likes floating

**Text Overlay**:
\`\`\`
⭐⭐⭐⭐⭐ 10K+ Users!
\`\`\`

**Audio**: Crowd cheering sound effect

### SCENE 6: CTA Punch (13-15 seconds)
**Visual**:
- Download button animation
- App icon with pulsing effect
- Final brand color flash

**Text Overlay**:
\`\`\`
DOWNLOAD FREE NOW! 📲
Link in bio ⬆️
\`\`\`

**Audio**: Final musical sting, call-to-action voice

## Platform-Specific Variations

### Instagram Stories/Reels
- **Aspect Ratio**: 9:16 (1080x1920)
- **Text**: Larger, more readable
- **CTAs**: "Swipe up" or "Link in bio"
- **Stickers**: Add interactive elements

### TikTok
- **Music**: Trending audio overlay
- **Effects**: Quick transitions, zoom effects  
- **Text**: Minimal, punchy
- **Hashtags**: #ProductivityHack #LifeChanger

### Facebook/Instagram Feed
- **Captions**: Auto-play friendly (visual story without sound)
- **Subtitles**: Burned-in text for silent viewing
- **Branding**: Stronger brand presence

### Twitter
- **Length**: Can be 30 seconds max
- **Text**: Hashtag-friendly captions
- **Reply**: Pin tweet with download links

## Content Variations (A/B Test Options)

### Version A: Problem-Focused
- Start with pain point
- Heavy emphasis on before/after
- Emotional appeal

### Version B: Solution-Focused  
- Start with app reveal
- Feature demonstrations
- Logical appeal

### Version C: Social Proof-Focused
- Start with user testimonials
- Community aspect
- FOMO appeal

## Multi-Platform Campaign Series

### Week 1: Problem Awareness
- Focus on pain points
- Build relatability
- No product reveal yet

### Week 2: Solution Introduction
- Reveal ${variant.name}
- Basic feature overview
- Brand awareness

### Week 3: Deep Dive Features
- Individual feature spotlights
- User-generated content
- Tutorial snippets

### Week 4: Social Proof & CTA
- Testimonials and reviews
- Success stories
- Strong conversion push

## User-Generated Content Encouragement

### Challenge Campaign: #${variant.name}Challenge
**Prompt**: "Show us your ${this.getContextArea(variant)} transformation!"

**Example Posts**:
- Before/after screenshots
- Success story videos
- Creative feature usage
- Results and achievements

### Hashtag Strategy
- **Primary**: #${variant.name}
- **Category**: #${variant.category}App
- **Benefit**: #${this.getHashtagBenefit(variant)}
- **Community**: #${variant.name}Community
- **Results**: #${this.getResultsHashtag(variant)}

## Analytics & Optimization

### Key Metrics to Track
- **View-through rate** (complete views / impressions)
- **Click-through rate** (link clicks / views)  
- **Conversion rate** (downloads / clicks)
- **Engagement rate** (likes, comments, shares)
- **Share rate** (organic reach amplification)

### Optimization Tests
1. **Hook variations** - Different opening lines
2. **Music choices** - Various energy levels
3. **CTA timing** - Earlier vs. later placement
4. **Visual styles** - Animation vs. live action
5. **Text density** - Minimal vs. detailed overlays

## Budget-Friendly Production

### DIY Options
- **Screen recording**: Use app interface directly
- **Stock footage**: Royalty-free lifestyle clips
- **Text animations**: Canva or After Effects templates
- **Music**: Epidemic Sound or similar services

### Cost Breakdown
- **Music License**: $50-200
- **Stock Footage**: $100-300  
- **Animation Software**: $20-50/month
- **Total per video**: $170-550

### Batch Production
- Create 10-15 variations in one session
- Use same music across multiple videos
- Template-based approach for consistency
- Cross-platform adaptation from one master
`;
  }

  createDemoScript(variant, type) {
    const features = this.getTopFeatures(variant);
    
    return `# ${variant.name} - Product Demo Script (2 minutes)

## Video Specifications
- **Duration**: ${type.duration} seconds (2 minutes)
- **Format**: ${type.format} (1920x1080)
- **Purpose**: ${type.purpose}
- **Audience**: Prospects, sales presentations, detailed feature exploration
- **Style**: Professional, comprehensive, educational

## Detailed Walkthrough Structure

### INTRODUCTION (0-15 seconds)

#### Opening Statement
**Visual**: Professional presenter or clean screen recording setup

**Script**: 
"Welcome to ${variant.name}, the comprehensive ${variant.category.toLowerCase()} solution designed specifically for ${variant.targetAudience}. I'm going to show you exactly how ${variant.name} can transform your ${this.getContextArea(variant)} in just the next two minutes."

**On-Screen**: 
- ${variant.name} logo
- Presenter name/title (if applicable)
- Demo agenda overview

### SECTION 1: OVERVIEW & SETUP (15-30 seconds)

#### Quick Overview
**Visual**: App dashboard, clean interface

**Script**: 
"Let me start by showing you the main dashboard. As you can see, ${variant.name} gives you ${this.getDashboardDescription(variant)}. The interface is clean, intuitive, and designed for ${variant.targetAudience} who need ${variant.mainBenefit}."

**Demonstrate**: 
- Main navigation
- Key sections overview
- User profile/settings access

### SECTION 2: CORE FEATURES DEEP DIVE (30-90 seconds)

#### Feature 1: ${features[0].title} (30-50 seconds)
**Visual**: Step-by-step demonstration

**Script**: 
"Let's dive into our first major feature: ${features[0].title}. This is where you'll ${features[0].detailedWalkthrough}. 

Watch what happens when I ${features[0].demoAction}. [Perform action] 

As you can see, ${features[0].result}. This solves the common problem of ${features[0].problemSolved}, which costs ${variant.targetAudience} valuable time and energy."

**Demonstrate**:
- Feature access and navigation
- Key inputs and configurations  
- Real-time processing/results
- Integration with other features

#### Feature 2: ${features[1].title} (50-70 seconds)
**Visual**: Different use case scenario

**Script**:
"Now let me show you ${features[1].title}. This feature is particularly powerful because ${features[1].uniqueValue}. 

I'll demonstrate with a real example. [Set up scenario] When I ${features[1].demoAction}, you'll notice ${features[1].immediateResult}. 

But here's what makes this really special: ${features[1].advancedCapability}. This level of ${features[1].sophistication} is what sets ${variant.name} apart from other ${variant.category.toLowerCase()} apps."

**Demonstrate**:
- Advanced configuration options
- Multiple input methods
- Data visualization/analytics
- Export/sharing capabilities

#### Feature 3: ${features[2].title} (70-90 seconds)
**Visual**: Power user scenario

**Script**:
"For our power users, ${features[2].title} takes things to the next level. This feature ${features[2].powerUserBenefit}. 

Let me show you a more complex scenario. [Complex setup] When dealing with ${features[2].complexScenario}, ${variant.name} handles it seamlessly. Watch this: [Advanced demonstration]

The system automatically ${features[2].automation}, which means you can focus on ${features[2].focusArea} instead of ${features[2].eliminatedTask}."

**Demonstrate**:
- Complex workflows
- Automation capabilities  
- Advanced analytics
- Integration possibilities

### SECTION 3: INTEGRATION & WORKFLOW (90-105 seconds)

#### How It All Works Together
**Visual**: Cross-feature workflow demonstration

**Script**:
"What makes ${variant.name} truly powerful is how all these features work together seamlessly. Let me show you a typical workflow.

Starting with ${features[0].title}, I ${this.getWorkflowStep1(variant)}. This automatically ${this.getWorkflowConnection1(variant)} in ${features[1].title}, which then ${this.getWorkflowStep2(variant)}. Finally, ${features[2].title} ${this.getWorkflowStep3(variant)}.

This integrated approach means ${this.getWorkflowBenefit(variant)}."

### SECTION 4: CUSTOMIZATION & PERSONALIZATION (105-115 seconds)

#### Adapting to Your Needs
**Visual**: Settings, preferences, customization options

**Script**:
"${variant.name} adapts to your specific needs. Whether you're ${this.getUserType1(variant)} or ${this.getUserType2(variant)}, the app customizes itself accordingly.

For example, you can ${this.getCustomizationExample1(variant)}, set up ${this.getCustomizationExample2(variant)}, and even ${this.getCustomizationExample3(variant)}.

The app learns from your usage patterns and ${this.getPersonalizationFeature(variant)}."

### SECTION 5: RESULTS & BENEFITS (115-120 seconds)

#### What You'll Achieve
**Visual**: Success metrics, before/after comparisons, user testimonials

**Script**:
"So what can you expect from using ${variant.name}? Our users typically see ${this.getTypicalResults(variant)}. 

The average user saves ${this.getTimeSavings(variant)} per week, increases their ${this.getEfficiencyMetric(variant)} by ${this.getImprovementPercent(variant)}, and reports ${this.getSatisfactionMetric(variant)}.

But don't just take my word for it - with over 10,000 active users and a 4.8-star rating, ${variant.name} delivers real results for ${variant.targetAudience}."

## Advanced Demo Features

### Interactive Elements
- **Clickable hotspots**: For detailed feature exploration
- **Branching paths**: Different demo flows for different user types
- **Pause points**: For questions during live presentations
- **Resource links**: To documentation and tutorials

### Multiple Demo Versions

#### Version A: Executive Summary (60 seconds)
- High-level overview
- Business benefits focus
- ROI and efficiency metrics
- Quick feature highlights

#### Version B: Technical Deep Dive (3 minutes)
- Detailed feature walkthroughs
- Integration capabilities
- API and customization options
- Security and compliance features

#### Version C: User Journey Focus (90 seconds)
- Day-in-the-life scenario
- Problem-solution narrative
- Emotional benefits emphasis
- Success story integration

### Customizable Demo Scripts

#### For Different Audiences

**Business Owners**:
- ROI and productivity focus
- Team collaboration emphasis
- Scaling and growth benefits
- Competitive advantages

**Individual Users**:
- Personal benefits focus  
- Ease of use emphasis
- Life improvement outcomes
- Community and support

**IT/Technical Buyers**:
- Security and privacy features
- Integration capabilities
- Data export/backup options
- Technical specifications

### Demo Enhancement Tools

#### Screen Recording Best Practices
- **Resolution**: 1920x1080 minimum
- **Frame rate**: 30fps smooth recording
- **Audio**: Clear, professional narration
- **Cursor**: Smooth, purposeful movements
- **Timing**: Allow processing time to show

#### Visual Enhancements
- **Callouts**: Highlight important UI elements
- **Annotations**: Explain complex features
- **Zoom effects**: Focus attention on details
- **Transitions**: Smooth scene changes
- **Branding**: Consistent visual identity

### Follow-Up Resources

#### What to Provide After Demo
1. **Demo recording**: Link to watch again
2. **Feature checklist**: Detailed capabilities list  
3. **Pricing information**: Plans and options
4. **Trial access**: Free trial setup
5. **Support contacts**: Sales and technical support
6. **Customer stories**: Success case studies
7. **Implementation guide**: Getting started steps

#### Success Metrics to Track
- **Demo completion rate**: How many watch to the end
- **Feature engagement**: Which sections get rewatched  
- **Conversion rate**: Demo view to trial signup
- **Follow-up requests**: Additional information requests
- **Sales qualified leads**: Demos that lead to sales conversations

## Technical Production Notes

### Equipment Requirements
- **Screen recording software**: Camtasia, OBS, or similar
- **Audio equipment**: Professional microphone
- **Lighting**: If showing presenter on camera
- **Multiple monitors**: For smooth demonstration
- **High-speed internet**: For smooth app performance

### Post-Production Checklist
- [ ] Audio levels balanced and clear
- [ ] Visual callouts and annotations added
- [ ] Smooth transitions between sections
- [ ] Consistent branding throughout
- [ ] Captions/subtitles for accessibility
- [ ] Multiple format exports (MP4, MOV)
- [ ] Compressed versions for web delivery
- [ ] Quality assurance review completed
`;
  }

  async generateTeaser(variant, outputDir) {
    const content = `# ${variant.name} - Teaser Video Script (10 seconds)

## Concept: "Coming Soon" Style Teaser

### SCENE 1: Mystery Opening (0-3 seconds)
**Visual**: 
- Dark screen with subtle particle effects
- Mysterious, intriguing atmosphere
- Brand color hints

**Text Overlay**: 
\`\`\`
The future of ${this.getContextArea(variant)} is coming...
\`\`\`

**Audio**: Deep, mysterious intro sound

### SCENE 2: Problem Flash (3-5 seconds)  
**Visual**:
- Quick flashes of current frustrations
- Fragmented, chaotic imagery
- Building tension

**Text Overlay**:
\`\`\`
Tired of the chaos?
\`\`\`

### SCENE 3: Solution Hint (5-8 seconds)
**Visual**:
- Light breaking through darkness
- ${variant.name} logo partially revealed
- Color explosion in ${variant.primaryColor}

**Text Overlay**:
\`\`\`
Something amazing is coming
${variant.name}
\`\`\`

### SCENE 4: Final Hook (8-10 seconds)
**Visual**:
- Full logo reveal
- "Coming Soon" animation
- Website/social media handles

**Text Overlay**:
\`\`\`
COMING SOON
Follow us for updates
@activelog
\`\`\`

**Audio**: Powerful, exciting finish

## Usage
Perfect for social media teasers, email campaigns, and building anticipation before launch.
`;

    const filepath = path.join(outputDir, 'teaser-script.md');
    await fs.writeFile(filepath, content);
  }

  async generateTestimonial(variant, outputDir) {
    const content = `# ${variant.name} - User Testimonial Video Script (45 seconds)

## Concept: Real User Success Story

### User Profile: ${this.getTestimonialUser(variant)}
- **Name**: ${this.getUserName(variant)}
- **Age**: ${this.getUserAge(variant)}
- **Background**: ${this.getUserBackground(variant)}
- **Challenge**: ${this.getUserChallenge(variant)}

### SCENE 1: Introduction (0-8 seconds)
**Setting**: ${this.getTestimonialSetting(variant)}
**Visual**: User in natural environment

**User Script**: 
"Hi, I'm ${this.getUserName(variant)}, and I'm ${this.getUserIntro(variant)}. Six months ago, I was really struggling with ${this.getUserProblem(variant)}."

### SCENE 2: The Problem (8-18 seconds)
**Visual**: B-roll of user's previous struggles

**User Script**: 
"I was spending hours every day just trying to ${this.getUserFrustration(variant)}. It was stressful, time-consuming, and honestly, I was ready to give up."

### SCENE 3: Discovery (18-28 seconds)
**Visual**: User with ${variant.name} on their device

**User Script**: 
"Then I found ${variant.name}. Within just a few days, everything changed. The ${this.getUserFavoriteFeature(variant)} completely transformed how I ${this.getUserTransformation(variant)}."

### SCENE 4: Results (28-38 seconds)
**Visual**: User showing results, success metrics

**User Script**: 
"Now I save ${this.getTimeSaved(variant)} every week, and my ${this.getImprovementArea(variant)} has improved dramatically. I actually look forward to ${this.getEnjoyableAspect(variant)}!"

### SCENE 5: Recommendation (38-45 seconds)
**Visual**: User direct to camera, confident and happy

**User Script**: 
"If you're struggling with ${this.getUserProblem(variant)} like I was, you need to try ${variant.name}. It's honestly been life-changing."

**Text Overlay**: 
\`\`\`
Download ${variant.name} Free
App Store • Google Play
\`\`\`

## Production Notes
- **Authentic**: Real user, genuine experience
- **Relatable**: Target demographic representation  
- **Specific**: Concrete results and benefits
- **Emotional**: Personal connection and transformation
- **Credible**: Believable claims and realistic outcomes
`;

    const filepath = path.join(outputDir, 'testimonial-script.md');
    await fs.writeFile(filepath, content);
  }

  async generateTutorial(variant, outputDir) {
    const topFeature = this.getTopFeatures(variant)[0];
    
    const content = `# ${variant.name} - Tutorial Video Script: "${topFeature.title}" (60 seconds)

## Tutorial Focus: ${topFeature.title}
**Learning Objective**: Users will be able to ${topFeature.learningObjective}

### INTRODUCTION (0-10 seconds)
**Visual**: Clean screen recording setup, ${variant.name} logo

**Script**: 
"Welcome to ${variant.name} tutorials. Today I'll show you how to master ${topFeature.title} in just 60 seconds. This feature will help you ${topFeature.benefit}."

### STEP 1: Getting Started (10-20 seconds)
**Visual**: Navigation to feature

**Script**: 
"First, ${topFeature.step1}. You'll find this in the ${topFeature.location} section. Tap here to get started."

**On-Screen**: 
- Clear navigation indicators
- Button highlights
- Smooth transitions

### STEP 2: Basic Setup (20-35 seconds)
**Visual**: Initial configuration

**Script**: 
"Now, ${topFeature.step2}. This is where you ${topFeature.configuration}. Don't worry about getting it perfect - you can always change these settings later."

**Tips Box**: 
- Pro tip appears on screen
- Best practices highlight
- Common mistakes to avoid

### STEP 3: Advanced Usage (35-50 seconds)
**Visual**: Power user features

**Script**: 
"Here's a pro tip: ${topFeature.proTip}. This advanced feature ${topFeature.advancedBenefit}. Most users don't know about this!"

### CONCLUSION (50-60 seconds)
**Visual**: Results screen, success state

**Script**: 
"And that's it! You've successfully ${topFeature.completedAction}. Try this out and let us know how it helps you. Subscribe for more ${variant.name} tutorials!"

**End Screen**: 
- Subscribe button
- Related tutorials
- ${variant.name} branding

## Series Integration
This tutorial is part of the "${variant.name} Mastery" series:
1. ${topFeature.title} (This video)
2. ${this.getTopFeatures(variant)[1].title}
3. ${this.getTopFeatures(variant)[2].title}
4. Advanced Workflows
5. Tips & Tricks

## Interactive Elements
- **Timestamps**: Jump to specific steps
- **Resources**: Links to help articles
- **Practice**: Interactive elements for hands-on learning
- **Community**: Comments for questions and tips
`;

    const filepath = path.join(outputDir, 'tutorial-script.md');
    await fs.writeFile(filepath, content);
  }

  async generateProductionGuide(outputDir) {
    const content = `# Video Production Master Guide

## Overview
This guide covers production standards, processes, and best practices for all ${Object.keys(APP_VARIANTS).length} app variant video content.

## Universal Production Standards

### Technical Specifications
- **Resolution**: Minimum 1080p (1920x1080)
- **Frame Rate**: 30fps (60fps for screen recordings)
- **Audio**: 48kHz/24-bit minimum
- **Color Space**: Rec. 709
- **File Formats**: MP4 (H.264), MOV (ProRes for post)

### Brand Guidelines
- **Logo Usage**: Always include app icon prominently
- **Color Consistency**: Use exact brand colors from variants
- **Typography**: San Francisco (iOS) / Roboto (Android) style fonts
- **Voice**: Professional, friendly, confident
- **Tone**: Helpful, empowering, solution-focused

### Content Standards
- **Accuracy**: All app features must be current and functional
- **Authenticity**: No fake testimonials or misleading claims
- **Accessibility**: Captions, audio descriptions when needed
- **Compliance**: Follow App Store and Google Play guidelines
- **Localization**: Consider international audiences

## Production Workflow

### Pre-Production (2-3 weeks)
1. **Script Development**: Write and refine all scripts
2. **Storyboarding**: Visual planning for complex sequences
3. **Asset Gathering**: Screenshots, logos, brand materials
4. **Casting**: If using talent, book professional actors
5. **Location Scouting**: For live-action segments
6. **Equipment Check**: Ensure all tech is working properly

### Production (1-2 weeks)
1. **Screen Recording**: Capture all app interactions
2. **Live Action**: Film any person-on-camera segments  
3. **Voiceover**: Record professional narration
4. **B-Roll**: Supplementary footage as needed
5. **Music Selection**: License appropriate background tracks
6. **Quality Control**: Review all raw footage

### Post-Production (2-4 weeks)
1. **Editing**: Assembly edit to rough cut
2. **Motion Graphics**: Titles, lower thirds, callouts
3. **Color Correction**: Brand-consistent color grading
4. **Audio Mix**: Balance voice, music, sound effects
5. **Captions**: Accurate subtitle generation
6. **Multiple Formats**: Various aspect ratios and lengths
7. **Final Review**: Approval from stakeholders

### Distribution (1 week)
1. **Format Delivery**: All required video formats
2. **Platform Upload**: App stores, YouTube, social media
3. **Analytics Setup**: Tracking pixels and goals
4. **Launch Coordination**: Timing with marketing campaigns

## Budget Planning

### Typical Cost Ranges (Per Video)

#### DIY/In-House Production
- **Screen Recording**: $0-500 (software/tools)
- **Basic Editing**: $0-200 (software subscriptions)
- **Music Licensing**: $50-200
- **Total Range**: $50-900 per video

#### Professional Production  
- **Scripting**: $500-2,000
- **Production**: $2,000-10,000
- **Post-Production**: $1,000-5,000
- **Talent/Voiceover**: $500-3,000
- **Music/SFX**: $200-1,000
- **Total Range**: $4,200-21,000 per video

#### Hybrid Approach (Recommended)
- **Professional Script**: $500-1,000
- **DIY Screen Recording**: $100-300
- **Professional Edit**: $800-2,000
- **Professional Voiceover**: $300-800
- **Music Licensing**: $100-300
- **Total Range**: $1,800-4,400 per video

## Quality Assurance Checklist

### Pre-Launch Review
- [ ] All app features shown are current and accurate
- [ ] Brand guidelines followed consistently
- [ ] Audio levels balanced and clear
- [ ] Video quality meets technical standards
- [ ] Captions accurate and properly timed
- [ ] Legal compliance verified
- [ ] Multiple format exports completed
- [ ] Stakeholder approval obtained

### Post-Launch Monitoring
- [ ] Analytics tracking properly
- [ ] User feedback monitored
- [ ] Performance metrics reviewed
- [ ] A/B testing results analyzed
- [ ] Optimization opportunities identified

## Success Metrics Framework

### Primary KPIs
1. **View Completion Rate**: % who watch to end
2. **Click-Through Rate**: % who click from video to app store
3. **Conversion Rate**: % who download after viewing
4. **Engagement Rate**: Likes, comments, shares
5. **Cost Per Acquisition**: Video cost ÷ downloads generated

### Secondary KPIs
1. **Brand Awareness**: Survey metrics pre/post campaign
2. **Feature Adoption**: In-app usage of featured capabilities
3. **User Retention**: Do video viewers stay active longer?
4. **Support Reduction**: Fewer questions about featured topics
5. **Viral Coefficient**: How much content gets shared

### Reporting Schedule
- **Daily**: Platform-specific metrics during active campaigns
- **Weekly**: Comprehensive performance dashboard
- **Monthly**: ROI analysis and optimization recommendations
- **Quarterly**: Strategic review and planning for next videos

## Legal Considerations

### Rights and Permissions
- **Music Licensing**: Commercial use rights required
- **Stock Footage**: Extended licenses for commercial use
- **Talent Releases**: Signed agreements for all people shown
- **Location Permits**: If filming in public/private spaces
- **App Store Compliance**: Follow platform content policies

### Accessibility Requirements
- **ADA Compliance**: Captions for hearing impaired
- **WCAG Guidelines**: Web content accessibility standards
- **Multiple Languages**: Consider primary target markets
- **Audio Descriptions**: For visually impaired users

### Privacy Protection
- **User Data**: Never show real personal information
- **Screenshots**: Use dummy data in app demonstrations
- **Consent**: Clear agreements for any user testimonials
- **Children**: Special considerations if app targets minors

## Optimization Strategies

### A/B Testing Framework
Test variations of:
- Opening hooks (first 3 seconds)
- Call-to-action timing and wording
- Music choices and energy levels
- Video length (15s vs 30s vs 60s)
- Visual styles (animation vs live action)

### Continuous Improvement Process
1. **Baseline Metrics**: Establish initial performance
2. **Hypothesis Formation**: What could improve performance?
3. **Test Design**: Create controlled variations
4. **Statistical Analysis**: Measure significant differences
5. **Implementation**: Roll out winning variations
6. **Documentation**: Record learnings for future videos

### Platform-Specific Optimization
- **YouTube**: Optimize for search, longer content performs better
- **Instagram**: Square/vertical formats, visual storytelling
- **TikTok**: Trending audio, native feel, authentic content
- **LinkedIn**: Professional tone, business benefits focus
- **Facebook**: Auto-play friendly, subtitled content

This production guide ensures consistent, high-quality video content across all app variants while maintaining efficiency and effectiveness.
`;

    const filepath = path.join(this.outputDir, 'PRODUCTION_GUIDE.md');
    await fs.writeFile(filepath, content);
    console.log('📋 Production guide generated');
  }

  async generateMasterIndex() {
    const variants = Object.keys(APP_VARIANTS);
    const videoTypes = Object.keys(VIDEO_TYPES);
    
    const content = `# Video Scripts Master Index

Generated: ${new Date().toLocaleString()}

## Overview
Complete video script library for all ${variants.length} ActiveLog app variants across ${videoTypes.length + 3} video types.

## App Variants

${Object.entries(APP_VARIANTS).map(([key, variant]) => `
### ${variant.name}
- **Subtitle**: ${variant.subtitle}
- **Primary Color**: ${variant.primaryColor}
- **Target Audience**: ${variant.targetAudience}
- **Main Benefit**: ${variant.mainBenefit}
- **Scripts Directory**: \`video-scripts/${key}/\`
`).join('')}

## Video Types Generated

${Object.entries(VIDEO_TYPES).map(([key, type]) => `
### ${type.name}
- **Duration**: ${type.duration} seconds
- **Format**: ${type.format}
- **Purpose**: ${type.purpose}
- **Description**: ${type.description}
`).join('')}

## Additional Scripts
- **Teaser**: 10-second anticipation builder
- **Testimonial**: 45-second user success story
- **Tutorial**: 60-second feature walkthrough

## File Structure

\`\`\`
video-scripts/
├── PRODUCTION_GUIDE.md
├── MASTER_INDEX.md (this file)
${variants.map(variant => `├── ${variant}/
│   ├── app-preview-script.md
│   ├── promotional-script.md
│   ├── explainer-script.md
│   ├── social-media-script.md
│   ├── demo-script.md
│   ├── teaser-script.md
│   ├── testimonial-script.md
│   └── tutorial-script.md`).join('\n')}
\`\`\`

## Production Priority

### Phase 1: Essential (Launch Ready)
1. **App Preview Scripts** - Required for app stores
2. **Social Media Scripts** - Quick marketing wins
3. **Promotional Scripts** - Main marketing content

### Phase 2: Growth (Post-Launch)
1. **Explainer Scripts** - Website integration
2. **Demo Scripts** - Sales support
3. **Tutorial Scripts** - User onboarding

### Phase 3: Optimization (Ongoing)
1. **Testimonial Scripts** - Social proof
2. **Teaser Scripts** - Campaign launches
3. **A/B Test Variations** - Performance optimization

## Budget Estimates

### Phase 1 Production
- **3 video types** × **6 variants** = **18 videos**
- **Professional production**: $75,600 - $378,000
- **Hybrid approach**: $32,400 - $79,200
- **DIY approach**: $900 - $16,200

### Complete Library
- **8 video types** × **6 variants** = **48 videos**
- **Professional production**: $201,600 - $1,008,000
- **Hybrid approach**: $86,400 - $211,200
- **DIY approach**: $2,400 - $43,200

## Usage Guidelines

### App Store Submissions
- Use **app-preview-script.md** for preview videos
- Maximum 30 seconds for App Store
- Portrait format required (9:16)
- Follow platform-specific guidelines

### Marketing Campaigns
- **promotional-script.md** for paid advertising
- **social-media-script.md** for organic content
- **explainer-script.md** for website integration
- A/B test different versions for optimization

### User Onboarding
- **tutorial-script.md** for feature education
- **demo-script.md** for comprehensive walkthroughs
- **testimonial-script.md** for social proof

### Special Campaigns
- **teaser-script.md** for pre-launch buzz
- Seasonal variations for holidays/events
- User-generated content encouragement

## Next Steps

1. **Prioritize Production**: Start with Phase 1 videos
2. **Choose Approach**: Professional, hybrid, or DIY based on budget
3. **Create Timeline**: Allow 8-12 weeks for professional production
4. **Set Up Analytics**: Track performance metrics from day one
5. **Plan Iterations**: Build in optimization cycles

## Support Resources

- **Production Guide**: See PRODUCTION_GUIDE.md for detailed process
- **Brand Assets**: Request from design team
- **App Access**: Ensure latest builds for screen recording
- **Legal Review**: All scripts should be compliance-checked
- **Translation**: Consider international markets early

---

*Last updated: ${new Date().toISOString()}*
*Total scripts generated: ${variants.length * (videoTypes.length + 3)} individual files*
`;

    const filepath = path.join(this.outputDir, 'MASTER_INDEX.md');
    await fs.writeFile(filepath, content);
    console.log('📋 Master index generated');
  }

  // Helper methods for generating dynamic content
  getTopFeatures(variant) {
    const featureMap = {
      'PersonalLog': [
        {
          title: 'Rich Writing Experience',
          description: 'Express yourself with our powerful text editor featuring formatting, photos, and voice notes',
          benefit: 'Write beautifully formatted entries',
          walkthrough: 'you can create rich, multimedia journal entries with photos, voice notes, and formatted text',
          demoAction: 'add a photo and format some text',
          result: 'you get a beautiful, organized entry',
          problemSolved: 'messy, plain-text journaling',
          detailedWalkthrough: 'create and format your journal entries with photos, voice recordings, and rich text',
          learningObjective: 'create rich, multimedia journal entries with confidence'
        },
        {
          title: 'Personal Insights',
          description: 'Discover patterns in your thoughts and mood with intelligent analytics',
          benefit: 'Understand yourself better',
          walkthrough: 'the app analyzes your entries to show mood patterns and writing trends',
          demoAction: 'check my insights dashboard',
          result: 'you see clear patterns in your thoughts and moods over time',
          problemSolved: 'lack of self-awareness and reflection'
        },
        {
          title: 'Secure Privacy',
          description: 'Your thoughts are protected with end-to-end encryption',
          benefit: 'Write with complete privacy',
          walkthrough: 'all your entries are encrypted and secure',
          demoAction: 'show the privacy settings',
          result: 'complete peace of mind about your personal thoughts',
          problemSolved: 'privacy concerns with digital journaling'
        }
      ],
      'BusinessLog': [
        {
          title: 'Smart Task Management',
          description: 'Organize projects with intelligent task prioritization and deadlines',
          benefit: 'Stay organized and productive',
          walkthrough: 'you can create, prioritize, and track tasks across multiple projects',
          demoAction: 'create a new project and add tasks',
          result: 'a clear overview of what needs to be done and when',
          problemSolved: 'scattered tasks and missed deadlines'
        },
        {
          title: 'Team Collaboration',
          description: 'Work seamlessly with your team using shared workspaces',
          benefit: 'Improve team communication',
          walkthrough: 'team members can collaborate on projects in real-time',
          demoAction: 'share a project with team members',
          result: 'everyone stays in sync and accountable',
          problemSolved: 'poor team communication and coordination'
        },
        {
          title: 'Business Analytics',
          description: 'Make data-driven decisions with comprehensive reports',
          benefit: 'Understand your business performance',
          walkthrough: 'you get detailed analytics on productivity and project performance',
          demoAction: 'generate a performance report',
          result: 'clear insights into team productivity and project success',
          problemSolved: 'lack of business performance visibility'
        }
      ]
      // Add other variants as needed...
    };

    return featureMap[variant.name] || featureMap['PersonalLog'];
  }

  getBenefits(variant) {
    const benefitMap = {
      'PersonalLog': [
        { title: 'Improve Self-Awareness', description: 'Gain deeper insights into your thoughts and emotions' },
        { title: 'Never Lose Memories', description: 'All your entries are safely backed up and searchable' },
        { title: 'Build Healthy Habits', description: 'Consistent journaling promotes mental wellness' }
      ],
      'BusinessLog': [
        { title: 'Increase Productivity', description: 'Smart task management helps you focus on what matters' },
        { title: 'Improve Team Communication', description: 'Collaboration tools keep everyone aligned' },
        { title: 'Make Better Decisions', description: 'Data-driven insights guide strategic choices' }
      ]
      // Add other variants...
    };

    return benefitMap[variant.name] || benefitMap['PersonalLog'];
  }

  getKeyFeatures(variant) {
    return this.getTopFeatures(variant);
  }

  // Context and problem helpers
  getContextArea(variant) {
    const contexts = {
      'PersonalLog': 'journaling',
      'BusinessLog': 'productivity',
      'FamilyLog': 'family life',
      'FitnessLog': 'fitness journey',
      'TravelLog': 'travel experiences',
      'EducationLog': 'learning'
    };
    return contexts[variant.name] || 'organization';
  }

  getProblemStatement(variant) {
    const problems = {
      'PersonalLog': 'scattered thoughts and inconsistent journaling',
      'BusinessLog': 'chaotic task management and poor team coordination',
      'FamilyLog': 'missed family moments and poor coordination',
      'FitnessLog': 'inconsistent tracking and lack of progress visibility',
      'TravelLog': 'disorganized travel planning and lost memories',
      'EducationLog': 'poor study organization and unclear progress'
    };
    return problems[variant.name] || 'disorganized digital life';
  }

  getShortProblem(variant) {
    const problems = {
      'PersonalLog': 'messy journaling',
      'BusinessLog': 'chaotic tasks',
      'FamilyLog': 'family chaos',
      'FitnessLog': 'fitness confusion',
      'TravelLog': 'travel stress',
      'EducationLog': 'study struggles'
    };
    return problems[variant.name] || 'disorganization';
  }

  getHashtagBenefit(variant) {
    const hashtags = {
      'PersonalLog': 'SelfAwareness',
      'BusinessLog': 'ProductivityBoost',
      'FamilyLog': 'FamilyFirst',
      'FitnessLog': 'FitnessGoals',
      'TravelLog': 'TravelMemories',
      'EducationLog': 'StudySuccess'
    };
    return hashtags[variant.name] || 'LifeOrganized';
  }

  getResultsHashtag(variant) {
    const hashtags = {
      'PersonalLog': 'JournalingSuccess',
      'BusinessLog': 'ProductivityWins',
      'FamilyLog': 'FamilyMemories',
      'FitnessLog': 'FitnessResults',
      'TravelLog': 'TravelStories',
      'EducationLog': 'LearningWins'
    };
    return hashtags[variant.name] || 'SuccessStory';
  }

  // Additional helper methods can be added here for other dynamic content...
  getUseCases(variant) {
    // Implementation for use cases
    return [];
  }

  getUniversalProblem(variant) {
    return `the challenge of ${this.getContextArea(variant)}`;
  }

  getProblemConsequences(variant) {
    return `wasting time and feeling frustrated`;
  }

  getCorePhilosophy(variant) {
    return `${variant.mainBenefit} should be effortless and intuitive`;
  }

  // Continue adding helper methods as needed for the script generation...
}

// Main execution
async function main() {
  const generator = new VideoScriptGenerator();
  
  try {
    await generator.generateAllScripts();
  } catch (error) {
    console.error('❌ Error generating video scripts:', error);
    process.exit(1);
  }
}

// Export for module usage
module.exports = { VideoScriptGenerator, APP_VARIANTS, VIDEO_TYPES };

// Run if called directly
if (require.main === module) {
  main();
}