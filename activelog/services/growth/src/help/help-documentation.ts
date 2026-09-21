import { marked } from 'marked';
import crypto from 'crypto';

export interface HelpArticle {
  id: string;
  title: string;
  content: string;
  summary: string;
  category: string;
  subcategory?: string;
  tags: string[];
  appVariant: 'PersonalLog' | 'BusinessLog' | 'FamilyLog' | 'FitnessLog' | 'TravelLog' | 'EducationLog' | 'all';
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedReadTime: number;
  author: string;
  lastUpdated: Date;
  published: boolean;
  featured: boolean;
  viewCount: number;
  helpfulCount: number;
  unhelpfulCount: number;
  relatedArticles: string[];
}

export interface HelpCategory {
  id: string;
  name: string;
  description: string;
  icon: string;
  order: number;
  subcategories: HelpSubcategory[];
  articleCount: number;
}

export interface HelpSubcategory {
  id: string;
  name: string;
  description: string;
  order: number;
}

export interface SearchResult {
  article: HelpArticle;
  relevanceScore: number;
  matchedContent: string;
}

export interface HelpAnalytics {
  totalArticles: number;
  totalViews: number;
  topViewedArticles: { article: HelpArticle; views: number }[];
  mostHelpfulArticles: { article: HelpArticle; helpfulRatio: number }[];
  searchQueries: { query: string; count: number; resultsFound: number }[];
  categoryPerformance: { category: string; views: number; articles: number }[];
}

export class HelpDocumentationSystem {
  private articles: Map<string, HelpArticle> = new Map();
  private categories: Map<string, HelpCategory> = new Map();
  private searchQueries: Map<string, { count: number; resultsFound: number }> = new Map();

  constructor() {
    this.initializeDefaultContent();
  }

  private initializeDefaultContent(): void {
    this.initializeCategories();
    this.initializeArticles();
  }

  private initializeCategories(): void {
    const gettingStarted: HelpCategory = {
      id: 'getting-started',
      name: 'Getting Started',
      description: 'Learn the basics of using our logging applications',
      icon: 'rocket',
      order: 1,
      articleCount: 0,
      subcategories: [
        { id: 'setup', name: 'Account Setup', description: 'Setting up your account and preferences', order: 1 },
        { id: 'first-steps', name: 'First Steps', description: 'Your first entries and basic features', order: 2 },
        { id: 'navigation', name: 'Navigation', description: 'Finding your way around the app', order: 3 }
      ]
    };

    const features: HelpCategory = {
      id: 'features',
      name: 'Features & Functions',
      description: 'Detailed guides for all app features',
      icon: 'settings',
      order: 2,
      articleCount: 0,
      subcategories: [
        { id: 'entries', name: 'Managing Entries', description: 'Creating, editing, and organizing entries', order: 1 },
        { id: 'media', name: 'Media & Files', description: 'Adding photos, videos, and attachments', order: 2 },
        { id: 'search', name: 'Search & Filter', description: 'Finding specific entries and content', order: 3 },
        { id: 'export', name: 'Export & Backup', description: 'Backing up and exporting your data', order: 4 }
      ]
    };

    const troubleshooting: HelpCategory = {
      id: 'troubleshooting',
      name: 'Troubleshooting',
      description: 'Solutions to common problems',
      icon: 'help-circle',
      order: 3,
      articleCount: 0,
      subcategories: [
        { id: 'login-issues', name: 'Login Issues', description: 'Problems signing in or accessing your account', order: 1 },
        { id: 'sync-problems', name: 'Sync Problems', description: 'Issues with data synchronization', order: 2 },
        { id: 'performance', name: 'Performance', description: 'App running slowly or freezing', order: 3 }
      ]
    };

    const advanced: HelpCategory = {
      id: 'advanced',
      name: 'Advanced Features',
      description: 'Power user features and customization',
      icon: 'zap',
      order: 4,
      articleCount: 0,
      subcategories: [
        { id: 'automation', name: 'Automation', description: 'Setting up automated workflows', order: 1 },
        { id: 'integrations', name: 'Integrations', description: 'Connecting with other tools and services', order: 2 },
        { id: 'api', name: 'API & Developer', description: 'Using our API and developer tools', order: 3 }
      ]
    };

    this.categories.set(gettingStarted.id, gettingStarted);
    this.categories.set(features.id, features);
    this.categories.set(troubleshooting.id, troubleshooting);
    this.categories.set(advanced.id, advanced);
  }

