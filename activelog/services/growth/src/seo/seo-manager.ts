import { NextSeoProps } from 'next-seo';
import { OpenGraph, Twitter } from 'next-seo/lib/types';

export interface SEOConfig {
  siteName: string;
  siteUrl: string;
  defaultTitle: string;
  defaultDescription: string;
  defaultImage: string;
  twitterHandle: string;
  facebookAppId?: string;
  themeColor: string;
  locale: string;
  alternateLocales?: string[];
}

export interface PageSEOData {
  title: string;
  description: string;
  keywords?: string[];
  image?: string;
  type?: 'website' | 'article' | 'product' | 'profile';
  publishedTime?: string;
  modifiedTime?: string;
  author?: string;
  section?: string;
  tags?: string[];
  noIndex?: boolean;
  noFollow?: boolean;
  canonical?: string;
  alternateUrls?: Record<string, string>;
}

export interface StructuredData {
  '@context': string;
  '@type': string;
  [key: string]: any;
}

class SEOManager {
  private config: SEOConfig;
  private structuredDataCache: Map<string, StructuredData[]> = new Map();

  constructor(config: SEOConfig) {
    this.config = config;
  }

  public generateSEO(path: string, pageData: PageSEOData): NextSeoProps {
    const fullUrl = `${this.config.siteUrl}${path}`;
    const title = pageData.title 
      ? `${pageData.title} | ${this.config.siteName}`
      : this.config.defaultTitle;

    const openGraph: OpenGraph = {
      type: pageData.type || 'website',
      url: fullUrl,
      title: pageData.title || this.config.defaultTitle,
      description: pageData.description || this.config.defaultDescription,
      site_name: this.config.siteName,
      locale: this.config.locale,
      images: [
        {
          url: pageData.image || this.config.defaultImage,
          width: 1200,
          height: 630,
          alt: pageData.title || this.config.defaultTitle,
          type: 'image/png',
        },
      ],
    };

    // Add article-specific OpenGraph data
    if (pageData.type === 'article') {
      openGraph.article = {
        publishedTime: pageData.publishedTime,
        modifiedTime: pageData.modifiedTime,
        author: pageData.author ? [pageData.author] : undefined,
        section: pageData.section,
        tags: pageData.tags,
      };
    }

    const twitter: Twitter = {
      handle: this.config.twitterHandle,
      site: this.config.twitterHandle,
      cardType: 'summary_large_image',
    };

    const seoProps: NextSeoProps = {
      title,
      description: pageData.description || this.config.defaultDescription,
      canonical: pageData.canonical || fullUrl,
      openGraph,
      twitter,
      additionalMetaTags: [
        {
          name: 'keywords',
          content: pageData.keywords?.join(', ') || '',
        },
        {
          name: 'author',
          content: pageData.author || this.config.siteName,
        },
        {
          name: 'theme-color',
          content: this.config.themeColor,
        },
        {
          name: 'application-name',
          content: this.config.siteName,
        },
        {
          name: 'apple-mobile-web-app-title',
          content: this.config.siteName,
        },
        {
          name: 'apple-mobile-web-app-capable',
          content: 'yes',
        },
        {
          name: 'apple-mobile-web-app-status-bar-style',
          content: 'default',
        },
        {
          name: 'mobile-web-app-capable',
          content: 'yes',
        },
        {
          name: 'msapplication-TileColor',
          content: this.config.themeColor,
        },
        {
          name: 'msapplication-config',
          content: '/browserconfig.xml',
        },
      ],
      additionalLinkTags: [
        {
          rel: 'icon',
          href: '/favicon.ico',
        },
        {
          rel: 'apple-touch-icon',
          href: '/apple-touch-icon.png',
          sizes: '180x180',
        },
        {
          rel: 'manifest',
          href: '/manifest.json',
        },
      ],
    };

    // Add noindex/nofollow if specified
    if (pageData.noIndex || pageData.noFollow) {
      const robotsContent = [
        pageData.noIndex ? 'noindex' : 'index',
        pageData.noFollow ? 'nofollow' : 'follow',
      ].join(', ');

      seoProps.additionalMetaTags?.push({
        name: 'robots',
        content: robotsContent,
      });
    }

    // Add alternate language links
    if (pageData.alternateUrls) {
      const alternateLinkTags = Object.entries(pageData.alternateUrls).map(([lang, url]) => ({
        rel: 'alternate',
        hrefLang: lang,
        href: url,
      }));
      seoProps.additionalLinkTags?.push(...alternateLinkTags);
    }

    return seoProps;
  }

