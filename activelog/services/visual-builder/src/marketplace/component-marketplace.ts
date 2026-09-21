import { EventEmitter } from 'events';
import { ComponentDefinition } from '../builder/drag-drop-builder.js';

export interface MarketplaceComponent {
  id: string;
  definition: ComponentDefinition;
  metadata: ComponentMetadata;
  publisher: PublisherInfo;
  pricing: PricingInfo;
  stats: ComponentStats;
  reviews: ComponentReview[];
  documentation: ComponentDocumentation;
  versions: ComponentVersion[];
  dependencies: ComponentDependency[];
  compatibility: CompatibilityInfo;
  certification: CertificationInfo;
  support: SupportInfo;
}

export interface ComponentMetadata {
  createdAt: Date;
  updatedAt: Date;
  publishedAt: Date;
  downloadCount: number;
  rating: number;
  reviewCount: number;
  featured: boolean;
  trending: boolean;
  status: ComponentStatus;
  license: LicenseInfo;
  screenshots: string[];
  demoUrl?: string;
  sourceUrl?: string;
  keywords: string[];
  frameworks: string[];
  platforms: string[];
  maturityLevel: MaturityLevel;
}

export enum ComponentStatus {
  DRAFT = 'draft',
  PENDING_REVIEW = 'pending_review',
  APPROVED = 'approved',
  PUBLISHED = 'published',
  DEPRECATED = 'deprecated',
  REMOVED = 'removed'
}

export enum MaturityLevel {
  EXPERIMENTAL = 'experimental',
  BETA = 'beta',
  STABLE = 'stable',
  MATURE = 'mature',
  LEGACY = 'legacy'
}

export interface PublisherInfo {
  id: string;
  name: string;
  displayName: string;
  avatar?: string;
  email: string;
  website?: string;
  verified: boolean;
  reputation: number;
  totalComponents: number;
  totalDownloads: number;
  memberSince: Date;
  badges: PublisherBadge[];
  socialLinks: SocialLink[];
}

export interface PublisherBadge {
  type: BadgeType;
  name: string;
  description: string;
  earnedAt: Date;
  icon: string;
}

export enum BadgeType {
  VERIFIED = 'verified',
  TOP_CONTRIBUTOR = 'top_contributor',
  QUALITY_AUTHOR = 'quality_author',
  COMMUNITY_CHAMPION = 'community_champion',
  EARLY_ADOPTER = 'early_adopter'
}

export interface SocialLink {
  platform: string;
  url: string;
  verified: boolean;
}

export interface PricingInfo {
  model: PricingModel;
  price: number;
  currency: string;
  billingPeriod?: BillingPeriod;
  trialPeriod?: number;
  features: PricingTier[];
  discounts: PricingDiscount[];
}

export enum PricingModel {
  FREE = 'free',
  PAID = 'paid',
  FREEMIUM = 'freemium',
  SUBSCRIPTION = 'subscription',
  PAY_PER_USE = 'pay_per_use',
  ENTERPRISE = 'enterprise'
}

export enum BillingPeriod {
  MONTHLY = 'monthly',
  YEARLY = 'yearly',
  ONE_TIME = 'one_time'
}

export interface PricingTier {
  name: string;
  price: number;
  features: string[];
  limitations: string[];
}

export interface PricingDiscount {
  type: DiscountType;
  value: number;
  condition: string;
  validUntil?: Date;
}

export enum DiscountType {
  PERCENTAGE = 'percentage',
  FIXED_AMOUNT = 'fixed_amount',
  BULK_DISCOUNT = 'bulk_discount',
  EARLY_BIRD = 'early_bird'
}

export interface ComponentStats {
  downloads: {
    total: number;
    lastMonth: number;
    lastWeek: number;
    daily: number[];
  };
  usage: {
    activeInstalls: number;
    projectsUsing: number;
    averageRating: number;
    retentionRate: number;
  };
  performance: {
    loadTime: number;
    bundleSize: number;
    renderTime: number;
    memoryUsage: number;
  };
  quality: {
    bugReports: number;
    fixedIssues: number;
    testCoverage: number;
    codeQuality: number;
  };
}

