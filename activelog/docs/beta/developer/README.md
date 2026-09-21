# Developer Documentation

Comprehensive developer guide for building on ActiveLog. From getting started with the API to advanced integration patterns, this guide covers everything you need to create powerful applications on the ActiveLog platform.

## 🚀 Getting Started

### Quick Setup
```bash
# Install ActiveLog CLI
npm install -g @activelog/cli

# Install SDK
npm install @activelog/sdk
# or
pip install activelog-sdk

# Authenticate
activelog auth login --beta
```

### First API Call
```javascript
const { ActiveLogAPI } = require('@activelog/sdk');

const api = new ActiveLogAPI({
  apiKey: process.env.ACTIVELOG_API_KEY,
  environment: 'beta'
});

// Get user profile
const profile = await api.user.getProfile();
console.log(profile);
```

## 📚 Core Concepts

### Authentication
ActiveLog uses JWT tokens for authentication with support for multiple scopes:

```javascript
// API Key Authentication (recommended for server-side)
const api = new ActiveLogAPI({
  apiKey: 'al_beta_sk_...',
  environment: 'beta'
});

// OAuth2 Authentication (for client-side applications)
const api = new ActiveLogAPI({
  clientId: 'your_client_id',
  redirectUri: 'https://yourapp.com/callback',
  environment: 'beta'
});

// Start OAuth flow
const authUrl = api.auth.getAuthorizationUrl({
  scopes: ['read', 'write', 'files']
});
```

### Data Model
ActiveLog organizes data in a hierarchical structure:

```
User
├── Workspaces
│   ├── Projects
│   │   ├── Documents
│   │   ├── Files
│   │   └── Metadata
│   └── Settings
└── Integrations
```

### Rate Limiting
Beta users get enhanced rate limits:
- **Standard**: 1,000 requests/hour
- **Beta**: 10,000 requests/hour
- **Enterprise Beta**: 50,000 requests/hour

```javascript
// Handle rate limiting gracefully
api.setRateLimitHandler((retryAfter) => {
  console.log(`Rate limited. Retry after ${retryAfter} seconds`);
  return new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
});
```

## 🔧 SDK Reference

### Installation & Setup

#### Node.js/JavaScript
```bash
npm install @activelog/sdk
```

```javascript
import { ActiveLogAPI, ActiveLogWebSocket } from '@activelog/sdk';

const api = new ActiveLogAPI({
  apiKey: process.env.ACTIVELOG_API_KEY,
  environment: 'beta',
  timeout: 30000,
  retries: 3
});
```

#### Python
```bash
pip install activelog-sdk
```

```python
from activelog import ActiveLogAPI
import os

api = ActiveLogAPI(
    api_key=os.getenv('ACTIVELOG_API_KEY'),
    environment='beta',
    timeout=30,
    max_retries=3
)
```

#### PHP
```bash
composer require activelog/activelog-php
```

```php
use ActiveLog\ActiveLogAPI;

$api = new ActiveLogAPI([
    'api_key' => $_ENV['ACTIVELOG_API_KEY'],
    'environment' => 'beta',
    'timeout' => 30
]);
```

### Core Operations

#### User Management
```javascript
// Get current user
const user = await api.user.getProfile();

// Update user preferences
await api.user.updatePreferences({
  theme: 'dark',
  timezone: 'UTC',
  notifications: {
    email: true,
    push: false
  }
});

// Get user statistics
const stats = await api.user.getStatistics({
  period: 'last_30_days',
  metrics: ['files_created', 'api_calls', 'storage_used']
});
```

#### Workspace Management
```javascript
// List workspaces
const workspaces = await api.workspaces.list({
  limit: 50,
  include_archived: false
});

// Create workspace
const workspace = await api.workspaces.create({
  name: 'My Development Workspace',
  description: 'Workspace for development projects',
  settings: {
    default_permissions: 'private',
    enable_ai_features: true
  }
});

// Update workspace
await api.workspaces.update(workspace.id, {
  name: 'Updated Workspace Name',
  settings: {
    enable_real_time_collaboration: true
  }
});
```

