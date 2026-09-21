const express = require('express');
const router = express.Router();
const { requireAuth } = require('../utils/auth');
const { getActiveCollaborators } = require('../services/collaboration');

router.use(requireAuth);

// Get active collaborators for a world
router.get('/:worldId/collaborators', async (req, res) => {
  try {
    const { worldId } = req.params;
    const collaborators = getActiveCollaborators(worldId);
    
    res.json({
      success: true,
      data: collaborators
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;