/**
 * PlayerLog Empire Game Server
 * Main server entry point with Express and Socket.IO
 */

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const path = require('path');
const winston = require('winston');

// Game modules
const GameSessionManager = require('./multiplayer/GameSessionManager');
const PlayerManager = require('./players/PlayerManager');
const EconomyEngine = require('./economy/EconomyEngine').EconomyEngine;
const CompanyManager = require('./companies/CompanyManager').CompanyManager;

// Configuration
const PORT = process.env.PORT || 8371;
const NODE_ENV = process.env.NODE_ENV || 'development';

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/empire-game.log' })
  ]
});

// Express app setup
const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(helmet());
app.use(compression());
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Static files
app.use(express.static(path.join(__dirname, '../public')));

// Game managers
const gameSessionManager = new GameSessionManager();
const playerManager = new PlayerManager();
let economyEngine = null;
let companyManager = null;

// Initialize game systems
function initializeGameSystems() {
  economyEngine = new EconomyEngine('adult'); // Default difficulty
  companyManager = new CompanyManager(economyEngine);
  
  economyEngine.initialize();
  
  logger.info('🎮 Game systems initialized');
}

// REST API Routes

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT
  });
});

// Game session endpoints
app.post('/api/sessions', async (req, res) => {
  try {
    const { name, mode, difficulty, maxPlayers, password } = req.body;
    
    const session = await gameSessionManager.createSession({
      name,
      mode,
      difficulty: difficulty || 'adult',
      maxPlayers: maxPlayers || 4,
      password
    });
    
    logger.info(`🎮 Created game session: ${session.id}`);
    res.json(session);
  } catch (error) {
    logger.error('Failed to create session:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/sessions', (req, res) => {
  try {
    const sessions = gameSessionManager.getActiveSessions();
    res.json(sessions);
  } catch (error) {
    logger.error('Failed to get sessions:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/sessions/:id', (req, res) => {
  try {
    const session = gameSessionManager.getSession(req.params.id);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }
    res.json(session);
  } catch (error) {
    logger.error('Failed to get session:', error);
    res.status(500).json({ error: error.message });
  }
});

// Player endpoints
app.post('/api/players', async (req, res) => {
  try {
    const { name, email, difficulty } = req.body;
    
    const player = await playerManager.createPlayer({
      name,
      email,
      level: difficulty || 'adult'
    });
    
    logger.info(`👤 Created player: ${player.name}`);
    res.json(player);
  } catch (error) {
    logger.error('Failed to create player:', error);
    res.status(500).json({ error: error.message });
  }
});

// Company endpoints
app.get('/api/companies', (req, res) => {
  try {
    const companies = companyManager.getAllCompanies();
    res.json(companies);
  } catch (error) {
    logger.error('Failed to get companies:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/companies/:id/valuation', (req, res) => {
  try {
    const valuation = companyManager.calculateValuation(req.params.id);
    res.json(valuation);
  } catch (error) {
    logger.error('Failed to calculate valuation:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/acquisitions/offer', async (req, res) => {
  try {
    const { buyerId, targetCompanyId, offerPrice, offerType, terms } = req.body;
    
    const offer = companyManager.makeAcquisitionOffer(
      buyerId,
      targetCompanyId,
      offerPrice,
      offerType,
      terms
    );
    
    logger.info(`💰 Acquisition offer made: ${offer.id}`);
    res.json(offer);
  } catch (error) {
    logger.error('Failed to make acquisition offer:', error);
    res.status(500).json({ error: error.message });
  }
});

// Economy endpoints
app.get('/api/economy', (req, res) => {
  try {
    const state = economyEngine.getState();
    res.json(state);
  } catch (error) {
    logger.error('Failed to get economy state:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/economy/forecast/:industry', (req, res) => {
  try {
    const { industry } = req.params;
    const months = parseInt(req.query.months) || 12;
    
    const forecast = economyEngine.getMarketForecast(industry, months);
    res.json(forecast);
  } catch (error) {
    logger.error('Failed to get market forecast:', error);
    res.status(500).json({ error: error.message });
  }
});

// Socket.IO real-time communication
io.on('connection', (socket) => {
  logger.info(`🔌 Client connected: ${socket.id}`);
  
  // Join game session
  socket.on('join_session', async (data) => {
    try {
      const { sessionId, playerId, password } = data;
      
      const success = await gameSessionManager.addPlayerToSession(sessionId, playerId, password);
      
      if (success) {
        socket.join(sessionId);
        socket.sessionId = sessionId;
        socket.playerId = playerId;
        
        // Send current game state
        const session = gameSessionManager.getSession(sessionId);
        socket.emit('session_joined', session);
        
        // Notify other players
        socket.to(sessionId).emit('player_joined', { playerId, socketId: socket.id });
        
        logger.info(`👤 Player ${playerId} joined session ${sessionId}`);
      } else {
        socket.emit('join_failed', { error: 'Failed to join session' });
      }
    } catch (error) {
      logger.error('Failed to join session:', error);
      socket.emit('join_failed', { error: error.message });
    }
  });
  
  // Leave game session
  socket.on('leave_session', () => {
    if (socket.sessionId && socket.playerId) {
      socket.leave(socket.sessionId);
      socket.to(socket.sessionId).emit('player_left', { playerId: socket.playerId });
      
      logger.info(`👤 Player ${socket.playerId} left session ${socket.sessionId}`);
      
      socket.sessionId = null;
      socket.playerId = null;
    }
  });
  
  // Game actions
  socket.on('roll_dice', async (data) => {
    try {
      const { sessionId, playerId } = data;
      
      if (socket.sessionId !== sessionId || socket.playerId !== playerId) {
        socket.emit('error', { message: 'Invalid session or player' });
        return;
      }
      
      const session = gameSessionManager.getSession(sessionId);
      if (!session) {
        socket.emit('error', { message: 'Session not found' });
        return;
      }
      
      const gameEngine = session.gameEngine;
      if (!gameEngine) {
        socket.emit('error', { message: 'Game not started' });
        return;
      }
      
      const result = await gameEngine.rollDice(playerId);
      
      // Broadcast dice roll to all players in session
      io.to(sessionId).emit('dice_rolled', {
        playerId,
        ...result,
        timestamp: Date.now()
      });
      
      logger.info(`🎲 Player ${playerId} rolled dice: ${result.dice.join(', ')}`);
    } catch (error) {
      logger.error('Failed to roll dice:', error);
      socket.emit('error', { message: error.message });
    }
  });
  
  // Property purchase
  socket.on('purchase_property', async (data) => {
    try {
      const { sessionId, playerId, propertyId, financing } = data;
      
      // Process property purchase
      const result = await gameSessionManager.processPropertyPurchase(
        sessionId, 
        playerId, 
        propertyId, 
        financing
      );
      
      // Broadcast to session
      io.to(sessionId).emit('property_purchased', {
        playerId,
        propertyId,
        result,
        timestamp: Date.now()
      });
      
      logger.info(`🏠 Player ${playerId} purchased property ${propertyId}`);
    } catch (error) {
      logger.error('Failed to purchase property:', error);
      socket.emit('error', { message: error.message });
    }
  });
  
  // Company creation
  socket.on('create_company', async (data) => {
    try {
      const { playerId, name, industry, type, initialCapital } = data;
      
      const company = companyManager.createCompany(
        playerId,
        name,
        industry,
        type,
        initialCapital
      );
      
      // Broadcast to session if player is in one
      if (socket.sessionId) {
        io.to(socket.sessionId).emit('company_created', {
          playerId,
          company,
          timestamp: Date.now()
        });
      }
      
      socket.emit('company_created', { company });
      
      logger.info(`🏢 Player ${playerId} created company: ${name}`);
    } catch (error) {
      logger.error('Failed to create company:', error);
      socket.emit('error', { message: error.message });
    }
  });
  
  // Acquisition offer
  socket.on('acquisition_offer', async (data) => {
    try {
      const { buyerId, targetCompanyId, offerPrice, offerType, terms } = data;
      
      const offer = companyManager.makeAcquisitionOffer(
        buyerId,
        targetCompanyId,
        offerPrice,
        offerType,
        terms
      );
      
      // Find target company owner and notify
      const targetCompany = companyManager.getCompany(targetCompanyId);
      if (targetCompany) {
        // Broadcast to all players for transparency
        if (socket.sessionId) {
          io.to(socket.sessionId).emit('acquisition_offer_made', {
            offer,
            targetCompany,
            timestamp: Date.now()
          });
        }
      }
      
      logger.info(`💰 Acquisition offer made: ${offer.id}`);
    } catch (error) {
      logger.error('Failed to make acquisition offer:', error);
      socket.emit('error', { message: error.message });
    }
  });
  
  // Acquisition response
  socket.on('acquisition_response', async (data) => {
    try {
      const { offerId, response, counterOffer } = data;
      
      companyManager.respondToAcquisitionOffer(offerId, response, counterOffer);
      
      // Broadcast response to session
      if (socket.sessionId) {
        io.to(socket.sessionId).emit('acquisition_response', {
          offerId,
          response,
          counterOffer,
          responderId: socket.playerId,
          timestamp: Date.now()
        });
      }
      
      logger.info(`📝 Acquisition response: ${response} for offer ${offerId}`);
    } catch (error) {
      logger.error('Failed to respond to acquisition offer:', error);
      socket.emit('error', { message: error.message });
    }
  });
  
  // End turn
  socket.on('end_turn', async (data) => {
    try {
      const { sessionId, playerId } = data;
      
      const session = gameSessionManager.getSession(sessionId);
      if (!session || !session.gameEngine) {
        socket.emit('error', { message: 'Invalid session or game not started' });
        return;
      }
      
      const currentPlayer = session.gameEngine.getCurrentPlayer();
      if (!currentPlayer || currentPlayer.id !== playerId) {
        socket.emit('error', { message: 'Not your turn' });
        return;
      }
      
      session.gameEngine.endTurn();
      
      // Broadcast turn ended
      io.to(sessionId).emit('turn_ended', {
        playerId,
        nextPlayer: session.gameEngine.getCurrentPlayer(),
        timestamp: Date.now()
      });
      
      logger.info(`⏭️ Player ${playerId} ended turn`);
    } catch (error) {
      logger.error('Failed to end turn:', error);
      socket.emit('error', { message: error.message });
    }
  });
  
  // Chat messages
  socket.on('chat_message', (data) => {
    try {
      const { sessionId, playerId, message } = data;
      
      if (socket.sessionId === sessionId) {
        // Broadcast chat message to session
        io.to(sessionId).emit('chat_message', {
          playerId,
          message,
          timestamp: Date.now()
        });
      }
    } catch (error) {
      logger.error('Failed to send chat message:', error);
    }
  });
  
  // Disconnect handling
  socket.on('disconnect', () => {
    if (socket.sessionId && socket.playerId) {
      socket.to(socket.sessionId).emit('player_disconnected', { 
        playerId: socket.playerId,
        socketId: socket.id 
      });
      
      // Mark player as offline but keep in session for reconnection
      gameSessionManager.markPlayerOffline(socket.sessionId, socket.playerId);
      
      logger.info(`👤 Player ${socket.playerId} disconnected from session ${socket.sessionId}`);
    }
    
    logger.info(`🔌 Client disconnected: ${socket.id}`);
  });
});

// Economy engine event handlers
if (economyEngine) {
  economyEngine.on('economy:updated', (state) => {
    // Broadcast economy updates to all connected clients
    io.emit('economy_updated', {
      state,
      timestamp: Date.now()
    });
  });
  
  economyEngine.on('economic:shock', (event) => {
    // Broadcast economic shock events
    io.emit('economic_shock', {
      ...event,
      timestamp: Date.now()
    });
    
    logger.warn(`⚡ Economic shock: ${event.type} (${(event.intensity * 100).toFixed(1)}%)`);
  });
}

// Company manager event handlers
if (companyManager) {
  companyManager.on('acquisition:completed', (event) => {
    // Broadcast completed acquisitions
    io.emit('acquisition_completed', {
      ...event,
      timestamp: Date.now()
    });
    
    logger.info(`✅ Acquisition completed: ${event.company.name}`);
  });
}

// Error handling
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('📴 Shutting down server...');
  
  // Stop economy engine
  if (economyEngine) {
    economyEngine.stop();
  }
  
  // Close all game sessions
  gameSessionManager.closeAllSessions();
  
  server.close(() => {
    logger.info('Server shut down complete');
    process.exit(0);
  });
});

// Start server
function startServer() {
  try {
    initializeGameSystems();
    
    server.listen(PORT, () => {
      logger.info(`🚀 PlayerLog Empire Game Server started on port ${PORT}`);
      logger.info(`🌍 Environment: ${NODE_ENV}`);
      logger.info(`🎮 Game systems ready`);
      
      console.log(`
╔══════════════════════════════════════════╗
║         PlayerLog Empire Game            ║
║                                          ║
║  🏢 Business Empire Building Game        ║
║  🎯 Monopoly + Cashflow Hybrid           ║
║  💼 Company Acquisitions & IPOs          ║
║  🏭 Equipment & Digital Transformation   ║
║  👨‍🎓 Career Paths & Education             ║
║                                          ║
║  Port: ${PORT.toString().padEnd(31)} ║
║  Status: READY                           ║
╚══════════════════════════════════════════╝
      `);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
startServer();

module.exports = { app, server, io };