#### Project Management
```javascript
// Create project
const project = await api.projects.create({
  workspace_id: workspace.id,
  name: 'API Integration Project',
  type: 'development',
  metadata: {
    tech_stack: ['Node.js', 'PostgreSQL'],
    priority: 'high'
  }
});

// Get project with related data
const fullProject = await api.projects.get(project.id, {
  include: ['documents', 'files', 'collaborators']
});

// Search projects
const results = await api.projects.search({
  query: 'API development',
  filters: {
    type: 'development',
    status: 'active'
  },
  sort: 'updated_at'
});
```

#### Document Management
```javascript
// Create document
const doc = await api.documents.create({
  project_id: project.id,
  title: 'API Documentation',
  content: 'Initial content',
  format: 'markdown',
  metadata: {
    author: 'developer@company.com',
    version: '1.0'
  }
});

// Update document with collaboration
await api.documents.update(doc.id, {
  content: 'Updated content',
  metadata: {
    version: '1.1',
    last_modified_by: 'developer@company.com'
  }
}, {
  enable_real_time: true,
  conflict_resolution: 'merge'
});

// Get document versions
const versions = await api.documents.getVersions(doc.id, {
  limit: 10,
  include_content: true
});
```

#### File Operations
```javascript
// Upload file
const file = await api.files.upload({
  project_id: project.id,
  file: fileBuffer, // or File object in browser
  filename: 'example.pdf',
  metadata: {
    category: 'documentation',
    confidential: false
  }
});

// Upload large file (chunked upload)
const largeFile = await api.files.uploadChunked({
  project_id: project.id,
  file: largeFileStream,
  filename: 'large-dataset.csv',
  chunk_size: 1024 * 1024, // 1MB chunks
  on_progress: (progress) => console.log(`Upload ${progress}% complete`)
});

// Download file
const fileData = await api.files.download(file.id, {
  format: 'buffer' // or 'stream', 'base64'
});

// Generate sharing URL
const shareUrl = await api.files.createShareUrl(file.id, {
  expires_at: Date.now() + (7 * 24 * 60 * 60 * 1000), // 7 days
  permissions: 'read',
  password_protected: true
});
```

## 🔄 Real-time Features

### WebSocket Connection
```javascript
import { ActiveLogWebSocket } from '@activelog/sdk';

const ws = new ActiveLogWebSocket({
  apiKey: process.env.ACTIVELOG_API_KEY,
  environment: 'beta'
});

await ws.connect();

// Subscribe to project updates
await ws.subscribe('project', project.id, (event) => {
  console.log('Project updated:', event);
  switch (event.type) {
    case 'document_updated':
      handleDocumentUpdate(event.data);
      break;
    case 'file_uploaded':
      handleFileUpload(event.data);
      break;
    case 'user_joined':
      handleUserJoined(event.data);
      break;
  }
});

// Send real-time updates
await ws.send('document_typing', {
  document_id: doc.id,
  user_id: user.id,
  cursor_position: 150
});
```

### Collaboration Features
```javascript
// Enable real-time collaboration on document
await api.collaboration.enable(doc.id, {
  features: ['real_time_editing', 'cursor_tracking', 'comments'],
  permissions: {
    edit: ['user1@example.com', 'user2@example.com'],
    comment: ['viewer@example.com'],
    view: ['public'] // or specific users
  }
});

// Get active collaborators
const collaborators = await api.collaboration.getActive(doc.id);

// Handle collaborative editing conflicts
await api.collaboration.resolveConflict(doc.id, {
  strategy: 'operational_transform', // or 'last_writer_wins', 'manual'
  base_version: 'v1.5',
  conflicts: [
    {
      type: 'text_edit',
      position: 120,
      user_a_change: 'Hello World',
      user_b_change: 'Hello ActiveLog'
    }
  ]
});
```

## 🤖 AI Integration

