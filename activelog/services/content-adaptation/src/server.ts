import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { createServer } from 'http';
import { Server } from 'socket.io';

import { readingLevelAdjuster } from './reading-level/reading-level-adjuster';
import { complexityScaler } from './explanation/complexity-scaler';
import { visualModeManager } from './visual/visual-mode-manager';

// Import simplified implementations for remaining components
import {
  TerminologyManager,
  ExampleGenerator,
  WorkflowSimplifier,
  ProgressiveDisclosure,
  ContextualHelpSystem,
  TutorialAdaptationSystem,
  SkillBasedUnlocking,
  ContentWarningSystem,
  CulturalSensitivityFilter
} from './components/content-adapters';

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.CLIENT_URL || "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 8210;

// Initialize components
const terminologyManager = new TerminologyManager();
const exampleGenerator = new ExampleGenerator();
const workflowSimplifier = new WorkflowSimplifier();
const progressiveDisclosure = new ProgressiveDisclosure();
const contextualHelp = new ContextualHelpSystem();
const tutorialAdaptation = new TutorialAdaptationSystem();
const skillUnlocking = new SkillBasedUnlocking();
const contentWarning = new ContentWarningSystem();
const culturalFilter = new CulturalSensitivityFilter();

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'content-adaptation', timestamp: new Date().toISOString() });
});

