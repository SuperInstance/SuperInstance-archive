import express from 'express';
import mongoose from 'mongoose';
import { v4 as uuidv4 } from 'uuid';

const router = express.Router();

// Community Hub schemas
const PostSchema = new mongoose.Schema({
  title: { type: String, required: true },
  content: { type: String, required: true },
  authorId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  type: { 
    type: String, 
    enum: ['discussion', 'showcase', 'help', 'resources', 'session-report'],
    default: 'discussion'
  },
  category: {
    type: String,
    enum: ['general', 'homebrew', 'campaigns', 'characters', 'rules', 'tools', 'art'],
    default: 'general'
  },
  tags: [String],
  attachments: [{
    type: String, // image, pdf, etc.
    url: String,
    filename: String,
    size: Number
  }],
  relatedCampaign: { type: mongoose.Schema.Types.ObjectId, ref: 'Campaign' },
  relatedCharacter: { type: mongoose.Schema.Types.ObjectId, ref: 'Character' },
  stats: {
    views: { type: Number, default: 0 },
    upvotes: { type: Number, default: 0 },
    downvotes: { type: Number, default: 0 },
    comments: { type: Number, default: 0 }
  },
  isPinned: { type: Boolean, default: false },
  isFeatured: { type: Boolean, default: false },
  isLocked: { type: Boolean, default: false },
  visibility: { 
    type: String, 
    enum: ['public', 'members', 'premium'],
    default: 'public'
  }
}, {
  timestamps: true
});

const CommentSchema = new mongoose.Schema({
  postId: { type: mongoose.Schema.Types.ObjectId, ref: 'Post', required: true },
  authorId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  content: { type: String, required: true },
  parentComment: { type: mongoose.Schema.Types.ObjectId, ref: 'Comment' },
  mentions: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  attachments: [{
    type: String,
    url: String,
    filename: String
  }],
  stats: {
    upvotes: { type: Number, default: 0 },
    downvotes: { type: Number, default: 0 }
  },
  isEdited: { type: Boolean, default: false },
  editedAt: Date
}, {
  timestamps: true
});

const CommunitySchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: String,
  creatorId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  moderators: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  members: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  type: {
    type: String,
    enum: ['public', 'private', 'invite-only'],
    default: 'public'
  },
  category: {
    type: String,
    enum: ['general', 'campaign-specific', 'system-specific', 'regional', 'age-specific'],
    default: 'general'
  },
  rules: [String],
  settings: {
    allowPosts: { type: Boolean, default: true },
    requireApproval: { type: Boolean, default: false },
    allowImageUploads: { type: Boolean, default: true },
    allowFileSharing: { type: Boolean, default: true },
    maxFileSize: { type: Number, default: 10485760 } // 10MB
  },
  stats: {
    memberCount: { type: Number, default: 0 },
    postCount: { type: Number, default: 0 },
    totalActivity: { type: Number, default: 0 }
  },
  avatar: String,
  banner: String,
  inviteCode: String
}, {
  timestamps: true
});

const EventSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: String,
  organizerId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  type: {
    type: String,
    enum: ['session', 'tournament', 'workshop', 'convention', 'meetup'],
    required: true
  },
  startTime: { type: Date, required: true },
  endTime: Date,
  timezone: String,
  isRecurring: { type: Boolean, default: false },
  recurrencePattern: String,
  maxAttendees: Number,
  attendees: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  waitlist: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  location: {
    type: { type: String, enum: ['online', 'physical', 'hybrid'] },
    address: String,
    platform: String, // Discord, Roll20, etc.
    link: String
  },
  requirements: [String],
  tags: [String],
  isPublic: { type: Boolean, default: true },
  requiresApproval: { type: Boolean, default: false },
  cost: {
    amount: { type: Number, default: 0 },
    currency: { type: String, default: 'USD' }
  },
  relatedCampaign: { type: mongoose.Schema.Types.ObjectId, ref: 'Campaign' },
  communityId: { type: mongoose.Schema.Types.ObjectId, ref: 'Community' }
}, {
  timestamps: true
});