export interface ComponentReview {
  id: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  rating: number;
  title: string;
  content: string;
  pros: string[];
  cons: string[];
  createdAt: Date;
  updatedAt: Date;
  verified: boolean;
  helpful: number;
  version: string;
  replies: ReviewReply[];
}

export interface ReviewReply {
  id: string;
  userId: string;
  userName: string;
  content: string;
  createdAt: Date;
  isPublisher: boolean;
}

export interface ComponentDocumentation {
  readme: string;
  changelog: string;
  apiReference: APIReference[];
  examples: CodeExample[];
  tutorials: Tutorial[];
  faq: FAQ[];
  troubleshooting: TroubleshootingGuide[];
}

export interface APIReference {
  name: string;
  type: 'property' | 'method' | 'event' | 'slot';
  description: string;
  parameters?: Parameter[];
  returns?: ReturnInfo;
  examples: string[];
  since: string;
  deprecated?: DeprecationInfo;
}

export interface Parameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
  defaultValue?: any;
}

export interface ReturnInfo {
  type: string;
  description: string;
}

export interface DeprecationInfo {
  since: string;
  replacement?: string;
  reason: string;
}

export interface CodeExample {
  id: string;
  title: string;
  description: string;
  code: string;
  language: string;
  framework?: string;
  runnable: boolean;
  complexity: 'beginner' | 'intermediate' | 'advanced';
}

export interface Tutorial {
  id: string;
  title: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedTime: number;
  steps: TutorialStep[];
  prerequisites: string[];
  outcomes: string[];
}

export interface TutorialStep {
  id: string;
  title: string;
  description: string;
  code?: string;
  image?: string;
  video?: string;
  interactive: boolean;
}

export interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: string;
  helpful: number;
  updatedAt: Date;
}

export interface TroubleshootingGuide {
  id: string;
  problem: string;
  symptoms: string[];
  causes: string[];
  solutions: Solution[];
  relatedIssues: string[];
}

export interface Solution {
  description: string;
  steps: string[];
  code?: string;
  difficulty: 'easy' | 'moderate' | 'hard';
  effectiveness: number;
}

export interface ComponentVersion {
  version: string;
  releaseDate: Date;
  changelog: string;
  breaking: boolean;
  deprecated: boolean;
  downloadUrl: string;
  checksum: string;
  compatibility: string[];
  requirements: SystemRequirement[];
}

export interface SystemRequirement {
  type: 'framework' | 'library' | 'node' | 'browser';
  name: string;
  version: string;
  optional: boolean;
}

export interface ComponentDependency {
  name: string;
  version: string;
  type: DependencyType;
  optional: boolean;
  reason: string;
}

export enum DependencyType {
  RUNTIME = 'runtime',
  DEV = 'dev',
  PEER = 'peer',
  OPTIONAL = 'optional'
}

export interface CompatibilityInfo {
  frameworks: FrameworkCompatibility[];
  browsers: BrowserCompatibility[];
  devices: DeviceCompatibility[];
  environments: EnvironmentCompatibility[];
}

export interface FrameworkCompatibility {
  name: string;
  versions: string[];
  status: 'supported' | 'partial' | 'not_supported';
  notes?: string;
}

export interface BrowserCompatibility {
  name: string;
  versions: string[];
  features: string[];
  polyfills?: string[];
}

export interface DeviceCompatibility {
  type: 'desktop' | 'tablet' | 'mobile' | 'tv' | 'watch';
  responsive: boolean;
  touchSupport: boolean;
  performance: 'excellent' | 'good' | 'fair' | 'poor';
}

export interface EnvironmentCompatibility {
  type: 'development' | 'staging' | 'production';
  requirements: string[];
  limitations: string[];
}

export interface CertificationInfo {
  certified: boolean;
  certifiedBy: string;
  certificationDate?: Date;
  certificationLevel: CertificationLevel;
  securityAudit: boolean;
  performanceAudit: boolean;
  accessibilityAudit: boolean;
  qualityScore: number;
}

export enum CertificationLevel {
  BASIC = 'basic',
  STANDARD = 'standard',
  PREMIUM = 'premium',
  ENTERPRISE = 'enterprise'
}