// Reading Level Adjustment Routes
app.post('/api/reading-level/configure', (req, res) => {
  try {
    const { userId, targetGrade, options } = req.body;
    const config = readingLevelAdjuster.createConfiguration(userId, targetGrade, options);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/reading-level/adapt', async (req, res) => {
  try {
    const { userId, content, contentType } = req.body;
    const result = await readingLevelAdjuster.adaptContent(userId, content, contentType);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/reading-level/batch-adapt', async (req, res) => {
  try {
    const { userId, contentItems } = req.body;
    const results = await readingLevelAdjuster.batchAdaptContent(userId, contentItems);
    res.json({ success: true, results: Object.fromEntries(results) });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/reading-level/assess', async (req, res) => {
  try {
    const { text } = req.body;
    const assessment = await readingLevelAdjuster.assessReadingLevel(text);
    res.json({ success: true, assessment });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/reading-level/personalized-terms', (req, res) => {
  try {
    const { userId, terms } = req.body;
    const termMap = new Map(Object.entries(terms));
    readingLevelAdjuster.updatePersonalizedTerms(userId, termMap);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/reading-level/progress/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const { contentHistory } = req.body || { contentHistory: [] };
    const report = readingLevelAdjuster.generateReadingProgressReport(userId, contentHistory);
    res.json({ success: true, report });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Explanation Complexity Scaler Routes
app.post('/api/explanation/configure', (req, res) => {
  try {
    const { userId, options } = req.body;
    const config = complexityScaler.createConfiguration(userId, options);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/explanation/generate', async (req, res) => {
  try {
    const { userId, request } = req.body;
    const result = await complexityScaler.generateExplanation(userId, request);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/explanation/adapt', async (req, res) => {
  try {
    const { userId, existingExplanation, newComplexity } = req.body;
    const result = await complexityScaler.adaptExistingExplanation(userId, existingExplanation, newComplexity);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/explanation/personalization', (req, res) => {
  try {
    const { userId, personalizationUpdates } = req.body;
    complexityScaler.updatePersonalization(userId, personalizationUpdates);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/explanation/concept-mastery', (req, res) => {
  try {
    const { userId, concept, masteryLevel } = req.body;
    complexityScaler.recordConceptMastery(userId, concept, masteryLevel);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/explanation/progression-plan', async (req, res) => {
  try {
    const { userId, concept, targetComplexity } = req.body;
    const plan = await complexityScaler.generateComplexityProgressionPlan(userId, concept, targetComplexity);
    res.json({ success: true, plan });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Visual Mode Manager Routes
app.post('/api/visual/configure', (req, res) => {
  try {
    const { userId, ageGroup, options } = req.body;
    const config = visualModeManager.createConfiguration(userId, ageGroup, options);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/visual/generate', async (req, res) => {
  try {
    const { userId, request } = req.body;
    const result = await visualModeManager.generateVisualContent(userId, request);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/visual/adapt-complexity', async (req, res) => {
  try {
    const { userId, visualContent, newComplexity } = req.body;
    const result = await visualModeManager.adaptVisualComplexity(userId, visualContent, newComplexity);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/visual/preferences', (req, res) => {
  try {
    const { userId, preferences } = req.body;
    visualModeManager.updateVisualPreferences(userId, preferences);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/visual/report/:userId/:timeframe', (req, res) => {
  try {
    const { userId, timeframe } = req.params;
    const report = visualModeManager.generateVisualReport(userId, timeframe as any);
    res.json({ success: true, report });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Professional Terminology Toggle Routes
app.post('/api/terminology/configure', (req, res) => {
  try {
    const { userId, settings } = req.body;
    const config = terminologyManager.configure(userId, settings);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/terminology/toggle', (req, res) => {
  try {
    const { userId, enabled } = req.body;
    const result = terminologyManager.toggleProfessionalTerms(userId, enabled);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/terminology/adapt', async (req, res) => {
  try {
    const { userId, content, domain } = req.body;
    const result = await terminologyManager.adaptTerminology(userId, content, domain);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Age-Appropriate Example Generator Routes
app.post('/api/examples/generate', async (req, res) => {
  try {
    const { concept, ageGroup, context, count } = req.body;
    const examples = await exampleGenerator.generateExamples(concept, ageGroup, context, count);
    res.json({ success: true, examples });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/examples/customize', async (req, res) => {
  try {
    const { userId, preferences } = req.body;
    const result = await exampleGenerator.customizeExamples(userId, preferences);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Simplified Workflow Routes
app.post('/api/workflow/simplify', async (req, res) => {
  try {
    const { userId, workflow, targetAge } = req.body;
    const simplified = await workflowSimplifier.simplifyWorkflow(userId, workflow, targetAge);
    res.json({ success: true, simplified });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/workflow/steps', async (req, res) => {
  try {
    const { userId, task, complexity } = req.body;
    const steps = await workflowSimplifier.generateSteps(userId, task, complexity);
    res.json({ success: true, steps });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Progressive Disclosure Routes
app.post('/api/disclosure/configure', (req, res) => {
  try {
    const { userId, settings } = req.body;
    const config = progressiveDisclosure.configure(userId, settings);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/disclosure/content', async (req, res) => {
  try {
    const { userId, content } = req.body;
    const layers = await progressiveDisclosure.createLayers(userId, content);
    res.json({ success: true, layers });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Contextual Help Routes
app.post('/api/help/configure', (req, res) => {
  try {
    const { userId, settings } = req.body;
    const config = contextualHelp.configure(userId, settings);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/help/generate', async (req, res) => {
  try {
    const { userId, context, element } = req.body;
    const help = await contextualHelp.generateHelp(userId, context, element);
    res.json({ success: true, help });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Tutorial Adaptation Routes
app.post('/api/tutorial/adapt', async (req, res) => {
  try {
    const { userId, tutorial, targetLevel } = req.body;
    const adapted = await tutorialAdaptation.adaptTutorial(userId, tutorial, targetLevel);
    res.json({ success: true, adapted });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/tutorial/progress', (req, res) => {
  try {
    const { userId, tutorialId, step, success } = req.body;
    tutorialAdaptation.recordProgress(userId, tutorialId, step, success);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Skill-Based Unlocking Routes
app.post('/api/skills/configure', (req, res) => {
  try {
    const { userId, settings } = req.body;
    const config = skillUnlocking.configure(userId, settings);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/skills/assess', async (req, res) => {
  try {
    const { userId, skill, evidence } = req.body;
    const assessment = await skillUnlocking.assessSkill(userId, skill, evidence);
    res.json({ success: true, assessment });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/skills/available/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const features = skillUnlocking.getAvailableFeatures(userId);
    res.json({ success: true, features });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Content Warning System Routes
app.post('/api/warnings/configure', (req, res) => {
  try {
    const { userId, settings } = req.body;
    const config = contentWarning.configure(userId, settings);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/warnings/analyze', async (req, res) => {
  try {
    const { userId, content } = req.body;
    const warnings = await contentWarning.analyzeContent(userId, content);
    res.json({ success: true, warnings });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Cultural Sensitivity Filter Routes
app.post('/api/cultural/configure', (req, res) => {
  try {
    const { userId, settings } = req.body;
    const config = culturalFilter.configure(userId, settings);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/cultural/filter', async (req, res) => {
  try {
    const { userId, content } = req.body;
    const filtered = await culturalFilter.filterContent(userId, content);
    res.json({ success: true, filtered });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Combined Content Adaptation Route
app.post('/api/adapt/comprehensive', async (req, res) => {
  try {
    const { 
      userId, 
      content, 
      targetAge, 
      complexity, 
      options = {}
    } = req.body;

    const results = {
      readingLevel: null,
      explanation: null,
      visual: null,
      terminology: null,
      examples: null,
      warnings: null,
      cultural: null
    };

    // Apply reading level adaptation if requested
    if (options.adaptReading !== false) {
      results.readingLevel = await readingLevelAdjuster.adaptContent(userId, content, 'text');
    }

    // Generate explanations if requested
    if (options.generateExplanations) {
      const explanationRequest = {
        concept: options.concept || 'General Content',
        context: content.substring(0, 200),
        targetAudience: {
          ageRange: { min: Math.max(5, targetAge - 2), max: targetAge + 2 },
          educationLevel: `Grade ${Math.floor(targetAge - 5)}`,
          domainExpertise: complexity || 0.5,
          languageLevel: 'intermediate',
          specialNeeds: []
        },
        complexity: complexity || 0.5,
        format: 'text',
        constraints: {
          maxLength: 1000,
          maxComplexity: complexity || 0.5,
          prohibitedConcepts: [],
          requiredElements: [],
          timeLimit: 30,
          accessibilityRequirements: []
        },
        learningObjectives: options.learningObjectives || []
      };
      results.explanation = await complexityScaler.generateExplanation(userId, explanationRequest);
    }

    // Generate visual content if requested
    if (options.generateVisual) {
      const visualRequest = {
        textContent: content,
        contentType: 'educational',
        targetAge,
        complexity: complexity || 0.5,
        learningObjectives: options.learningObjectives || [],
        context: 'learning',
        constraints: {
          maxElements: 10,
          timeLimit: 300,
          fileSize: 1024,
          dimensions: { width: 800, height: 600 },
          accessibility: ['alt_text', 'high_contrast'],
          culturalConsiderations: ['diversity', 'inclusion']
        }
      };
      results.visual = await visualModeManager.generateVisualContent(userId, visualRequest);
    }

    // Apply terminology adaptation if requested
    if (options.adaptTerminology !== false) {
      results.terminology = await terminologyManager.adaptTerminology(userId, content, options.domain);
    }

    // Generate examples if requested
    if (options.generateExamples) {
      results.examples = await exampleGenerator.generateExamples(
        options.concept || 'General Content',
        this.ageToAgeGroup(targetAge),
        content.substring(0, 200),
        3
      );
    }

    // Check for content warnings if requested
    if (options.checkWarnings !== false) {
      results.warnings = await contentWarning.analyzeContent(userId, content);
    }

    // Apply cultural sensitivity filter if requested
    if (options.culturalFilter !== false) {
      results.cultural = await culturalFilter.filterContent(userId, content);
    }

    res.json({ success: true, results });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// WebSocket handling for real-time adaptation
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('join-user-room', (userId) => {
    socket.join(`user:${userId}`);
  });

  socket.on('real-time-adapt', async (data) => {
    try {
      const { userId, content, adaptationType } = data;
      
      let result;
      switch (adaptationType) {
        case 'reading-level':
          result = await readingLevelAdjuster.adaptContent(userId, content, 'text');
          break;
        case 'visual':
          const visualRequest = {
            textContent: content,
            contentType: 'educational',
            targetAge: data.targetAge || 12,
            complexity: data.complexity || 0.5,
            learningObjectives: [],
            context: 'real-time',
            constraints: {
              maxElements: 5,
              timeLimit: 60,
              fileSize: 512,
              dimensions: { width: 400, height: 300 },
              accessibility: ['alt_text'],
              culturalConsiderations: []
            }
          };
          result = await visualModeManager.generateVisualContent(userId, visualRequest);
          break;
        default:
          throw new Error(`Unknown adaptation type: ${adaptationType}`);
      }

      socket.emit('adaptation-result', { success: true, result });
      
    } catch (error) {
      socket.emit('adaptation-result', { success: false, error: error.message });
    }
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Event listeners for system events
readingLevelAdjuster.on('contentAdapted', (data) => {
  io.to(`user:${data.userId}`).emit('reading-level-adapted', data.result);
});

complexityScaler.on('explanationGenerated', (data) => {
  io.to(`user:${data.userId}`).emit('explanation-generated', data.result);
});

visualModeManager.on('visualContentGenerated', (data) => {
  io.to(`user:${data.userId}`).emit('visual-content-generated', data.result);
});

// Utility method
const ageToAgeGroup = (age: number): string => {
  if (age <= 4) return 'toddler';
  if (age <= 6) return 'preschool';
  if (age <= 9) return 'early_elementary';
  if (age <= 12) return 'late_elementary';
  if (age <= 15) return 'middle_school';
  if (age <= 17) return 'high_school';
  return 'adult';
};

// Error handling middleware
app.use((error: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Server error:', error);
  res.status(500).json({ 
    success: false, 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ 
    success: false, 
    error: 'Not found',
    message: `Route ${req.method} ${req.path} not found`
  });
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('Process terminated');
  });
});

server.listen(PORT, () => {
  console.log(`Content Adaptation Service running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log('Available services:');
  console.log('- Reading Level Adjustment');
  console.log('- Explanation Complexity Scaling');
  console.log('- Visual Mode Management');
  console.log('- Professional Terminology Toggle');
  console.log('- Age-Appropriate Example Generation');
  console.log('- Simplified Workflow Creation');
  console.log('- Progressive Disclosure');
  console.log('- Contextual Help System');
  console.log('- Tutorial Adaptation');
  console.log('- Skill-Based Feature Unlocking');
  console.log('- Content Warning System');
  console.log('- Cultural Sensitivity Filtering');
});

export default app;