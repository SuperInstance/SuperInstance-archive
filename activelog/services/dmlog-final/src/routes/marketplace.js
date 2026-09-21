import express from 'express';

const router = express.Router();

// GET /api/marketplace - Browse marketplace
router.get('/', async (req, res) => {
  try {
    const { marketplace } = req.app.locals.services;
    const {
      page = 1,
      limit = 20,
      category,
      search,
      sort = 'popularity',
      minPrice,
      maxPrice,
      printable = 'true'
    } = req.query;

    const filters = {
      category,
      search,
      minPrice: minPrice ? parseFloat(minPrice) : null,
      maxPrice: maxPrice ? parseFloat(maxPrice) : null,
      printable: printable === 'true'
    };

    const items = await marketplace.browseItems(filters, {
      page: parseInt(page),
      limit: parseInt(limit),
      sort
    });

    res.json(items);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/marketplace/:id - Get marketplace item
router.get('/:id', async (req, res) => {
  try {
    const { marketplace } = req.app.locals.services;
    const item = await marketplace.getItem(req.params.id);
    
    if (!item) {
      return res.status(404).json({ error: 'Item not found' });
    }

    res.json(item);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/marketplace - Create marketplace item
router.post('/', async (req, res) => {
  try {
    const { marketplace } = req.app.locals.services;
    
    const itemData = {
      ...req.body,
      creatorId: req.user.id
    };

    const item = await marketplace.createItem(itemData);
    res.status(201).json(item);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/marketplace/:id/analyze - Analyze 3D model
router.post('/:id/analyze', async (req, res) => {
  try {
    const { marketplace } = req.app.locals.services;
    const analysis = await marketplace.analyzeModel(req.params.id, req.body);
    res.json(analysis);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/marketplace/:id/purchase - Purchase item
router.post('/:id/purchase', async (req, res) => {
  try {
    const { marketplace, monetization } = req.app.locals.services;
    
    const item = await marketplace.getItem(req.params.id);
    if (!item) {
      return res.status(404).json({ error: 'Item not found' });
    }

    // Process payment through monetization service
    const paymentIntent = await monetization.processMarketplacePayment(
      req.user.id,
      item.creatorId,
      req.params.id,
      item.price
    );

    res.json({ paymentIntent });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/marketplace/:id/files - Get item files (after purchase)
router.get('/:id/files', async (req, res) => {
  try {
    const { marketplace } = req.app.locals.services;
    
    // Check if user has purchased this item
    const hasPurchased = await marketplace.checkPurchase(req.user.id, req.params.id);
    if (!hasPurchased) {
      return res.status(403).json({ error: 'Purchase required to access files' });
    }

    const files = await marketplace.getItemFiles(req.params.id);
    res.json(files);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

export default router;