  private initializeArticles(): void {
    const articles: Omit<HelpArticle, 'id' | 'viewCount' | 'helpfulCount' | 'unhelpfulCount'>[] = [
      {
        title: 'Getting Started with PersonalLog',
        content: `# Getting Started with PersonalLog

Welcome to PersonalLog! This guide will help you get started with your personal journaling journey.

## Creating Your First Entry

1. Click the "New Entry" button on your dashboard
2. Choose a title that reflects your mood or the day's events
3. Start writing in the editor - you can format text, add images, and create lists
4. Add categories to organize your entries
5. Click "Save" when you're done

## Organizing Your Entries

Use categories to keep your entries organized:
- **Daily Life**: Regular daily experiences
- **Goals**: Progress on personal goals
- **Reflections**: Deep thoughts and insights
- **Memories**: Special moments you want to remember

## Tips for Consistent Logging

- Set a daily reminder
- Start small - even a few sentences count
- Be honest and authentic
- Don't worry about perfect grammar
- Add photos to capture moments visually

## Privacy and Security

Your entries are private and secure. Only you can see them unless you explicitly choose to share.`,
        summary: 'Learn how to create your first entry and start your personal logging journey with PersonalLog.',
        category: 'getting-started',
        subcategory: 'first-steps',
        tags: ['beginner', 'first-entry', 'personal-log', 'journaling'],
        appVariant: 'PersonalLog',
        difficulty: 'beginner',
        estimatedReadTime: 5,
        author: 'ActiveLog Team',
        lastUpdated: new Date(),
        published: true,
        featured: true,
        relatedArticles: []
      },
      {
        title: 'Setting Up Your BusinessLog Workspace',
        content: `# Setting Up Your BusinessLog Workspace

Configure BusinessLog to match your team's workflow and business needs.

## Company Setup

1. Navigate to Settings > Company
2. Enter your company name and industry
3. Upload your company logo
4. Set your timezone and business hours

## Team Management

### Inviting Team Members
- Go to Team > Invite Members
- Enter email addresses
- Assign roles (Admin, Editor, Viewer)
- Set project permissions

### Creating Teams
- Organize members into teams
- Set team-specific permissions
- Create team channels for focused discussions

## Project Organization

### Creating Projects
1. Click "New Project" from your dashboard
2. Choose a project template or start blank
3. Set project goals and deadlines
4. Assign team members

### Log Templates
Create templates for common business activities:
- Meeting notes
- Project updates
- Client communications
- Performance reviews

## Integration Setup

Connect with your existing tools:
- Slack for notifications
- Google Calendar for scheduling
- Microsoft Teams for collaboration
- CRM systems for customer data`,
        summary: 'Complete guide to setting up your BusinessLog workspace for optimal team collaboration.',
        category: 'getting-started',
        subcategory: 'setup',
        tags: ['business', 'team', 'setup', 'workspace'],
        appVariant: 'BusinessLog',
        difficulty: 'intermediate',
        estimatedReadTime: 8,
        author: 'ActiveLog Team',
        lastUpdated: new Date(),
        published: true,
        featured: true,
        relatedArticles: []
      },
      {
        title: 'Tracking Workouts in FitnessLog',
        content: `# Tracking Workouts in FitnessLog

Master workout logging to maximize your fitness progress tracking.

## Starting a New Workout

1. Tap "New Workout" on your dashboard
2. Choose a workout type:
   - Strength Training
   - Cardio
   - Flexibility
   - Sports
   - Custom

## Adding Exercises

### From Exercise Database
- Browse by muscle group
- Search by exercise name
- Filter by equipment needed
- Select difficulty level

### Creating Custom Exercises
- Enter exercise name
- Select primary muscle groups
- Add equipment requirements
- Include technique notes

## Logging Sets and Reps

### Strength Training
- Weight used
- Number of reps
- Rest time between sets
- Rate of perceived exertion (RPE)

### Cardio Workouts
- Duration
- Distance
- Heart rate zones
- Calories burned

## Progress Tracking

### Measurements
- Body weight
- Body fat percentage
- Muscle measurements
- Progress photos

### Performance Metrics
- Personal records (PRs)
- Volume trends
- Consistency streaks
- Goal achievement rates

## Workout Programs

Follow structured programs:
- Beginner routines
- Intermediate programs
- Advanced training plans
- Sport-specific workouts`,
        summary: 'Complete guide to logging workouts and tracking fitness progress in FitnessLog.',
        category: 'features',
        subcategory: 'entries',
        tags: ['fitness', 'workout', 'tracking', 'exercise'],
        appVariant: 'FitnessLog',
        difficulty: 'beginner',
        estimatedReadTime: 7,
        author: 'ActiveLog Team',
        lastUpdated: new Date(),
        published: true,
        featured: false,
        relatedArticles: []
      },
      {
        title: 'Troubleshooting Sync Issues',
        content: `# Troubleshooting Sync Issues

Resolve common data synchronization problems across devices.

## Common Sync Problems

### Data Not Updating
If your entries aren't syncing between devices:

1. **Check Internet Connection**
   - Ensure stable internet connection
   - Try switching between WiFi and mobile data

2. **Force Sync**
   - Pull down on the main screen to refresh
   - Or go to Settings > Sync > Manual Sync

3. **Sign Out and Back In**
   - Settings > Account > Sign Out
   - Sign back in with your credentials

### Duplicate Entries
If you see duplicate entries:

1. **Automatic Merge**
   - We'll detect and merge duplicates
   - Check your Recently Merged folder

2. **Manual Resolution**
   - Go to Settings > Data Management
   - Review and resolve conflicts

### Missing Entries
If entries seem to be missing:

1. **Check All Devices**
   - Entries might exist on one device only
   - Force sync on all devices

2. **Recovery Options**
   - Check Trash/Deleted Items
   - Use backup restore if available

## Prevention Tips

- Enable automatic sync
- Regular backups to cloud storage
- Keep app updated
- Don't force close the app during sync`,
        summary: 'Step-by-step solutions for common data synchronization issues.',
        category: 'troubleshooting',
        subcategory: 'sync-problems',
        tags: ['sync', 'troubleshooting', 'data', 'devices'],
        appVariant: 'all',
        difficulty: 'intermediate',
        estimatedReadTime: 6,
        author: 'ActiveLog Support',
        lastUpdated: new Date(),
        published: true,
        featured: false,
        relatedArticles: []
      }
    ];

    articles.forEach(articleData => {
      const article: HelpArticle = {
        ...articleData,
        id: crypto.randomUUID(),
        viewCount: Math.floor(Math.random() * 1000),
        helpfulCount: Math.floor(Math.random() * 50),
        unhelpfulCount: Math.floor(Math.random() * 10)
      };
      this.articles.set(article.id, article);
      
      const category = this.categories.get(article.category);
      if (category) {
        category.articleCount++;
      }
    });
  }

