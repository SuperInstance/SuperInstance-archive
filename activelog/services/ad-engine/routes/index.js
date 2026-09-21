const express = require('express');
const router = express.Router();

// Import controllers
const AdEngineController = require('../controllers/AdEngineController');
const ReviewController = require('../controllers/ReviewController');
const EducationController = require('../controllers/EducationController');
const ParentChildController = require('../controllers/ParentChildController');

// Initialize controllers
const adEngine = new AdEngineController();
const reviewController = new ReviewController();
const educationController = new EducationController();
const parentChildController = new ParentChildController();

// Ad Engine Routes - Watch-Ad-to-Use System
router.get('/users/:userId/compute/eligibility', adEngine.checkComputeEligibility.bind(adEngine));
router.post('/users/:userId/compute/request', adEngine.requestComputeAccess.bind(adEngine));
router.put('/users/:userId/ad-frequency', adEngine.updateUserAdFrequency.bind(adEngine));

// Startup Ads
router.get('/users/:userId/ads/startup', adEngine.getStartupAd.bind(adEngine));

// Double Banner System
router.get('/users/:userId/ads/double-banner', adEngine.getDoubleBannerOffer.bind(adEngine));

// Ad-Free Status and Thresholds
router.get('/users/:userId/ad-free-status', adEngine.checkAdFreeStatus.bind(adEngine));

// Ad Break Scheduling
router.post('/users/:userId/ad-breaks/schedule', adEngine.scheduleAdBreak.bind(adEngine));

// Ad Viewing and CCC Earning
router.post('/users/:userId/ads/view', adEngine.processAdView.bind(adEngine));

// Review System Routes - CCC Earning Through Reviews
router.post('/users/:userId/reviews', reviewController.submitReview.bind(reviewController));
router.get('/users/:userId/reviews/opportunities', reviewController.getReviewOpportunities.bind(reviewController));
router.get('/users/:userId/reviews/stats', reviewController.getReviewStats.bind(reviewController));
router.put('/users/:userId/reviews/:reviewId/helpful', reviewController.markReviewHelpful.bind(reviewController));

// Educational Participation Routes
router.post('/users/:userId/education/complete', educationController.completeActivity.bind(educationController));
router.get('/users/:userId/education/activities', educationController.getAvailableActivities.bind(educationController));
router.get('/users/:userId/education/progress', educationController.getEducationProgress.bind(educationController));
router.post('/users/:userId/education/achievements/:achievementId', educationController.unlockAchievement.bind(educationController));
router.get('/users/:userId/education/recommendations', educationController.getLearningRecommendations.bind(educationController));

// Parent-Child System Routes
router.post('/parents/:parentId/children/link', parentChildController.linkChildAccount.bind(parentChildController));
router.put('/parents/:parentId/children/:childId/allowance', parentChildController.setChildAllowance.bind(parentChildController));

// Spending Approval Workflow
router.post('/children/:childId/spending/request-approval', parentChildController.requestSpendingApproval.bind(parentChildController));
router.put('/parents/:parentId/approvals/:requestId', parentChildController.reviewSpendingRequest.bind(parentChildController));

// Child Account Management
router.get('/parents/:parentId/children/:childId/status', parentChildController.getChildAccountStatus.bind(parentChildController));
router.put('/parents/:parentId/children/:childId/restrictions', parentChildController.updateChildRestrictions.bind(parentChildController));
router.get('/parents/:parentId/dashboard', parentChildController.getParentDashboard.bind(parentChildController));

// Scheduled Tasks (would typically be called by cron jobs)
router.post('/system/allowances/reset', parentChildController.processDailyAllowanceReset.bind(parentChildController));

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'ad-engine',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Service status endpoint
router.get('/status', async (req, res) => {
  try {
    // In a real app, these would check actual service health
    const status = {
      service: 'ad-engine',
      version: '1.0.0',
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      components: {
        database: 'connected',
        redis: 'connected',
        adProviders: {
          primary: 'connected',
          secondary: 'connected'
        }
      },
      metrics: {
        totalUsers: 1250,
        activeUsers: 180,
        adsServedToday: 2840,
        creditsEarnedToday: 8520,
        averageAdFrequency: '12 minutes'
      },
      features: {
        watchAdToUse: true,
        dynamicFrequency: true,
        startupAds: true,
        doubleBanners: true,
        adFreeThresholds: true,
        reviewSystem: true,
        educationRewards: true,
        parentChildSystem: true
      }
    };

    res.json(status);
  } catch (error) {
    console.error('Error getting service status:', error);
    res.status(500).json({
      status: 'error',
      error: 'Failed to get service status'
    });
  }
});