export interface SupportInfo {
  channels: SupportChannel[];
  responseTime: ResponseTime;
  availability: SupportAvailability;
  languages: string[];
  documentation: boolean;
  community: boolean;
  priority: boolean;
}

export interface SupportChannel {
  type: 'email' | 'chat' | 'phone' | 'forum' | 'ticket';
  contact: string;
  available: boolean;
  cost: 'free' | 'paid' | 'premium';
}

export interface ResponseTime {
  first: string;
  resolution: string;
  guaranteed: boolean;
}

export interface SupportAvailability {
  timezone: string;
  hours: string;
  days: string[];
  holidays: boolean;
}

export interface LicenseInfo {
  type: LicenseType;
  name: string;
  url: string;
  commercial: boolean;
  opensource: boolean;
  attribution: boolean;
  modification: boolean;
  distribution: boolean;
  privateUse: boolean;
  warranty: boolean;
  liability: boolean;
}

export enum LicenseType {
  MIT = 'mit',
  APACHE = 'apache',
  GPL = 'gpl',
  BSD = 'bsd',
  PROPRIETARY = 'proprietary',
  CREATIVE_COMMONS = 'creative_commons',
  CUSTOM = 'custom'
}

export interface MarketplaceFilter {
  categories?: string[];
  pricing?: PricingModel[];
  rating?: number;
  verified?: boolean;
  frameworks?: string[];
  platforms?: string[];
  maturity?: MaturityLevel[];
  features?: string[];
  sortBy?: SortOption;
  sortOrder?: 'asc' | 'desc';
  search?: string;
}

export enum SortOption {
  RELEVANCE = 'relevance',
  POPULARITY = 'popularity',
  RATING = 'rating',
  DOWNLOADS = 'downloads',
  RECENT = 'recent',
  PRICE = 'price',
  NAME = 'name'
}

export interface MarketplaceSearchResult {
  components: MarketplaceComponent[];
  totalCount: number;
  page: number;
  pageSize: number;
  facets: SearchFacet[];
  suggestions: string[];
  relatedSearches: string[];
}

export interface SearchFacet {
  field: string;
  values: FacetValue[];
}

export interface FacetValue {
  value: string;
  count: number;
  selected: boolean;
}

export interface ComponentCollection {
  id: string;
  name: string;
  description: string;
  curator: string;
  components: string[];
  featured: boolean;
  createdAt: Date;
  updatedAt: Date;
  followers: number;
  tags: string[];
}

export interface InstallationInfo {
  componentId: string;
  version: string;
  installedAt: Date;
  installPath: string;
  configuration: Record<string, any>;
  dependencies: string[];
  updateAvailable: boolean;
  lastUsed?: Date;
  usage: ComponentUsage;
}

export interface ComponentUsage {
  projectCount: number;
  instanceCount: number;
  lastAccessed: Date;
  totalRenderTime: number;
  errorCount: number;
  performanceScore: number;
}

export class ComponentMarketplace extends EventEmitter {
  private components: Map<string, MarketplaceComponent> = new Map();
  private collections: Map<string, ComponentCollection> = new Map();
  private installedComponents: Map<string, InstallationInfo> = new Map();
  private publishers: Map<string, PublisherInfo> = new Map();
  private userPreferences: UserPreferences = {};
  private cache: Map<string, any> = new Map();

  constructor() {
    super();
    this.initializeMarketplace();
  }

  private initializeMarketplace(): void {
    // Initialize with some featured components
    this.loadFeaturedComponents();
    this.loadPublishers();
    this.loadCollections();
  }

