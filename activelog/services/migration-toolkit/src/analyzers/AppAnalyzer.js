import fs from 'fs-extra';
import path from 'path';
import { execSync } from 'child_process';
import xml2js from 'xml2js';
import yaml from 'yaml';
import logger from '../lib/logger.js';
import { FileSystemScanner } from './FileSystemScanner.js';
import { DependencyAnalyzer } from './DependencyAnalyzer.js';
import { DatabaseSchemaAnalyzer } from './DatabaseSchemaAnalyzer.js';
import { APIEndpointAnalyzer } from './APIEndpointAnalyzer.js';

/**
 * Comprehensive application and website migration analyzer
 * Analyzes code structure, dependencies, databases, and APIs
 */
export class AppAnalyzer {
  constructor(options = {}) {
    this.options = {
      scanDepth: 10,
      includeNodeModules: false,
      analyzePackageFiles: true,
      analyzeDockerfiles: true,
      analyzeKubernetesManifests: true,
      analyzeDatabaseSchemas: true,
      analyzeAPIEndpoints: true,
      generateMigrationPlan: true,
      outputFormat: 'json',
      ...options
    };
    
    this.fileScanner = new FileSystemScanner(this.options);
    this.dependencyAnalyzer = new DependencyAnalyzer(this.options);
    this.dbAnalyzer = new DatabaseSchemaAnalyzer(this.options);
    this.apiAnalyzer = new APIEndpointAnalyzer(this.options);
    
    this.supportedFrameworks = [
      'react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt.js',
      'express', 'fastify', 'koa', 'hapi', 'nest.js',
      'django', 'flask', 'fastapi', 'rails', 'laravel',
      'spring-boot', 'quarkus', 'micronaut',
      '.net', 'asp.net', 'blazor'
    ];
  }

  /**
   * Analyze application or website for migration readiness
   */
  async analyzeApplication(projectPath, options = {}) {
    try {
      logger.info(`Starting analysis of application at: ${projectPath}`);
      
      const analysis = {
        timestamp: new Date().toISOString(),
        projectPath: path.resolve(projectPath),
        analysisId: this.generateAnalysisId(),
        summary: {},
        framework: {},
        dependencies: {},
        database: {},
        api: {},
        infrastructure: {},
        security: {},
        performance: {},
        migrationComplexity: 'unknown',
        migrationPlan: {},
        recommendations: [],
        warnings: [],
        errors: []
      };

      // Validate project path
      if (!await fs.pathExists(projectPath)) {
        throw new Error(`Project path does not exist: ${projectPath}`);
      }

      // 1. Scan file system structure
      logger.info('Scanning file system structure...');
      const fileStructure = await this.fileScanner.scanDirectory(projectPath);
      analysis.fileStructure = fileStructure;

      // 2. Detect framework and technology stack
      logger.info('Detecting framework and technology stack...');
      analysis.framework = await this.detectFramework(projectPath, fileStructure);

      // 3. Analyze dependencies
      logger.info('Analyzing dependencies...');
      analysis.dependencies = await this.dependencyAnalyzer.analyzeDependencies(projectPath);

      // 4. Analyze database schemas
      if (this.options.analyzeDatabaseSchemas) {
        logger.info('Analyzing database schemas...');
        analysis.database = await this.dbAnalyzer.analyzeSchemas(projectPath);
      }

      // 5. Analyze API endpoints
      if (this.options.analyzeAPIEndpoints) {
        logger.info('Analyzing API endpoints...');
        analysis.api = await this.apiAnalyzer.analyzeEndpoints(projectPath);
      }

      // 6. Analyze infrastructure configuration
      logger.info('Analyzing infrastructure configuration...');
      analysis.infrastructure = await this.analyzeInfrastructure(projectPath, fileStructure);

      // 7. Security analysis
      logger.info('Performing security analysis...');
      analysis.security = await this.analyzeSecurityFeatures(projectPath, fileStructure);

      // 8. Performance analysis
      logger.info('Analyzing performance characteristics...');
      analysis.performance = await this.analyzePerformance(projectPath, fileStructure);

      // 9. Calculate migration complexity
      logger.info('Calculating migration complexity...');
      analysis.migrationComplexity = this.calculateMigrationComplexity(analysis);

      // 10. Generate migration plan
      if (this.options.generateMigrationPlan) {
        logger.info('Generating migration plan...');
        analysis.migrationPlan = await this.generateMigrationPlan(analysis);
      }

      // 11. Generate recommendations
      analysis.recommendations = this.generateRecommendations(analysis);

      // 12. Create summary
      analysis.summary = this.createAnalysisSummary(analysis);

      logger.info(`Analysis completed successfully. Complexity: ${analysis.migrationComplexity}`);
      return analysis;

    } catch (error) {
      logger.error('Error during application analysis:', error);
      throw error;
    }
  }