  async createArticle(articleData: Omit<HelpArticle, 'id' | 'viewCount' | 'helpfulCount' | 'unhelpfulCount' | 'lastUpdated'>): Promise<HelpArticle> {
    const article: HelpArticle = {
      ...articleData,
      id: crypto.randomUUID(),
      viewCount: 0,
      helpfulCount: 0,
      unhelpfulCount: 0,
      lastUpdated: new Date()
    };

    this.articles.set(article.id, article);
    
    const category = this.categories.get(article.category);
    if (category) {
      category.articleCount++;
    }

    return article;
  }

  async updateArticle(articleId: string, updates: Partial<HelpArticle>): Promise<boolean> {
    const article = this.articles.get(articleId);
    if (!article) return false;

    Object.assign(article, { ...updates, lastUpdated: new Date() });
    return true;
  }

  async deleteArticle(articleId: string): Promise<boolean> {
    const article = this.articles.get(articleId);
    if (!article) return false;

    this.articles.delete(articleId);
    
    const category = this.categories.get(article.category);
    if (category && category.articleCount > 0) {
      category.articleCount--;
    }

    return true;
  }

  async searchArticles(query: string, appVariant?: string, category?: string): Promise<SearchResult[]> {
    const searchTerms = query.toLowerCase().split(' ').filter(term => term.length > 2);
    const results: SearchResult[] = [];

    this.searchQueries.set(query, {
      count: (this.searchQueries.get(query)?.count || 0) + 1,
      resultsFound: 0
    });

    Array.from(this.articles.values())
      .filter(article => {
        if (!article.published) return false;
        if (appVariant && article.appVariant !== 'all' && article.appVariant !== appVariant) return false;
        if (category && article.category !== category) return false;
        return true;
      })
      .forEach(article => {
        let relevanceScore = 0;
        let matchedContent = '';

        const titleLower = article.title.toLowerCase();
        const contentLower = article.content.toLowerCase();
        const summaryLower = article.summary.toLowerCase();
        const tagsLower = article.tags.join(' ').toLowerCase();

        searchTerms.forEach(term => {
          if (titleLower.includes(term)) {
            relevanceScore += 10;
            if (!matchedContent.includes(article.title)) {
              matchedContent += `Title: ${article.title}\n`;
            }
          }
          
          if (summaryLower.includes(term)) {
            relevanceScore += 5;
            if (!matchedContent.includes('Summary:')) {
              matchedContent += `Summary: ${article.summary}\n`;
            }
          }
          
          if (tagsLower.includes(term)) {
            relevanceScore += 3;
          }
          
          if (contentLower.includes(term)) {
            relevanceScore += 1;
            const contentIndex = contentLower.indexOf(term);
            const snippet = article.content.substring(
              Math.max(0, contentIndex - 50),
              Math.min(article.content.length, contentIndex + 100)
            );
            if (!matchedContent.includes(snippet)) {
              matchedContent += `Content: ...${snippet}...\n`;
            }
          }
        });

        if (relevanceScore > 0) {
          results.push({ article, relevanceScore, matchedContent });
        }
      });

    const sortedResults = results.sort((a, b) => b.relevanceScore - a.relevanceScore);
    
    const queryRecord = this.searchQueries.get(query)!;
    queryRecord.resultsFound = sortedResults.length;

    return sortedResults;
  }