### AI-Powered Features
```javascript
// Enable AI insights for project
await api.ai.enableInsights(project.id, {
  features: ['content_analysis', 'suggestion_generation', 'auto_tagging'],
  model: 'gpt-4', // or 'claude-3', 'custom'
  config: {
    context_window: 'full_project',
    update_frequency: 'real_time'
  }
});

// Get AI-generated insights
const insights = await api.ai.getInsights(project.id, {
  types: ['summary', 'action_items', 'trends'],
  time_range: 'last_week'
});

// Generate content suggestions
const suggestions = await api.ai.generateSuggestions(doc.id, {
  type: 'completion',
  context_length: 500,
  temperature: 0.7,
  max_suggestions: 3
});

// AI-powered search
const searchResults = await api.search.aiEnhanced({
  query: 'API documentation best practices',
  scope: 'project',
  project_id: project.id,
  enhance_with: ['semantic_similarity', 'intent_understanding']
});
```

### Custom AI Models
```javascript
// Register custom AI model (Enterprise Beta only)
const customModel = await api.ai.models.register({
  name: 'company-specific-model',
  type: 'text-generation',
  endpoint: 'https://api.company.com/ai/generate',
  authentication: {
    type: 'bearer_token',
    token: process.env.CUSTOM_AI_TOKEN
  },
  capabilities: ['text_completion', 'summarization']
});

// Use custom model
const result = await api.ai.generate({
  model: 'company-specific-model',
  prompt: 'Generate API documentation for...',
  parameters: {
    max_length: 1000,
    temperature: 0.5
  }
});
```

## 🔗 Integration Patterns

### Webhooks
```javascript
// Setup webhook endpoints
await api.webhooks.create({
  url: 'https://yourapp.com/webhooks/activelog',
  events: ['project.created', 'document.updated', 'file.uploaded'],
  secret: 'your-webhook-secret',
  active: true
});

// Webhook handler (Express.js example)
app.post('/webhooks/activelog', express.raw({type: 'application/json'}), (req, res) => {
  const payload = req.body;
  const signature = req.headers['x-activelog-signature'];
  
  // Verify webhook signature
  const expectedSignature = crypto
    .createHmac('sha256', process.env.WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  
  if (signature !== `sha256=${expectedSignature}`) {
    return res.status(401).send('Invalid signature');
  }
  
  const event = JSON.parse(payload);
  
  switch (event.type) {
    case 'project.created':
      handleProjectCreated(event.data);
      break;
    case 'document.updated':
      handleDocumentUpdated(event.data);
      break;
    default:
      console.log(`Unknown event type: ${event.type}`);
  }
  
  res.status(200).send('OK');
});
```

### OAuth2 Integration
```javascript
// OAuth2 setup for third-party apps
const oauth = api.oauth.createClient({
  client_id: process.env.ACTIVELOG_CLIENT_ID,
  client_secret: process.env.ACTIVELOG_CLIENT_SECRET,
  redirect_uri: 'https://yourapp.com/oauth/callback'
});

// Authorization flow
app.get('/auth', (req, res) => {
  const authUrl = oauth.getAuthorizationUrl({
    scopes: ['read', 'write', 'files'],
    state: generateRandomState()
  });
  res.redirect(authUrl);
});

app.get('/oauth/callback', async (req, res) => {
  const { code, state } = req.query;
  
  try {
    const tokens = await oauth.exchangeCodeForTokens(code);
    
    // Store tokens securely
    await storeUserTokens(req.user.id, tokens);
    
    res.redirect('/dashboard?auth=success');
  } catch (error) {
    res.redirect('/auth?error=oauth_failed');
  }
});
```

### Third-party Service Integration
```javascript
// Google Workspace integration
const integration = await api.integrations.setup('google_workspace', {
  credentials: {
    client_id: process.env.GOOGLE_CLIENT_ID,
    client_secret: process.env.GOOGLE_CLIENT_SECRET
  },
  scopes: ['drive', 'docs', 'sheets'],
  sync_settings: {
    auto_sync: true,
    sync_frequency: '15min',
    conflict_resolution: 'activelog_wins'
  }
});

// Sync data from Google Drive
const syncResult = await api.integrations.sync('google_workspace', {
  folders: ['/ActiveLog Projects'],
  file_types: ['docs', 'sheets', 'slides'],
  preserve_structure: true
});

// Setup bidirectional sync
await api.integrations.enableBidirectionalSync('google_workspace', {
  activelog_to_google: {
    enabled: true,
    auto_export_formats: ['docx', 'xlsx']
  },
  google_to_activelog: {
    enabled: true,
    import_as_native: true
  }
});
```

