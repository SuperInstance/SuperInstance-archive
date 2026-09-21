import express from 'express';
import mongoose from 'mongoose';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import path from 'path';

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/campaigns/');
  },
  filename: (req, file, cb) => {
    const uniqueId = uuidv4();
    cb(null, `${uniqueId}_${file.originalname}`);
  }
});

const upload = multer({ 
  storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB limit
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['image/', 'audio/', 'application/pdf'];
    if (allowedTypes.some(type => file.mimetype.startsWith(type))) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'), false);
    }
  }
});

// Campaign schema (would be in separate model file in production)
const CampaignSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  dmId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  players: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  characters: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Character' }],
  sessions: [{
    number: Number,
    title: String,
    date: Date,
    summary: String,
    notes: String,
    battleMaps: [String],
    audio: String,
    duration: Number,
    attendance: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }]
  }],
  settings: {
    system: { type: String, default: 'dnd5e' },
    level: { type: Number, default: 1 },
    xpType: { type: String, enum: ['milestone', 'xp'], default: 'milestone' },
    restType: { type: String, enum: ['normal', 'gritty', 'epic'], default: 'normal' },
    variant_rules: [String]
  },
  assets: [{
    type: { type: String, enum: ['image', 'audio', 'pdf', 'map'] },
    filename: String,
    originalName: String,
    path: String,
    size: Number,
    uploadedAt: { type: Date, default: Date.now },
    tags: [String]
  }],
  sharing: {
    isPublic: { type: Boolean, default: false },
    shareId: String,
    allowComments: { type: Boolean, default: true },
    allowForks: { type: Boolean, default: false },
    license: { type: String, enum: ['cc0', 'cc-by', 'cc-by-sa', 'proprietary'], default: 'proprietary' }
  },
  monetization: {
    isPaid: { type: Boolean, default: false },
    price: Number,
    subscriptionTiers: [{
      name: String,
      price: Number,
      benefits: [String]
    }],
    donationGoal: {
      target: Number,
      current: { type: Number, default: 0 },
      description: String
    }
  },
  stats: {
    views: { type: Number, default: 0 },
    likes: { type: Number, default: 0 },
    forks: { type: Number, default: 0 },
    subscribers: { type: Number, default: 0 }
  }
}, {
  timestamps: true
});

const Campaign = mongoose.models.Campaign || mongoose.model('Campaign', CampaignSchema);

