import { EventEmitter } from 'events';

export interface DeveloperBox {
  id: string;
  name: string;
  description: string;
  category: 'development' | 'testing' | 'deployment' | 'ai_ml' | 'data_science' | 'gaming' | 'rendering' | 'blockchain';
  subcategory?: string;
  version: string;
  author: string;
  authorId: string;
  tags: string[];
  status: 'draft' | 'published' | 'deprecated' | 'suspended';
  visibility: 'public' | 'private' | 'organization';
  pricing: BoxPricing;
  configuration: BoxConfiguration;
  resources: ResourceRequirements;
  features: BoxFeature[];
  screenshots: BoxScreenshot[];
  documentation: BoxDocumentation;
  reviews: BoxReview[];
  ratings: BoxRating;
  usage: BoxUsage;
  createdAt: Date;
  updatedAt: Date;
  publishedAt?: Date;
  verificationStatus: 'unverified' | 'community_verified' | 'official_verified';
  security: SecurityInfo;
  compatibility: CompatibilityInfo;
  support: SupportInfo;
}

export interface BoxPricing {
  model: 'free' | 'freemium' | 'paid' | 'subscription' | 'usage_based';
  basePrice: number;
  currency: string;
  billingCycle?: 'hourly' | 'daily' | 'monthly' | 'annual';
  tiers?: PricingTier[];
  trialPeriod?: number; // days
  usageMetrics?: UsageMetric[];
}

export interface PricingTier {
  name: string;
  price: number;
  description: string;
  features: string[];
  limits: ResourceLimits;
  recommended?: boolean;
}

export interface UsageMetric {
  name: string;
  unit: string;
  pricePerUnit: number;
  includedAmount?: number;
}

export interface ResourceLimits {
  cpu?: number;
  memory?: number; // GB
  storage?: number; // GB
  gpu?: number;
  network?: number; // GB transfer
  concurrentUsers?: number;
  apiCalls?: number;
}

export interface BoxConfiguration {
  baseImage: string;
  runtime: 'docker' | 'kubernetes' | 'vm' | 'bare_metal';
  ports: PortConfiguration[];
  environment: EnvironmentVariable[];
  volumes: VolumeConfiguration[];
  entrypoint?: string;
  command?: string[];
  healthCheck?: HealthCheckConfiguration;
  networking: NetworkConfiguration;
  init?: InitScript[];
}

export interface PortConfiguration {
  containerPort: number;
  hostPort?: number;
  protocol: 'tcp' | 'udp';
  description: string;
  public?: boolean;
}

export interface EnvironmentVariable {
  name: string;
  value?: string;
  secret?: boolean;
  required: boolean;
  description: string;
  defaultValue?: string;
}

export interface VolumeConfiguration {
  name: string;
  mountPath: string;
  type: 'emptyDir' | 'hostPath' | 'persistentVolume' | 'configMap' | 'secret';
  size?: string;
  accessModes?: string[];
  persistent: boolean;
}

export interface HealthCheckConfiguration {
  type: 'http' | 'tcp' | 'command';
  endpoint?: string;
  port?: number;
  command?: string[];
  initialDelay: number;
  interval: number;
  timeout: number;
  retries: number;
}

export interface NetworkConfiguration {
  type: 'bridge' | 'host' | 'overlay' | 'none';
  customNetworks?: CustomNetwork[];
  dnsConfig?: DnsConfiguration;
  firewallRules?: FirewallRule[];
}

export interface CustomNetwork {
  name: string;
  driver: string;
  options?: Record<string, string>;
}

export interface DnsConfiguration {
  nameservers: string[];
  searches: string[];
  options: string[];
}

export interface FirewallRule {
  direction: 'inbound' | 'outbound';
  protocol: 'tcp' | 'udp' | 'icmp' | 'any';
  port?: number;
  portRange?: [number, number];
  source?: string;
  destination?: string;
  action: 'allow' | 'deny';
}

export interface InitScript {
  name: string;
  stage: 'pre_start' | 'post_start' | 'pre_stop';
  script: string;
  timeout?: number;
}

