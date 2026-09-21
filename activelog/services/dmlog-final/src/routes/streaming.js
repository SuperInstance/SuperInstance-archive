import express from 'express';

const router = express.Router();

// GET /api/streaming/overlays/:streamId - Get stream overlays
router.get('/overlays/:streamId', async (req, res) => {
  try {
    const { streaming } = req.app.locals.services;
    const overlays = streaming.getStreamOverlays(req.params.streamId);
    res.json(overlays);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/streaming/overlays - Create overlay
router.post('/overlays', async (req, res) => {
  try {
    const { streaming } = req.app.locals.services;
    const overlay = await streaming.createOverlay(req.body.streamId, req.body.config);
    res.status(201).json(overlay);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// PUT /api/streaming/overlays/:streamId - Update overlay
router.put('/overlays/:streamId', async (req, res) => {
  try {
    const { streaming } = req.app.locals.services;
    const overlay = await streaming.updateOverlay(req.params.streamId, req.body);
    res.json(overlay);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/streaming/clips - Generate clip
router.post('/clips', async (req, res) => {
  try {
    const { streaming } = req.app.locals.services;
    const clip = await streaming.generateClip(req.body.streamId, req.body.duration);
    res.json(clip);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

export default router;