## 📊 Analytics & Monitoring

### Usage Analytics
```javascript
// Track custom events
await api.analytics.track('feature_used', {
  feature: 'ai_document_analysis',
  user_id: user.id,
  project_id: project.id,
  metadata: {
    document_type: 'technical_spec',
    ai_model: 'gpt-4'
  }
});

// Get usage statistics
const stats = await api.analytics.getUsage({
  timeframe: 'last_30_days',
  group_by: 'day',
  metrics: ['api_calls', 'storage_used', 'active_users'],
  filters: {
    project_id: project.id
  }
});

// Create custom dashboard
const dashboard = await api.analytics.createDashboard({
  name: 'API Usage Dashboard',
  widgets: [
    {
      type: 'metric',
      title: 'Daily API Calls',
      query: 'api_calls',
      visualization: 'line_chart'
    },
    {
      type: 'table',
      title: 'Top Endpoints',
      query: 'endpoint_usage',
      visualization: 'data_table'
    }
  ]
});
```

### Performance Monitoring
```javascript
// Enable performance monitoring
api.setPerformanceMonitoring({
  enabled: true,
  sample_rate: 0.1, // 10% of requests
  include_payloads: false, // for privacy
  custom_tags: {
    service: 'my-app',
    version: '1.0.0'
  }
});

// Custom performance tracking
const timer = api.performance.startTimer('document_processing');
// ... your code here ...
timer.end({
  document_size: doc.content.length,
  processing_type: 'ai_analysis'
});

// Get performance insights
const insights = await api.performance.getInsights({
  timeframe: 'last_24_hours',
  breakdown: ['endpoint', 'response_time', 'error_rate']
});
```

## 🧪 Testing & Development

### Beta Feature Flags
```javascript
// Check feature availability
const features = await api.features.getAvailable();

// Enable beta feature for testing
await api.features.enable('experimental_ai_model', {
  scope: 'user', // or 'project', 'workspace'
  rollout_percentage: 50 // gradual rollout
});

// Feature flag in code
if (await api.features.isEnabled('real_time_collaboration')) {
  // Use real-time features
  enableRealtimeEditing();
} else {
  // Fallback to standard features
  enableStandardEditing();
}
```

### Testing Framework Integration
```javascript
// Jest testing with ActiveLog mock
import { mockActiveLogAPI } from '@activelog/sdk/testing';

describe('Document Creation', () => {
  let api;

  beforeEach(() => {
    api = mockActiveLogAPI({
      environment: 'test',
      responses: {
        'documents.create': {
          id: 'doc_123',
          title: 'Test Document',
          created_at: new Date().toISOString()
        }
      }
    });
  });

  test('should create document with correct title', async () => {
    const doc = await api.documents.create({
      title: 'Test Document',
      content: 'Test content'
    });

    expect(doc.title).toBe('Test Document');
    expect(api.requests).toHaveLength(1);
  });
});
```

### Development Environment Setup
```bash
# Setup development environment
activelog dev setup --beta

# Start local development server with hot reload
activelog dev start --watch --proxy-api beta.activelog.dev

# Run tests against beta environment
ACTIVELOG_ENV=beta npm test

# Generate API documentation
activelog dev generate-docs --output ./docs/api
```

## 🚀 Deployment Patterns

### Server-side Applications
```javascript
// Production configuration
const api = new ActiveLogAPI({
  apiKey: process.env.ACTIVELOG_API_KEY,
  environment: 'beta', // will become 'production'
  timeout: 30000,
  retries: 3,
  cache: {
    enabled: true,
    ttl: 300, // 5 minutes
    redis_url: process.env.REDIS_URL
  },
  logging: {
    level: 'info',
    destination: './logs/activelog.log'
  }
});

// Health check endpoint
app.get('/health', async (req, res) => {
  try {
    const status = await api.health.check();
    res.json({ status: 'ok', activelog: status });
  } catch (error) {
    res.status(503).json({ status: 'error', message: error.message });
  }
});
```