export interface ResourceRequirements {
  minimum: ComputeResources;
  recommended: ComputeResources;
  maximum?: ComputeResources;
  scalable: boolean;
  autoScaling?: AutoScalingConfig;
}

export interface ComputeResources {
  cpu: {
    cores: number;
    type?: 'x86_64' | 'arm64' | 'any';
    features?: string[];
  };
  memory: {
    amount: number; // GB
    type?: 'DDR4' | 'DDR5' | 'any';
  };
  storage: {
    amount: number; // GB
    type: 'hdd' | 'ssd' | 'nvme' | 'any';
    iops?: number;
  };
  gpu?: {
    count: number;
    type?: 'nvidia' | 'amd' | 'intel' | 'any';
    vram?: number;
    computeCapability?: string;
  };
  network: {
    bandwidth: number; // Mbps
    latency?: number; // ms
  };
}

export interface AutoScalingConfig {
  enabled: boolean;
  minInstances: number;
  maxInstances: number;
  metrics: ScalingMetric[];
  cooldownPeriod: number; // seconds
}

export interface ScalingMetric {
  type: 'cpu' | 'memory' | 'network' | 'custom';
  threshold: number;
  direction: 'up' | 'down';
  metric?: string;
}

export interface BoxFeature {
  name: string;
  description: string;
  category: 'functionality' | 'integration' | 'security' | 'performance' | 'usability';
  icon?: string;
  enabled: boolean;
  configurable: boolean;
  dependencies?: string[];
}

export interface BoxScreenshot {
  id: string;
  url: string;
  caption: string;
  type: 'screenshot' | 'diagram' | 'demo';
  order: number;
}

export interface BoxDocumentation {
  readme: string;
  installation: string;
  configuration: string;
  usage: string;
  api?: string;
  troubleshooting: string;
  changelog: string;
  license: string;
  externalLinks: ExternalLink[];
}

export interface ExternalLink {
  title: string;
  url: string;
  type: 'documentation' | 'demo' | 'source' | 'support' | 'tutorial';
}

export interface BoxReview {
  id: string;
  userId: string;
  username: string;
  rating: number; // 1-5
  title: string;
  content: string;
  pros: string[];
  cons: string[];
  createdAt: Date;
  updatedAt?: Date;
  verified: boolean;
  helpful: number;
  reported: boolean;
  response?: ReviewResponse;
}

export interface ReviewResponse {
  authorId: string;
  content: string;
  createdAt: Date;
}

export interface BoxRating {
  average: number;
  total: number;
  distribution: RatingDistribution;
  breakdown: RatingBreakdown;
}

export interface RatingDistribution {
  1: number;
  2: number;
  3: number;
  4: number;
  5: number;
}

export interface RatingBreakdown {
  functionality: number;
  performance: number;
  documentation: number;
  support: number;
  valueForMoney: number;
}

export interface BoxUsage {
  totalDownloads: number;
  monthlyDownloads: number;
  activeInstances: number;
  totalRuntime: number; // hours
  averageRating: number;
  popularityRank: number;
  trendingScore: number;
  lastUsed: Date;
}

export interface SecurityInfo {
  vulnerabilities: Vulnerability[];
  lastScan: Date;
  securityRating: 'A' | 'B' | 'C' | 'D' | 'F';
  certifications: SecurityCertification[];
  complianceStandards: string[];
  dataHandling: DataHandlingInfo;
}

export interface Vulnerability {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  type: string;
  description: string;
  component: string;
  version: string;
  fixedIn?: string;
  publishedAt: Date;
  acknowledged: boolean;
}

export interface SecurityCertification {
  name: string;
  issuer: string;
  issuedAt: Date;
  expiresAt: Date;
  certificateUrl: string;
}

export interface DataHandlingInfo {
  collectsPersonalData: boolean;
  dataTypes: string[];
  storageLocation: string;
  encryption: boolean;
  retention: string;
  sharing: string;
  gdprCompliant: boolean;
}

export interface CompatibilityInfo {
  platforms: string[];
  operatingSystems: OSCompatibility[];
  architectures: string[];
  runtimeVersions: RuntimeCompatibility[];
  dependencies: Dependency[];
  conflicts: string[];
}

