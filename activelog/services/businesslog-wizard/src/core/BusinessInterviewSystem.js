/**
 * Intelligent Business Interview System
 * Conducts adaptive interviews to understand business needs and generate recommendations
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/interview.log' })
  ]
});

export class BusinessInterviewSystem extends EventEmitter {
  constructor(recommendationEngine) {
    super();
    this.recommendationEngine = recommendationEngine;
    this.interviews = new Map();
    this.questionTemplates = new Map();
    this.businessProfiles = new Map();
    
    this.initializeQuestionTemplates();
  }

  /**
   * Initialize question templates for different business types and stages
   */
  initializeQuestionTemplates() {
    // Basic business information questions
    const basicQuestions = [
      {
        id: 'business_name',
        type: 'text',
        category: 'basic',
        question: 'What is the name of your business?',
        required: true,
        validation: { minLength: 2, maxLength: 100 }
      },
      {
        id: 'business_type',
        type: 'select',
        category: 'basic',
        question: 'What type of business do you operate?',
        options: [
          'Retail Store', 'Restaurant', 'Manufacturing', 'Professional Services',
          'Healthcare', 'Technology', 'Construction', 'Automotive', 'Real Estate',
          'Education', 'Entertainment', 'Agriculture', 'Transportation', 'Other'
        ],
        required: true
      },
      {
        id: 'business_stage',
        type: 'select',
        category: 'basic',
        question: 'What stage is your business in?',
        options: [
          'Planning/Startup', 'Less than 1 year', '1-3 years', '3-5 years',
          '5-10 years', 'More than 10 years'
        ],
        required: true
      },
      {
        id: 'employee_count',
        type: 'number',
        category: 'basic',
        question: 'How many employees do you currently have?',
        validation: { min: 0, max: 10000 },
        required: true
      },
      {
        id: 'annual_revenue',
        type: 'select',
        category: 'basic',
        question: 'What is your approximate annual revenue?',
        options: [
          'Pre-revenue', 'Under $50K', '$50K - $100K', '$100K - $500K',
          '$500K - $1M', '$1M - $5M', '$5M - $10M', 'Over $10M'
        ],
        required: false
      }
    ];

    // Operations questions
    const operationsQuestions = [
      {
        id: 'current_systems',
        type: 'multiselect',
        category: 'operations',
        question: 'Which business systems do you currently use?',
        options: [
          'Point of Sale (POS)', 'Inventory Management', 'Customer Relationship Management (CRM)',
          'Accounting Software', 'Employee Scheduling', 'Security System', 'Website/E-commerce',
          'Social Media Management', 'Project Management', 'Email Marketing', 'None'
        ],
        required: true
      },
      {
        id: 'biggest_challenges',
        type: 'multiselect',
        category: 'operations',
        question: 'What are your biggest operational challenges?',
        options: [
          'Managing inventory', 'Employee scheduling', 'Customer management',
          'Financial tracking', 'Marketing', 'Security', 'Maintenance',
          'Supply chain', 'Quality control', 'Compliance', 'Technology adoption'
        ],
        required: true
      },
      {
        id: 'daily_tasks',
        type: 'text',
        category: 'operations',
        question: 'Describe your typical daily business tasks and workflow.',
        placeholder: 'e.g., Opening procedures, customer interactions, inventory checks, closing procedures...',
        validation: { minLength: 20, maxLength: 1000 }
      },
      {
        id: 'peak_hours',
        type: 'multiselect',
        category: 'operations',
        question: 'When are your busiest hours/days?',
        options: [
          'Early morning (6-9 AM)', 'Morning (9-12 PM)', 'Afternoon (12-5 PM)',
          'Evening (5-9 PM)', 'Late night (9 PM+)', 'Weekends', 'Holidays',
          'Seasonal peaks', 'No specific pattern'
        ]
      }
    ];

    // Technology questions
    const technologyQuestions = [
      {
        id: 'tech_comfort',
        type: 'scale',
        category: 'technology',
        question: 'How comfortable are you and your team with technology?',
        scale: { min: 1, max: 5, labels: ['Not comfortable', 'Very comfortable'] },
        required: true
      },
      {
        id: 'current_devices',
        type: 'multiselect',
        category: 'technology',
        question: 'What devices do you currently use for business?',
        options: [
          'Desktop computers', 'Laptops', 'Tablets', 'Smartphones',
          'Cash registers', 'Barcode scanners', 'Security cameras',
          'Point-of-sale terminals', 'Industrial equipment', 'None'
        ]
      },
      {
        id: 'automation_interest',
        type: 'scale',
        category: 'technology',
        question: 'How interested are you in automating business processes?',
        scale: { min: 1, max: 5, labels: ['Not interested', 'Very interested'] },
        required: true
      },
      {
        id: 'budget_technology',
        type: 'select',
        category: 'technology',
        question: 'What is your monthly budget for technology solutions?',
        options: [
          'Under $100', '$100 - $500', '$500 - $1,000', '$1,000 - $5,000',
          '$5,000 - $10,000', 'Over $10,000', 'Varies by need'
        ]
      }
    ];

    // Growth and goals questions
    const growthQuestions = [
      {
        id: 'growth_goals',
        type: 'multiselect',
        category: 'growth',
        question: 'What are your primary business goals for the next year?',
        options: [
          'Increase sales', 'Reduce costs', 'Improve efficiency', 'Expand locations',
          'Hire more staff', 'Improve customer service', 'Better inventory control',
          'Enhance security', 'Go digital', 'Improve marketing', 'Compliance'
        ],
        required: true
      },
      {
        id: 'target_customers',
        type: 'text',
        category: 'growth',
        question: 'Describe your target customers and how you currently reach them.',
        validation: { minLength: 20, maxLength: 500 }
      },
      {
        id: 'competitive_advantages',
        type: 'text',
        category: 'growth',
        question: 'What sets your business apart from competitors?',
        validation: { minLength: 10, maxLength: 300 }
      }
    ];

    // Store question templates
    this.questionTemplates.set('basic', basicQuestions);
    this.questionTemplates.set('operations', operationsQuestions);
    this.questionTemplates.set('technology', technologyQuestions);
    this.questionTemplates.set('growth', growthQuestions);
  }

  /**
   * Start a new business interview
   */
  async startInterview({ businessName, industry, ownerInfo }) {
    const interviewId = uuidv4();
    
    const interview = {
      id: interviewId,
      businessName,
      industry,
      ownerInfo,
      startedAt: Date.now(),
      currentStage: 'basic',
      currentQuestionIndex: 0,
      answers: new Map(),
      completedStages: [],
      businessProfile: {
        businessName,
        industry,
        ownerInfo
      },
      adaptiveFlow: {
        skipReasons: [],
        customQuestions: [],
        focusAreas: []
      },
      status: 'in_progress'
    };

    // Generate initial question sequence
    interview.questionSequence = this.generateQuestionSequence(interview);
    
    this.interviews.set(interviewId, interview);
    
    logger.info(`Started business interview: ${interviewId} for ${businessName}`);
    
    this.emit('interview:started', {
      interviewId,
      businessName,
      firstQuestion: interview.questionSequence[0]
    });

    return {
      interviewId,
      currentQuestion: interview.questionSequence[0],
      progress: this.calculateProgress(interview),
      estimatedTimeRemaining: this.estimateTimeRemaining(interview)
    };
  }

  /**
   * Submit an answer to the current question
   */
  async submitAnswer(interviewId, questionId, answer) {
    const interview = this.interviews.get(interviewId);
    if (!interview) {
      throw new Error('Interview not found');
    }

    if (interview.status !== 'in_progress') {
      throw new Error('Interview is not in progress');
    }

    // Validate answer
    const currentQuestion = interview.questionSequence[interview.currentQuestionIndex];
    if (currentQuestion.id !== questionId) {
      throw new Error('Question ID mismatch');
    }

    const validationResult = this.validateAnswer(currentQuestion, answer);
    if (!validationResult.valid) {
      return {
        success: false,
        error: validationResult.error,
        currentQuestion
      };
    }

    // Store answer
    interview.answers.set(questionId, {
      questionId,
      answer: validationResult.processedAnswer,
      answeredAt: Date.now()
    });

    // Update business profile with new information
    this.updateBusinessProfile(interview, questionId, validationResult.processedAnswer);

    // Determine next question or stage
    const nextStep = await this.determineNextStep(interview);
    
    if (nextStep.completed) {
      return await this.completeInterview(interview);
    }

    interview.currentQuestionIndex = nextStep.questionIndex;
    if (nextStep.newStage) {
      interview.currentStage = nextStep.newStage;
      interview.completedStages.push(nextStep.previousStage);
    }

    const nextQuestion = interview.questionSequence[interview.currentQuestionIndex];
    
    this.emit('interview:answer_submitted', {
      interviewId,
      questionId,
      answer: validationResult.processedAnswer,
      nextQuestion
    });

    return {
      success: true,
      nextQuestion,
      progress: this.calculateProgress(interview),
      estimatedTimeRemaining: this.estimateTimeRemaining(interview),
      insights: this.generateRealTimeInsights(interview)
    };
  }

  /**
   * Generate adaptive question sequence based on business profile
   */
  generateQuestionSequence(interview) {
    let sequence = [];
    
    // Always start with basic questions
    const basicQuestions = this.questionTemplates.get('basic');
    sequence = [...basicQuestions];

    // Add operations questions
    const operationsQuestions = this.questionTemplates.get('operations');
    sequence = [...sequence, ...operationsQuestions];

    // Conditionally add technology questions based on industry
    if (this.needsTechnologyFocus(interview.industry)) {
      const technologyQuestions = this.questionTemplates.get('technology');
      sequence = [...sequence, ...technologyQuestions];
    }

    // Add growth questions for established businesses
    if (interview.businessStage !== 'Planning/Startup') {
      const growthQuestions = this.questionTemplates.get('growth');
      sequence = [...sequence, ...growthQuestions];
    }

    // Add industry-specific questions
    const industryQuestions = this.generateIndustryQuestions(interview.industry);
    sequence = [...sequence, ...industryQuestions];

    return sequence;
  }

  /**
   * Generate industry-specific questions
   */
  generateIndustryQuestions(industry) {
    const industryQuestions = {
      'Retail Store': [
        {
          id: 'store_layout',
          type: 'text',
          category: 'industry',
          question: 'Describe your store layout and customer flow.',
          validation: { minLength: 20, maxLength: 500 }
        },
        {
          id: 'inventory_turnover',
          type: 'select',
          category: 'industry',
          question: 'How often do you need to restock your main products?',
          options: ['Daily', 'Weekly', 'Monthly', 'Seasonally', 'Varies by product']
        },
        {
          id: 'customer_payment',
          type: 'multiselect',
          category: 'industry',
          question: 'What payment methods do you currently accept?',
          options: ['Cash', 'Credit/Debit Cards', 'Mobile Payments', 'Checks', 'Store Credit', 'Layaway']
        }
      ],
      'Restaurant': [
        {
          id: 'restaurant_type',
          type: 'select',
          category: 'industry',
          question: 'What type of restaurant do you operate?',
          options: ['Fast Food', 'Casual Dining', 'Fine Dining', 'Cafe', 'Food Truck', 'Catering']
        },
        {
          id: 'seating_capacity',
          type: 'number',
          category: 'industry',
          question: 'What is your seating capacity?',
          validation: { min: 0, max: 1000 }
        },
        {
          id: 'food_safety',
          type: 'multiselect',
          category: 'industry',
          question: 'Which food safety practices do you currently track?',
          options: ['Temperature logs', 'Cleaning schedules', 'Supplier certifications', 'Staff training', 'Health inspections']
        }
      ],
      'Manufacturing': [
        {
          id: 'production_type',
          type: 'select',
          category: 'industry',
          question: 'What type of manufacturing do you do?',
          options: ['Made-to-order', 'Made-to-stock', 'Assembly', 'Custom fabrication', 'Mass production']
        },
        {
          id: 'quality_control',
          type: 'text',
          category: 'industry',
          question: 'Describe your current quality control processes.',
          validation: { minLength: 20, maxLength: 500 }
        }
      ]
    };

    return industryQuestions[industry] || [];
  }

  /**
   * Validate answer based on question type and validation rules
   */
  validateAnswer(question, answer) {
    if (question.required && (!answer || answer.length === 0)) {
      return { valid: false, error: 'This question is required' };
    }

    switch (question.type) {
      case 'text':
        return this.validateTextAnswer(question, answer);
      case 'number':
        return this.validateNumberAnswer(question, answer);
      case 'select':
        return this.validateSelectAnswer(question, answer);
      case 'multiselect':
        return this.validateMultiSelectAnswer(question, answer);
      case 'scale':
        return this.validateScaleAnswer(question, answer);
      default:
        return { valid: true, processedAnswer: answer };
    }
  }

  validateTextAnswer(question, answer) {
    if (typeof answer !== 'string') {
      return { valid: false, error: 'Answer must be text' };
    }

    if (question.validation) {
      if (question.validation.minLength && answer.length < question.validation.minLength) {
        return { valid: false, error: `Answer must be at least ${question.validation.minLength} characters` };
      }
      if (question.validation.maxLength && answer.length > question.validation.maxLength) {
        return { valid: false, error: `Answer must be no more than ${question.validation.maxLength} characters` };
      }
    }

    return { valid: true, processedAnswer: answer.trim() };
  }

  validateNumberAnswer(question, answer) {
    const num = parseInt(answer);
    if (isNaN(num)) {
      return { valid: false, error: 'Answer must be a number' };
    }

    if (question.validation) {
      if (question.validation.min !== undefined && num < question.validation.min) {
        return { valid: false, error: `Number must be at least ${question.validation.min}` };
      }
      if (question.validation.max !== undefined && num > question.validation.max) {
        return { valid: false, error: `Number must be no more than ${question.validation.max}` };
      }
    }

    return { valid: true, processedAnswer: num };
  }

  validateSelectAnswer(question, answer) {
    if (!question.options.includes(answer)) {
      return { valid: false, error: 'Please select a valid option' };
    }
    return { valid: true, processedAnswer: answer };
  }

  validateMultiSelectAnswer(question, answer) {
    if (!Array.isArray(answer)) {
      return { valid: false, error: 'Answer must be an array' };
    }

    const invalidOptions = answer.filter(option => !question.options.includes(option));
    if (invalidOptions.length > 0) {
      return { valid: false, error: 'Some selected options are not valid' };
    }

    return { valid: true, processedAnswer: answer };
  }

  validateScaleAnswer(question, answer) {
    const num = parseInt(answer);
    if (isNaN(num)) {
      return { valid: false, error: 'Please select a number on the scale' };
    }

    if (num < question.scale.min || num > question.scale.max) {
      return { valid: false, error: `Please select a number between ${question.scale.min} and ${question.scale.max}` };
    }

    return { valid: true, processedAnswer: num };
  }

  /**
   * Update business profile with new answer
   */
  updateBusinessProfile(interview, questionId, answer) {
    const profile = interview.businessProfile;

    // Map answers to business profile fields
    const mappings = {
      'business_type': 'businessType',
      'business_stage': 'businessStage',
      'employee_count': 'employeeCount',
      'annual_revenue': 'annualRevenue',
      'current_systems': 'currentSystems',
      'biggest_challenges': 'biggestChallenges',
      'tech_comfort': 'techComfortLevel',
      'automation_interest': 'automationInterest',
      'growth_goals': 'growthGoals'
    };

    if (mappings[questionId]) {
      profile[mappings[questionId]] = answer;
    }

    // Store all answers for reference
    profile.allAnswers = profile.allAnswers || {};
    profile.allAnswers[questionId] = answer;
  }

  /**
   * Determine next step in interview process
   */
  async determineNextStep(interview) {
    const currentIndex = interview.currentQuestionIndex;
    const sequence = interview.questionSequence;

    // Check if we need to add adaptive questions
    const adaptiveQuestions = await this.generateAdaptiveQuestions(interview);
    if (adaptiveQuestions.length > 0) {
      // Insert adaptive questions into sequence
      sequence.splice(currentIndex + 1, 0, ...adaptiveQuestions);
      interview.adaptiveFlow.customQuestions.push(...adaptiveQuestions);
    }

    // Move to next question
    if (currentIndex + 1 < sequence.length) {
      return {
        completed: false,
        questionIndex: currentIndex + 1,
        newStage: this.determineStage(sequence[currentIndex + 1]),
        previousStage: interview.currentStage
      };
    }

    return { completed: true };
  }

  /**
   * Generate adaptive questions based on previous answers
   */
  async generateAdaptiveQuestions(interview) {
    const adaptiveQuestions = [];
    const answers = interview.businessProfile.allAnswers;

    // If they mentioned specific challenges, ask for details
    if (answers.biggest_challenges && answers.biggest_challenges.includes('Managing inventory')) {
      adaptiveQuestions.push({
        id: 'inventory_details',
        type: 'text',
        category: 'adaptive',
        question: 'Can you describe your current inventory management process and specific challenges?',
        validation: { minLength: 20, maxLength: 500 }
      });
    }

    // If they have security concerns, ask about current setup
    if (answers.biggest_challenges && answers.biggest_challenges.includes('Security')) {
      adaptiveQuestions.push({
        id: 'security_current',
        type: 'multiselect',
        category: 'adaptive',
        question: 'What security measures do you currently have in place?',
        options: ['Security cameras', 'Alarm system', 'Access control', 'Security guards', 'None']
      });
    }

    // If they're interested in automation, ask about specific areas
    if (answers.automation_interest >= 4) {
      adaptiveQuestions.push({
        id: 'automation_areas',
        type: 'multiselect',
        category: 'adaptive',
        question: 'Which business processes would you most like to automate?',
        options: [
          'Customer check-in/out', 'Inventory tracking', 'Employee scheduling',
          'Report generation', 'Customer communications', 'Order processing',
          'Quality control', 'Maintenance alerts'
        ]
      });
    }

    return adaptiveQuestions;
  }

  /**
   * Complete the interview and generate business profile
   */
  async completeInterview(interview) {
    interview.status = 'completed';
    interview.completedAt = Date.now();

    // Generate comprehensive business profile
    const businessProfile = this.generateComprehensiveProfile(interview);
    
    // Store the profile
    this.businessProfiles.set(interview.id, businessProfile);

    // Generate initial recommendations
    let recommendations = [];
    if (this.recommendationEngine) {
      try {
        recommendations = await this.recommendationEngine.generateInitialRecommendations(businessProfile);
      } catch (error) {
        logger.error('Failed to generate recommendations:', error);
      }
    }

    logger.info(`Completed interview ${interview.id} for ${interview.businessName}`);

    this.emit('interview:completed', {
      interviewId: interview.id,
      businessProfile,
      recommendations,
      duration: interview.completedAt - interview.startedAt
    });

    return {
      success: true,
      completed: true,
      businessProfile,
      recommendations,
      summary: this.generateInterviewSummary(interview),
      nextSteps: this.generateNextSteps(businessProfile)
    };
  }

  /**
   * Generate comprehensive business profile from interview answers
   */
  generateComprehensiveProfile(interview) {
    const answers = interview.businessProfile.allAnswers;
    
    return {
      businessId: interview.id,
      basicInfo: {
        name: interview.businessName,
        type: answers.business_type,
        industry: interview.industry,
        stage: answers.business_stage,
        employeeCount: answers.employee_count,
        annualRevenue: answers.annual_revenue,
        ownerInfo: interview.ownerInfo
      },
      operations: {
        currentSystems: answers.current_systems || [],
        dailyWorkflow: answers.daily_tasks,
        peakHours: answers.peak_hours || [],
        biggestChallenges: answers.biggest_challenges || [],
        specificDetails: this.extractSpecificDetails(answers)
      },
      technology: {
        comfortLevel: answers.tech_comfort || 3,
        currentDevices: answers.current_devices || [],
        automationInterest: answers.automation_interest || 3,
        budget: answers.budget_technology,
        preferredAreas: answers.automation_areas || []
      },
      growth: {
        goals: answers.growth_goals || [],
        targetCustomers: answers.target_customers,
        competitiveAdvantages: answers.competitive_advantages
      },
      industrySpecific: this.extractIndustrySpecific(answers, interview.industry),
      recommendations: {
        complexity: this.determineInitialComplexity(answers),
        priorities: this.determinePriorities(answers),
        timeline: this.suggestTimeline(answers)
      },
      createdAt: Date.now(),
      lastUpdated: Date.now()
    };
  }

  /**
   * Extract industry-specific details
   */
  extractIndustrySpecific(answers, industry) {
    const industryData = {};

    if (industry === 'Retail Store') {
      industryData.storeLayout = answers.store_layout;
      industryData.inventoryTurnover = answers.inventory_turnover;
      industryData.paymentMethods = answers.customer_payment || [];
    } else if (industry === 'Restaurant') {
      industryData.restaurantType = answers.restaurant_type;
      industryData.seatingCapacity = answers.seating_capacity;
      industryData.foodSafety = answers.food_safety || [];
    } else if (industry === 'Manufacturing') {
      industryData.productionType = answers.production_type;
      industryData.qualityControl = answers.quality_control;
    }

    return industryData;
  }

  /**
   * Determine initial system complexity level
   */
  determineInitialComplexity(answers) {
    let complexity = 1; // Start at basic

    // Increase based on business size
    if (answers.employee_count > 10) complexity++;
    if (answers.employee_count > 50) complexity++;

    // Increase based on current systems
    if (answers.current_systems && answers.current_systems.length > 3) complexity++;
    if (answers.current_systems && answers.current_systems.length > 6) complexity++;

    // Increase based on tech comfort
    if (answers.tech_comfort >= 4) complexity++;

    // Cap at level 5
    return Math.min(complexity, 5);
  }

  /**
   * Determine implementation priorities
   */
  determinePriorities(answers) {
    const priorities = [];
    const challenges = answers.biggest_challenges || [];

    if (challenges.includes('Managing inventory')) {
      priorities.push({ area: 'inventory', priority: 'high', reason: 'Identified as major challenge' });
    }
    if (challenges.includes('Employee scheduling')) {
      priorities.push({ area: 'employee_management', priority: 'high', reason: 'Identified as major challenge' });
    }
    if (challenges.includes('Security')) {
      priorities.push({ area: 'security', priority: 'medium', reason: 'Security concerns identified' });
    }
    if (challenges.includes('Customer management')) {
      priorities.push({ area: 'customer_management', priority: 'medium', reason: 'Customer management challenges' });
    }

    // Add automation priorities if interested
    if (answers.automation_interest >= 4) {
      priorities.push({ area: 'automation', priority: 'high', reason: 'High interest in automation' });
    }

    return priorities;
  }

  /**
   * Generate interview summary
   */
  generateInterviewSummary(interview) {
    const answers = interview.businessProfile.allAnswers;
    const duration = interview.completedAt - interview.startedAt;
    
    return {
      businessName: interview.businessName,
      industry: interview.industry,
      questionsAnswered: interview.answers.size,
      duration: Math.round(duration / 1000 / 60), // minutes
      keyInsights: this.extractKeyInsights(answers),
      recommendedComplexity: this.determineInitialComplexity(answers)
    };
  }

  /**
   * Extract key insights from answers
   */
  extractKeyInsights(answers) {
    const insights = [];

    if (answers.biggest_challenges && answers.biggest_challenges.length > 0) {
      insights.push(`Main challenges: ${answers.biggest_challenges.join(', ')}`);
    }

    if (answers.tech_comfort) {
      const comfort = answers.tech_comfort <= 2 ? 'low' : answers.tech_comfort >= 4 ? 'high' : 'moderate';
      insights.push(`Technology comfort level: ${comfort}`);
    }

    if (answers.automation_interest) {
      const interest = answers.automation_interest <= 2 ? 'low' : answers.automation_interest >= 4 ? 'high' : 'moderate';
      insights.push(`Automation interest: ${interest}`);
    }

    return insights;
  }

  /**
   * Generate next steps recommendations
   */
  generateNextSteps(profile) {
    const steps = [
      'Review and customize your business interface',
      'Set up priority systems based on your challenges',
      'Configure integrations with existing software',
      'Train team members on new processes'
    ];

    // Add specific steps based on profile
    if (profile.operations.biggestChallenges.includes('Managing inventory')) {
      steps.splice(1, 0, 'Set up inventory management system');
    }
    
    if (profile.operations.biggestChallenges.includes('Employee scheduling')) {
      steps.splice(1, 0, 'Configure employee management and scheduling');
    }

    return steps;
  }

  /**
   * Get interview progress
   */
  getProgress(interviewId) {
    const interview = this.interviews.get(interviewId);
    if (!interview) {
      throw new Error('Interview not found');
    }

    return {
      interviewId,
      progress: this.calculateProgress(interview),
      currentStage: interview.currentStage,
      questionsAnswered: interview.answers.size,
      totalQuestions: interview.questionSequence.length,
      estimatedTimeRemaining: this.estimateTimeRemaining(interview),
      currentQuestion: interview.questionSequence[interview.currentQuestionIndex],
      status: interview.status
    };
  }

  calculateProgress(interview) {
    return Math.round((interview.answers.size / interview.questionSequence.length) * 100);
  }

  estimateTimeRemaining(interview) {
    const avgTimePerQuestion = 45; // seconds
    const remainingQuestions = interview.questionSequence.length - interview.answers.size;
    return remainingQuestions * avgTimePerQuestion;
  }

  determineStage(question) {
    return question.category || 'general';
  }

  needsTechnologyFocus(industry) {
    const techFocusIndustries = ['Technology', 'Professional Services', 'Healthcare', 'Manufacturing'];
    return techFocusIndustries.includes(industry);
  }

  extractSpecificDetails(answers) {
    const details = {};
    
    // Extract any industry-specific or adaptive answers
    Object.keys(answers).forEach(key => {
      if (key.includes('_details') || key.includes('_current') || key.includes('_areas')) {
        details[key] = answers[key];
      }
    });

    return details;
  }

  suggestTimeline(answers) {
    const complexity = this.determineInitialComplexity(answers);
    const timelines = {
      1: '1-2 weeks',
      2: '2-4 weeks', 
      3: '1-2 months',
      4: '2-3 months',
      5: '3-6 months'
    };
    
    return timelines[complexity] || '2-4 weeks';
  }

  generateRealTimeInsights(interview) {
    const insights = [];
    const answers = interview.businessProfile.allAnswers;

    // Generate insights based on patterns in answers
    if (answers.current_systems && answers.current_systems.length === 0) {
      insights.push({
        type: 'opportunity',
        message: 'Great opportunity to build an integrated system from the ground up!'
      });
    }

    if (answers.tech_comfort >= 4 && answers.automation_interest >= 4) {
      insights.push({
        type: 'recommendation',
        message: 'Your tech comfort level suggests you\'ll benefit from advanced automation features.'
      });
    }

    return insights;
  }
}