  public generateStructuredData(type: string, data: any): StructuredData {
    const baseData: StructuredData = {
      '@context': 'https://schema.org',
      '@type': type,
    };

    switch (type) {
      case 'WebSite':
        return {
          ...baseData,
          name: this.config.siteName,
          url: this.config.siteUrl,
          potentialAction: {
            '@type': 'SearchAction',
            target: `${this.config.siteUrl}/search?q={search_term_string}`,
            'query-input': 'required name=search_term_string',
          },
          ...data,
        };

      case 'Organization':
        return {
          ...baseData,
          name: this.config.siteName,
          url: this.config.siteUrl,
          logo: `${this.config.siteUrl}/logo.png`,
          sameAs: data.socialProfiles || [],
          contactPoint: {
            '@type': 'ContactPoint',
            telephone: data.phone,
            contactType: 'customer service',
            email: data.email,
          },
          ...data,
        };

      case 'Article':
        return {
          ...baseData,
          headline: data.title,
          description: data.description,
          image: data.image,
          author: {
            '@type': 'Person',
            name: data.author,
          },
          publisher: {
            '@type': 'Organization',
            name: this.config.siteName,
            logo: {
              '@type': 'ImageObject',
              url: `${this.config.siteUrl}/logo.png`,
            },
          },
          datePublished: data.publishedTime,
          dateModified: data.modifiedTime,
          mainEntityOfPage: {
            '@type': 'WebPage',
            '@id': data.url,
          },
          ...data,
        };

      case 'Product':
        return {
          ...baseData,
          name: data.name,
          description: data.description,
          image: data.image,
          brand: {
            '@type': 'Brand',
            name: this.config.siteName,
          },
          offers: {
            '@type': 'Offer',
            url: data.url,
            priceCurrency: data.currency || 'USD',
            price: data.price,
            availability: data.availability || 'https://schema.org/InStock',
            seller: {
              '@type': 'Organization',
              name: this.config.siteName,
            },
          },
          aggregateRating: data.rating ? {
            '@type': 'AggregateRating',
            ratingValue: data.rating.value,
            reviewCount: data.rating.count,
          } : undefined,
          ...data,
        };

      case 'SoftwareApplication':
        return {
          ...baseData,
          name: data.name,
          description: data.description,
          applicationCategory: data.category || 'BusinessApplication',
          operatingSystem: data.operatingSystem || 'iOS, Android, Web',
          offers: {
            '@type': 'Offer',
            price: data.price || '0',
            priceCurrency: data.currency || 'USD',
          },
          aggregateRating: data.rating ? {
            '@type': 'AggregateRating',
            ratingValue: data.rating.value,
            reviewCount: data.rating.count,
          } : undefined,
          ...data,
        };

      case 'HowTo':
        return {
          ...baseData,
          name: data.name,
          description: data.description,
          image: data.image,
          totalTime: data.totalTime,
          estimatedCost: data.estimatedCost,
          supply: data.supplies?.map((supply: string) => ({
            '@type': 'HowToSupply',
            name: supply,
          })),
          tool: data.tools?.map((tool: string) => ({
            '@type': 'HowToTool',
            name: tool,
          })),
          step: data.steps?.map((step: any, index: number) => ({
            '@type': 'HowToStep',
            position: index + 1,
            name: step.name,
            text: step.text,
            image: step.image,
            url: step.url,
          })),
          ...data,
        };

      case 'FAQPage':
        return {
          ...baseData,
          mainEntity: data.faqs?.map((faq: any) => ({
            '@type': 'Question',
            name: faq.question,
            acceptedAnswer: {
              '@type': 'Answer',
              text: faq.answer,
            },
          })),
          ...data,
        };

      case 'BreadcrumbList':
        return {
          ...baseData,
          itemListElement: data.breadcrumbs?.map((crumb: any, index: number) => ({
            '@type': 'ListItem',
            position: index + 1,
            name: crumb.name,
            item: crumb.url,
          })),
          ...data,
        };

      default:
        return { ...baseData, ...data };
    }
  }

