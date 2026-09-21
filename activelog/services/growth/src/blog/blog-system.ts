import { marked } from 'marked';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';

export interface BlogPost {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  htmlContent?: string;
  
  // Author information
  author: {
    id: string;
    name: string;
    bio: string;
    avatar: string;
    socialLinks?: {
      twitter?: string;
      linkedin?: string;
      website?: string;
    };
  };
  
  // Categorization and tagging
  category: {
    id: string;
    name: string;
    slug: string;
    description: string;
    color: string;
  };
  tags: Array<{
    id: string;
    name: string;
    slug: string;
  }>;
  
  // SEO and social
  seo: {
    metaTitle?: string;
    metaDescription?: string;
    keywords: string[];
    canonicalUrl?: string;
    socialImage?: string;
  };
  
  // Media
  featuredImage: {
    url: string;
    alt: string;
    caption?: string;
    credit?: string;
  };
  gallery?: Array<{
    url: string;
    alt: string;
    caption?: string;
  }>;
  
  // Publishing
  status: 'draft' | 'scheduled' | 'published' | 'archived';
  publishedAt?: Date;
  scheduledAt?: Date;
  updatedAt: Date;
  createdAt: Date;
  
  // Engagement and analytics
  metrics?: {
    views: number;
    uniqueViews: number;
    likes: number;
    shares: number;
    comments: number;
    readingTime: number; // in minutes
    engagementScore: number;
    conversionRate: number;
    bounceRate: number;
    avgTimeOnPage: number; // in seconds
  };
  
  // Content features
  features: {
    allowComments: boolean;
    allowSharing: boolean;
    showAuthor: boolean;
    showRelated: boolean;
    enableNewsletter: boolean;
    ctaEnabled: boolean;
    ctaText?: string;
    ctaUrl?: string;
  };
  
  // Targeting
  targeting?: {
    appVariants?: string[];
    userSegments?: string[];
    geoTargeting?: string[];
  };
}

export interface BlogCategory {
  id: string;
  name: string;
  slug: string;
  description: string;
  color: string;
  parentId?: string;
  isActive: boolean;
  sortOrder: number;
  postCount: number;
  
  // SEO
  seo: {
    metaTitle?: string;
    metaDescription?: string;
    keywords: string[];
  };
  
  // Content strategy
  contentStrategy?: {
    targetAudience: string;
    contentPillars: string[];
    publishingFrequency: 'daily' | 'weekly' | 'biweekly' | 'monthly';
    goalMetrics: string[];
  };
}

export interface ContentTemplate {
  id: string;
  name: string;
  description: string;
  type: 'how-to' | 'listicle' | 'case-study' | 'interview' | 'news' | 'opinion' | 'review';
  
  // Template structure
  structure: Array<{
    section: string;
    description: string;
    placeholder: string;
    required: boolean;
  }>;
  
  // Auto-generated elements
  autoElements: {
    generateOutline: boolean;
    suggestImages: boolean;
    generateSEO: boolean;
    suggestTags: boolean;
  };
  
  // Target metrics
  targetWordCount: number;
  estimatedReadingTime: number;
  
  isActive: boolean;
  createdAt: Date;
}

export interface ContentCalendar {
  id: string;
  name: string;
  description: string;
  startDate: Date;
  endDate: Date;
  
  // Publishing schedule
  schedule: Array<{
    id: string;
    title: string;
    categoryId: string;
    templateId?: string;
    authorId: string;
    scheduledDate: Date;
    status: 'planned' | 'in-progress' | 'review' | 'scheduled' | 'published';
    priority: 'low' | 'medium' | 'high';
    notes?: string;
    assignedTo?: string;
    keywords: string[];
    targetAppVariants?: string[];
  }>;
  
  // Content themes and campaigns
  themes: Array<{
    name: string;
    description: string;
    startDate: Date;
    endDate: Date;
    goals: string[];
    targetMetrics: Record<string, number>;
  }>;
}