// GET /api/campaigns - List campaigns
router.get('/', async (req, res) => {
  try {
    const { 
      page = 1, 
      limit = 10, 
      search, 
      system, 
      public_only,
      sort = 'updatedAt'
    } = req.query;

    const userId = req.user.id;
    const query = {};

    // Filter by user's campaigns or public campaigns
    if (public_only === 'true') {
      query['sharing.isPublic'] = true;
    } else {
      query.$or = [
        { dmId: userId },
        { players: userId },
        { 'sharing.isPublic': true }
      ];
    }

    // Search filter
    if (search) {
      query.$or = [
        { name: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } }
      ];
    }

    // System filter
    if (system) {
      query['settings.system'] = system;
    }

    const options = {
      page: parseInt(page),
      limit: parseInt(limit),
      sort: { [sort]: -1 },
      populate: ['dmId', 'players', 'characters']
    };

    const campaigns = await Campaign.paginate(query, options);
    res.json(campaigns);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/campaigns/:id - Get specific campaign
router.get('/:id', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id)
      .populate('dmId', 'username avatar')
      .populate('players', 'username avatar')
      .populate('characters', 'name class level');

    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    // Check permissions
    const userId = req.user.id;
    const hasAccess = campaign.dmId._id.toString() === userId ||
                     campaign.players.some(p => p._id.toString() === userId) ||
                     campaign.sharing.isPublic;

    if (!hasAccess) {
      return res.status(403).json({ error: 'Access denied' });
    }

    // Increment view count if public
    if (campaign.sharing.isPublic) {
      await Campaign.findByIdAndUpdate(req.params.id, {
        $inc: { 'stats.views': 1 }
      });
    }

    res.json(campaign);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/campaigns - Create new campaign
router.post('/', async (req, res) => {
  try {
    const campaignData = {
      ...req.body,
      dmId: req.user.id,
      sharing: {
        ...req.body.sharing,
        shareId: uuidv4()
      }
    };

    const campaign = new Campaign(campaignData);
    await campaign.save();

    await campaign.populate('dmId', 'username avatar');
    res.status(201).json(campaign);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// PUT /api/campaigns/:id - Update campaign
router.put('/:id', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    // Check if user is DM
    if (campaign.dmId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the DM can update this campaign' });
    }

    const updatedCampaign = await Campaign.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    ).populate('dmId players characters');

    res.json(updatedCampaign);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// DELETE /api/campaigns/:id - Delete campaign
router.delete('/:id', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    if (campaign.dmId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the DM can delete this campaign' });
    }

    await Campaign.findByIdAndDelete(req.params.id);
    res.json({ message: 'Campaign deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/sessions - Add session
router.post('/:id/sessions', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    if (campaign.dmId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the DM can add sessions' });
    }

    const sessionData = {
      ...req.body,
      number: campaign.sessions.length + 1,
      date: new Date()
    };

    campaign.sessions.push(sessionData);
    await campaign.save();

    // Get services from app.locals
    const { logger } = req.app.locals.services;
    logger.info(`New session added to campaign ${campaign.name}`);

    res.status(201).json(sessionData);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// PUT /api/campaigns/:id/sessions/:sessionId - Update session
router.put('/:id/sessions/:sessionId', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    if (campaign.dmId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the DM can update sessions' });
    }

    const session = campaign.sessions.id(req.params.sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    Object.assign(session, req.body);
    await campaign.save();

    res.json(session);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/assets - Upload campaign assets
router.post('/:id/assets', upload.array('files', 10), async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    // Check if user has permission (DM or player)
    const userId = req.user.id;
    const hasPermission = campaign.dmId.toString() === userId ||
                         campaign.players.some(p => p.toString() === userId);

    if (!hasPermission) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const uploadedAssets = req.files.map(file => ({
      type: file.mimetype.startsWith('image/') ? 'image' :
            file.mimetype.startsWith('audio/') ? 'audio' :
            file.mimetype === 'application/pdf' ? 'pdf' : 'other',
      filename: file.filename,
      originalName: file.originalname,
      path: file.path,
      size: file.size,
      tags: req.body.tags ? req.body.tags.split(',') : []
    }));

    campaign.assets.push(...uploadedAssets);
    await campaign.save();

    res.status(201).json(uploadedAssets);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/join - Join campaign
router.post('/:id/join', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    const userId = req.user.id;

    // Check if already a player or DM
    if (campaign.dmId.toString() === userId || 
        campaign.players.includes(userId)) {
      return res.status(400).json({ error: 'Already part of this campaign' });
    }

    campaign.players.push(userId);
    await campaign.save();

    await campaign.populate('players', 'username avatar');
    res.json({ message: 'Successfully joined campaign', players: campaign.players });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/leave - Leave campaign
router.post('/:id/leave', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    const userId = req.user.id;

    if (campaign.dmId.toString() === userId) {
      return res.status(400).json({ error: 'DM cannot leave their own campaign' });
    }

    campaign.players = campaign.players.filter(p => p.toString() !== userId);
    await campaign.save();

    res.json({ message: 'Successfully left campaign' });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/share - Share campaign publicly
router.post('/:id/share', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    if (campaign.dmId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the DM can share this campaign' });
    }

    const { isPublic, allowComments, allowForks, license } = req.body;

    campaign.sharing = {
      ...campaign.sharing,
      isPublic,
      allowComments,
      allowForks,
      license
    };

    await campaign.save();

    // Get services from app.locals
    const { logger } = req.app.locals.services;
    logger.info(`Campaign ${campaign.name} sharing updated: public=${isPublic}`);

    res.json({ 
      message: 'Campaign sharing settings updated',
      shareUrl: isPublic ? `${process.env.FRONTEND_URL}/campaign/${campaign.sharing.shareId}` : null
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/fork - Fork a public campaign
router.post('/:id/fork', async (req, res) => {
  try {
    const originalCampaign = await Campaign.findById(req.params.id);
    
    if (!originalCampaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    if (!originalCampaign.sharing.isPublic || !originalCampaign.sharing.allowForks) {
      return res.status(403).json({ error: 'Campaign cannot be forked' });
    }

    // Create forked campaign
    const forkedCampaign = new Campaign({
      ...originalCampaign.toObject(),
      _id: undefined,
      name: `${originalCampaign.name} (Fork)`,
      dmId: req.user.id,
      players: [],
      characters: [],
      sessions: [], // Start with empty sessions
      sharing: {
        isPublic: false,
        shareId: uuidv4(),
        allowComments: true,
        allowForks: true,
        license: originalCampaign.sharing.license
      },
      stats: {
        views: 0,
        likes: 0,
        forks: 0,
        subscribers: 0
      },
      forkedFrom: originalCampaign._id
    });

    await forkedCampaign.save();

    // Increment fork count on original
    await Campaign.findByIdAndUpdate(req.params.id, {
      $inc: { 'stats.forks': 1 }
    });

    await forkedCampaign.populate('dmId', 'username avatar');
    res.status(201).json(forkedCampaign);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/campaigns/:id/like - Like/unlike campaign
router.post('/:id/like', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id);
    
    if (!campaign || !campaign.sharing.isPublic) {
      return res.status(404).json({ error: 'Campaign not found or not public' });
    }

    const userId = req.user.id;
    
    // Check if user already liked (this would be in a separate likes collection)
    // For now, just increment/decrement
    const action = req.body.like ? 1 : -1;
    await Campaign.findByIdAndUpdate(req.params.id, {
      $inc: { 'stats.likes': action }
    });

    res.json({ message: req.body.like ? 'Campaign liked' : 'Campaign unliked' });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/campaigns/:id/export - Export campaign data
router.get('/:id/export', async (req, res) => {
  try {
    const campaign = await Campaign.findById(req.params.id)
      .populate('dmId players characters');
    
    if (!campaign) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    // Check permissions
    const userId = req.user.id;
    const hasAccess = campaign.dmId._id.toString() === userId ||
                     campaign.players.some(p => p._id.toString() === userId);

    if (!hasAccess) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const { format = 'json' } = req.query;

    if (format === 'pdf') {
      // Use backup service to generate PDF
      const { backup } = req.app.locals.services;
      const pdf = await backup.exportCampaignToPDF(campaign);
      
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename="${campaign.name}.pdf"`);
      res.send(pdf.buffer);
    } else {
      // JSON export
      const exportData = {
        campaign: campaign.toObject(),
        exported_at: new Date().toISOString(),
        format: 'dmlog_v2',
        version: '2.0.0'
      };

      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', `attachment; filename="${campaign.name}.json"`);
      res.json(exportData);
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;