  async getArticle(articleId: string): Promise<HelpArticle | null> {
    const article = this.articles.get(articleId);
    if (!article) return null;

    article.viewCount++;
    return article;
  }

  async getArticlesByCategory(categoryId: string, subcategoryId?: string): Promise<HelpArticle[]> {
    return Array.from(this.articles.values())
      .filter(article => {
        if (!article.published) return false;
        if (article.category !== categoryId) return false;
        if (subcategoryId && article.subcategory !== subcategoryId) return false;
        return true;
      })
      .sort((a, b) => {
        if (a.featured && !b.featured) return -1;
        if (b.featured && !a.featured) return 1;
        return b.viewCount - a.viewCount;
      });
  }

  async getFeaturedArticles(appVariant?: string): Promise<HelpArticle[]> {
    return Array.from(this.articles.values())
      .filter(article => {
        if (!article.published || !article.featured) return false;
        if (appVariant && article.appVariant !== 'all' && article.appVariant !== appVariant) return false;
        return true;
      })
      .sort((a, b) => b.viewCount - a.viewCount)
      .slice(0, 6);
  }

  async getRelatedArticles(articleId: string, limit: number = 5): Promise<HelpArticle[]> {
    const article = this.articles.get(articleId);
    if (!article) return [];

    if (article.relatedArticles.length > 0) {
      return article.relatedArticles
        .map(id => this.articles.get(id))
        .filter((a): a is HelpArticle => a !== undefined && a.published)
        .slice(0, limit);
    }

    return Array.from(this.articles.values())
      .filter(a => {
        if (!a.published || a.id === articleId) return false;
        if (a.category === article.category) return true;
        return a.tags.some(tag => article.tags.includes(tag));
      })
      .sort((a, b) => {
        const aTagMatches = a.tags.filter(tag => article.tags.includes(tag)).length;
        const bTagMatches = b.tags.filter(tag => article.tags.includes(tag)).length;
        if (aTagMatches !== bTagMatches) return bTagMatches - aTagMatches;
        return b.viewCount - a.viewCount;
      })
      .slice(0, limit);
  }

