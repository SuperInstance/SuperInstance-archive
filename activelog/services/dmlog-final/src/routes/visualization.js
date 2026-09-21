import express from 'express';

const router = express.Router();

// GET /api/visualization/battlemap - Generate battle map
router.get('/battlemap', async (req, res) => {
  try {
    const { visualization } = req.app.locals.services;
    const mapData = await visualization.createBattleMap(req.query);
    res.json(mapData);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/visualization/dice - Render dice animation
router.post('/dice', async (req, res) => {
  try {
    const { visualization } = req.app.locals.services;
    const diceRender = await visualization.renderDice(req.body);
    res.json(diceRender);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/visualization/spell - Render spell effect
router.post('/spell', async (req, res) => {
  try {
    const { visualization } = req.app.locals.services;
    const spellEffect = await visualization.renderSpellEffect(req.body);
    res.json(spellEffect);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

export default router;