### Client-side Applications
```javascript
// Browser configuration with service worker
const api = new ActiveLogAPI({
  environment: 'beta',
  authentication: 'oauth2',
  client_id: process.env.REACT_APP_ACTIVELOG_CLIENT_ID,
  offline: {
    enabled: true,
    storage: 'indexeddb',
    sync_on_reconnect: true
  }
});

// React hook example
import { useActiveLog } from '@activelog/react-hooks';

function DocumentEditor({ documentId }) {
  const { document, loading, error, update } = useActiveLog.useDocument(documentId);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <div>
      <input 
        value={document.title} 
        onChange={(e) => update({ title: e.target.value })}
      />
      <textarea 
        value={document.content}
        onChange={(e) => update({ content: e.target.value })}
      />
    </div>
  );
}
```

### Microservices Architecture
```javascript
// Service discovery and load balancing
const cluster = new ActiveLogCluster({
  discovery: {
    type: 'consul',
    host: 'consul.service.consul',
    service: 'activelog-api'
  },
  load_balancer: {
    strategy: 'round_robin',
    health_check: {
      interval: 30000,
      timeout: 5000
    }
  }
});

// Circuit breaker pattern
const circuitBreaker = new ActiveLogCircuitBreaker({
  failure_threshold: 5,
  recovery_timeout: 60000,
  fallback: async (method, args) => {
    // Fallback to cached data or alternative service
    return await cacheService.get(generateCacheKey(method, args));
  }
});

const api = new ActiveLogAPI({
  cluster,
  circuit_breaker: circuitBreaker,
  environment: 'beta'
});
```

## 📖 Advanced Examples

### Building a Document Management System
```javascript
class DocumentManager {
  constructor(apiKey) {
    this.api = new ActiveLogAPI({ apiKey, environment: 'beta' });
    this.cache = new Map();
    this.subscribers = new Map();
  }

  async createDocument(projectId, options) {
    // Create document with AI-generated metadata
    const aiTags = await this.api.ai.generateTags(options.content);
    
    const document = await this.api.documents.create({
      project_id: projectId,
      ...options,
      metadata: {
        ...options.metadata,
        ai_generated_tags: aiTags,
        created_by_ai: false,
        confidence_score: aiTags.confidence
      }
    });

    // Setup real-time collaboration
    if (options.collaborative) {
      await this.enableCollaboration(document.id);
    }

    // Cache locally
    this.cache.set(document.id, document);

    return document;
  }

  async enableCollaboration(documentId) {
    await this.api.collaboration.enable(documentId, {
      features: ['real_time_editing', 'cursor_tracking', 'comments'],
      conflict_resolution: 'operational_transform'
    });

    // Setup WebSocket for real-time updates
    const ws = new ActiveLogWebSocket({ api: this.api });
    await ws.subscribe('document', documentId, (event) => {
      this.handleRealtimeUpdate(documentId, event);
    });

    return ws;
  }

  async searchDocuments(query, options = {}) {
    // Use AI-enhanced search
    const results = await this.api.search.aiEnhanced({
      query,
      enhance_with: ['semantic_similarity', 'intent_understanding'],
      filters: options.filters,
      sort: options.sort || 'relevance'
    });

    // Post-process results with additional metadata
    return Promise.all(results.map(async (result) => ({
      ...result,
      ai_summary: await this.api.ai.summarize(result.content, { max_length: 200 }),
      related_documents: await this.findRelatedDocuments(result.id)
    })));
  }

  async findRelatedDocuments(documentId, limit = 5) {
    const document = await this.getDocument(documentId);
    
    return this.api.search.findSimilar({
      document_id: documentId,
      similarity_threshold: 0.7,
      limit,
      include_metadata: true
    });
  }

  handleRealtimeUpdate(documentId, event) {
    const subscribers = this.subscribers.get(documentId) || [];
    
    subscribers.forEach(callback => {
      try {
        callback(event);
      } catch (error) {
        console.error('Error in subscriber callback:', error);
      }
    });

    // Update cache
    if (event.type === 'document_updated') {
      this.cache.set(documentId, { ...this.cache.get(documentId), ...event.data });
    }
  }

  subscribe(documentId, callback) {
    if (!this.subscribers.has(documentId)) {
      this.subscribers.set(documentId, []);
    }
    this.subscribers.get(documentId).push(callback);
  }
}

// Usage example
const docManager = new DocumentManager(process.env.ACTIVELOG_API_KEY);

// Create collaborative document
const document = await docManager.createDocument('project_123', {
  title: 'API Design Document',
  content: 'Initial API design...',
  collaborative: true,
  metadata: {
    category: 'technical_specification',
    priority: 'high'
  }
});

// Subscribe to real-time updates
docManager.subscribe(document.id, (event) => {
  console.log('Document updated:', event);
  updateUI(event.data);
});

// Search with AI enhancement
const searchResults = await docManager.searchDocuments('REST API best practices', {
  filters: { category: 'technical_specification' },
  sort: 'updated_at'
});
```