export interface OSCompatibility {
  name: string;
  versions: string[];
  tested: boolean;
}

export interface RuntimeCompatibility {
  runtime: string;
  versions: string[];
  tested: boolean;
}

export interface Dependency {
  name: string;
  version: string;
  type: 'required' | 'optional' | 'development';
  description: string;
}

export interface SupportInfo {
  channels: SupportChannel[];
  responseTime: string;
  languages: string[];
  businessHours: string;
  level: 'community' | 'standard' | 'premium' | 'enterprise';
  documentation: boolean;
  videoTutorials: boolean;
  liveChatSupport: boolean;
}

export interface SupportChannel {
  type: 'email' | 'chat' | 'phone' | 'forum' | 'ticket' | 'discord' | 'slack';
  contact: string;
  availability: string;
  description: string;
}

export interface MarketplaceOrder {
  id: string;
  boxId: string;
  buyerId: string;
  sellerId: string;
  type: 'purchase' | 'subscription' | 'trial';
  status: 'pending' | 'active' | 'completed' | 'cancelled' | 'refunded' | 'expired';
  pricing: {
    plan: string;
    amount: number;
    currency: string;
    billingCycle?: string;
  };
  deployment: DeploymentInfo;
  createdAt: Date;
  activatedAt?: Date;
  expiresAt?: Date;
  cancelledAt?: Date;
  metadata?: Record<string, any>;
}

export interface DeploymentInfo {
  instanceId?: string;
  region: string;
  configuration: Record<string, any>;
  endpoints: DeploymentEndpoint[];
  status: 'deploying' | 'running' | 'stopped' | 'failed';
  resources: AllocatedResources;
  logs?: DeploymentLog[];
}

export interface DeploymentEndpoint {
  name: string;
  url: string;
  type: 'http' | 'https' | 'websocket' | 'grpc' | 'tcp' | 'udp';
  public: boolean;
  authentication?: string;
}

export interface AllocatedResources {
  cpu: number;
  memory: number;
  storage: number;
  gpu?: number;
  network: number;
  cost: number; // per hour
}

export interface DeploymentLog {
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  source: string;
}

export interface MarketplaceCategory {
  id: string;
  name: string;
  description: string;
  icon: string;
  parentId?: string;
  subcategories: MarketplaceCategory[];
  boxCount: number;
  featured: boolean;
  order: number;
}

export interface MarketplaceCollection {
  id: string;
  name: string;
  description: string;
  curatorId: string;
  curatorName: string;
  boxIds: string[];
  tags: string[];
  featured: boolean;
  visibility: 'public' | 'private' | 'unlisted';
  createdAt: Date;
  updatedAt: Date;
}

export class DeveloperMarketplace extends EventEmitter {
  private boxes: Map<string, DeveloperBox> = new Map();
  private orders: Map<string, MarketplaceOrder> = new Map();
  private categories: Map<string, MarketplaceCategory> = new Map();
  private collections: Map<string, MarketplaceCollection> = new Map();
  private userFavorites: Map<string, Set<string>> = new Map();
  private searchIndex: MarketplaceSearchIndex;

  constructor() {
    super();
    this.searchIndex = new MarketplaceSearchIndex();
    this.initializeDefaultCategories();
  }

  public async publishBox(box: Omit<DeveloperBox, 'id' | 'createdAt' | 'updatedAt' | 'reviews' | 'ratings' | 'usage'>): Promise<string> {
    const boxId = this.generateBoxId();
    const now = new Date();

    const developerBox: DeveloperBox = {
      ...box,
      id: boxId,
      createdAt: now,
      updatedAt: now,
      reviews: [],
      ratings: {
        average: 0,
        total: 0,
        distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 },
        breakdown: {
          functionality: 0,
          performance: 0,
          documentation: 0,
          support: 0,
          valueForMoney: 0
        }
      },
      usage: {
        totalDownloads: 0,
        monthlyDownloads: 0,
        activeInstances: 0,
        totalRuntime: 0,
        averageRating: 0,
        popularityRank: 0,
        trendingScore: 0,
        lastUsed: now
      }
    };