  private loadFeaturedComponents(): void {
    const featuredComponents: MarketplaceComponent[] = [
      {
        id: 'advanced-data-table',
        definition: {
          id: 'advanced-data-table',
          name: 'Advanced Data Table',
          category: 'data_display' as any,
          version: '2.1.0',
          description: 'A powerful data table component with sorting, filtering, pagination, and more',
          icon: 'table',
          tags: ['table', 'data', 'grid', 'sorting', 'filtering'],
          properties: [],
          events: [],
          slots: [],
          isContainer: false,
          isLeaf: true,
          defaultProps: {},
          styles: {},
          responsiveBreakpoints: [],
          accessibility: {
            keyboardNavigation: true,
            screenReaderSupport: true,
            highContrast: true
          },
          seo: {},
          performance: {
            lazyLoad: true,
            critical: false,
            preload: false,
            caching: 'browser' as any,
            bundleSize: 15000,
            renderTime: 5
          }
        },
        metadata: {
          createdAt: new Date('2023-01-15'),
          updatedAt: new Date('2024-01-10'),
          publishedAt: new Date('2023-02-01'),
          downloadCount: 125000,
          rating: 4.8,
          reviewCount: 342,
          featured: true,
          trending: true,
          status: ComponentStatus.PUBLISHED,
          license: {
            type: LicenseType.MIT,
            name: 'MIT License',
            url: 'https://opensource.org/licenses/MIT',
            commercial: true,
            opensource: true,
            attribution: true,
            modification: true,
            distribution: true,
            privateUse: true,
            warranty: false,
            liability: false
          },
          screenshots: [
            '/screenshots/data-table-1.png',
            '/screenshots/data-table-2.png'
          ],
          demoUrl: 'https://demo.example.com/data-table',
          keywords: ['table', 'data', 'grid', 'enterprise'],
          frameworks: ['react', 'vue', 'angular'],
          platforms: ['web', 'mobile'],
          maturityLevel: MaturityLevel.STABLE
        },
        publisher: {
          id: 'datavis-pro',
          name: 'datavis-pro',
          displayName: 'DataVis Pro',
          email: 'contact@datavispro.com',
          website: 'https://datavispro.com',
          verified: true,
          reputation: 95,
          totalComponents: 23,
          totalDownloads: 500000,
          memberSince: new Date('2022-05-10'),
          badges: [
            {
              type: BadgeType.VERIFIED,
              name: 'Verified Publisher',
              description: 'Publisher verified by marketplace team',
              earnedAt: new Date('2022-06-01'),
              icon: 'verified'
            },
            {
              type: BadgeType.QUALITY_AUTHOR,
              name: 'Quality Author',
              description: 'Consistently high-quality components',
              earnedAt: new Date('2023-01-15'),
              icon: 'quality'
            }
          ],
          socialLinks: [
            { platform: 'github', url: 'https://github.com/datavispro', verified: true },
            { platform: 'twitter', url: 'https://twitter.com/datavispro', verified: true }
          ]
        },
        pricing: {
          model: PricingModel.FREEMIUM,
          price: 0,
          currency: 'USD',
          features: [
            {
              name: 'Free',
              price: 0,
              features: ['Basic table', 'Up to 1000 rows', 'Standard themes'],
              limitations: ['No advanced filtering', 'Basic export only']
            },
            {
              name: 'Pro',
              price: 29,
              features: ['Advanced filtering', 'Unlimited rows', 'Custom themes', 'Excel export'],
              limitations: []
            }
          ],
          discounts: [
            {
              type: DiscountType.PERCENTAGE,
              value: 20,
              condition: 'Annual subscription',
              validUntil: new Date('2024-12-31')
            }
          ]
        },
        stats: {
          downloads: {
            total: 125000,
            lastMonth: 8500,
            lastWeek: 2100,
            daily: [350, 420, 380, 510, 460, 320, 280]
          },
          usage: {
            activeInstalls: 45000,
            projectsUsing: 12000,
            averageRating: 4.8,
            retentionRate: 0.85
          },
          performance: {
            loadTime: 150,
            bundleSize: 15000,
            renderTime: 5,
            memoryUsage: 2048
          },
          quality: {
            bugReports: 12,
            fixedIssues: 45,
            testCoverage: 92,
            codeQuality: 8.7
          }
        },
        reviews: [],
        documentation: {
          readme: '# Advanced Data Table\n\nA powerful and flexible data table component...',
          changelog: '## v2.1.0\n- Added virtual scrolling\n- Improved performance...',
          apiReference: [],
          examples: [],
          tutorials: [],
          faq: [],
          troubleshooting: []
        },
        versions: [
          {
            version: '2.1.0',
            releaseDate: new Date('2024-01-10'),
            changelog: 'Added virtual scrolling and performance improvements',
            breaking: false,
            deprecated: false,
            downloadUrl: 'https://cdn.example.com/data-table-2.1.0.zip',
            checksum: 'sha256:abc123...',
            compatibility: ['react@16+', 'vue@3+'],
            requirements: [
              { type: 'framework', name: 'react', version: '>=16.0.0', optional: false },
              { type: 'browser', name: 'chrome', version: '>=80', optional: false }
            ]
          }
        ],
        dependencies: [
          { name: 'react', version: '>=16.0.0', type: DependencyType.PEER, optional: false, reason: 'UI framework' },
          { name: 'lodash', version: '^4.17.0', type: DependencyType.RUNTIME, optional: false, reason: 'Utility functions' }
        ],
        compatibility: {
          frameworks: [
            { name: 'React', versions: ['16.x', '17.x', '18.x'], status: 'supported' },
            { name: 'Vue', versions: ['3.x'], status: 'supported' },
            { name: 'Angular', versions: ['14+'], status: 'partial', notes: 'Wrapper required' }
          ],
          browsers: [
            { name: 'Chrome', versions: ['80+'], features: ['all'], polyfills: [] },
            { name: 'Firefox', versions: ['75+'], features: ['all'], polyfills: [] },
            { name: 'Safari', versions: ['13+'], features: ['most'], polyfills: ['ResizeObserver'] }
          ],
          devices: [
            { type: 'desktop', responsive: true, touchSupport: false, performance: 'excellent' },
            { type: 'tablet', responsive: true, touchSupport: true, performance: 'good' },
            { type: 'mobile', responsive: true, touchSupport: true, performance: 'fair' }
          ],
          environments: [
            { type: 'development', requirements: ['Node.js 14+'], limitations: [] },
            { type: 'production', requirements: ['Modern browser'], limitations: ['Large dataset performance'] }
          ]
        },
        certification: {
          certified: true,
          certifiedBy: 'Marketplace Team',
          certificationDate: new Date('2023-12-15'),
          certificationLevel: CertificationLevel.PREMIUM,
          securityAudit: true,
          performanceAudit: true,
          accessibilityAudit: true,
          qualityScore: 9.2
        },
        support: {
          channels: [
            { type: 'email', contact: 'support@datavispro.com', available: true, cost: 'free' },
            { type: 'chat', contact: 'https://chat.datavispro.com', available: true, cost: 'paid' }
          ],
          responseTime: {
            first: '24 hours',
            resolution: '3 business days',
            guaranteed: true
          },
          availability: {
            timezone: 'UTC',
            hours: '9 AM - 6 PM',
            days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            holidays: false
          },
          languages: ['English', 'Spanish', 'German'],
          documentation: true,
          community: true,
          priority: true
        }
      }
    ];

    featuredComponents.forEach(component => {
      this.components.set(component.id, component);
    });
  }