  async markHelpful(articleId: string, helpful: boolean): Promise<boolean> {
    const article = this.articles.get(articleId);
    if (!article) return false;

    if (helpful) {
      article.helpfulCount++;
    } else {
      article.unhelpfulCount++;
    }

    return true;
  }

  async getAnalytics(): Promise<HelpAnalytics> {
    const articles = Array.from(this.articles.values()).filter(a => a.published);
    const totalViews = articles.reduce((sum, a) => sum + a.viewCount, 0);

    const topViewedArticles = articles
      .sort((a, b) => b.viewCount - a.viewCount)
      .slice(0, 10)
      .map(article => ({ article, views: article.viewCount }));

    const mostHelpfulArticles = articles
      .filter(a => a.helpfulCount + a.unhelpfulCount > 0)
      .map(article => ({
        article,
        helpfulRatio: article.helpfulCount / (article.helpfulCount + article.unhelpfulCount)
      }))
      .sort((a, b) => b.helpfulRatio - a.helpfulRatio)
      .slice(0, 10);

    const searchQueries = Array.from(this.searchQueries.entries())
      .map(([query, data]) => ({ query, count: data.count, resultsFound: data.resultsFound }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 20);

    const categoryPerformance = Array.from(this.categories.values())
      .map(category => {
        const categoryArticles = articles.filter(a => a.category === category.id);
        const views = categoryArticles.reduce((sum, a) => sum + a.viewCount, 0);
        return {
          category: category.name,
          views,
          articles: categoryArticles.length
        };
      })
      .sort((a, b) => b.views - a.views);

    return {
      totalArticles: articles.length,
      totalViews,
      topViewedArticles,
      mostHelpfulArticles,
      searchQueries,
      categoryPerformance
    };
  }

  async generateSitemap(): Promise<string> {
    const articles = Array.from(this.articles.values()).filter(a => a.published);
    
    let sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n';
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
    
    sitemap += '  <url>\n';
    sitemap += '    <loc>https://help.activelogapp.com/</loc>\n';
    sitemap += '    <changefreq>daily</changefreq>\n';
    sitemap += '    <priority>1.0</priority>\n';
    sitemap += '  </url>\n';

    Array.from(this.categories.values()).forEach(category => {
      sitemap += '  <url>\n';
      sitemap += `    <loc>https://help.activelogapp.com/category/${category.id}</loc>\n`;
      sitemap += '    <changefreq>weekly</changefreq>\n';
      sitemap += '    <priority>0.8</priority>\n';
      sitemap += '  </url>\n';
    });

    articles.forEach(article => {
      sitemap += '  <url>\n';
      sitemap += `    <loc>https://help.activelogapp.com/article/${article.id}</loc>\n`;
      sitemap += `    <lastmod>${article.lastUpdated.toISOString().split('T')[0]}</lastmod>\n`;
      sitemap += '    <changefreq>monthly</changefreq>\n';
      sitemap += '    <priority>0.6</priority>\n';
      sitemap += '  </url>\n';
    });

    sitemap += '</urlset>\n';
    return sitemap;
  }

  getCategories(): HelpCategory[] {
    return Array.from(this.categories.values()).sort((a, b) => a.order - b.order);
  }

  getCategory(categoryId: string): HelpCategory | undefined {
    return this.categories.get(categoryId);
  }

  getAllArticles(): HelpArticle[] {
    return Array.from(this.articles.values());
  }

  getPublishedArticles(): HelpArticle[] {
    return Array.from(this.articles.values()).filter(a => a.published);
  }
}

export const helpDocumentation = new HelpDocumentationSystem();