// Initialize models
const Post = mongoose.models.Post || mongoose.model('Post', PostSchema);
const Comment = mongoose.models.Comment || mongoose.model('Comment', CommentSchema);
const Community = mongoose.models.Community || mongoose.model('Community', CommunitySchema);
const Event = mongoose.models.Event || mongoose.model('Event', EventSchema);

// Posts endpoints
// GET /api/community/posts - List posts
router.get('/posts', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      category,
      type,
      search,
      tags,
      sort = 'createdAt',
      order = 'desc'
    } = req.query;

    const query = { visibility: { $in: ['public'] } };

    // Add user's member visibility if authenticated
    if (req.user) {
      query.visibility.$in.push('members');
    }

    if (category) query.category = category;
    if (type) query.type = type;
    if (search) {
      query.$or = [
        { title: { $regex: search, $options: 'i' } },
        { content: { $regex: search, $options: 'i' } }
      ];
    }
    if (tags) {
      const tagArray = Array.isArray(tags) ? tags : [tags];
      query.tags = { $in: tagArray };
    }

    const options = {
      page: parseInt(page),
      limit: parseInt(limit),
      sort: { [sort]: order === 'desc' ? -1 : 1 },
      populate: [
        { path: 'authorId', select: 'username avatar reputation' },
        { path: 'relatedCampaign', select: 'name sharing' },
        { path: 'relatedCharacter', select: 'name class level' }
      ]
    };

    const posts = await Post.paginate(query, options);
    res.json(posts);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/community/posts/:id - Get specific post
