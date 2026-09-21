import crypto from 'crypto';
import { marked } from 'marked';

export interface ForumUser {
  id: string;
  username: string;
  email: string;
  displayName: string;
  avatar?: string;
  role: 'admin' | 'moderator' | 'member' | 'newbie';
  reputation: number;
  badges: string[];
  joinedAt: Date;
  lastActiveAt: Date;
  postCount: number;
  helpfulAnswers: number;
  isVerified: boolean;
  bio?: string;
  location?: string;
  website?: string;
}

export interface ForumCategory {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
  order: number;
  parentId?: string;
  subcategories: string[];
  moderators: string[];
  postCount: number;
  topicCount: number;
  isArchived: boolean;
  requiredRole?: string;
  appVariant?: 'PersonalLog' | 'BusinessLog' | 'FamilyLog' | 'FitnessLog' | 'TravelLog' | 'EducationLog';
}

export interface ForumTopic {
  id: string;
  title: string;
  content: string;
  authorId: string;
  categoryId: string;
  tags: string[];
  isPinned: boolean;
  isLocked: boolean;
  isResolved: boolean;
  createdAt: Date;
  updatedAt: Date;
  lastActivityAt: Date;
  viewCount: number;
  likeCount: number;
  replyCount: number;
  acceptedAnswerId?: string;
  type: 'discussion' | 'question' | 'announcement' | 'feature-request' | 'bug-report';
  status: 'active' | 'closed' | 'archived';
}

export interface ForumPost {
  id: string;
  content: string;
  authorId: string;
  topicId: string;
  parentPostId?: string;
  createdAt: Date;
  editedAt?: Date;
  likeCount: number;
  isAcceptedAnswer: boolean;
  isHidden: boolean;
  flagCount: number;
  attachments: ForumAttachment[];
}

export interface ForumAttachment {
  id: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  url: string;
  uploadedAt: Date;
}

export interface ForumModeration {
  id: string;
  type: 'flag' | 'hide' | 'lock' | 'pin' | 'move' | 'ban';
  targetType: 'user' | 'topic' | 'post';
  targetId: string;
  moderatorId: string;
  reason: string;
  action: string;
  createdAt: Date;
  resolvedAt?: Date;
  notes?: string;
}

export interface ForumNotification {
  id: string;
  userId: string;
  type: 'reply' | 'mention' | 'like' | 'accept' | 'follow' | 'system';
  title: string;
  content: string;
  isRead: boolean;
  relatedTopicId?: string;
  relatedPostId?: string;
  relatedUserId?: string;
  createdAt: Date;
}

export interface ForumAnalytics {
  totalUsers: number;
  totalTopics: number;
  totalPosts: number;
  activeUsers: number;
  newUsersThisMonth: number;
  topContributors: { user: ForumUser; posts: number; reputation: number }[];
  popularCategories: { category: ForumCategory; activity: number }[];
  trendingTopics: { topic: ForumTopic; engagementScore: number }[];
  resolutionRate: number;
  averageResponseTime: number;
}

export class CommunityForumSystem {
  private users: Map<string, ForumUser> = new Map();
  private categories: Map<string, ForumCategory> = new Map();
  private topics: Map<string, ForumTopic> = new Map();
  private posts: Map<string, ForumPost> = new Map();
  private moderations: Map<string, ForumModeration> = new Map();
  private notifications: Map<string, ForumNotification> = new Map();
  private userFollows: Map<string, Set<string>> = new Map();
  private topicSubscriptions: Map<string, Set<string>> = new Map();

  constructor() {
    this.initializeDefaultContent();
  }

  private initializeDefaultContent(): void {
    this.createDefaultCategories();
    this.createSampleUsers();
    this.createSampleTopics();
  }