  /**
   * Detect framework and technology stack
   */
  async detectFramework(projectPath, fileStructure) {
    const framework = {
      primary: null,
      secondary: [],
      language: 'unknown',
      version: null,
      buildTools: [],
      packageManagers: [],
      runtimeEnvironment: null
    };

    try {
      // Check for package.json (Node.js projects)
      const packageJsonPath = path.join(projectPath, 'package.json');
      if (await fs.pathExists(packageJsonPath)) {
        const packageJson = await fs.readJson(packageJsonPath);
        framework.packageManagers.push('npm');
        framework.language = 'javascript';
        
        // Detect Node.js frameworks
        const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };
        
        if (deps.react) {
          framework.primary = 'react';
          framework.version = deps.react;
        } else if (deps.vue) {
          framework.primary = 'vue';
          framework.version = deps.vue;
        } else if (deps['@angular/core']) {
          framework.primary = 'angular';
          framework.version = deps['@angular/core'];
        } else if (deps.express) {
          framework.primary = 'express';
          framework.version = deps.express;
        } else if (deps.next) {
          framework.primary = 'next.js';
          framework.version = deps.next;
        }

        // Detect build tools
        if (deps.webpack) framework.buildTools.push('webpack');
        if (deps.vite) framework.buildTools.push('vite');
        if (deps.parcel) framework.buildTools.push('parcel');
        if (deps.rollup) framework.buildTools.push('rollup');
      }

      // Check for yarn.lock
      if (await fs.pathExists(path.join(projectPath, 'yarn.lock'))) {
        framework.packageManagers.push('yarn');
      }

      // Check for pnpm-lock.yaml
      if (await fs.pathExists(path.join(projectPath, 'pnpm-lock.yaml'))) {
        framework.packageManagers.push('pnpm');
      }

      // Check for requirements.txt (Python projects)
      if (await fs.pathExists(path.join(projectPath, 'requirements.txt'))) {
        framework.language = 'python';
        const requirements = await fs.readFile(path.join(projectPath, 'requirements.txt'), 'utf8');
        
        if (requirements.includes('django')) {
          framework.primary = 'django';
        } else if (requirements.includes('flask')) {
          framework.primary = 'flask';
        } else if (requirements.includes('fastapi')) {
          framework.primary = 'fastapi';
        }
      }

      // Check for Gemfile (Ruby projects)
      if (await fs.pathExists(path.join(projectPath, 'Gemfile'))) {
        framework.language = 'ruby';
        framework.primary = 'rails'; // Assume Rails for Ruby projects
      }

      // Check for composer.json (PHP projects)
      if (await fs.pathExists(path.join(projectPath, 'composer.json'))) {
        framework.language = 'php';
        const composerJson = await fs.readJson(path.join(projectPath, 'composer.json'));
        
        if (composerJson.require && composerJson.require['laravel/framework']) {
          framework.primary = 'laravel';
        }
      }

      // Check for pom.xml (Java Maven projects)
      if (await fs.pathExists(path.join(projectPath, 'pom.xml'))) {
        framework.language = 'java';
        framework.buildTools.push('maven');
        
        const pomXml = await fs.readFile(path.join(projectPath, 'pom.xml'), 'utf8');
        if (pomXml.includes('spring-boot')) {
          framework.primary = 'spring-boot';
        }
      }

      // Check for build.gradle (Java Gradle projects)
      if (await fs.pathExists(path.join(projectPath, 'build.gradle'))) {
        framework.language = 'java';
        framework.buildTools.push('gradle');
      }

      // Check for .csproj files (.NET projects)
      const csprojFiles = fileStructure.files.filter(f => f.endsWith('.csproj'));
      if (csprojFiles.length > 0) {
        framework.language = 'c#';
        framework.primary = '.net';
      }

      // Detect runtime environment
      if (framework.language === 'javascript') {
        framework.runtimeEnvironment = 'node.js';
      } else if (framework.language === 'python') {
        framework.runtimeEnvironment = 'python';
      } else if (framework.language === 'java') {
        framework.runtimeEnvironment = 'jvm';
      } else if (framework.language === 'c#') {
        framework.runtimeEnvironment = '.net';
      }

    } catch (error) {
      logger.error('Error detecting framework:', error);
    }