router.get('/posts/:id', async (req, res) => {
  try {
    const post = await Post.findById(req.params.id)
      .populate('authorId', 'username avatar reputation')
      .populate('relatedCampaign', 'name sharing')
      .populate('relatedCharacter', 'name class level');

    if (!post) {
      return res.status(404).json({ error: 'Post not found' });
    }

    // Check visibility permissions
    if (post.visibility === 'premium' && !req.user?.subscription?.isPremium) {
      return res.status(403).json({ error: 'Premium membership required' });
    }

    // Increment view count
    await Post.findByIdAndUpdate(req.params.id, { $inc: { 'stats.views': 1 } });

    // Get comments for this post
    const comments = await Comment.find({ postId: req.params.id, parentComment: null })
      .populate('authorId', 'username avatar reputation')
      .sort({ createdAt: -1 })
      .limit(50);

    // Get nested replies for each comment
    for (let comment of comments) {
      const replies = await Comment.find({ parentComment: comment._id })
        .populate('authorId', 'username avatar reputation')
        .sort({ createdAt: 1 })
        .limit(20);
      comment.replies = replies;
    }

    res.json({ post, comments });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/community/posts - Create new post
router.post('/posts', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const postData = {
      ...req.body,
      authorId: req.user.id
    };

    const post = new Post(postData);
    await post.save();

    await post.populate([
      { path: 'authorId', select: 'username avatar reputation' },
      { path: 'relatedCampaign', select: 'name sharing' },
      { path: 'relatedCharacter', select: 'name class level' }
    ]);

    // Broadcast new post to community
    const { io } = req.app.locals.services;
    if (io) {
      io.emit('community-post', {
        type: 'new_post',
        post: post.toObject()
      });
    }

    res.status(201).json(post);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// PUT /api/community/posts/:id - Update post
router.put('/posts/:id', async (req, res) => {
  try {
    const post = await Post.findById(req.params.id);
    
    if (!post) {
      return res.status(404).json({ error: 'Post not found' });
    }

    if (post.authorId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the author can edit this post' });
    }

    const updatedPost = await Post.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    ).populate([
      { path: 'authorId', select: 'username avatar reputation' },
      { path: 'relatedCampaign', select: 'name sharing' },
      { path: 'relatedCharacter', select: 'name class level' }
    ]);

    res.json(updatedPost);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// DELETE /api/community/posts/:id - Delete post
router.delete('/posts/:id', async (req, res) => {
  try {
    const post = await Post.findById(req.params.id);
    
    if (!post) {
      return res.status(404).json({ error: 'Post not found' });
    }

    // Check if user can delete (author or moderator)
    const canDelete = post.authorId.toString() === req.user.id || req.user.role === 'moderator';
    
    if (!canDelete) {
      return res.status(403).json({ error: 'Access denied' });
    }

    await Post.findByIdAndDelete(req.params.id);
    
    // Delete associated comments
    await Comment.deleteMany({ postId: req.params.id });

    res.json({ message: 'Post deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/community/posts/:id/vote - Vote on post
router.post('/posts/:id/vote', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const { vote } = req.body; // 'up', 'down', or 'remove'
    const postId = req.params.id;
    const userId = req.user.id;

    // In a real implementation, you'd track votes in a separate collection
    // For now, we'll just update the counters
    let updateQuery = {};
    
    switch (vote) {
      case 'up':
        updateQuery = { $inc: { 'stats.upvotes': 1 } };
        break;
      case 'down':
        updateQuery = { $inc: { 'stats.downvotes': 1 } };
        break;
      case 'remove':
        // Logic to remove previous vote would go here
        break;
    }

    const post = await Post.findByIdAndUpdate(postId, updateQuery, { new: true });
    
    if (!post) {
      return res.status(404).json({ error: 'Post not found' });
    }

    res.json({ 
      upvotes: post.stats.upvotes, 
      downvotes: post.stats.downvotes 
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Comments endpoints
// POST /api/community/posts/:id/comments - Add comment
router.post('/posts/:id/comments', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const commentData = {
      ...req.body,
      postId: req.params.id,
      authorId: req.user.id
    };

    const comment = new Comment(commentData);
    await comment.save();

    // Update post comment count
    await Post.findByIdAndUpdate(req.params.id, { $inc: { 'stats.comments': 1 } });

    await comment.populate('authorId', 'username avatar reputation');
    res.status(201).json(comment);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Communities endpoints
// GET /api/community/communities - List communities
router.get('/communities', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      category,
      search,
      type = 'public'
    } = req.query;

    const query = { type: { $in: ['public'] } };
    
    if (req.user) {
      // Include communities user is member of
      query.$or = [
        { type: 'public' },
        { members: req.user.id }
      ];
    }

    if (category) query.category = category;
    if (search) {
      query.$or = [
        { name: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } }
      ];
    }

    const options = {
      page: parseInt(page),
      limit: parseInt(limit),
      sort: { 'stats.memberCount': -1 },
      populate: [
        { path: 'creatorId', select: 'username avatar' },
        { path: 'moderators', select: 'username avatar' }
      ]
    };

    const communities = await Community.paginate(query, options);
    res.json(communities);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/community/communities - Create community
router.post('/communities', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const communityData = {
      ...req.body,
      creatorId: req.user.id,
      members: [req.user.id],
      inviteCode: uuidv4(),
      stats: { memberCount: 1 }
    };

    const community = new Community(communityData);
    await community.save();

    await community.populate([
      { path: 'creatorId', select: 'username avatar' },
      { path: 'moderators', select: 'username avatar' }
    ]);

    res.status(201).json(community);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/community/communities/:id/join - Join community
router.post('/communities/:id/join', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const community = await Community.findById(req.params.id);
    
    if (!community) {
      return res.status(404).json({ error: 'Community not found' });
    }

    if (community.members.includes(req.user.id)) {
      return res.status(400).json({ error: 'Already a member of this community' });
    }

    community.members.push(req.user.id);
    community.stats.memberCount += 1;
    await community.save();

    res.json({ message: 'Successfully joined community' });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Events endpoints
// GET /api/community/events - List events
router.get('/events', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      type,
      upcoming = 'true',
      search
    } = req.query;

    const query = { isPublic: true };
    
    if (type) query.type = type;
    if (upcoming === 'true') {
      query.startTime = { $gte: new Date() };
    }
    if (search) {
      query.$or = [
        { title: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } }
      ];
    }

    const options = {
      page: parseInt(page),
      limit: parseInt(limit),
      sort: { startTime: 1 },
      populate: [
        { path: 'organizerId', select: 'username avatar' },
        { path: 'relatedCampaign', select: 'name' },
        { path: 'communityId', select: 'name' }
      ]
    };

    const events = await Event.paginate(query, options);
    res.json(events);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/community/events - Create event
router.post('/events', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const eventData = {
      ...req.body,
      organizerId: req.user.id
    };

    const event = new Event(eventData);
    await event.save();

    await event.populate([
      { path: 'organizerId', select: 'username avatar' },
      { path: 'relatedCampaign', select: 'name' },
      { path: 'communityId', select: 'name' }
    ]);

    res.status(201).json(event);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/community/events/:id/attend - RSVP to event
router.post('/events/:id/attend', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const event = await Event.findById(req.params.id);
    
    if (!event) {
      return res.status(404).json({ error: 'Event not found' });
    }

    if (event.attendees.includes(req.user.id)) {
      return res.status(400).json({ error: 'Already attending this event' });
    }

    // Check if event is full
    if (event.maxAttendees && event.attendees.length >= event.maxAttendees) {
      // Add to waitlist
      if (!event.waitlist.includes(req.user.id)) {
        event.waitlist.push(req.user.id);
        await event.save();
        return res.json({ message: 'Added to waitlist', status: 'waitlisted' });
      }
      return res.status(400).json({ error: 'Event is full and already on waitlist' });
    }

    event.attendees.push(req.user.id);
    await event.save();

    res.json({ message: 'Successfully registered for event', status: 'attending' });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/community/trending - Get trending content
router.get('/trending', async (req, res) => {
  try {
    const timeframe = req.query.timeframe || '24h';
    const limit = parseInt(req.query.limit) || 10;
    
    let timeFilter;
    switch (timeframe) {
      case '1h':
        timeFilter = new Date(Date.now() - 60 * 60 * 1000);
        break;
      case '24h':
        timeFilter = new Date(Date.now() - 24 * 60 * 60 * 1000);
        break;
      case '7d':
        timeFilter = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        break;
      default:
        timeFilter = new Date(Date.now() - 24 * 60 * 60 * 1000);
    }

    // Get trending posts based on engagement
    const trendingPosts = await Post.aggregate([
      { 
        $match: { 
          createdAt: { $gte: timeFilter },
          visibility: 'public'
        } 
      },
      {
        $addFields: {
          engagementScore: {
            $add: [
              { $multiply: ['$stats.upvotes', 3] },
              { $multiply: ['$stats.comments', 2] },
              '$stats.views'
            ]
          }
        }
      },
      { $sort: { engagementScore: -1 } },
      { $limit: limit }
    ]);

    // Populate author information
    await Post.populate(trendingPosts, { 
      path: 'authorId', 
      select: 'username avatar reputation' 
    });

    res.json({ trending: trendingPosts, timeframe });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/community/feed - Get personalized feed
router.get('/feed', async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const { page = 1, limit = 20 } = req.query;

    // Get user's communities
    const userCommunities = await Community.find({ members: req.user.id }).select('_id');
    const communityIds = userCommunities.map(c => c._id);

    // Get feed based on user's interests
    const query = {
      $or: [
        { visibility: 'public', isFeatured: true },
        { authorId: { $in: req.user.following || [] } }, // Following users
        { communityId: { $in: communityIds } }, // User's communities
        { tags: { $in: req.user.interests || [] } } // User's interests
      ]
    };

    const options = {
      page: parseInt(page),
      limit: parseInt(limit),
      sort: { createdAt: -1 },
      populate: [
        { path: 'authorId', select: 'username avatar reputation' },
        { path: 'relatedCampaign', select: 'name sharing' }
      ]
    };

    const feed = await Post.paginate(query, options);
    res.json(feed);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/community/stats - Get community statistics
router.get('/stats', async (req, res) => {
  try {
    const stats = {
      totalPosts: await Post.countDocuments(),
      totalComments: await Comment.countDocuments(),
      totalCommunities: await Community.countDocuments(),
      totalEvents: await Event.countDocuments(),
      activeUsers: 0, // Would require user activity tracking
      postsToday: await Post.countDocuments({
        createdAt: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) }
      }),
      topCategories: await Post.aggregate([
        { $group: { _id: '$category', count: { $sum: 1 } } },
        { $sort: { count: -1 } },
        { $limit: 5 }
      ])
    };

    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;