export interface BlogAnalytics {
  period: {
    start: Date;
    end: Date;
  };
  
  // Overall metrics
  overview: {
    totalPosts: number;
    totalViews: number;
    uniqueVisitors: number;
    avgTimeOnSite: number;
    bounceRate: number;
    pagesPerSession: number;
    conversionRate: number;
  };
  
  // Content performance
  topPosts: Array<{
    postId: string;
    title: string;
    views: number;
    engagementScore: number;
    conversionRate: number;
  }>;
  
  topCategories: Array<{
    categoryId: string;
    name: string;
    postCount: number;
    views: number;
    engagementScore: number;
  }>;
  
  topKeywords: Array<{
    keyword: string;
    posts: number;
    totalViews: number;
    avgPosition: number;
  }>;
  
  // Audience insights
  audienceInsights: {
    demographics: {
      ageGroups: Record<string, number>;
      countries: Record<string, number>;
      devices: Record<string, number>;
    };
    behavior: {
      returningVisitors: number;
      avgSessionDuration: number;
      mostPopularTimes: Record<string, number>;
    };
  };
  
  // SEO performance
  seoMetrics: {
    organicTraffic: number;
    avgPosition: number;
    impressions: number;
    clickThroughRate: number;
    featuredSnippets: number;
    backlinks: number;
  };
  
  // Social media performance
  socialMetrics: {
    totalShares: number;
    sharesByPlatform: Record<string, number>;
    socialTraffic: number;
    viralityScore: number;
  };
}

class BlogSystem {
  private posts: Map<string, BlogPost> = new Map();
  private categories: Map<string, BlogCategory> = new Map();
  private templates: Map<string, ContentTemplate> = new Map();
  private calendars: Map<string, ContentCalendar> = new Map();
  private contentDir: string;

  constructor(contentDir: string = './content') {
    this.contentDir = contentDir;
    this.initializeDefaultData();
  }

  public createPost(postData: Omit<BlogPost, 'id' | 'createdAt' | 'updatedAt' | 'htmlContent'>): BlogPost {
    const post: BlogPost = {
      ...postData,
      id: uuidv4(),
      createdAt: new Date(),
      updatedAt: new Date(),
      htmlContent: this.convertMarkdownToHtml(postData.content),
    };

    // Calculate reading time
    const wordCount = post.content.split(' ').length;
    const readingTime = Math.ceil(wordCount / 200); // Average reading speed
    
    if (!post.metrics) {
      post.metrics = {
        views: 0,
        uniqueViews: 0,
        likes: 0,
        shares: 0,
        comments: 0,
        readingTime,
        engagementScore: 0,
        conversionRate: 0,
        bounceRate: 0,
        avgTimeOnPage: 0,
      };
    }

    this.posts.set(post.id, post);
    this.savePostToDisk(post);
    
    return post;
  }

  public updatePost(postId: string, updates: Partial<BlogPost>): BlogPost {
    const post = this.posts.get(postId);
    if (!post) {
      throw new Error(`Post ${postId} not found`);
    }

    const updatedPost: BlogPost = {
      ...post,
      ...updates,
      updatedAt: new Date(),
    };

    // Regenerate HTML if content changed
    if (updates.content && updates.content !== post.content) {
      updatedPost.htmlContent = this.convertMarkdownToHtml(updates.content);
      
      // Recalculate reading time
      const wordCount = updatedPost.content.split(' ').length;
      const readingTime = Math.ceil(wordCount / 200);
      if (updatedPost.metrics) {
        updatedPost.metrics.readingTime = readingTime;
      }
    }

    this.posts.set(postId, updatedPost);
    this.savePostToDisk(updatedPost);
    
    return updatedPost;
  }