  private createDefaultCategories(): void {
    const categories: Omit<ForumCategory, 'postCount' | 'topicCount'>[] = [
      {
        id: 'general',
        name: 'General Discussion',
        description: 'General topics and community discussions',
        color: '#007bff',
        icon: 'chat-dots',
        order: 1,
        subcategories: [],
        moderators: [],
        isArchived: false
      },
      {
        id: 'getting-started',
        name: 'Getting Started',
        description: 'New user questions and onboarding help',
        color: '#28a745',
        icon: 'play-circle',
        order: 2,
        subcategories: [],
        moderators: [],
        isArchived: false
      },
      {
        id: 'feature-requests',
        name: 'Feature Requests',
        description: 'Suggest new features and improvements',
        color: '#ffc107',
        icon: 'lightbulb',
        order: 3,
        subcategories: [],
        moderators: [],
        isArchived: false
      },
      {
        id: 'bug-reports',
        name: 'Bug Reports',
        description: 'Report bugs and technical issues',
        color: '#dc3545',
        icon: 'bug',
        order: 4,
        subcategories: [],
        moderators: [],
        isArchived: false
      },
      {
        id: 'personal-log',
        name: 'PersonalLog',
        description: 'Discussions specific to PersonalLog',
        color: '#6f42c1',
        icon: 'journal-text',
        order: 5,
        subcategories: [],
        moderators: [],
        isArchived: false,
        appVariant: 'PersonalLog'
      },
      {
        id: 'business-log',
        name: 'BusinessLog',
        description: 'Discussions specific to BusinessLog',
        color: '#fd7e14',
        icon: 'briefcase',
        order: 6,
        subcategories: [],
        moderators: [],
        isArchived: false,
        appVariant: 'BusinessLog'
      },
      {
        id: 'fitness-log',
        name: 'FitnessLog',
        description: 'Discussions specific to FitnessLog',
        color: '#20c997',
        icon: 'heart-pulse',
        order: 7,
        subcategories: [],
        moderators: [],
        isArchived: false,
        appVariant: 'FitnessLog'
      },
      {
        id: 'tips-tricks',
        name: 'Tips & Tricks',
        description: 'Share your best practices and workflows',
        color: '#17a2b8',
        icon: 'magic',
        order: 8,
        subcategories: [],
        moderators: [],
        isArchived: false
      },
      {
        id: 'showcase',
        name: 'Showcase',
        description: 'Show off your logging achievements',
        color: '#e83e8c',
        icon: 'trophy',
        order: 9,
        subcategories: [],
        moderators: [],
        isArchived: false
      },
      {
        id: 'announcements',
        name: 'Announcements',
        description: 'Official updates and news',
        color: '#6c757d',
        icon: 'megaphone',
        order: 0,
        subcategories: [],
        moderators: [],
        isArchived: false,
        requiredRole: 'admin'
      }
    ];

    categories.forEach(categoryData => {
      const category: ForumCategory = {
        ...categoryData,
        postCount: 0,
        topicCount: 0
      };
      this.categories.set(category.id, category);
    });
  }

