// ActiveLog Growth Systems - Main Export Index
// Complete growth infrastructure for user acquisition, engagement, and retention

// SEO & Content Marketing
export { seoManager, SEOManager } from './seo/seo-manager';
export type { SEOData, StructuredData, SitemapEntry, AppVariant } from './seo/seo-manager';

export { blogSystem, BlogSystem } from './blog/blog-system';
export type { BlogPost, BlogTemplate, ContentCalendar, BlogAnalytics } from './blog/blog-system';

// Social Media & Viral Growth
export { socialIntegration, SocialIntegrationManager } from './social/social-integration';
export type { SocialPost, ContentTemplate, SocialAnalytics, PlatformConfig } from './social/social-integration';

export { referralSystem, ReferralSystem } from './referral/referral-system';
export type { ReferralLink, ReferralConversion, ReferralAnalytics, RewardRule } from './referral/referral-system';

export { affiliateTracking, AffiliateTrackingSystem } from './affiliate/affiliate-tracking';
export type { AffiliateUser, AffiliateCommission, AffiliateAnalytics, AffiliateLink } from './affiliate/affiliate-tracking';

// Email Marketing & Automation
export { emailAutomation, EmailAutomationSystem } from './email/email-automation';
export type { EmailCampaign, AutomationFlow, EmailTemplate, EmailAnalytics } from './email/email-automation';

// User Onboarding & Product Tours
export { onboardingFlows, OnboardingFlowSystem } from './onboarding/onboarding-flows';
export type { OnboardingFlow, OnboardingStep, OnboardingSession, OnboardingAnalytics } from './onboarding/onboarding-flows';

export { productTours, ProductTourSystem } from './tours/product-tours';
export type { ProductTour, TourStep, TourSession, TourAnalytics } from './tours/product-tours';

// Support & Community
export { helpDocumentation, HelpDocumentationSystem } from './help/help-documentation';
export type { HelpArticle, HelpCategory, SearchResult, HelpAnalytics } from './help/help-documentation';

export { tutorialScripts, VideoTutorialScriptSystem } from './videos/tutorial-scripts';
export type { VideoScript, VideoScriptSection, ScreenAction, VideoAnalytics } from './videos/tutorial-scripts';

export { communityForum, CommunityForumSystem } from './community/forum-system';
export type { ForumUser, ForumTopic, ForumPost, ForumCategory, ForumAnalytics } from './community/forum-system';

export { supportTicketing, CustomerSupportTicketingSystem } from './support/ticketing-system';
export type { SupportTicket, TicketMessage, SupportAgent, SupportAnalytics } from './support/ticketing-system';

// Growth Systems Integration Class
export class ActiveLogGrowthSystems {
  // All systems are accessible as static properties
  static readonly seo = seoManager;
  static readonly blog = blogSystem;
  static readonly social = socialIntegration;
  static readonly referrals = referralSystem;
  static readonly affiliates = affiliateTracking;
  static readonly email = emailAutomation;
  static readonly onboarding = onboardingFlows;
  static readonly tours = productTours;
  static readonly help = helpDocumentation;
  static readonly videos = tutorialScripts;
  static readonly forum = communityForum;
  static readonly support = supportTicketing;

  // Unified analytics across all systems
  static async getGlobalAnalytics() {
    const [
      seoData,
      socialData,
      referralData,
      emailData,
      onboardingData,
      tourData,
      helpData,
      forumData,
      supportData
    ] = await Promise.all([
      this.seo.getSystemAnalytics(),
      this.social.getAnalytics(),
      this.referrals.getSystemAnalytics(),
      this.email.getSystemAnalytics(),
      this.onboarding.getOnboardingAnalytics(),
      this.tours.getTourAnalytics(),
      this.help.getAnalytics(),
      this.forum.getForumAnalytics(),
      this.support.getSupportAnalytics()
    ]);

    return {
      seo: seoData,
      social: socialData,
      referrals: referralData,
      email: emailData,
      onboarding: onboardingData,
      tours: tourData,
      help: helpData,
      forum: forumData,
      support: supportData,
      generatedAt: new Date()
    };
  }

  // App variant specific analytics
  static async getAppVariantAnalytics(appVariant: AppVariant) {
    return {
      seo: await this.seo.generateSEO(appVariant, 'dashboard', {}),
      onboarding: await this.onboarding.getOnboardingAnalytics(),
      tours: await this.tours.getAvailableTours('user', appVariant),
      help: await this.help.getFeaturedArticles(appVariant),
      appVariant,
      generatedAt: new Date()
    };
  }

  // Initialize all systems for a new app variant
  static async initializeForApp(appVariant: AppVariant) {
    // Setup SEO configuration
    await this.seo.generateSEO(appVariant, 'dashboard', {});
    
    // Initialize onboarding flow
    await this.onboarding.startOnboardingFlow('system', appVariant);
    
    // Setup product tours
    const tours = await this.tours.getAvailableTours('system', appVariant);
    
    // Create help articles
    const helpArticles = await this.help.getFeaturedArticles(appVariant);
    
    return {
      seo: `SEO configuration created for ${appVariant}`,
      onboarding: `Onboarding flow initialized`,
      tours: `${tours.length} product tours available`,
      help: `${helpArticles.length} help articles ready`,
      status: 'initialized'
    };
  }
}

// Export the unified growth systems
export default ActiveLogGrowthSystems;