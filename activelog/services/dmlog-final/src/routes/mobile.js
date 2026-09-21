import express from 'express';

const router = express.Router();

// GET /api/mobile/sync - Get sync data for mobile app
router.get('/sync', async (req, res) => {
  try {
    const userId = req.user.id;
    const lastSync = req.query.last_sync;
    
    // Get updated data since last sync
    const syncData = {
      campaigns: [], // Would fetch user's campaigns updated since lastSync
      characters: [], // Would fetch user's characters updated since lastSync
      sessions: [], // Would fetch recent session data
      timestamp: new Date().toISOString()
    };
    
    res.json(syncData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/mobile/sync - Upload changes from mobile
router.post('/sync', async (req, res) => {
  try {
    const { changes } = req.body;
    
    // Process mobile changes
    const results = {
      processed: 0,
      errors: []
    };
    
    // Apply changes to database
    // This would handle conflict resolution, etc.
    
    res.json(results);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/mobile/offline-data - Get essential data for offline mode
router.get('/offline-data', async (req, res) => {
  try {
    const userId = req.user.id;
    
    const offlineData = {
      user_campaigns: [], // Essential campaign data
      user_characters: [], // Essential character data
      spell_database: [], // Spell reference data
      rules_reference: [], // Basic rules data
      dice_presets: [] // Common dice combinations
    };
    
    res.json(offlineData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;