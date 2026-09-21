import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { createServer } from 'http';
import { Server } from 'socket.io';

import { ageDetector } from './age-detection/age-detector';
import { uiTransformer } from './ui-transformation/transformer';
import { vocabularyAdapter } from './vocabulary/vocabulary-adapter';
import { iconSystem } from './icons/icon-system';
import { complexityManager } from './complexity/complexity-manager';
import { workspaceManager } from './workspace/workspace-manager';
import { safeBrowser } from './browser/safe-browser';

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.CLIENT_URL || "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 8209;

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'dual-interface', timestamp: new Date().toISOString() });
});

// Age Detection Routes
app.post('/api/age-detection/detect', async (req, res) => {
  try {
    const { userId, profile } = req.body;
    const result = await ageDetector.detectAge(userId, profile);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/age-detection/update-behavioral', async (req, res) => {
  try {
    const { userId, behavioralData } = req.body;
    await ageDetector.updateBehavioralData(userId, behavioralData);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/age-detection/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const result = ageDetector.getAgeResult(userId);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// UI Transformation Routes
app.post('/api/ui-transformation/configure', async (req, res) => {
  try {
    const { userId, ageResult, preferences } = req.body;
    const config = uiTransformer.createConfiguration(userId, ageResult, preferences);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/ui-transformation/transform-element', (req, res) => {
  try {
    const { userId, element } = req.body;
    const transformed = uiTransformer.transformElement(userId, element);
    res.json({ success: true, element: transformed });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/ui-transformation/transform-page', (req, res) => {
  try {
    const { userId, page } = req.body;
    const transformed = uiTransformer.transformPage(userId, page);
    res.json({ success: true, page: transformed });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/ui-transformation/css/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const css = uiTransformer.generateCSS(userId);
    res.setHeader('Content-Type', 'text/css');
    res.send(css);
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Vocabulary Adaptation Routes
app.post('/api/vocabulary/create-profile', (req, res) => {
  try {
    const { userId, ageGroup, options } = req.body;
    const profile = vocabularyAdapter.createProfile(userId, ageGroup, options);
    res.json({ success: true, profile });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/vocabulary/adapt-text', async (req, res) => {
  try {
    const { userId, text, domain } = req.body;
    const adaptation = await vocabularyAdapter.adaptText(userId, text, domain);
    res.json({ success: true, adaptation });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/vocabulary/adapt-word', (req, res) => {
  try {
    const { userId, word, context } = req.body;
    const adapted = vocabularyAdapter.adaptWord(userId, word, context);
    res.json({ success: true, adaptedWord: adapted });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/vocabulary/assess-readability', (req, res) => {
  try {
    const { text } = req.body;
    const assessment = vocabularyAdapter.assessReadability(text);
    res.json({ success: true, assessment });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Icon System Routes
app.post('/api/icons/configure', (req, res) => {
  try {
    const { userId, ageGroup, preferences } = req.body;
    const config = iconSystem.createConfiguration(userId, ageGroup, preferences);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/icons/get-icon', async (req, res) => {
  try {
    const { userId, request } = req.body;
    const icon = await iconSystem.getIcon(userId, request);
    res.json({ success: true, icon });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/icons/grid/:userId/:category', (req, res) => {
  try {
    const { userId, category } = req.params;
    const grid = iconSystem.generateIconGrid(userId, category as any);
    res.json({ success: true, grid });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/icons/suggest', (req, res) => {
  try {
    const { userId, concept } = req.body;
    const suggestions = iconSystem.suggestIcons(userId, concept);
    res.json({ success: true, suggestions });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Complexity Management Routes
app.post('/api/complexity/configure', (req, res) => {
  try {
    const { userId, ageGroup, preferences } = req.body;
    const config = complexityManager.createConfiguration(userId, ageGroup, preferences);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/complexity/adjust-global', (req, res) => {
  try {
    const { userId, newLevel, reason } = req.body;
    const success = complexityManager.adjustGlobalComplexity(userId, newLevel, reason);
    res.json({ success });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/complexity/adjust-feature', (req, res) => {
  try {
    const { userId, featureId, newLevel, reason } = req.body;
    const success = complexityManager.adjustFeatureComplexity(userId, featureId, newLevel, reason);
    res.json({ success });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/complexity/features/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const features = complexityManager.getAvailableFeatures(userId);
    res.json({ success: true, features });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/complexity/suggestions/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const suggestions = complexityManager.suggestComplexityAdjustment(userId);
    res.json({ success: true, suggestions });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/complexity/record-interaction', (req, res) => {
  try {
    const { userId, featureId, success, duration, errorCount } = req.body;
    complexityManager.recordInteraction(userId, featureId, success, duration, errorCount);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Workspace Management Routes
app.post('/api/workspace/create', async (req, res) => {
  try {
    const { userId, type, options } = req.body;
    const workspace = await workspaceManager.createWorkspace(userId, type, options);
    res.json({ success: true, workspace });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/workspace/start-session', async (req, res) => {
  try {
    const { userId, workspaceId } = req.body;
    const session = await workspaceManager.startSession(userId, workspaceId);
    res.json({ success: true, session });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/workspace/end-session', async (req, res) => {
  try {
    const { sessionId } = req.body;
    await workspaceManager.endSession(sessionId);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/workspace/user/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const workspaces = workspaceManager.getWorkspacesByUser(userId);
    res.json({ success: true, workspaces });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/workspace/isolate', (req, res) => {
  try {
    const { workspaceId, reason } = req.body;
    const success = workspaceManager.isolateWorkspace(workspaceId, reason);
    res.json({ success });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.get('/api/workspace/report/:workspaceId/:period', (req, res) => {
  try {
    const { workspaceId, period } = req.params;
    const report = workspaceManager.generateReport(workspaceId, period as any);
    res.json({ success: true, report });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Safe Browser Routes
app.post('/api/browser/configure', (req, res) => {
  try {
    const { userId, ageGroup, preferences } = req.body;
    const config = safeBrowser.createConfiguration(userId, ageGroup, preferences);
    res.json({ success: true, config });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/start-session', async (req, res) => {
  try {
    const { userId } = req.body;
    const session = await safeBrowser.startBrowsingSession(userId);
    res.json({ success: true, session });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/navigate', async (req, res) => {
  try {
    const { sessionId, url } = req.body;
    const result = await safeBrowser.navigateToUrl(sessionId, url);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/search', async (req, res) => {
  try {
    const { sessionId, query, searchEngine } = req.body;
    const result = await safeBrowser.performSearch(sessionId, query, searchEngine);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/download', async (req, res) => {
  try {
    const { sessionId, url, filename } = req.body;
    const result = await safeBrowser.downloadFile(sessionId, url, filename);
    res.json({ success: true, result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/end-session', (req, res) => {
  try {
    const { sessionId } = req.body;
    const report = safeBrowser.endBrowsingSession(sessionId);
    res.json({ success: true, report });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/request-approval', async (req, res) => {
  try {
    const { userId, url, reason } = req.body;
    const approved = await safeBrowser.requestSiteApproval(userId, url, reason);
    res.json({ success: true, approved });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

app.post('/api/browser/add-project', (req, res) => {
  try {
    const { userId, project } = req.body;
    const projectId = safeBrowser.addEducationalProject(userId, project);
    res.json({ success: true, projectId });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// WebSocket handling for real-time features
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('join-user-room', (userId) => {
    socket.join(`user:${userId}`);
  });

  socket.on('ui-transform-request', async (data) => {
    try {
      const { userId, element } = data;
      const transformed = uiTransformer.transformElement(userId, element);
      socket.emit('ui-transform-result', { success: true, element: transformed });
    } catch (error) {
      socket.emit('ui-transform-result', { success: false, error: error.message });
    }
  });

  socket.on('complexity-adjustment', (data) => {
    try {
      const { userId, featureId, newLevel, reason } = data;
      const success = complexityManager.adjustFeatureComplexity(userId, featureId, newLevel, reason);
      socket.emit('complexity-adjustment-result', { success });
      
      // Notify all connected clients for this user
      io.to(`user:${userId}`).emit('complexity-changed', { featureId, newLevel });
    } catch (error) {
      socket.emit('complexity-adjustment-result', { success: false, error: error.message });
    }
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Event listeners for system events
ageDetector.on('ageDetected', (data) => {
  io.to(`user:${data.userId}`).emit('age-detected', data.result);
});

uiTransformer.on('transitionStart', (data) => {
  io.to(`user:${data.userId}`).emit('ui-transition-start', data);
});

uiTransformer.on('transitionComplete', (data) => {
  io.to(`user:${data.userId}`).emit('ui-transition-complete', data);
});

vocabularyAdapter.on('textAdapted', (data) => {
  io.to(`user:${data.userId}`).emit('text-adapted', data.adaptation);
});

complexityManager.on('complexityAdjusted', (data) => {
  io.to(`user:${data.userId}`).emit('complexity-adjusted', data);
});

workspaceManager.on('sessionStarted', (data) => {
  io.to(`user:${data.userId}`).emit('workspace-session-started', data);
});

workspaceManager.on('violationReported', (data) => {
  const session = workspaceManager.getActiveSession(data.sessionId, data.sessionId); // Would need proper lookup
  if (session) {
    io.to(`user:${session.userId}`).emit('workspace-violation', data);
  }
});

safeBrowser.on('sessionStarted', (data) => {
  io.to(`user:${data.userId}`).emit('browser-session-started', data);
});

safeBrowser.on('contentBlocked', (data) => {
  // Notify parent if applicable
  io.emit('content-blocked', data);
});

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
  console.log(`Dual Interface System running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log('Available services:');
  console.log('- Age Detection');
  console.log('- UI Transformation');
  console.log('- Vocabulary Adaptation');
  console.log('- Icon System');
  console.log('- Complexity Management');
  console.log('- Workspace Management');
  console.log('- Safe Browser');
});

export default app;