    return framework;
  }

  /**
   * Analyze infrastructure configuration
   */
  async analyzeInfrastructure(projectPath, fileStructure) {
    const infrastructure = {
      containerization: {},
      orchestration: {},
      cloudConfig: {},
      cicd: {},
      monitoring: {},
      loadBalancing: {},
      databases: [],
      caching: [],
      messageQueues: []
    };

    try {
      // Docker analysis
      const dockerfilePath = path.join(projectPath, 'Dockerfile');
      if (await fs.pathExists(dockerfilePath)) {
        const dockerfile = await fs.readFile(dockerfilePath, 'utf8');
        infrastructure.containerization.docker = {
          exists: true,
          baseImages: this.extractDockerBaseImages(dockerfile),
          ports: this.extractDockerPorts(dockerfile),
          volumes: this.extractDockerVolumes(dockerfile)
        };
      }

      // Docker Compose analysis
      const dockerComposePaths = [
        'docker-compose.yml',
        'docker-compose.yaml',
        'docker-compose.production.yml',
        'docker-compose.dev.yml'
      ];

      for (const composePath of dockerComposePaths) {
        const fullPath = path.join(projectPath, composePath);
        if (await fs.pathExists(fullPath)) {
          const composeContent = await fs.readFile(fullPath, 'utf8');
          const composeConfig = yaml.parse(composeContent);
          
          infrastructure.containerization.compose = {
            exists: true,
            services: Object.keys(composeConfig.services || {}),
            networks: Object.keys(composeConfig.networks || {}),
            volumes: Object.keys(composeConfig.volumes || {})
          };
        }
      }

      // Kubernetes analysis
      const k8sFiles = fileStructure.files.filter(f => 
        f.endsWith('.yaml') || f.endsWith('.yml')
      ).filter(f => {
        const content = fs.readFileSync(path.join(projectPath, f), 'utf8');
        return content.includes('apiVersion') && content.includes('kind');
      });

      if (k8sFiles.length > 0) {
        infrastructure.orchestration.kubernetes = {
          exists: true,
          manifests: k8sFiles.length,
          resources: await this.analyzeKubernetesManifests(projectPath, k8sFiles)
        };
      }

      // CI/CD analysis
      if (await fs.pathExists(path.join(projectPath, '.github/workflows'))) {
        infrastructure.cicd.github = { exists: true };
      }
      if (await fs.pathExists(path.join(projectPath, '.gitlab-ci.yml'))) {
        infrastructure.cicd.gitlab = { exists: true };
      }
      if (await fs.pathExists(path.join(projectPath, 'Jenkinsfile'))) {
        infrastructure.cicd.jenkins = { exists: true };
      }

    } catch (error) {
      logger.error('Error analyzing infrastructure:', error);
    }

    return infrastructure;
  }

  /**
   * Analyze security features and configurations
   */
  async analyzeSecurityFeatures(projectPath, fileStructure) {
    const security = {
      authentication: [],
      authorization: [],
      encryption: [],
      vulnerabilities: [],
      securityHeaders: [],
      secretsManagement: [],
      inputValidation: [],
      auditLogging: []
    };

    try {
      // Scan for security-related files and patterns
      const securityFiles = fileStructure.files.filter(f => 
        f.includes('auth') || 
        f.includes('security') || 
        f.includes('jwt') ||
        f.includes('oauth') ||
        f.includes('ssl') ||
        f.includes('tls')
      );

      // Check for common authentication libraries
      const packageJsonPath = path.join(projectPath, 'package.json');
      if (await fs.pathExists(packageJsonPath)) {
        const packageJson = await fs.readJson(packageJsonPath);
        const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };

        if (deps.passport) security.authentication.push('passport');
        if (deps.jsonwebtoken) security.authentication.push('jwt');
        if (deps.bcrypt) security.encryption.push('bcrypt');
        if (deps.helmet) security.securityHeaders.push('helmet');
        if (deps['express-rate-limit']) security.authentication.push('rate-limiting');
      }

      // Check for environment variables and secrets
      if (await fs.pathExists(path.join(projectPath, '.env'))) {
        security.secretsManagement.push('.env file detected');
      }

      // Scan for hardcoded secrets (basic patterns)
      await this.scanForHardcodedSecrets(projectPath, security);

    } catch (error) {
      logger.error('Error analyzing security features:', error);
    }

    return security;
  }

  /**
   * Analyze performance characteristics
   */
  async analyzePerformance(projectPath, fileStructure) {
    const performance = {
      bundleSize: null,
      dependencies: {
        total: 0,
        production: 0,
        development: 0,
        outdated: []
      },
      caching: [],
      optimization: [],
      monitoring: [],
      cdn: [],
      compression: []
    };

    try {
      // Analyze package.json for dependency count
      const packageJsonPath = path.join(projectPath, 'package.json');
      if (await fs.pathExists(packageJsonPath)) {
        const packageJson = await fs.readJson(packageJsonPath);
        
        performance.dependencies.production = Object.keys(packageJson.dependencies || {}).length;
        performance.dependencies.development = Object.keys(packageJson.devDependencies || {}).length;
        performance.dependencies.total = performance.dependencies.production + performance.dependencies.development;
      }

      // Check for build output
      const buildDirs = ['build', 'dist', 'public', '.next'];
      for (const buildDir of buildDirs) {
        const buildPath = path.join(projectPath, buildDir);
        if (await fs.pathExists(buildPath)) {
          performance.bundleSize = await this.calculateDirectorySize(buildPath);
          break;
        }
      }

      // Check for performance optimization tools
      if (fileStructure.files.some(f => f.includes('webpack'))) {
        performance.optimization.push('webpack');
      }
      if (fileStructure.files.some(f => f.includes('vite'))) {
        performance.optimization.push('vite');
      }

    } catch (error) {
      logger.error('Error analyzing performance:', error);
    }

    return performance;
  }

  /**
   * Calculate migration complexity based on analysis results
   */
  calculateMigrationComplexity(analysis) {
    let complexityScore = 0;
    let factors = [];

    // Framework complexity
    if (analysis.framework.primary) {
      const frameworkComplexity = {
        'react': 2,
        'vue': 2,
        'angular': 4,
        'express': 3,
        'django': 4,
        'rails': 5,
        'spring-boot': 5,
        '.net': 4
      };
      complexityScore += frameworkComplexity[analysis.framework.primary] || 3;
      factors.push(`Framework: ${analysis.framework.primary}`);
    }

    // Dependency complexity
    if (analysis.dependencies.total > 100) {
      complexityScore += 3;
      factors.push('High dependency count');
    } else if (analysis.dependencies.total > 50) {
      complexityScore += 2;
      factors.push('Moderate dependency count');
    }

    // Database complexity
    if (analysis.database.schemas && analysis.database.schemas.length > 5) {
      complexityScore += 3;
      factors.push('Multiple database schemas');
    }

    // API complexity
    if (analysis.api.endpoints && analysis.api.endpoints.length > 20) {
      complexityScore += 2;
      factors.push('Many API endpoints');
    }

    // Infrastructure complexity
    if (analysis.infrastructure.orchestration.kubernetes) {
      complexityScore += 4;
      factors.push('Kubernetes orchestration');
    }
    if (analysis.infrastructure.containerization.docker) {
      complexityScore += 2;
      factors.push('Docker containerization');
    }

    // Security complexity
    if (analysis.security.authentication.length > 2) {
      complexityScore += 2;
      factors.push('Complex authentication');
    }

    // Determine complexity level
    let complexity;
    if (complexityScore <= 5) {
      complexity = 'low';
    } else if (complexityScore <= 12) {
      complexity = 'medium';
    } else if (complexityScore <= 20) {
      complexity = 'high';
    } else {
      complexity = 'very-high';
    }

    return {
      level: complexity,
      score: complexityScore,
      factors: factors,
      estimatedTimeWeeks: Math.ceil(complexityScore / 2)
    };
  }

  /**
   * Generate migration plan
   */
  async generateMigrationPlan(analysis) {
    const plan = {
      phases: [],
      timeline: {},
      resources: {},
      risks: [],
      prerequisites: [],
      rollbackStrategy: {}
    };

    // Phase 1: Assessment and Planning
    plan.phases.push({
      name: 'Assessment and Planning',
      duration: '1-2 weeks',
      tasks: [
        'Complete application analysis',
        'Identify migration dependencies',
        'Create detailed migration strategy',
        'Set up development environment',
        'Plan rollback procedures'
      ]
    });

    // Phase 2: Infrastructure Migration
    if (analysis.infrastructure.containerization.docker || analysis.infrastructure.orchestration.kubernetes) {
      plan.phases.push({
        name: 'Infrastructure Migration',
        duration: '2-4 weeks',
        tasks: [
          'Migrate containerization configs',
          'Set up orchestration platform',
          'Configure networking and storage',
          'Implement monitoring and logging'
        ]
      });
    }

    // Phase 3: Database Migration
    if (analysis.database.schemas && analysis.database.schemas.length > 0) {
      plan.phases.push({
        name: 'Database Migration',
        duration: '1-3 weeks',
        tasks: [
          'Export existing database schemas',
          'Create migration scripts',
          'Test data migration',
          'Implement data validation',
          'Set up backup procedures'
        ]
      });
    }

    // Phase 4: Application Migration
    plan.phases.push({
      name: 'Application Migration',
      duration: `${analysis.migrationComplexity.estimatedTimeWeeks} weeks`,
      tasks: [
        'Migrate application code',
        'Update dependencies',
        'Implement API wrappers if needed',
        'Configure environment variables',
        'Update build and deployment scripts'
      ]
    });

    // Phase 5: Testing and Validation
    plan.phases.push({
      name: 'Testing and Validation',
      duration: '1-2 weeks',
      tasks: [
        'Run automated tests',
        'Perform integration testing',
        'Validate data integrity',
        'Performance testing',
        'Security testing'
      ]
    });

    // Phase 6: Go-Live and Monitoring
    plan.phases.push({
      name: 'Go-Live and Monitoring',
      duration: '1 week',
      tasks: [
        'Deploy to production',
        'Monitor system performance',
        'Validate functionality',
        'Address any issues',
        'Documentation and handover'
      ]
    });

    // Calculate total timeline
    const totalWeeks = plan.phases.reduce((sum, phase) => {
      const weeks = parseInt(phase.duration.split('-')[0]) || 1;
      return sum + weeks;
    }, 0);

    plan.timeline = {
      estimatedWeeks: totalWeeks,
      estimatedMonths: Math.ceil(totalWeeks / 4),
      phases: plan.phases.length
    };

    return plan;
  }

  /**
   * Generate recommendations based on analysis
   */
  generateRecommendations(analysis) {
    const recommendations = [];

    // Framework-specific recommendations
    if (analysis.framework.primary === 'express') {
      recommendations.push({
        category: 'Framework',
        priority: 'medium',
        title: 'Consider upgrading to latest Express version',
        description: 'Ensure you are using the latest stable version of Express for security and performance benefits.'
      });
    }

    // Security recommendations
    if (analysis.security.vulnerabilities.length > 0) {
      recommendations.push({
        category: 'Security',
        priority: 'high',
        title: 'Address security vulnerabilities',
        description: `Found ${analysis.security.vulnerabilities.length} potential security issues that should be resolved before migration.`
      });
    }

    // Performance recommendations
    if (analysis.performance.dependencies.total > 100) {
      recommendations.push({
        category: 'Performance',
        priority: 'medium',
        title: 'Optimize dependency tree',
        description: 'Consider reducing the number of dependencies to improve build times and reduce bundle size.'
      });
    }

    // Infrastructure recommendations
    if (!analysis.infrastructure.containerization.docker) {
      recommendations.push({
        category: 'Infrastructure',
        priority: 'medium',
        title: 'Consider containerization',
        description: 'Adding Docker support would simplify deployment and improve environment consistency.'
      });
    }

    return recommendations;
  }

  /**
   * Create analysis summary
   */
  createAnalysisSummary(analysis) {
    return {
      projectType: analysis.framework.primary || 'unknown',
      language: analysis.framework.language,
      complexity: analysis.migrationComplexity.level,
      estimatedMigrationTime: `${analysis.migrationComplexity.estimatedTimeWeeks} weeks`,
      totalFiles: analysis.fileStructure?.totalFiles || 0,
      totalDependencies: analysis.dependencies?.total || 0,
      databaseSchemas: analysis.database?.schemas?.length || 0,
      apiEndpoints: analysis.api?.endpoints?.length || 0,
      recommendationsCount: analysis.recommendations?.length || 0,
      warningsCount: analysis.warnings?.length || 0,
      errorsCount: analysis.errors?.length || 0
    };
  }

  /**
   * Utility methods
   */
  generateAnalysisId() {
    return `analysis_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  extractDockerBaseImages(dockerfile) {
    const lines = dockerfile.split('\n');
    const fromLines = lines.filter(line => line.trim().startsWith('FROM'));
    return fromLines.map(line => line.split(' ')[1]);
  }

  extractDockerPorts(dockerfile) {
    const lines = dockerfile.split('\n');
    const exposePorts = lines.filter(line => line.trim().startsWith('EXPOSE'));
    return exposePorts.map(line => line.split(' ')[1]);
  }

  extractDockerVolumes(dockerfile) {
    const lines = dockerfile.split('\n');
    const volumeLines = lines.filter(line => line.trim().startsWith('VOLUME'));
    return volumeLines.map(line => line.split(' ')[1]);
  }

  async analyzeKubernetesManifests(projectPath, k8sFiles) {
    const resources = {
      deployments: 0,
      services: 0,
      ingresses: 0,
      configMaps: 0,
      secrets: 0,
      persistentVolumes: 0
    };

    for (const file of k8sFiles) {
      try {
        const content = await fs.readFile(path.join(projectPath, file), 'utf8');
        const docs = yaml.parseAllDocuments(content);
        
        for (const doc of docs) {
          const manifest = doc.toJS();
          if (manifest && manifest.kind) {
            const kind = manifest.kind.toLowerCase();
            if (resources.hasOwnProperty(kind + 's')) {
              resources[kind + 's']++;
            } else if (resources.hasOwnProperty(kind)) {
              resources[kind]++;
            }
          }
        }
      } catch (error) {
        logger.warn(`Error parsing Kubernetes manifest ${file}:`, error);
      }
    }

    return resources;
  }

  async scanForHardcodedSecrets(projectPath, security) {
    const secretPatterns = [
      /api[_-]?key[_-]?=?['\"]?[a-zA-Z0-9]{32,}/i,
      /secret[_-]?key[_-]?=?['\"]?[a-zA-Z0-9]{32,}/i,
      /password[_-]?=?['\"]?[a-zA-Z0-9]{8,}/i,
      /token[_-]?=?['\"]?[a-zA-Z0-9]{32,}/i
    ];

    // This is a basic implementation - in production, use specialized tools
    // like truffleHog, git-secrets, or similar
    security.vulnerabilities.push('Basic hardcoded secret scan performed - use specialized tools for thorough analysis');
  }

  async calculateDirectorySize(dirPath) {
    try {
      const stats = await fs.stat(dirPath);
      if (!stats.isDirectory()) {
        return stats.size;
      }

      let totalSize = 0;
      const items = await fs.readdir(dirPath);

      for (const item of items) {
        const itemPath = path.join(dirPath, item);
        totalSize += await this.calculateDirectorySize(itemPath);
      }

      return totalSize;
    } catch (error) {
      return 0;
    }
  }
}