  public publishPost(postId: string, publishAt?: Date): BlogPost {
    const post = this.posts.get(postId);
    if (!post) {
      throw new Error(`Post ${postId} not found`);
    }

    if (publishAt && publishAt > new Date()) {
      post.status = 'scheduled';
      post.scheduledAt = publishAt;
      
      // Schedule publication
      const delay = publishAt.getTime() - new Date().getTime();
      setTimeout(() => {
        this.publishPost(postId);
      }, delay);
    } else {
      post.status = 'published';
      post.publishedAt = new Date();
      post.scheduledAt = undefined;
    }

    post.updatedAt = new Date();
    this.posts.set(postId, post);
    this.savePostToDisk(post);

    return post;
  }

  public createCategory(categoryData: Omit<BlogCategory, 'id' | 'postCount'>): BlogCategory {
    const category: BlogCategory = {
      ...categoryData,
      id: uuidv4(),
      postCount: 0,
    };

    this.categories.set(category.id, category);
    return category;
  }

  public createTemplate(templateData: Omit<ContentTemplate, 'id' | 'createdAt'>): ContentTemplate {
    const template: ContentTemplate = {
      ...templateData,
      id: uuidv4(),
      createdAt: new Date(),
    };

    this.templates.set(template.id, template);
    return template;
  }

  public createContentFromTemplate(templateId: string, data: Record<string, string>): Partial<BlogPost> {
    const template = this.templates.get(templateId);
    if (!template) {
      throw new Error(`Template ${templateId} not found`);
    }

    let content = '';
    let title = '';
    let excerpt = '';

    // Generate content based on template structure
    template.structure.forEach(section => {
      const sectionContent = data[section.section] || section.placeholder;
      
      if (section.section === 'title') {
        title = sectionContent;
      } else if (section.section === 'excerpt') {
        excerpt = sectionContent;
      } else {
        content += `## ${section.section}\n\n${sectionContent}\n\n`;
      }
    });

    // Generate SEO elements if enabled
    let seoData: BlogPost['seo'] = { keywords: [] };
    if (template.autoElements.generateSEO) {
      seoData = this.generateSEOData(title, content);
    }

    return {
      title,
      excerpt,
      content: content.trim(),
      seo: seoData,
    };
  }

  public createContentCalendar(calendarData: Omit<ContentCalendar, 'id'>): ContentCalendar {
    const calendar: ContentCalendar = {
      ...calendarData,
      id: uuidv4(),
    };

    this.calendars.set(calendar.id, calendar);
    return calendar;
  }

  public generateContentIdeas(
    category: string,
    appVariant?: string,
    count: number = 10
  ): Array<{
    title: string;
    type: ContentTemplate['type'];
    keywords: string[];
    estimatedTraffic: number;
    difficulty: 'easy' | 'medium' | 'hard';
    targetAudience: string;
  }> {
    // This would integrate with keyword research tools and competitor analysis
    const ideas = this.getContentIdeasForCategory(category, appVariant);
    return ideas.slice(0, count);
  }