  private createSampleUsers(): void {
    const sampleUsers: Omit<ForumUser, 'joinedAt' | 'lastActiveAt' | 'postCount' | 'helpfulAnswers'>[] = [
      {
        id: crypto.randomUUID(),
        username: 'admin',
        email: 'admin@activelogapp.com',
        displayName: 'ActiveLog Team',
        role: 'admin',
        reputation: 1000,
        badges: ['founder', 'expert', 'helpful'],
        isVerified: true,
        bio: 'Official ActiveLog team account'
      },
      {
        id: crypto.randomUUID(),
        username: 'moderator1',
        email: 'mod1@activelogapp.com',
        displayName: 'Community Manager',
        role: 'moderator',
        reputation: 500,
        badges: ['moderator', 'helpful'],
        isVerified: true,
        bio: 'Keeping our community friendly and helpful'
      }
    ];

    sampleUsers.forEach(userData => {
      const user: ForumUser = {
        ...userData,
        joinedAt: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000),
        lastActiveAt: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000),
        postCount: Math.floor(Math.random() * 50),
        helpfulAnswers: Math.floor(Math.random() * 20)
      };
      this.users.set(user.id, user);
    });
  }

  private createSampleTopics(): void {
    const adminUser = Array.from(this.users.values()).find(u => u.role === 'admin');
    if (!adminUser) return;

    const sampleTopics: Omit<ForumTopic, 'id' | 'createdAt' | 'updatedAt' | 'lastActivityAt' | 'viewCount' | 'likeCount' | 'replyCount'>[] = [
      {
        title: 'Welcome to the ActiveLog Community!',
        content: `# Welcome to our community forum!

We're excited to have you here. This is a place where you can:

- Ask questions about any of our logging apps
- Share tips and tricks
- Request new features
- Connect with other users

## Community Guidelines

Please be respectful, helpful, and constructive in all your interactions.

Happy logging! 🚀`,
        authorId: adminUser.id,
        categoryId: 'announcements',
        tags: ['welcome', 'community', 'guidelines'],
        isPinned: true,
        isLocked: false,
        isResolved: false,
        type: 'announcement',
        status: 'active'
      },
      {
        title: 'How to get started with PersonalLog?',
        content: `I just signed up for PersonalLog and I'm not sure where to begin. 

What are the best practices for personal journaling? How do you organize your entries?

Any tips for staying consistent with daily logging?`,
        authorId: adminUser.id,
        categoryId: 'getting-started',
        tags: ['personal-log', 'beginner', 'tips'],
        isPinned: false,
        isLocked: false,
        isResolved: false,
        type: 'question',
        status: 'active'
      },
      {
        title: 'Feature Request: Dark Mode',
        content: `It would be great to have a dark mode option for the apps. 

Many users prefer dark interfaces, especially for evening logging sessions.

Is this something that's being considered?`,
        authorId: adminUser.id,
        categoryId: 'feature-requests',
        tags: ['dark-mode', 'ui', 'feature-request'],
        isPinned: false,
        isLocked: false,
        isResolved: false,
        type: 'feature-request',
        status: 'active'
      }
    ];

    sampleTopics.forEach(topicData => {
      const topic: ForumTopic = {
        ...topicData,
        id: crypto.randomUUID(),
        createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(),
        lastActivityAt: new Date(),
        viewCount: Math.floor(Math.random() * 500),
        likeCount: Math.floor(Math.random() * 50),
        replyCount: Math.floor(Math.random() * 20)
      };
      this.topics.set(topic.id, topic);
      
      const category = this.categories.get(topic.categoryId);
      if (category) {
        category.topicCount++;
      }
    });
  }

  async createUser(userData: Omit<ForumUser, 'id' | 'joinedAt' | 'lastActiveAt' | 'postCount' | 'helpfulAnswers' | 'reputation' | 'badges'>): Promise<ForumUser> {
    const user: ForumUser = {
      ...userData,
      id: crypto.randomUUID(),
      joinedAt: new Date(),
      lastActiveAt: new Date(),
      postCount: 0,
      helpfulAnswers: 0,
      reputation: 0,
      badges: []
    };

    this.users.set(user.id, user);
    return user;
  }

  async createTopic(topicData: Omit<ForumTopic, 'id' | 'createdAt' | 'updatedAt' | 'lastActivityAt' | 'viewCount' | 'likeCount' | 'replyCount'>): Promise<ForumTopic> {
    const topic: ForumTopic = {
      ...topicData,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date(),
      lastActivityAt: new Date(),
      viewCount: 0,
      likeCount: 0,
      replyCount: 0
    };

    this.topics.set(topic.id, topic);
    
    const category = this.categories.get(topic.categoryId);
    if (category) {
      category.topicCount++;
    }

    const author = this.users.get(topic.authorId);
    if (author) {
      author.postCount++;
    }

    return topic;
  }

  async createPost(postData: Omit<ForumPost, 'id' | 'createdAt' | 'likeCount' | 'isAcceptedAnswer' | 'isHidden' | 'flagCount' | 'attachments'>): Promise<ForumPost> {
    const post: ForumPost = {
      ...postData,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      likeCount: 0,
      isAcceptedAnswer: false,
      isHidden: false,
      flagCount: 0,
      attachments: []
    };

    this.posts.set(post.id, post);

    const topic = this.topics.get(post.topicId);
    if (topic) {
      topic.replyCount++;
      topic.lastActivityAt = new Date();
      topic.updatedAt = new Date();
    }

    const author = this.users.get(post.authorId);
    if (author) {
      author.postCount++;
      author.lastActiveAt = new Date();
    }

    this.notifyTopicSubscribers(post.topicId, post.authorId, 'reply');
    return post;
  }

  async getTopicsByCategory(categoryId: string, page: number = 1, limit: number = 20): Promise<{ topics: ForumTopic[]; total: number }> {
    const allTopics = Array.from(this.topics.values())
      .filter(topic => topic.categoryId === categoryId && topic.status === 'active')
      .sort((a, b) => {
        if (a.isPinned && !b.isPinned) return -1;
        if (!a.isPinned && b.isPinned) return 1;
        return b.lastActivityAt.getTime() - a.lastActivityAt.getTime();
      });

    const startIndex = (page - 1) * limit;
    const topics = allTopics.slice(startIndex, startIndex + limit);

    return { topics, total: allTopics.length };
  }

  async getPostsByTopic(topicId: string, page: number = 1, limit: number = 20): Promise<{ posts: ForumPost[]; total: number }> {
    const topic = this.topics.get(topicId);
    if (topic) {
      topic.viewCount++;
    }

    const allPosts = Array.from(this.posts.values())
      .filter(post => post.topicId === topicId && !post.isHidden)
      .sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());

    const startIndex = (page - 1) * limit;
    const posts = allPosts.slice(startIndex, startIndex + limit);

    return { posts, total: allPosts.length };
  }

  async searchTopics(query: string, filters?: {
    categoryId?: string;
    tags?: string[];
    authorId?: string;
    type?: string;
    resolved?: boolean;
  }): Promise<ForumTopic[]> {
    const queryLower = query.toLowerCase();
    
    return Array.from(this.topics.values())
      .filter(topic => {
        if (topic.status !== 'active') return false;
        
        if (filters?.categoryId && topic.categoryId !== filters.categoryId) return false;
        if (filters?.authorId && topic.authorId !== filters.authorId) return false;
        if (filters?.type && topic.type !== filters.type) return false;
        if (filters?.resolved !== undefined && topic.isResolved !== filters.resolved) return false;
        if (filters?.tags && !filters.tags.every(tag => topic.tags.includes(tag))) return false;
        
        return (
          topic.title.toLowerCase().includes(queryLower) ||
          topic.content.toLowerCase().includes(queryLower) ||
          topic.tags.some(tag => tag.toLowerCase().includes(queryLower))
        );
      })
      .sort((a, b) => b.lastActivityAt.getTime() - a.lastActivityAt.getTime());
  }

  async likeTopic(topicId: string, userId: string): Promise<boolean> {
    const topic = this.topics.get(topicId);
    if (!topic) return false;

    topic.likeCount++;
    
    if (topic.authorId !== userId) {
      this.createNotification({
        userId: topic.authorId,
        type: 'like',
        title: 'Topic Liked',
        content: `Someone liked your topic "${topic.title}"`,
        relatedTopicId: topicId,
        relatedUserId: userId
      });
    }

    return true;
  }

  async likePost(postId: string, userId: string): Promise<boolean> {
    const post = this.posts.get(postId);
    if (!post) return false;

    post.likeCount++;
    
    if (post.authorId !== userId) {
      this.createNotification({
        userId: post.authorId,
        type: 'like',
        title: 'Post Liked',
        content: 'Someone liked your post',
        relatedPostId: postId,
        relatedUserId: userId
      });
    }

    return true;
  }

  async acceptAnswer(topicId: string, postId: string, userId: string): Promise<boolean> {
    const topic = this.topics.get(topicId);
    const post = this.posts.get(postId);
    
    if (!topic || !post || topic.authorId !== userId || post.topicId !== topicId) {
      return false;
    }

    if (topic.acceptedAnswerId) {
      const previousAnswer = this.posts.get(topic.acceptedAnswerId);
      if (previousAnswer) {
        previousAnswer.isAcceptedAnswer = false;
      }
    }

    topic.acceptedAnswerId = postId;
    topic.isResolved = true;
    post.isAcceptedAnswer = true;

    const answerAuthor = this.users.get(post.authorId);
    if (answerAuthor) {
      answerAuthor.helpfulAnswers++;
      answerAuthor.reputation += 15;
    }

    this.createNotification({
      userId: post.authorId,
      type: 'accept',
      title: 'Answer Accepted',
      content: `Your answer was accepted for "${topic.title}"`,
      relatedTopicId: topicId,
      relatedPostId: postId
    });

    return true;
  }

  async followUser(followerId: string, followedId: string): Promise<boolean> {
    if (!this.userFollows.has(followerId)) {
      this.userFollows.set(followerId, new Set());
    }
    
    this.userFollows.get(followerId)!.add(followedId);
    
    this.createNotification({
      userId: followedId,
      type: 'follow',
      title: 'New Follower',
      content: 'Someone started following you',
      relatedUserId: followerId
    });

    return true;
  }

  async subscribeToTopic(topicId: string, userId: string): Promise<boolean> {
    if (!this.topicSubscriptions.has(topicId)) {
      this.topicSubscriptions.set(topicId, new Set());
    }
    
    this.topicSubscriptions.get(topicId)!.add(userId);
    return true;
  }

  async flagContent(targetType: 'topic' | 'post', targetId: string, reporterId: string, reason: string): Promise<boolean> {
    const moderation: ForumModeration = {
      id: crypto.randomUUID(),
      type: 'flag',
      targetType,
      targetId,
      moderatorId: reporterId,
      reason,
      action: 'flagged',
      createdAt: new Date()
    };

    this.moderations.set(moderation.id, moderation);

    if (targetType === 'post') {
      const post = this.posts.get(targetId);
      if (post) {
        post.flagCount++;
      }
    }

    return true;
  }

  async moderateContent(moderationId: string, moderatorId: string, action: 'approve' | 'hide' | 'delete', notes?: string): Promise<boolean> {
    const moderation = this.moderations.get(moderationId);
    if (!moderation) return false;

    const moderator = this.users.get(moderatorId);
    if (!moderator || (moderator.role !== 'moderator' && moderator.role !== 'admin')) {
      return false;
    }

    moderation.resolvedAt = new Date();
    moderation.notes = notes;

    if (action === 'hide' && moderation.targetType === 'post') {
      const post = this.posts.get(moderation.targetId);
      if (post) {
        post.isHidden = true;
      }
    } else if (action === 'delete') {
      if (moderation.targetType === 'post') {
        this.posts.delete(moderation.targetId);
      } else if (moderation.targetType === 'topic') {
        this.topics.delete(moderation.targetId);
      }
    }

    return true;
  }

  private async notifyTopicSubscribers(topicId: string, authorId: string, type: 'reply'): Promise<void> {
    const subscribers = this.topicSubscriptions.get(topicId);
    if (!subscribers) return;

    const topic = this.topics.get(topicId);
    if (!topic) return;

    subscribers.forEach(subscriberId => {
      if (subscriberId !== authorId) {
        this.createNotification({
          userId: subscriberId,
          type,
          title: 'New Reply',
          content: `New reply in "${topic.title}"`,
          relatedTopicId: topicId,
          relatedUserId: authorId
        });
      }
    });
  }

  private createNotification(notificationData: Omit<ForumNotification, 'id' | 'isRead' | 'createdAt'>): void {
    const notification: ForumNotification = {
      ...notificationData,
      id: crypto.randomUUID(),
      isRead: false,
      createdAt: new Date()
    };

    this.notifications.set(notification.id, notification);
  }

  async getForumAnalytics(): Promise<ForumAnalytics> {
    const users = Array.from(this.users.values());
    const topics = Array.from(this.topics.values());
    const posts = Array.from(this.posts.values());

    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const activeUsers = users.filter(user => user.lastActiveAt > thirtyDaysAgo).length;
    const newUsersThisMonth = users.filter(user => user.joinedAt > thirtyDaysAgo).length;

    const topContributors = users
      .filter(user => user.postCount > 0)
      .sort((a, b) => b.reputation - a.reputation)
      .slice(0, 10)
      .map(user => ({
        user,
        posts: user.postCount,
        reputation: user.reputation
      }));

    const categoryActivity = new Map<string, number>();
    topics.forEach(topic => {
      const current = categoryActivity.get(topic.categoryId) || 0;
      categoryActivity.set(topic.categoryId, current + topic.replyCount + 1);
    });

    const popularCategories = Array.from(this.categories.values())
      .map(category => ({
        category,
        activity: categoryActivity.get(category.id) || 0
      }))
      .sort((a, b) => b.activity - a.activity)
      .slice(0, 5);

    const trendingTopics = topics
      .filter(topic => topic.status === 'active')
      .map(topic => {
        const age = Date.now() - topic.createdAt.getTime();
        const ageInDays = age / (24 * 60 * 60 * 1000);
        const engagementScore = (topic.viewCount + topic.likeCount * 2 + topic.replyCount * 3) / Math.max(ageInDays, 1);
        return { topic, engagementScore };
      })
      .sort((a, b) => b.engagementScore - a.engagementScore)
      .slice(0, 10);

    const questionTopics = topics.filter(t => t.type === 'question');
    const resolvedQuestions = questionTopics.filter(t => t.isResolved);
    const resolutionRate = questionTopics.length > 0 ? (resolvedQuestions.length / questionTopics.length) * 100 : 0;

    const topicResponseTimes = topics
      .filter(t => t.replyCount > 0)
      .map(topic => {
        const firstReply = posts
          .filter(post => post.topicId === topic.id)
          .sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime())[0];
        
        if (firstReply) {
          return firstReply.createdAt.getTime() - topic.createdAt.getTime();
        }
        return 0;
      })
      .filter(time => time > 0);

    const averageResponseTime = topicResponseTimes.length > 0
      ? topicResponseTimes.reduce((sum, time) => sum + time, 0) / topicResponseTimes.length / (60 * 60 * 1000)
      : 0;

    return {
      totalUsers: users.length,
      totalTopics: topics.length,
      totalPosts: posts.length,
      activeUsers,
      newUsersThisMonth,
      topContributors,
      popularCategories,
      trendingTopics,
      resolutionRate: Math.round(resolutionRate * 100) / 100,
      averageResponseTime: Math.round(averageResponseTime * 100) / 100
    };
  }

  async getUserNotifications(userId: string, unreadOnly: boolean = false): Promise<ForumNotification[]> {
    return Array.from(this.notifications.values())
      .filter(notification => {
        if (notification.userId !== userId) return false;
        if (unreadOnly && notification.isRead) return false;
        return true;
      })
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  async markNotificationAsRead(notificationId: string): Promise<boolean> {
    const notification = this.notifications.get(notificationId);
    if (!notification) return false;

    notification.isRead = true;
    return true;
  }

  getCategories(): ForumCategory[] {
    return Array.from(this.categories.values()).sort((a, b) => a.order - b.order);
  }

  getCategory(categoryId: string): ForumCategory | undefined {
    return this.categories.get(categoryId);
  }

  getTopic(topicId: string): ForumTopic | undefined {
    return this.topics.get(topicId);
  }

  getPost(postId: string): ForumPost | undefined {
    return this.posts.get(postId);
  }

  getUser(userId: string): ForumUser | undefined {
    return this.users.get(userId);
  }

  async updateUser(userId: string, updates: Partial<ForumUser>): Promise<boolean> {
    const user = this.users.get(userId);
    if (!user) return false;

    Object.assign(user, updates);
    return true;
  }

  async updateTopic(topicId: string, updates: Partial<ForumTopic>): Promise<boolean> {
    const topic = this.topics.get(topicId);
    if (!topic) return false;

    Object.assign(topic, { ...updates, updatedAt: new Date() });
    return true;
  }

  async updatePost(postId: string, updates: Partial<ForumPost>): Promise<boolean> {
    const post = this.posts.get(postId);
    if (!post) return false;

    Object.assign(post, { ...updates, editedAt: new Date() });
    return true;
  }
}

export const communityForum = new CommunityForumSystem();