### Building a Custom Integration
```javascript
class SlackActiveLogIntegration {
  constructor(config) {
    this.activelog = new ActiveLogAPI({
      apiKey: config.activelogApiKey,
      environment: 'beta'
    });
    
    this.slack = new SlackAPI({
      token: config.slackToken
    });

    this.setupWebhooks();
  }

  async setupWebhooks() {
    // Setup ActiveLog webhook
    await this.activelog.webhooks.create({
      url: `${process.env.BASE_URL}/webhook/activelog`,
      events: ['document.created', 'project.completed', 'file.shared'],
      active: true
    });

    // Setup Slack webhook
    await this.slack.webhooks.create({
      url: `${process.env.BASE_URL}/webhook/slack`,
      events: ['message', 'file_shared', 'reaction_added']
    });
  }

  async handleActiveLogUpdate(event) {
    switch (event.type) {
      case 'document.created':
        await this.notifySlackChannel({
          channel: '#project-updates',
          text: `New document created: ${event.data.title}`,
          attachments: [{
            color: 'good',
            fields: [{
              title: 'Project',
              value: event.data.project_name,
              short: true
            }, {
              title: 'Author',
              value: event.data.author_name,
              short: true
            }],
            actions: [{
              type: 'button',
              text: 'View Document',
              url: `https://beta.activelog.dev/documents/${event.data.id}`
            }]
          }]
        });
        break;

      case 'project.completed':
        await this.createSlackSummary(event.data.project_id);
        break;
    }
  }

  async handleSlackMessage(event) {
    // Check if message contains ActiveLog mention
    if (event.text.includes('@activelog')) {
      const command = this.parseSlackCommand(event.text);
      
      switch (command.action) {
        case 'create_document':
          const document = await this.activelog.documents.create({
            title: command.title || 'New Document from Slack',
            content: command.content || event.text,
            project_id: await this.getProjectFromSlackChannel(event.channel)
          });

          await this.slack.chat.postMessage({
            channel: event.channel,
            text: `Document created: ${document.title}`,
            thread_ts: event.ts
          });
          break;

        case 'search':
          const results = await this.activelog.search.query({
            query: command.query,
            limit: 5
          });

          const searchMessage = this.formatSearchResults(results);
          await this.slack.chat.postMessage({
            channel: event.channel,
            ...searchMessage,
            thread_ts: event.ts
          });
          break;
      }
    }
  }

  parseSlackCommand(text) {
    // Simple command parser
    const patterns = {
      create_document: /create document(?:\s+"([^"]+)")?(?:\s+(.+))?/i,
      search: /search\s+(.+)/i
    };

    for (const [action, pattern] of Object.entries(patterns)) {
      const match = text.match(pattern);
      if (match) {
        switch (action) {
          case 'create_document':
            return { action, title: match[1], content: match[2] };
          case 'search':
            return { action, query: match[1] };
        }
      }
    }

    return { action: 'unknown' };
  }

  async createSlackSummary(projectId) {
    const project = await this.activelog.projects.get(projectId, {
      include: ['documents', 'files', 'collaborators', 'statistics']
    });

    const summary = await this.activelog.ai.generateSummary({
      project_id: projectId,
      include: ['achievements', 'challenges', 'metrics'],
      format: 'slack_friendly'
    });

    await this.slack.chat.postMessage({
      channel: '#project-summaries',
      text: `Project "${project.name}" has been completed! 🎉`,
      attachments: [{
        color: 'good',
        title: 'Project Summary',
        text: summary.text,
        fields: [
          {
            title: 'Documents Created',
            value: project.statistics.documents_count,
            short: true
          },
          {
            title: 'Files Uploaded',
            value: project.statistics.files_count,
            short: true
          },
          {
            title: 'Contributors',
            value: project.collaborators.length,
            short: true
          },
          {
            title: 'Duration',
            value: this.formatDuration(project.created_at, project.completed_at),
            short: true
          }
        ],
        actions: [{
          type: 'button',
          text: 'View Project',
          url: `https://beta.activelog.dev/projects/${projectId}`
        }]
      }]
    });
  }
}