// API Documentation endpoint
router.get('/docs', (req, res) => {
  const documentation = {
    service: 'ActiveLog Ad Engine API',
    version: '1.0.0',
    description: 'Smart ad monetization system with compute credits and usage-based frequency',
    baseUrl: `http://localhost:${process.env.PORT || 8381}/api`,
    
    endpoints: {
      
      adEngine: {
        description: 'Watch-ad-to-use system for compute-heavy features',
        endpoints: [
          {
            method: 'GET',
            path: '/users/:userId/compute/eligibility',
            description: 'Check if user can access compute features',
            parameters: ['userId', 'operation', 'operationType']
          },
          {
            method: 'POST',
            path: '/users/:userId/compute/request',
            description: 'Request access to compute features',
            body: ['operation', 'operationType', 'skipAd']
          },
          {
            method: 'GET',
            path: '/users/:userId/ads/startup',
            description: 'Get startup ad with clear messaging'
          },
          {
            method: 'GET',
            path: '/users/:userId/ads/double-banner',
            description: 'Get double banner offer for extra credits'
          },
          {
            method: 'POST',
            path: '/users/:userId/ads/view',
            description: 'Process ad view and award credits',
            body: ['adId', 'adType', 'completed', 'watchTime']
          }
        ]
      },
      
      reviews: {
        description: 'Review system for earning CCC through user reviews',
        endpoints: [
          {
            method: 'POST',
            path: '/users/:userId/reviews',
            description: 'Submit a review and earn credits',
            body: ['targetId', 'targetType', 'rating', 'reviewText', 'photos', 'videoUrl']
          },
          {
            method: 'GET',
            path: '/users/:userId/reviews/opportunities',
            description: 'Get available review opportunities'
          },
          {
            method: 'GET',
            path: '/users/:userId/reviews/stats',
            description: 'Get user review statistics and reputation'
          }
        ]
      },
      
      education: {
        description: 'Educational participation rewards system',
        endpoints: [
          {
            method: 'POST',
            path: '/users/:userId/education/complete',
            description: 'Complete educational activity and earn credits',
            body: ['activityId', 'activityType', 'score', 'timeSpent']
          },
          {
            method: 'GET',
            path: '/users/:userId/education/activities',
            description: 'Get available educational activities'
          },
          {
            method: 'GET',
            path: '/users/:userId/education/progress',
            description: 'Get user education progress and stats'
          },
          {
            method: 'GET',
            path: '/users/:userId/education/recommendations',
            description: 'Get personalized learning recommendations'
          }
        ]
      },
      
      parentChild: {
        description: 'Parent-child account management and allowance system',
        endpoints: [
          {
            method: 'POST',
            path: '/parents/:parentId/children/link',
            description: 'Link child account to parent',
            body: ['childUserId', 'childAge', 'permissions']
          },
          {
            method: 'PUT',
            path: '/parents/:parentId/children/:childId/allowance',
            description: 'Set child allowance amounts',
            body: ['dailyAllowance', 'weeklyAllowance']
          },
          {
            method: 'POST',
            path: '/children/:childId/spending/request-approval',
            description: 'Request parental approval for spending',
            body: ['amount', 'purpose', 'description']
          },
          {
            method: 'PUT',
            path: '/parents/:parentId/approvals/:requestId',
            description: 'Approve or deny child spending request',
            body: ['decision', 'reason', 'conditions']
          },
          {
            method: 'GET',
            path: '/parents/:parentId/dashboard',
            description: 'Get parent dashboard with all children status'
          }
        ]
      }
    },
    
    concepts: {
      ccc: {
        name: 'Compute Currency Credits (CCC)',
        description: 'Virtual currency earned through ads, reviews, and education',
        usedFor: ['Compute operations', 'Premium features', 'Service usage']
      },
      
      usageTiers: {
        light: 'Low usage users - fewer ads, longer intervals',
        moderate: 'Regular users - balanced ad frequency',
        heavy: 'Power users - more frequent ads but higher rewards',
        extreme: 'Heavy users - maximum ad frequency with best rewards'
      },
      
      adTypes: {
        banner: 'Simple banner ads - 2 CCC reward',
        interstitial: 'Full-screen ads - 5 CCC reward',
        video: 'Video ads - 10 CCC reward',
        rewarded: 'Rewarded video ads - 15 CCC reward'
      },
      
      reputationSystem: {
        newcomer: 'New reviewer - 1.0x multiplier',
        contributor: '11+ reviews - 1.2x multiplier',
        expert: '51+ reviews - 1.5x multiplier',
        master: '200+ reviews - 2.0x multiplier'
      }
    },
    
    examples: {
      watchAdForCompute: {
        description: 'User needs 15 CCC for heavy compute operation but only has 5 CCC',
        flow: [
          'Check eligibility - insufficient credits',
          'System offers ad viewing option',
          'User watches video ad (10 CCC reward)',
          'User now has 15 CCC and can proceed'
        ]
      },
      
      parentChildFlow: {
        description: 'Child wants to spend 30 CCC but threshold is 25 CCC',
        flow: [
          'Child requests spending approval',
          'Parent receives notification',
          'Parent reviews and approves with conditions',
          'Child can now make the purchase'
        ]
      }
    }
  };

  res.json(documentation);
});

// Error handling middleware
router.use((error, req, res, next) => {
  console.error('API Error:', error);
  
  if (error.name === 'ValidationError') {
    return res.status(400).json({
      error: 'Validation Error',
      details: error.message
    });
  }
  
  if (error.name === 'CastError') {
    return res.status(400).json({
      error: 'Invalid ID format',
      details: error.message
    });
  }
  
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'production' 
      ? 'Something went wrong' 
      : error.message
  });
});

// 404 handler
router.use('*', (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found',
    availableEndpoints: '/api/docs'
  });
});

module.exports = router;