  private loadPublishers(): void {
    // Load publisher information
    const publishers: PublisherInfo[] = [
      {
        id: 'datavis-pro',
        name: 'datavis-pro',
        displayName: 'DataVis Pro',
        email: 'contact@datavispro.com',
        website: 'https://datavispro.com',
        verified: true,
        reputation: 95,
        totalComponents: 23,
        totalDownloads: 500000,
        memberSince: new Date('2022-05-10'),
        badges: [],
        socialLinks: []
      }
    ];

    publishers.forEach(publisher => {
      this.publishers.set(publisher.id, publisher);
    });
  }

  private loadCollections(): void {
    const collections: ComponentCollection[] = [
      {
        id: 'data-visualization',
        name: 'Data Visualization Essentials',
        description: 'Essential components for data visualization and analytics',
        curator: 'marketplace-team',
        components: ['advanced-data-table', 'chart-builder', 'metrics-dashboard'],
        featured: true,
        createdAt: new Date('2023-06-01'),
        updatedAt: new Date('2024-01-15'),
        followers: 1250,
        tags: ['data', 'visualization', 'charts', 'analytics']
      }
    ];

    collections.forEach(collection => {
      this.collections.set(collection.id, collection);
    });
  }

  // Search and Discovery
  public async searchComponents(
    filter: MarketplaceFilter,
    page = 1,
    pageSize = 20
  ): Promise<MarketplaceSearchResult> {
    const cacheKey = `search_${JSON.stringify(filter)}_${page}_${pageSize}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < 300000) { // 5 min cache
      return cached.data;
    }

    let filteredComponents = Array.from(this.components.values());

    // Apply filters
    if (filter.categories?.length) {
      filteredComponents = filteredComponents.filter(comp =>
        filter.categories!.includes(comp.definition.category)
      );
    }

    if (filter.pricing?.length) {
      filteredComponents = filteredComponents.filter(comp =>
        filter.pricing!.includes(comp.pricing.model)
      );
    }

    if (filter.rating) {
      filteredComponents = filteredComponents.filter(comp =>
        comp.metadata.rating >= filter.rating!
      );
    }

    if (filter.verified !== undefined) {
      filteredComponents = filteredComponents.filter(comp =>
        comp.publisher.verified === filter.verified
      );
    }

    if (filter.frameworks?.length) {
      filteredComponents = filteredComponents.filter(comp =>
        filter.frameworks!.some(framework =>
          comp.metadata.frameworks.includes(framework)
        )
      );
    }

    if (filter.search) {
      const searchTerm = filter.search.toLowerCase();
      filteredComponents = filteredComponents.filter(comp =>
        comp.definition.name.toLowerCase().includes(searchTerm) ||
        comp.definition.description.toLowerCase().includes(searchTerm) ||
        comp.definition.tags.some(tag => tag.toLowerCase().includes(searchTerm))
      );
    }

    // Apply sorting
    if (filter.sortBy) {
      filteredComponents.sort((a, b) => {
        let comparison = 0;
        
        switch (filter.sortBy) {
          case SortOption.POPULARITY:
            comparison = b.stats.downloads.total - a.stats.downloads.total;
            break;
          case SortOption.RATING:
            comparison = b.metadata.rating - a.metadata.rating;
            break;
          case SortOption.RECENT:
            comparison = b.metadata.updatedAt.getTime() - a.metadata.updatedAt.getTime();
            break;
          case SortOption.PRICE:
            comparison = a.pricing.price - b.pricing.price;
            break;
          case SortOption.NAME:
            comparison = a.definition.name.localeCompare(b.definition.name);
            break;
          default:
            comparison = 0;
        }

        return filter.sortOrder === 'desc' ? comparison : -comparison;
      });
    }

    // Pagination
    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const paginatedComponents = filteredComponents.slice(startIndex, endIndex);

    // Generate facets
    const facets = this.generateSearchFacets(filteredComponents);
    
    // Generate suggestions (simplified)
    const suggestions = filter.search 
      ? this.generateSearchSuggestions(filter.search)
      : [];

    const result: MarketplaceSearchResult = {
      components: paginatedComponents,
      totalCount: filteredComponents.length,
      page,
      pageSize,
      facets,
      suggestions,
      relatedSearches: []
    };

    // Cache result
    this.cache.set(cacheKey, {
      data: result,
      timestamp: Date.now()
    });

    return result;
  }

  private generateSearchFacets(components: MarketplaceComponent[]): SearchFacet[] {
    const categoryFacet: SearchFacet = {
      field: 'category',
      values: this.calculateFacetValues(
        components.map(c => c.definition.category),
        'category'
      )
    };

    const pricingFacet: SearchFacet = {
      field: 'pricing',
      values: this.calculateFacetValues(
        components.map(c => c.pricing.model),
        'pricing'
      )
    };

    return [categoryFacet, pricingFacet];
  }

  private calculateFacetValues(values: any[], field: string): FacetValue[] {
    const counts = new Map<string, number>();
    values.forEach(value => {
      counts.set(value, (counts.get(value) || 0) + 1);
    });

    return Array.from(counts.entries()).map(([value, count]) => ({
      value,
      count,
      selected: false
    }));
  }

  private generateSearchSuggestions(searchTerm: string): string[] {
    // Simplified suggestion generation
    const suggestions = [
      'data table',
      'chart component',
      'form builder',
      'navigation menu',
      'modal dialog'
    ];

    return suggestions.filter(suggestion =>
      suggestion.toLowerCase().includes(searchTerm.toLowerCase())
    ).slice(0, 5);
  }

  // Component Management
  public getComponent(componentId: string): MarketplaceComponent | undefined {
    return this.components.get(componentId);
  }

  public getFeaturedComponents(): MarketplaceComponent[] {
    return Array.from(this.components.values()).filter(comp => comp.metadata.featured);
  }

  public getTrendingComponents(): MarketplaceComponent[] {
    return Array.from(this.components.values()).filter(comp => comp.metadata.trending);
  }

  public getComponentsByPublisher(publisherId: string): MarketplaceComponent[] {
    return Array.from(this.components.values()).filter(comp => comp.publisher.id === publisherId);
  }

  public getRecommendedComponents(baseComponentId: string, limit = 10): MarketplaceComponent[] {
    const baseComponent = this.components.get(baseComponentId);
    if (!baseComponent) return [];

    // Simple recommendation based on category and tags
    const recommendations = Array.from(this.components.values())
      .filter(comp => comp.id !== baseComponentId)
      .map(comp => ({
        component: comp,
        score: this.calculateRecommendationScore(baseComponent, comp)
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map(item => item.component);

    return recommendations;
  }

  private calculateRecommendationScore(base: MarketplaceComponent, candidate: MarketplaceComponent): number {
    let score = 0;

    // Category match
    if (base.definition.category === candidate.definition.category) {
      score += 30;
    }

    // Tag overlap
    const baseTags = new Set(base.definition.tags);
    const candidateTags = new Set(candidate.definition.tags);
    const tagOverlap = [...baseTags].filter(tag => candidateTags.has(tag)).length;
    score += tagOverlap * 10;

    // Publisher reputation
    score += candidate.publisher.reputation * 0.1;

    // Rating
    score += candidate.metadata.rating * 5;

    // Popularity
    score += Math.log10(candidate.stats.downloads.total + 1) * 2;

    return score;
  }

  // Installation and Management
  public async installComponent(
    componentId: string,
    version?: string,
    configuration?: Record<string, any>
  ): Promise<InstallationInfo> {
    const component = this.components.get(componentId);
    if (!component) {
      throw new Error(`Component not found: ${componentId}`);
    }

    const targetVersion = version || component.definition.version;
    const versionInfo = component.versions.find(v => v.version === targetVersion);
    
    if (!versionInfo) {
      throw new Error(`Version not found: ${targetVersion}`);
    }

    // Simulate installation process
    await this.downloadComponent(versionInfo.downloadUrl);
    await this.installDependencies(component.dependencies);
    await this.configureComponent(componentId, configuration || {});

    const installation: InstallationInfo = {
      componentId,
      version: targetVersion,
      installedAt: new Date(),
      installPath: `/components/${componentId}`,
      configuration: configuration || {},
      dependencies: component.dependencies.map(dep => dep.name),
      updateAvailable: false,
      usage: {
        projectCount: 0,
        instanceCount: 0,
        lastAccessed: new Date(),
        totalRenderTime: 0,
        errorCount: 0,
        performanceScore: 100
      }
    };

    this.installedComponents.set(componentId, installation);
    this.emit('componentInstalled', installation);

    return installation;
  }

  private async downloadComponent(url: string): Promise<void> {
    // Simulate download
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  private async installDependencies(dependencies: ComponentDependency[]): Promise<void> {
    // Simulate dependency installation
    for (const dep of dependencies) {
      if (!dep.optional) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  }

  private async configureComponent(componentId: string, configuration: Record<string, any>): Promise<void> {
    // Simulate configuration
    await new Promise(resolve => setTimeout(resolve, 200));
  }

  public async uninstallComponent(componentId: string): Promise<boolean> {
    const installation = this.installedComponents.get(componentId);
    if (!installation) return false;

    // Check for dependencies
    const dependents = this.findDependentComponents(componentId);
    if (dependents.length > 0) {
      throw new Error(`Cannot uninstall: Component is used by ${dependents.join(', ')}`);
    }

    // Simulate uninstallation
    await new Promise(resolve => setTimeout(resolve, 500));
    
    this.installedComponents.delete(componentId);
    this.emit('componentUninstalled', componentId);

    return true;
  }

  private findDependentComponents(componentId: string): string[] {
    const dependents: string[] = [];
    
    for (const [id, installation] of this.installedComponents) {
      if (installation.dependencies.includes(componentId)) {
        dependents.push(id);
      }
    }

    return dependents;
  }

  public getInstalledComponents(): InstallationInfo[] {
    return Array.from(this.installedComponents.values());
  }

  public checkForUpdates(): string[] {
    const updatesAvailable: string[] = [];

    for (const [componentId, installation] of this.installedComponents) {
      const component = this.components.get(componentId);
      if (component && component.definition.version !== installation.version) {
        updatesAvailable.push(componentId);
        installation.updateAvailable = true;
      }
    }

    if (updatesAvailable.length > 0) {
      this.emit('updatesAvailable', updatesAvailable);
    }

    return updatesAvailable;
  }

  // Reviews and Ratings
  public async addReview(
    componentId: string,
    userId: string,
    review: Omit<ComponentReview, 'id' | 'createdAt' | 'updatedAt' | 'replies'>
  ): Promise<ComponentReview> {
    const component = this.components.get(componentId);
    if (!component) {
      throw new Error(`Component not found: ${componentId}`);
    }

    const fullReview: ComponentReview = {
      ...review,
      id: `review_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date(),
      updatedAt: new Date(),
      replies: []
    };