    if (box.status === 'published') {
      developerBox.publishedAt = now;
    }

    this.boxes.set(boxId, developerBox);
    await this.searchIndex.indexBox(developerBox);

    this.emit('boxPublished', developerBox);
    return boxId;
  }

  public async updateBox(boxId: string, updates: Partial<DeveloperBox>): Promise<void> {
    const box = this.boxes.get(boxId);
    if (!box) {
      throw new Error('Developer box not found');
    }

    const updatedBox = {
      ...box,
      ...updates,
      updatedAt: new Date()
    };

    if (updates.status === 'published' && !box.publishedAt) {
      updatedBox.publishedAt = new Date();
    }

    this.boxes.set(boxId, updatedBox);
    await this.searchIndex.updateBox(updatedBox);

    this.emit('boxUpdated', updatedBox);
  }

  public async searchBoxes(query: SearchQuery): Promise<SearchResult> {
    return await this.searchIndex.search(query);
  }

  public async getBox(boxId: string): Promise<DeveloperBox | undefined> {
    return this.boxes.get(boxId);
  }

  public async getFeaturedBoxes(limit: number = 10): Promise<DeveloperBox[]> {
    const boxes = Array.from(this.boxes.values());
    return boxes
      .filter(box => box.status === 'published' && box.usage.popularityRank > 0)
      .sort((a, b) => a.usage.popularityRank - b.usage.popularityRank)
      .slice(0, limit);
  }

  public async getTrendingBoxes(limit: number = 10): Promise<DeveloperBox[]> {
    const boxes = Array.from(this.boxes.values());
    return boxes
      .filter(box => box.status === 'published')
      .sort((a, b) => b.usage.trendingScore - a.usage.trendingScore)
      .slice(0, limit);
  }

  public async getBoxesByCategory(categoryId: string, limit: number = 50): Promise<DeveloperBox[]> {
    const boxes = Array.from(this.boxes.values());
    return boxes
      .filter(box => box.status === 'published' && box.category === categoryId)
      .sort((a, b) => b.usage.totalDownloads - a.usage.totalDownloads)
      .slice(0, limit);
  }

  public async orderBox(order: Omit<MarketplaceOrder, 'id' | 'createdAt' | 'status'>): Promise<string> {
    const orderId = this.generateOrderId();
    const box = this.boxes.get(order.boxId);
    
    if (!box) {
      throw new Error('Developer box not found');
    }

    const marketplaceOrder: MarketplaceOrder = {
      ...order,
      id: orderId,
      status: 'pending',
      createdAt: new Date()
    };

    this.orders.set(orderId, marketplaceOrder);

    // Start deployment process
    await this.deployBox(orderId);

    this.emit('boxOrdered', marketplaceOrder);
    return orderId;
  }

  private async deployBox(orderId: string): Promise<void> {
    const order = this.orders.get(orderId);
    if (!order) return;

    const box = this.boxes.get(order.boxId);
    if (!box) return;

    try {
      order.status = 'active';
      order.activatedAt = new Date();

      // Simulate deployment
      order.deployment.status = 'deploying';
      order.deployment.instanceId = this.generateInstanceId();
      
      // Simulate deployment completion
      setTimeout(async () => {
        order.deployment.status = 'running';
        order.deployment.endpoints = await this.generateEndpoints(box, order.deployment.region);
        
        this.orders.set(orderId, order);
        this.emit('boxDeployed', order);

        // Update box usage statistics
        await this.updateBoxUsage(order.boxId, 'deployment');
      }, 5000);

      this.orders.set(orderId, order);

    } catch (error) {
      order.status = 'cancelled';
      order.deployment.status = 'failed';
      this.orders.set(orderId, order);
      this.emit('deploymentFailed', order, error);
    }
  }

  private async generateEndpoints(box: DeveloperBox, region: string): Promise<DeploymentEndpoint[]> {
    const endpoints: DeploymentEndpoint[] = [];
    
    for (const port of box.configuration.ports) {
      if (port.public) {
        endpoints.push({
          name: port.description || `Port ${port.containerPort}`,
          url: `https://${this.generateInstanceId()}.${region}.compute-market.com:${port.hostPort || port.containerPort}`,
          type: port.protocol === 'tcp' ? 'https' : 'tcp',
          public: true,
          authentication: 'bearer_token'
        });
      }
    }

    return endpoints;
  }

  public async stopDeployment(orderId: string): Promise<void> {
    const order = this.orders.get(orderId);
    if (!order) {
      throw new Error('Order not found');
    }

    order.status = 'completed';
    order.deployment.status = 'stopped';
    this.orders.set(orderId, order);

    await this.updateBoxUsage(order.boxId, 'stop');
    this.emit('deploymentStopped', order);
  }

  public async addReview(boxId: string, review: Omit<BoxReview, 'id' | 'createdAt' | 'helpful' | 'reported'>): Promise<string> {
    const box = this.boxes.get(boxId);
    if (!box) {
      throw new Error('Developer box not found');
    }

    const reviewId = this.generateReviewId();
    const boxReview: BoxReview = {
      ...review,
      id: reviewId,
      createdAt: new Date(),
      helpful: 0,
      reported: false
    };

    box.reviews.push(boxReview);
    await this.updateBoxRatings(boxId);

    this.boxes.set(boxId, box);
    this.emit('reviewAdded', boxId, boxReview);

    return reviewId;
  }

  private async updateBoxRatings(boxId: string): Promise<void> {
    const box = this.boxes.get(boxId);
    if (!box) return;

    const reviews = box.reviews;
    if (reviews.length === 0) return;

    const total = reviews.length;
    const sum = reviews.reduce((acc, review) => acc + review.rating, 0);
    const average = sum / total;

    const distribution: RatingDistribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    reviews.forEach(review => {
      distribution[review.rating as keyof RatingDistribution]++;
    });

    box.ratings = {
      average: Math.round(average * 10) / 10,
      total,
      distribution,
      breakdown: {
        functionality: average,
        performance: average,
        documentation: average,
        support: average,
        valueForMoney: average
      }
    };

    box.usage.averageRating = average;
  }

  public async addToFavorites(userId: string, boxId: string): Promise<void> {
    let favorites = this.userFavorites.get(userId);
    if (!favorites) {
      favorites = new Set();
      this.userFavorites.set(userId, favorites);
    }

    favorites.add(boxId);
    this.emit('boxFavorited', userId, boxId);
  }

  public async removeFromFavorites(userId: string, boxId: string): Promise<void> {
    const favorites = this.userFavorites.get(userId);
    if (favorites) {
      favorites.delete(boxId);
      this.emit('boxUnfavorited', userId, boxId);
    }
  }

  public async getUserFavorites(userId: string): Promise<DeveloperBox[]> {
    const favorites = this.userFavorites.get(userId);
    if (!favorites) return [];

    return Array.from(favorites)
      .map(boxId => this.boxes.get(boxId))
      .filter(box => box !== undefined) as DeveloperBox[];
  }

  public async createCollection(collection: Omit<MarketplaceCollection, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    const collectionId = this.generateCollectionId();
    const now = new Date();

    const marketplaceCollection: MarketplaceCollection = {
      ...collection,
      id: collectionId,
      createdAt: now,
      updatedAt: now
    };

    this.collections.set(collectionId, marketplaceCollection);
    this.emit('collectionCreated', marketplaceCollection);

    return collectionId;
  }

  public async getCollection(collectionId: string): Promise<MarketplaceCollection | undefined> {
    return this.collections.get(collectionId);
  }

  public async getCollectionBoxes(collectionId: string): Promise<DeveloperBox[]> {
    const collection = this.collections.get(collectionId);
    if (!collection) return [];

    return collection.boxIds
      .map(boxId => this.boxes.get(boxId))
      .filter(box => box !== undefined) as DeveloperBox[];
  }

  private async updateBoxUsage(boxId: string, action: 'download' | 'deployment' | 'stop'): Promise<void> {
    const box = this.boxes.get(boxId);
    if (!box) return;

    switch (action) {
      case 'download':
        box.usage.totalDownloads++;
        box.usage.monthlyDownloads++;
        break;
      case 'deployment':
        box.usage.activeInstances++;
        box.usage.lastUsed = new Date();
        break;
      case 'stop':
        box.usage.activeInstances = Math.max(0, box.usage.activeInstances - 1);
        break;
    }

    // Update trending score based on recent activity
    box.usage.trendingScore = this.calculateTrendingScore(box);

    this.boxes.set(boxId, box);
  }

  private calculateTrendingScore(box: DeveloperBox): number {
    const now = Date.now();
    const daysSinceLastUsed = (now - box.usage.lastUsed.getTime()) / (1000 * 60 * 60 * 24);
    const recencyScore = Math.max(0, 1 - (daysSinceLastUsed / 30)); // Decay over 30 days
    
    const popularityScore = Math.log(box.usage.totalDownloads + 1) / 10;
    const ratingScore = box.usage.averageRating / 5;
    const activityScore = Math.log(box.usage.activeInstances + 1) / 5;

    return (recencyScore * 0.4 + popularityScore * 0.3 + ratingScore * 0.2 + activityScore * 0.1) * 100;
  }

  public getCategories(): MarketplaceCategory[] {
    return Array.from(this.categories.values());
  }

  public getOrder(orderId: string): MarketplaceOrder | undefined {
    return this.orders.get(orderId);
  }

  public getUserOrders(userId: string): MarketplaceOrder[] {
    return Array.from(this.orders.values())
      .filter(order => order.buyerId === userId)
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  private initializeDefaultCategories(): void {
    const categories: Omit<MarketplaceCategory, 'subcategories' | 'boxCount'>[] = [
      {
        id: 'development',
        name: 'Development',
        description: 'Development environments and tools',
        icon: '💻',
        featured: true,
        order: 1
      },
      {
        id: 'ai_ml',
        name: 'AI & Machine Learning',
        description: 'AI, ML, and data science environments',
        icon: '🤖',
        featured: true,
        order: 2
      },
      {
        id: 'testing',
        name: 'Testing',
        description: 'Testing and QA environments',
        icon: '🧪',
        featured: false,
        order: 3
      },
      {
        id: 'deployment',
        name: 'Deployment',
        description: 'Deployment and CI/CD tools',
        icon: '🚀',
        featured: true,
        order: 4
      },
      {
        id: 'data_science',
        name: 'Data Science',
        description: 'Data analysis and visualization tools',
        icon: '📊',
        featured: true,
        order: 5
      },
      {
        id: 'gaming',
        name: 'Gaming',
        description: 'Game development and gaming servers',
        icon: '🎮',
        featured: false,
        order: 6
      },
      {
        id: 'rendering',
        name: 'Rendering',
        description: '3D rendering and graphics workloads',
        icon: '🎨',
        featured: false,
        order: 7
      },
      {
        id: 'blockchain',
        name: 'Blockchain',
        description: 'Blockchain and cryptocurrency tools',
        icon: '⛓️',
        featured: false,
        order: 8
      }
    ];

    categories.forEach(category => {
      this.categories.set(category.id, {
        ...category,
        subcategories: [],
        boxCount: 0
      });
    });
  }

  private generateBoxId(): string {
    return `box_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateOrderId(): string {
    return `order_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateInstanceId(): string {
    return `instance_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateReviewId(): string {
    return `review_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateCollectionId(): string {
    return `collection_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Search functionality
export interface SearchQuery {
  query?: string;
  category?: string;
  tags?: string[];
  priceRange?: [number, number];
  rating?: number;
  sortBy?: 'relevance' | 'popularity' | 'rating' | 'price' | 'newest' | 'updated';
  sortOrder?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
  filters?: SearchFilters;
}

export interface SearchFilters {
  pricing?: ('free' | 'paid' | 'subscription')[];
  verification?: ('unverified' | 'community_verified' | 'official_verified')[];
  features?: string[];
  compatibility?: string[];
  support?: ('community' | 'standard' | 'premium' | 'enterprise')[];
}

export interface SearchResult {
  boxes: DeveloperBox[];
  total: number;
  facets: SearchFacets;
  suggestions?: string[];
}

export interface SearchFacets {
  categories: FacetBucket[];
  tags: FacetBucket[];
  pricing: FacetBucket[];
  rating: FacetBucket[];
}

export interface FacetBucket {
  key: string;
  count: number;
  selected?: boolean;
}

class MarketplaceSearchIndex {
  private index: Map<string, DeveloperBox> = new Map();
  private tagIndex: Map<string, Set<string>> = new Map();
  private categoryIndex: Map<string, Set<string>> = new Map();

  public async indexBox(box: DeveloperBox): Promise<void> {
    this.index.set(box.id, box);
    
    // Index tags
    for (const tag of box.tags) {
      const tagLower = tag.toLowerCase();
      if (!this.tagIndex.has(tagLower)) {
        this.tagIndex.set(tagLower, new Set());
      }
      this.tagIndex.get(tagLower)!.add(box.id);
    }
    
    // Index category
    if (!this.categoryIndex.has(box.category)) {
      this.categoryIndex.set(box.category, new Set());
    }
    this.categoryIndex.get(box.category)!.add(box.id);
  }

  public async updateBox(box: DeveloperBox): Promise<void> {
    // Remove old indexes
    await this.removeBox(box.id);
    // Add new indexes
    await this.indexBox(box);
  }

  public async removeBox(boxId: string): Promise<void> {
    const box = this.index.get(boxId);
    if (!box) return;

    this.index.delete(boxId);
    
    // Remove from tag index
    for (const tag of box.tags) {
      const tagLower = tag.toLowerCase();
      const tagSet = this.tagIndex.get(tagLower);
      if (tagSet) {
        tagSet.delete(boxId);
        if (tagSet.size === 0) {
          this.tagIndex.delete(tagLower);
        }
      }
    }
    
    // Remove from category index
    const categorySet = this.categoryIndex.get(box.category);
    if (categorySet) {
      categorySet.delete(boxId);
      if (categorySet.size === 0) {
        this.categoryIndex.delete(box.category);
      }
    }
  }

  public async search(query: SearchQuery): Promise<SearchResult> {
    let candidateIds = new Set<string>();
    
    // Text search
    if (query.query) {
      const textResults = this.searchByText(query.query);
      candidateIds = new Set(textResults);
    } else {
      candidateIds = new Set(this.index.keys());
    }
    
    // Filter by category
    if (query.category) {
      const categoryResults = this.categoryIndex.get(query.category) || new Set();
      candidateIds = new Set([...candidateIds].filter(id => categoryResults.has(id)));
    }
    
    // Filter by tags
    if (query.tags && query.tags.length > 0) {
      for (const tag of query.tags) {
        const tagResults = this.tagIndex.get(tag.toLowerCase()) || new Set();
        candidateIds = new Set([...candidateIds].filter(id => tagResults.has(id)));
      }
    }
    
    // Get boxes and apply additional filters
    let boxes = Array.from(candidateIds)
      .map(id => this.index.get(id))
      .filter(box => box !== undefined) as DeveloperBox[];
    
    // Apply filters
    boxes = this.applyFilters(boxes, query);
    
    // Sort results
    boxes = this.sortResults(boxes, query.sortBy || 'relevance', query.sortOrder || 'desc');
    
    // Pagination
    const total = boxes.length;
    const offset = query.offset || 0;
    const limit = query.limit || 20;
    boxes = boxes.slice(offset, offset + limit);
    
    return {
      boxes,
      total,
      facets: this.generateFacets(Array.from(candidateIds).map(id => this.index.get(id)!)),
      suggestions: this.generateSuggestions(query.query)
    };
  }

  private searchByText(query: string): string[] {
    const queryLower = query.toLowerCase();
    const results: Array<{ id: string; score: number }> = [];
    
    for (const [id, box] of this.index) {
      let score = 0;
      
      // Title match
      if (box.name.toLowerCase().includes(queryLower)) {
        score += 10;
      }
      
      // Description match
      if (box.description.toLowerCase().includes(queryLower)) {
        score += 5;
      }
      
      // Tag match
      for (const tag of box.tags) {
        if (tag.toLowerCase().includes(queryLower)) {
          score += 3;
        }
      }
      
      // Author match
      if (box.author.toLowerCase().includes(queryLower)) {
        score += 2;
      }
      
      if (score > 0) {
        results.push({ id, score });
      }
    }
    
    return results
      .sort((a, b) => b.score - a.score)
      .map(result => result.id);
  }

  private applyFilters(boxes: DeveloperBox[], query: SearchQuery): DeveloperBox[] {
    let filtered = boxes;
    
    // Price range filter
    if (query.priceRange) {
      const [min, max] = query.priceRange;
      filtered = filtered.filter(box => 
        box.pricing.basePrice >= min && box.pricing.basePrice <= max
      );
    }
    
    // Rating filter
    if (query.rating) {
      filtered = filtered.filter(box => box.ratings.average >= query.rating!);
    }
    
    // Additional filters
    if (query.filters) {
      const filters = query.filters;
      
      if (filters.pricing) {
        filtered = filtered.filter(box => filters.pricing!.includes(box.pricing.model));
      }
      
      if (filters.verification) {
        filtered = filtered.filter(box => filters.verification!.includes(box.verificationStatus));
      }
    }
    
    return filtered;
  }

  private sortResults(boxes: DeveloperBox[], sortBy: string, sortOrder: string): DeveloperBox[] {
    const direction = sortOrder === 'asc' ? 1 : -1;
    
    return boxes.sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'popularity':
          comparison = a.usage.totalDownloads - b.usage.totalDownloads;
          break;
        case 'rating':
          comparison = a.ratings.average - b.ratings.average;
          break;
        case 'price':
          comparison = a.pricing.basePrice - b.pricing.basePrice;
          break;
        case 'newest':
          comparison = a.createdAt.getTime() - b.createdAt.getTime();
          break;
        case 'updated':
          comparison = a.updatedAt.getTime() - b.updatedAt.getTime();
          break;
        default: // relevance
          comparison = b.usage.trendingScore - a.usage.trendingScore;
          break;
      }
      
      return comparison * direction;
    });
  }

  private generateFacets(boxes: DeveloperBox[]): SearchFacets {
    const categories = new Map<string, number>();
    const tags = new Map<string, number>();
    const pricing = new Map<string, number>();
    const rating = new Map<string, number>();
    
    for (const box of boxes) {
      // Categories
      categories.set(box.category, (categories.get(box.category) || 0) + 1);
      
      // Tags
      for (const tag of box.tags) {
        tags.set(tag, (tags.get(tag) || 0) + 1);
      }
      
      // Pricing
      pricing.set(box.pricing.model, (pricing.get(box.pricing.model) || 0) + 1);
      
      // Rating
      const ratingBucket = Math.floor(box.ratings.average).toString();
      rating.set(ratingBucket, (rating.get(ratingBucket) || 0) + 1);
    }
    
    return {
      categories: Array.from(categories.entries())
        .map(([key, count]) => ({ key, count }))
        .sort((a, b) => b.count - a.count),
      tags: Array.from(tags.entries())
        .map(([key, count]) => ({ key, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 20), // Top 20 tags
      pricing: Array.from(pricing.entries())
        .map(([key, count]) => ({ key, count })),
      rating: Array.from(rating.entries())
        .map(([key, count]) => ({ key, count }))
        .sort((a, b) => b.key.localeCompare(a.key))
    };
  }

  private generateSuggestions(query?: string): string[] {
    if (!query) return [];
    
    // Simple suggestion based on popular tags
    const popularTags = Array.from(this.tagIndex.entries())
      .sort((a, b) => b[1].size - a[1].size)
      .slice(0, 10)
      .map(([tag]) => tag);
    
    return popularTags.filter(tag => 
      tag.toLowerCase().includes(query.toLowerCase())
    );
  }
}

export default DeveloperMarketplace;