  public generateAppSEO(appVariant: string): {
    meta: PageSEOData;
    structuredData: StructuredData[];
  } {
    const appConfigs = {
      'personal-log': {
        title: 'PersonalLog - Digital Journal & Life Tracking App',
        description: 'Transform your journaling with PersonalLog. Track thoughts, moods, and memories with our beautiful, secure digital diary. Start your mindfulness journey today.',
        keywords: ['digital journal', 'diary app', 'mood tracking', 'mindfulness', 'personal growth', 'life logging'],
        category: 'Lifestyle',
        features: ['Rich text editor', 'Mood tracking', 'Photo journals', 'Privacy focused', 'Cross-platform sync'],
      },
      'business-log': {
        title: 'BusinessLog - Professional Task & Project Management',
        description: 'Streamline your business operations with BusinessLog. Manage tasks, track projects, and collaborate with your team. Boost productivity and achieve your goals.',
        keywords: ['business management', 'task management', 'project tracking', 'team collaboration', 'productivity', 'workflow'],
        category: 'Business',
        features: ['Project management', 'Team collaboration', 'Task tracking', 'Analytics dashboard', 'Time tracking'],
      },
      'fitness-log': {
        title: 'FitnessLog - Complete Health & Workout Tracker',
        description: 'Achieve your fitness goals with FitnessLog. Track workouts, monitor nutrition, and visualize progress. Your personal fitness companion for a healthier life.',
        keywords: ['fitness tracker', 'workout log', 'nutrition tracking', 'health app', 'exercise planner', 'fitness goals'],
        category: 'Health & Fitness',
        features: ['Workout tracking', 'Nutrition logging', 'Progress analytics', 'Goal setting', 'Exercise library'],
      },
      'family-log': {
        title: 'FamilyLog - Family Organization & Memory Keeper',
        description: 'Keep your family connected with FamilyLog. Share memories, organize schedules, and create lasting bonds. The perfect app for modern families.',
        keywords: ['family app', 'family organizer', 'memory sharing', 'family calendar', 'photo sharing', 'family bonding'],
        category: 'Lifestyle',
        features: ['Family calendar', 'Memory sharing', 'Photo albums', 'Event planning', 'Family chat'],
      },
      'travel-log': {
        title: 'TravelLog - Travel Planner & Memory Keeper',
        description: 'Document every adventure with TravelLog. Plan trips, track expenses, and preserve memories. Turn your travels into beautiful digital stories.',
        keywords: ['travel planner', 'trip organizer', 'travel diary', 'expense tracker', 'travel memories', 'itinerary planner'],
        category: 'Travel',
        features: ['Trip planning', 'Expense tracking', 'Location mapping', 'Photo journals', 'Travel statistics'],
      },
      'education-log': {
        title: 'EducationLog - Student Planner & Learning Tracker',
        description: 'Excel in your studies with EducationLog. Organize courses, track grades, and plan your academic journey. The ultimate student companion.',
        keywords: ['student planner', 'grade tracker', 'study organizer', 'academic planner', 'course management', 'learning tracker'],
        category: 'Education',
        features: ['Grade tracking', 'Study scheduling', 'Course management', 'Assignment tracking', 'Academic analytics'],
      },
    };

    const config = appConfigs[appVariant as keyof typeof appConfigs];
    if (!config) {
      throw new Error(`Unknown app variant: ${appVariant}`);
    }

    const meta: PageSEOData = {
      title: config.title,
      description: config.description,
      keywords: config.keywords,
      type: 'website',
      image: `${this.config.siteUrl}/images/apps/${appVariant}/og-image.png`,
    };

    const structuredData: StructuredData[] = [
      this.generateStructuredData('SoftwareApplication', {
        name: config.title.split(' - ')[0],
        description: config.description,
        applicationCategory: config.category,
        operatingSystem: 'iOS, Android, Web',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
        featureList: config.features,
        screenshot: `${this.config.siteUrl}/images/apps/${appVariant}/screenshots/`,
        downloadUrl: `${this.config.siteUrl}/${appVariant}/download`,
      }),
      this.generateStructuredData('Organization', {
        name: this.config.siteName,
        description: 'Digital life organization platform',
        foundingDate: '2024',
        founder: {
          '@type': 'Person',
          name: 'ActiveLog Team',
        },
      }),
    ];

    return { meta, structuredData };
  }