  public optimizeForSEO(postId: string): {
    suggestions: string[];
    score: number;
    improvements: Array<{
      category: string;
      issue: string;
      suggestion: string;
      impact: 'high' | 'medium' | 'low';
    }>;
  } {
    const post = this.posts.get(postId);
    if (!post) {
      throw new Error(`Post ${postId} not found`);
    }

    const improvements = [];
    let score = 100;

    // Check title length
    if (post.title.length > 60) {
      improvements.push({
        category: 'Title',
        issue: 'Title too long',
        suggestion: 'Keep title under 60 characters for better SERP display',
        impact: 'medium' as const,
      });
      score -= 10;
    }

    // Check meta description
    if (!post.seo.metaDescription) {
      improvements.push({
        category: 'Meta Description',
        issue: 'Missing meta description',
        suggestion: 'Add a compelling meta description (150-160 characters)',
        impact: 'high' as const,
      });
      score -= 15;
    } else if (post.seo.metaDescription.length > 160) {
      improvements.push({
        category: 'Meta Description',
        issue: 'Meta description too long',
        suggestion: 'Keep meta description under 160 characters',
        impact: 'medium' as const,
      });
      score -= 10;
    }

    // Check keyword usage
    if (post.seo.keywords.length === 0) {
      improvements.push({
        category: 'Keywords',
        issue: 'No target keywords',
        suggestion: 'Add 3-5 target keywords for this post',
        impact: 'high' as const,
      });
      score -= 20;
    }

    // Check content length
    const wordCount = post.content.split(' ').length;
    if (wordCount < 300) {
      improvements.push({
        category: 'Content',
        issue: 'Content too short',
        suggestion: 'Aim for at least 300 words for better SEO performance',
        impact: 'medium' as const,
      });
      score -= 10;
    }

    // Check alt text for images
    if (!post.featuredImage.alt) {
      improvements.push({
        category: 'Images',
        issue: 'Missing alt text for featured image',
        suggestion: 'Add descriptive alt text for accessibility and SEO',
        impact: 'medium' as const,
      });
      score -= 5;
    }

    const suggestions = [
      'Optimize title length and include primary keyword',
      'Write compelling meta description',
      'Add internal links to related posts',
      'Include external links to authoritative sources',
      'Optimize images with descriptive alt text',
      'Structure content with proper headings (H2, H3)',
      'Add schema markup for better SERP features',
    ];

    return {
      suggestions,
      score: Math.max(0, score),
      improvements,
    };
  }

  public getAnalytics(startDate: Date, endDate: Date): BlogAnalytics {
    const posts = this.getPostsInDateRange(startDate, endDate);
    
    // This would typically integrate with Google Analytics or similar
    const analytics: BlogAnalytics = {
      period: { start: startDate, end: endDate },
      overview: {
        totalPosts: posts.length,
        totalViews: posts.reduce((sum, post) => sum + (post.metrics?.views || 0), 0),
        uniqueVisitors: 0, // Would come from analytics service
        avgTimeOnSite: 0,
        bounceRate: 0,
        pagesPerSession: 0,
        conversionRate: 0,
      },
      topPosts: posts
        .sort((a, b) => (b.metrics?.views || 0) - (a.metrics?.views || 0))
        .slice(0, 10)
        .map(post => ({
          postId: post.id,
          title: post.title,
          views: post.metrics?.views || 0,
          engagementScore: post.metrics?.engagementScore || 0,
          conversionRate: post.metrics?.conversionRate || 0,
        })),
      topCategories: [],
      topKeywords: [],
      audienceInsights: {
        demographics: {
          ageGroups: {},
          countries: {},
          devices: {},
        },
        behavior: {
          returningVisitors: 0,
          avgSessionDuration: 0,
          mostPopularTimes: {},
        },
      },
      seoMetrics: {
        organicTraffic: 0,
        avgPosition: 0,
        impressions: 0,
        clickThroughRate: 0,
        featuredSnippets: 0,
        backlinks: 0,
      },
      socialMetrics: {
        totalShares: 0,
        sharesByPlatform: {},
        socialTraffic: 0,
        viralityScore: 0,
      },
    };

    return analytics;
  }

  public generateSitemap(): string {
    const posts = Array.from(this.posts.values())
      .filter(post => post.status === 'published');
    
    const urls = posts.map(post => {
      const lastmod = post.updatedAt.toISOString().split('T')[0];
      return `
  <url>
    <loc>https://blog.activelog.com/${post.slug}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`;
    }).join('');

    return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${urls}
</urlset>`;
  }

  public generateRSSFeed(): string {
    const posts = Array.from(this.posts.values())
      .filter(post => post.status === 'published')
      .sort((a, b) => (b.publishedAt?.getTime() || 0) - (a.publishedAt?.getTime() || 0))
      .slice(0, 20);

    const items = posts.map(post => `
    <item>
      <title><![CDATA[${post.title}]]></title>
      <description><![CDATA[${post.excerpt}]]></description>
      <link>https://blog.activelog.com/${post.slug}</link>
      <guid>https://blog.activelog.com/${post.slug}</guid>
      <pubDate>${post.publishedAt?.toUTCString()}</pubDate>
      <author>${post.author.name}</author>
      <category><![CDATA[${post.category.name}]]></category>
    </item>`).join('');

    return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>ActiveLog Blog</title>
    <description>The latest insights on productivity, personal growth, and digital organization</description>
    <link>https://blog.activelog.com</link>
    <language>en-US</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    ${items}
  </channel>
</rss>`;
  }

