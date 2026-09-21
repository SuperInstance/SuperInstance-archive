import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { BehaviorPredictionEngine } from './core/BehaviorPredictionEngine';
import { FolderSuggestionEngine } from './engines/FolderSuggestionEngine';
import { FutureNeedsPredictor } from './engines/FutureNeedsPredictor';
import { SmartPreCachingEngine } from './engines/SmartPreCachingEngine';
import { RelationshipMappingEngine } from './engines/RelationshipMappingEngine';
import { TimelineReconstructionEngine } from './engines/TimelineReconstructionEngine';
import { MissingDataDetector } from './engines/MissingDataDetector';
import { PredictiveAIService } from './api/PredictiveAIService';

dotenv.config();

const app = express();
const port = process.env.PORT || 3003;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize engines
const behaviorEngine = new BehaviorPredictionEngine();
const relationshipEngine = new RelationshipMappingEngine();
const folderSuggestionEngine = new FolderSuggestionEngine(behaviorEngine);
const futureNeedsPredictor = new FutureNeedsPredictor(behaviorEngine);
const preCachingEngine = new SmartPreCachingEngine(behaviorEngine, futureNeedsPredictor);
const timelineEngine = new TimelineReconstructionEngine(relationshipEngine);
const missingDataDetector = new MissingDataDetector(behaviorEngine, timelineEngine);

// Initialize AI service
const aiService = new PredictiveAIService({
  behaviorEngine,
  folderSuggestionEngine,
  futureNeedsPredictor,
  preCachingEngine,
  relationshipEngine,
  timelineEngine,
  missingDataDetector
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'predictive-ai' });
});

// API Routes
app.use('/api/v1', aiService.getRouter());

// Error handling
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
async function startServer() {
  try {
    await behaviorEngine.initialize();
    console.log('Behavior prediction engine initialized');
    
    app.listen(port, () => {
      console.log(`Predictive AI service listening on port ${port}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

export {
  behaviorEngine,
  folderSuggestionEngine,
  futureNeedsPredictor,
  preCachingEngine,
  relationshipEngine,
  timelineEngine,
  missingDataDetector,
  aiService
};