  public generateBlogPostSEO(post: {
    title: string;
    excerpt: string;
    content: string;
    author: string;
    publishedAt: string;
    updatedAt?: string;
    tags: string[];
    category: string;
    featuredImage: string;
    slug: string;
  }): { meta: PageSEOData; structuredData: StructuredData[] } {
    const url = `${this.config.siteUrl}/blog/${post.slug}`;
    const wordCount = post.content.split(' ').length;
    const readingTime = Math.ceil(wordCount / 200); // Average reading speed

    const meta: PageSEOData = {
      title: post.title,
      description: post.excerpt,
      keywords: post.tags,
      type: 'article',
      image: post.featuredImage,
      publishedTime: post.publishedAt,
      modifiedTime: post.updatedAt,
      author: post.author,
      section: post.category,
      tags: post.tags,
    };

    const structuredData: StructuredData[] = [
      this.generateStructuredData('Article', {
        headline: post.title,
        description: post.excerpt,
        image: post.featuredImage,
        author: post.author,
        publishedTime: post.publishedAt,
        modifiedTime: post.updatedAt,
        url,
        wordCount,
        timeRequired: `PT${readingTime}M`,
        keywords: post.tags.join(', '),
        articleSection: post.category,
      }),
      this.generateStructuredData('BreadcrumbList', {
        breadcrumbs: [
          { name: 'Home', url: this.config.siteUrl },
          { name: 'Blog', url: `${this.config.siteUrl}/blog` },
          { name: post.category, url: `${this.config.siteUrl}/blog/category/${post.category.toLowerCase()}` },
          { name: post.title, url },
        ],
      }),
    ];

    return { meta, structuredData };
  }

  public generateSitemap(pages: Array<{
    url: string;
    lastModified?: Date;
    changeFrequency?: 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never';
    priority?: number;
  }>): string {
    const urls = pages.map(page => {
      const lastmod = page.lastModified ? page.lastModified.toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
      return `
  <url>
    <loc>${this.config.siteUrl}${page.url}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${page.changeFrequency || 'monthly'}</changefreq>
    <priority>${page.priority || 0.5}</priority>
  </url>`;
    }).join('');

    return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${urls}
</urlset>`;
  }

  public generateRobotsTxt(customRules?: string): string {
    const baseRules = `User-agent: *
Allow: /

Sitemap: ${this.config.siteUrl}/sitemap.xml

# Disallow crawling of admin, api, and private pages
Disallow: /admin/
Disallow: /api/
Disallow: /_next/
Disallow: /private/

# Allow crawling of public assets
Allow: /images/
Allow: /videos/
Allow: /docs/

# Crawl delay (be respectful)
Crawl-delay: 1`;

    return customRules ? `${baseRules}\n\n${customRules}` : baseRules;
  }

  public cacheStructuredData(key: string, data: StructuredData[]): void {
    this.structuredDataCache.set(key, data);
  }

  public getCachedStructuredData(key: string): StructuredData[] | undefined {
    return this.structuredDataCache.get(key);
  }

  public clearCache(): void {
    this.structuredDataCache.clear();
  }
}

export default SEOManager;