// Initialize integration
const integration = new SlackActiveLogIntegration({
  activelogApiKey: process.env.ACTIVELOG_API_KEY,
  slackToken: process.env.SLACK_BOT_TOKEN
});
```

## 🛡️ Security Best Practices

### API Security
```javascript
// Secure API configuration
const api = new ActiveLogAPI({
  apiKey: process.env.ACTIVELOG_API_KEY,
  environment: 'beta',
  security: {
    validate_ssl: true,
    timeout: 30000,
    max_retries: 3,
    rate_limit_headers: true,
    user_agent: 'MyApp/1.0.0'
  }
});

// Secure token storage (Node.js)
const keytar = require('keytar');

class SecureTokenManager {
  async storeToken(userId, token) {
    await keytar.setPassword('activelog', userId, JSON.stringify({
      access_token: token.access_token,
      refresh_token: token.refresh_token,
      expires_at: token.expires_at
    }));
  }

  async getToken(userId) {
    const tokenData = await keytar.getPassword('activelog', userId);
    return tokenData ? JSON.parse(tokenData) : null;
  }

  async refreshToken(userId) {
    const tokenData = await this.getToken(userId);
    if (!tokenData) throw new Error('No token found');

    const refreshed = await this.api.auth.refreshToken({
      refresh_token: tokenData.refresh_token
    });

    await this.storeToken(userId, refreshed);
    return refreshed;
  }
}
```

### Data Encryption
```javascript
// Encrypt sensitive data before storing
const crypto = require('crypto');

class EncryptedStorage {
  constructor(encryptionKey) {
    this.key = crypto.createHash('sha256').update(encryptionKey).digest();
  }

  encrypt(data) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher('aes-256-gcm', this.key, iv);
    
    let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const authTag = cipher.getAuthTag();
    
    return {
      iv: iv.toString('hex'),
      data: encrypted,
      authTag: authTag.toString('hex')
    };
  }

  decrypt(encryptedData) {
    const decipher = crypto.createDecipher('aes-256-gcm', this.key, Buffer.from(encryptedData.iv, 'hex'));
    decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'hex'));
    
    let decrypted = decipher.update(encryptedData.data, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return JSON.parse(decrypted);
  }
}

// Store encrypted user data
const storage = new EncryptedStorage(process.env.ENCRYPTION_KEY);

const encryptedUserData = storage.encrypt({
  user_id: 'user123',
  preferences: { theme: 'dark' },
  api_keys: { activelog: 'al_beta_sk_...' }
});

await database.store('user_data', encryptedUserData);
```

## 📞 Support & Resources

### Beta Developer Support
- **Email**: developer-support@activelog.dev
- **Discord**: [ActiveLog Developers](https://discord.gg/activelog-dev)
- **Office Hours**: Tuesdays 2-3 PM PST
- **Response Time**: < 4 hours for beta developers

### Resources
- **API Reference**: [Complete REST API documentation](../api/rest-api.md)
- **SDK Documentation**: [Language-specific SDK guides](./sdks.md)
- **Sample Projects**: [GitHub repository with examples](https://github.com/activelog/examples)
- **Changelog**: [API and SDK updates](./changelog.md)

### Community
- **Developer Forum**: [community.activelog.dev](https://community.activelog.dev)
- **Stack Overflow**: Tag questions with `activelog-api`
- **GitHub Issues**: Report bugs and request features
- **Newsletter**: Monthly developer updates

---

Ready to start building? Get your API key at [beta.activelog.dev/api-keys](https://beta.activelog.dev/api-keys) and join our developer community!

**Last Updated**: [Current Date]  
**Developer Guide Version**: 2.1.0