    component.reviews.push(fullReview);
    
    // Update component rating
    this.updateComponentRating(componentId);
    
    this.emit('reviewAdded', fullReview);
    return fullReview;
  }

  private updateComponentRating(componentId: string): void {
    const component = this.components.get(componentId);
    if (!component || component.reviews.length === 0) return;

    const totalRating = component.reviews.reduce((sum, review) => sum + review.rating, 0);
    component.metadata.rating = totalRating / component.reviews.length;
    component.metadata.reviewCount = component.reviews.length;
  }

  // Collections
  public getCollection(collectionId: string): ComponentCollection | undefined {
    return this.collections.get(collectionId);
  }

  public getAllCollections(): ComponentCollection[] {
    return Array.from(this.collections.values());
  }

  public getFeaturedCollections(): ComponentCollection[] {
    return Array.from(this.collections.values()).filter(collection => collection.featured);
  }

  // Publisher Management
  public getPublisher(publisherId: string): PublisherInfo | undefined {
    return this.publishers.get(publisherId);
  }

  public getTopPublishers(limit = 10): PublisherInfo[] {
    return Array.from(this.publishers.values())
      .sort((a, b) => b.reputation - a.reputation)
      .slice(0, limit);
  }

  // Analytics and Statistics
  public getMarketplaceStats(): {
    totalComponents: number;
    totalDownloads: number;
    averageRating: number;
    topCategories: { category: string; count: number }[];
    recentActivity: any[];
  } {
    const components = Array.from(this.components.values());
    
    const totalComponents = components.length;
    const totalDownloads = components.reduce((sum, comp) => sum + comp.stats.downloads.total, 0);
    const averageRating = components.reduce((sum, comp) => sum + comp.metadata.rating, 0) / totalComponents;

    // Top categories
    const categoryCount = new Map<string, number>();
    components.forEach(comp => {
      const count = categoryCount.get(comp.definition.category) || 0;
      categoryCount.set(comp.definition.category, count + 1);
    });

    const topCategories = Array.from(categoryCount.entries())
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return {
      totalComponents,
      totalDownloads,
      averageRating,
      topCategories,
      recentActivity: [] // Would be populated with real activity data
    };
  }

  // User Preferences and Personalization
  public setUserPreferences(preferences: Partial<UserPreferences>): void {
    Object.assign(this.userPreferences, preferences);
    this.emit('preferencesUpdated', this.userPreferences);
  }

  public getUserPreferences(): UserPreferences {
    return { ...this.userPreferences };
  }

  // Cache Management
  public clearCache(): void {
    this.cache.clear();
    this.emit('cacheCleared');
  }

  public getCacheStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys())
    };
  }
}

interface UserPreferences {
  favoriteCategories?: string[];
  preferredPricing?: PricingModel[];
  autoUpdate?: boolean;
  notifications?: {
    newComponents?: boolean;
    updates?: boolean;
    reviews?: boolean;
  };
  ui?: {
    theme?: 'light' | 'dark' | 'auto';
    density?: 'compact' | 'comfortable' | 'spacious';
    language?: string;
  };
}