  private convertMarkdownToHtml(markdown: string): string {
    return marked(markdown, {
      highlight: (code, lang) => {
        // Would integrate with syntax highlighter
        return `<pre><code class="language-${lang}">${code}</code></pre>`;
      },
      breaks: true,
      gfm: true,
    });
  }

  private generateSEOData(title: string, content: string): BlogPost['seo'] {
    // Extract keywords from content (simplified)
    const words = content.toLowerCase().split(/\W+/);
    const wordFreq = words.reduce((freq, word) => {
      if (word.length > 4) {
        freq[word] = (freq[word] || 0) + 1;
      }
      return freq;
    }, {} as Record<string, number>);

    const keywords = Object.entries(wordFreq)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([word]) => word);

    return {
      metaTitle: title,
      metaDescription: content.substring(0, 160).replace(/\n/g, ' '),
      keywords,
    };
  }

  private getContentIdeasForCategory(category: string, appVariant?: string) {
    // This would typically integrate with SEO tools and competitor analysis
    const baseIdeas = [
      {
        title: `10 ${category} Tips for Beginners`,
        type: 'listicle' as const,
        keywords: [`${category} tips`, 'beginner guide'],
        estimatedTraffic: 1200,
        difficulty: 'easy' as const,
        targetAudience: 'new users',
      },
      {
        title: `How to Master ${category} in 30 Days`,
        type: 'how-to' as const,
        keywords: [`${category} guide`, 'master', '30 days'],
        estimatedTraffic: 800,
        difficulty: 'medium' as const,
        targetAudience: 'intermediate users',
      },
      {
        title: `Case Study: How ${category} Changed My Life`,
        type: 'case-study' as const,
        keywords: [`${category} case study`, 'success story'],
        estimatedTraffic: 600,
        difficulty: 'medium' as const,
        targetAudience: 'potential customers',
      },
    ];

    return baseIdeas;
  }

  private getPostsInDateRange(startDate: Date, endDate: Date): BlogPost[] {
    return Array.from(this.posts.values()).filter(post => 
      post.publishedAt && 
      post.publishedAt >= startDate && 
      post.publishedAt <= endDate
    );
  }

  private savePostToDisk(post: BlogPost): void {
    const categoryDir = path.join(this.contentDir, post.category.slug);
    if (!fs.existsSync(categoryDir)) {
      fs.mkdirSync(categoryDir, { recursive: true });
    }

    const filePath = path.join(categoryDir, `${post.slug}.md`);
    const frontmatter = `---
title: "${post.title}"
excerpt: "${post.excerpt}"
author: "${post.author.name}"
category: "${post.category.name}"
tags: [${post.tags.map(tag => `"${tag.name}"`).join(', ')}]
publishedAt: ${post.publishedAt?.toISOString() || ''}
featuredImage: "${post.featuredImage.url}"
seo:
  metaTitle: "${post.seo.metaTitle || ''}"
  metaDescription: "${post.seo.metaDescription || ''}"
  keywords: [${post.seo.keywords.map(k => `"${k}"`).join(', ')}]
---

`;

    const fullContent = frontmatter + post.content;
    fs.writeFileSync(filePath, fullContent, 'utf8');
  }

  private initializeDefaultData(): void {
    // Create default categories
    const categories = [
      {
        name: 'Productivity',
        slug: 'productivity',
        description: 'Tips and strategies for better productivity',
        color: '#4CAF50',
      },
      {
        name: 'Personal Growth',
        slug: 'personal-growth',
        description: 'Articles on self-improvement and personal development',
        color: '#2196F3',
      },
      {
        name: 'App Updates',
        slug: 'app-updates',
        description: 'Latest updates and features',
        color: '#FF9800',
      },
      {
        name: 'Tutorials',
        slug: 'tutorials',
        description: 'Step-by-step guides and how-tos',
        color: '#9C27B0',
      },
    ];

    categories.forEach(cat => {
      this.createCategory({
        ...cat,
        isActive: true,
        sortOrder: 0,
        seo: {
          keywords: [cat.name.toLowerCase(), cat.slug],
        },
      });
    });

    // Create default content templates
    const templates = [
      {
        name: 'How-to Guide',
        description: 'Step-by-step tutorial template',
        type: 'how-to' as const,
        structure: [
          { section: 'title', description: 'Main title', placeholder: 'How to [Action] [Outcome]', required: true },
          { section: 'introduction', description: 'Brief introduction', placeholder: 'Introduce the topic and why it matters', required: true },
          { section: 'prerequisites', description: 'What readers need first', placeholder: 'Before you start, you\'ll need...', required: false },
          { section: 'steps', description: 'Main content steps', placeholder: 'Step-by-step instructions', required: true },
          { section: 'conclusion', description: 'Wrap up and next steps', placeholder: 'Summary and what to do next', required: true },
        ],
        autoElements: {
          generateOutline: true,
          suggestImages: true,
          generateSEO: true,
          suggestTags: true,
        },
        targetWordCount: 1200,
        estimatedReadingTime: 6,
        isActive: true,
      },
      {
        name: 'Listicle',
        description: 'Number-based article template',
        type: 'listicle' as const,
        structure: [
          { section: 'title', description: 'List title with number', placeholder: 'X [Things] That [Benefit]', required: true },
          { section: 'introduction', description: 'Brief intro', placeholder: 'Why this list matters', required: true },
          { section: 'items', description: 'List items', placeholder: 'Each numbered item with explanation', required: true },
          { section: 'conclusion', description: 'Summary', placeholder: 'Key takeaways and call to action', required: true },
        ],
        autoElements: {
          generateOutline: true,
          suggestImages: false,
          generateSEO: true,
          suggestTags: true,
        },
        targetWordCount: 800,
        estimatedReadingTime: 4,
        isActive: true,
      },
    ];

    templates.forEach(template => {
      this.createTemplate(template);
    });
  }

  // Public getters for accessing data
  public getPosts(filters?: {
    status?: BlogPost['status'];
    categoryId?: string;
    authorId?: string;
    tags?: string[];
  }): BlogPost[] {
    let posts = Array.from(this.posts.values());
    
    if (filters?.status) {
      posts = posts.filter(post => post.status === filters.status);
    }
    
    if (filters?.categoryId) {
      posts = posts.filter(post => post.category.id === filters.categoryId);
    }
    
    if (filters?.authorId) {
      posts = posts.filter(post => post.author.id === filters.authorId);
    }
    
    if (filters?.tags && filters.tags.length > 0) {
      posts = posts.filter(post => 
        post.tags.some(tag => filters.tags!.includes(tag.id))
      );
    }
    
    return posts.sort((a, b) => (b.publishedAt?.getTime() || 0) - (a.publishedAt?.getTime() || 0));
  }

  public getCategories(): BlogCategory[] {
    return Array.from(this.categories.values())
      .sort((a, b) => a.sortOrder - b.sortOrder);
  }

  public getTemplates(): ContentTemplate[] {
    return Array.from(this.templates.values())
      .filter(template => template.isActive);
  }

  public getCalendars(): ContentCalendar[] {
    return Array.from(this.calendars.values());
  }
}

export default BlogSystem;