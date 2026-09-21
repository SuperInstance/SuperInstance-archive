const fs = require('fs').promises;
const path = require('path');
const { EventEmitter } = require('events');
const crypto = require('crypto');
const tar = require('tar');
const { spawn } = require('child_process');

class EnvironmentManager extends EventEmitter {
  constructor(containerManager, config = {}) {
    super();
    
    this.containerManager = containerManager;
    this.config = {
      templatePath: config.templatePath || './templates',
      environmentsPath: config.environmentsPath || './environments',
      supportedLanguages: config.supportedLanguages || [
        'javascript', 'python', 'go', 'rust', 'java', 'php', 'ruby', 'c', 'cpp'
      ],
      supportedFrameworks: config.supportedFrameworks || {
        javascript: ['node', 'express', 'react', 'next', 'vue', 'svelte'],
        python: ['flask', 'django', 'fastapi', 'tornado'],
        go: ['gin', 'echo', 'fiber'],
        java: ['spring', 'quarkus'],
        php: ['laravel', 'symfony'],
        ruby: ['rails', 'sinatra']
      },
      
      // Environment lifecycle
      maxEnvironments: config.maxEnvironments || {
        free: 5,
        pro: 50,
        enterprise: 500
      },
      environmentTTL: config.environmentTTL || 7 * 24 * 60 * 60 * 1000, // 7 days
      
      // Version control
      enableVersioning: config.enableVersioning ?? true,
      maxVersions: config.maxVersions || 10,
      
      ...config
    };

    this.environments = new Map(); // envId -> environment info
    this.userEnvironments = new Map(); // userId -> Set of envIds
    this.templates = new Map(); // templateId -> template info
    this.snapshots = new Map(); // snapshotId -> snapshot info
    
    this.stats = {
      totalEnvironments: 0,
      activeEnvironments: 0,
      environmentsCreated: 0,
      environmentsDestroyed: 0,
      snapshotsTaken: 0
    };

    this.initializeTemplates();
  }

  // Initialize environment templates
  async initializeTemplates() {
    try {
      const templatesDir = this.config.templatePath;
      
      // Ensure templates directory exists
      await fs.mkdir(templatesDir, { recursive: true });
      
      // Load existing templates
      await this.loadTemplates();
      
      // Create default templates if none exist
      if (this.templates.size === 0) {
        await this.createDefaultTemplates();
      }
      
      this.emit('templatesInitialized', { count: this.templates.size });
      
    } catch (error) {
      console.error('Failed to initialize templates:', error);
      this.emit('error', { type: 'template_init', error });
    }
  }

  // Load existing templates
  async loadTemplates() {
    try {
      const templatesDir = this.config.templatePath;
      const entries = await fs.readdir(templatesDir, { withFileTypes: true });
      
      for (const entry of entries) {
        if (entry.isDirectory()) {
          const templatePath = path.join(templatesDir, entry.name);
          const configPath = path.join(templatePath, 'template.json');
          
          try {
            const configContent = await fs.readFile(configPath, 'utf8');
            const template = JSON.parse(configContent);
            template.path = templatePath;
            template.id = entry.name;
            
            this.templates.set(template.id, template);
          } catch (error) {
            console.warn(`Failed to load template ${entry.name}:`, error.message);
          }
        }
      }
    } catch (error) {
      console.warn('Templates directory not found, will create default templates');
    }
  }

  // Create default environment templates
  async createDefaultTemplates() {
    const defaultTemplates = [
      {
        id: 'node-basic',
        name: 'Node.js Basic',
        description: 'Basic Node.js environment with Express',
        language: 'javascript',
        framework: 'express',
        runtime: 'node:18-alpine',
        files: {
          'package.json': this.getNodePackageJson(),
          'server.js': this.getBasicExpressServer(),
          'README.md': '# Node.js Development Environment\n\nBasic Node.js setup with Express framework.'
        },
        commands: {
          install: 'npm install',
          start: 'npm start',
          dev: 'npm run dev',
          test: 'npm test'
        },
        ports: [3000],
        environment: {
          NODE_ENV: 'development'
        }
      },
      {
        id: 'python-flask',
        name: 'Python Flask',
        description: 'Python environment with Flask framework',
        language: 'python',
        framework: 'flask',
        runtime: 'python:3.11-slim',
        files: {
          'requirements.txt': 'Flask==2.3.3\nflask-cors==4.0.0\nrequests==2.31.0',
          'app.py': this.getBasicFlaskApp(),
          'README.md': '# Python Flask Development Environment\n\nBasic Flask application setup.'
        },
        commands: {
          install: 'pip install -r requirements.txt',
          start: 'python app.py',
          dev: 'flask run --debug',
          test: 'python -m pytest'
        },
        ports: [5000],
        environment: {
          FLASK_ENV: 'development',
          FLASK_DEBUG: '1'
        }
      },
      {
        id: 'react-app',
        name: 'React Application',
        description: 'React development environment with Vite',
        language: 'javascript',
        framework: 'react',
        runtime: 'node:18-alpine',
        files: {
          'package.json': this.getReactPackageJson(),
          'vite.config.js': this.getViteConfig(),
          'index.html': this.getReactIndexHtml(),
          'src/App.jsx': this.getBasicReactApp(),
          'src/main.jsx': this.getReactMain(),
          'README.md': '# React Development Environment\n\nModern React setup with Vite.'
        },
        commands: {
          install: 'npm install',
          start: 'npm run dev',
          build: 'npm run build',
          test: 'npm run test'
        },
        ports: [5173],
        environment: {
          NODE_ENV: 'development'
        }
      },
      {
        id: 'go-api',
        name: 'Go API',
        description: 'Go REST API with Gin framework',
        language: 'go',
        framework: 'gin',
        runtime: 'golang:1.21-alpine',
        files: {
          'go.mod': 'module api\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9.1',
          'main.go': this.getBasicGoAPI(),
          'README.md': '# Go API Development Environment\n\nREST API with Gin framework.'
        },
        commands: {
          install: 'go mod tidy',
          start: 'go run main.go',
          build: 'go build -o app main.go',
          test: 'go test ./...'
        },
        ports: [8080],
        environment: {
          GO111MODULE: 'on',
          CGO_ENABLED: '0'
        }
      }
    ];

    for (const template of defaultTemplates) {
      await this.saveTemplate(template);
    }
  }

  // Save template to filesystem
  async saveTemplate(template) {
    try {
      const templateDir = path.join(this.config.templatePath, template.id);
      await fs.mkdir(templateDir, { recursive: true });
      
      // Save template configuration
      const configPath = path.join(templateDir, 'template.json');
      await fs.writeFile(configPath, JSON.stringify(template, null, 2));
      
      // Create template files
      for (const [filePath, content] of Object.entries(template.files)) {
        const fullPath = path.join(templateDir, filePath);
        const fileDir = path.dirname(fullPath);
        
        await fs.mkdir(fileDir, { recursive: true });
        await fs.writeFile(fullPath, content);
      }
      
      template.path = templateDir;
      this.templates.set(template.id, template);
      
      this.emit('templateSaved', template);
      
    } catch (error) {
      console.error(`Failed to save template ${template.id}:`, error);
      throw error;
    }
  }

  // Create new environment from template
  async createEnvironment(userId, userTier, environmentConfig) {
    try {
      const userEnvs = this.userEnvironments.get(userId) || new Set();
      const maxEnvs = this.config.maxEnvironments[userTier] || this.config.maxEnvironments.free;
      
      if (userEnvs.size >= maxEnvs) {
        throw new Error(`Environment limit exceeded for ${userTier} tier: ${maxEnvs}`);
      }

      const template = this.templates.get(environmentConfig.templateId);
      if (!template) {
        throw new Error(`Template not found: ${environmentConfig.templateId}`);
      }

      const envId = crypto.randomUUID();
      const containerName = `env-${envId}`;
      
      // Create container for the environment
      const container = await this.containerManager.createUserContainer(
        userId, 
        userTier, 
        {
          image: template.runtime,
          containerConfig: {
            WorkingDir: '/workspace',
            Cmd: ['/bin/sh', '-c', 'sleep infinity'], // Keep container running
            ExposedPorts: this.buildExposedPorts(template.ports)
          }
        }
      );

      // Initialize environment in container
      await this.initializeEnvironmentFiles(container, template, environmentConfig);
      
      const environment = {
        id: envId,
        name: environmentConfig.name || `${template.name} Environment`,
        description: environmentConfig.description || template.description,
        userId,
        userTier,
        templateId: template.id,
        template,
        container,
        status: 'initializing',
        createdAt: new Date(),
        lastActivity: new Date(),
        version: 1,
        versions: [],
        metadata: {
          language: template.language,
          framework: template.framework,
          runtime: template.runtime,
          ports: template.ports
        },
        settings: {
          ...template.environment,
          ...environmentConfig.environment
        }
      };

      // Store environment
      this.environments.set(envId, environment);
      
      if (!this.userEnvironments.has(userId)) {
        this.userEnvironments.set(userId, new Set());
      }
      this.userEnvironments.get(userId).add(envId);

      // Install dependencies
      await this.installDependencies(environment);
      
      environment.status = 'ready';
      
      this.stats.totalEnvironments++;
      this.stats.activeEnvironments++;
      this.stats.environmentsCreated++;

      this.emit('environmentCreated', environment);
      
      return environment;
      
    } catch (error) {
      this.emit('environmentError', { userId, error });
      throw error;
    }
  }

  // Initialize environment files in container
  async initializeEnvironmentFiles(container, template, config) {
    try {
      // Create workspace structure
      const commands = [
        'mkdir -p /workspace',
        'cd /workspace'
      ];

      for (const command of commands) {
        await this.containerManager.executeCode(
          container.userId, 
          container.id, 
          command, 
          { language: 'bash' }
        );
      }

      // Copy template files to container
      for (const [filePath, content] of Object.entries(template.files)) {
        const command = `cat > "/workspace/${filePath}" << 'EOF'\n${content}\nEOF`;
        
        await this.containerManager.executeCode(
          container.userId,
          container.id,
          command,
          { language: 'bash' }
        );
      }

      // Apply any custom files from config
      if (config.files) {
        for (const [filePath, content] of Object.entries(config.files)) {
          const command = `cat > "/workspace/${filePath}" << 'EOF'\n${content}\nEOF`;
          
          await this.containerManager.executeCode(
            container.userId,
            container.id,
            command,
            { language: 'bash' }
          );
        }
      }

      this.emit('environmentFilesInitialized', { 
        containerId: container.id, 
        templateId: template.id 
      });
      
    } catch (error) {
      console.error('Failed to initialize environment files:', error);
      throw error;
    }
  }

  // Install dependencies in environment
  async installDependencies(environment) {
    try {
      const template = environment.template;
      
      if (template.commands?.install) {
        const result = await this.containerManager.executeCode(
          environment.userId,
          environment.container.id,
          template.commands.install,
          { 
            language: 'bash',
            workingDir: '/workspace',
            timeout: 300 // 5 minutes for installation
          }
        );

        if (result.exitCode !== 0) {
          throw new Error(`Dependency installation failed: ${result.stderr}`);
        }

        this.emit('dependenciesInstalled', { 
          environmentId: environment.id,
          output: result.stdout 
        });
      }
      
    } catch (error) {
      console.error('Failed to install dependencies:', error);
      throw error;
    }
  }

  // Execute command in environment
  async executeInEnvironment(userId, envId, command, options = {}) {
    try {
      const environment = this.environments.get(envId);
      if (!environment) {
        throw new Error('Environment not found');
      }

      if (environment.userId !== userId) {
        throw new Error('Unauthorized access to environment');
      }

      // Update last activity
      environment.lastActivity = new Date();

      // Execute command in container
      const result = await this.containerManager.executeCode(
        userId,
        environment.container.id,
        command,
        {
          workingDir: '/workspace',
          ...options
        }
      );

      this.emit('commandExecuted', { 
        environmentId: envId, 
        command, 
        result 
      });
      
      return result;
      
    } catch (error) {
      this.emit('executionError', { userId, envId, command, error });
      throw error;
    }
  }

  // Update environment files
  async updateEnvironmentFile(userId, envId, filePath, content) {
    try {
      const environment = this.environments.get(envId);
      if (!environment) {
        throw new Error('Environment not found');
      }

      if (environment.userId !== userId) {
        throw new Error('Unauthorized access to environment');
      }

      // Create backup before update
      if (this.config.enableVersioning) {
        await this.createSnapshot(envId, `Before updating ${filePath}`);
      }

      // Update file in container
      const command = `cat > "/workspace/${filePath}" << 'EOF'\n${content}\nEOF`;
      
      const result = await this.containerManager.executeCode(
        userId,
        environment.container.id,
        command,
        { language: 'bash' }
      );

      if (result.exitCode !== 0) {
        throw new Error(`Failed to update file: ${result.stderr}`);
      }

      environment.lastActivity = new Date();
      
      this.emit('fileUpdated', { 
        environmentId: envId, 
        filePath, 
        size: content.length 
      });
      
      return { success: true, filePath };
      
    } catch (error) {
      this.emit('fileUpdateError', { userId, envId, filePath, error });
      throw error;
    }
  }

  // Read environment file
  async readEnvironmentFile(userId, envId, filePath) {
    try {
      const environment = this.environments.get(envId);
      if (!environment) {
        throw new Error('Environment not found');
      }

      if (environment.userId !== userId) {
        throw new Error('Unauthorized access to environment');
      }

      const command = `cat "/workspace/${filePath}"`;
      
      const result = await this.containerManager.executeCode(
        userId,
        environment.container.id,
        command,
        { language: 'bash' }
      );

      if (result.exitCode !== 0) {
        throw new Error(`File not found or read error: ${result.stderr}`);
      }

      return {
        filePath,
        content: result.stdout,
        size: result.stdout.length
      };
      
    } catch (error) {
      this.emit('fileReadError', { userId, envId, filePath, error });
      throw error;
    }
  }

  // List environment files
  async listEnvironmentFiles(userId, envId, directoryPath = '/workspace') {
    try {
      const environment = this.environments.get(envId);
      if (!environment) {
        throw new Error('Environment not found');
      }

      if (environment.userId !== userId) {
        throw new Error('Unauthorized access to environment');
      }

      const command = `find "${directoryPath}" -type f -exec ls -la {} + 2>/dev/null || true`;
      
      const result = await this.containerManager.executeCode(
        userId,
        environment.container.id,
        command,
        { language: 'bash' }
      );

      // Parse ls output
      const files = this.parseLsOutput(result.stdout);
      
      return {
        path: directoryPath,
        files
      };
      
    } catch (error) {
      this.emit('fileListError', { userId, envId, directoryPath, error });
      throw error;
    }
  }

  // Create environment snapshot
  async createSnapshot(envId, description = '') {
    try {
      const environment = this.environments.get(envId);
      if (!environment) {
        throw new Error('Environment not found');
      }

      const snapshotId = crypto.randomUUID();
      const timestamp = Date.now();

      // Create tar archive of workspace
      const archiveCommand = `cd /workspace && tar -czf /tmp/snapshot-${snapshotId}.tar.gz .`;
      
      const result = await this.containerManager.executeCode(
        environment.userId,
        environment.container.id,
        archiveCommand,
        { language: 'bash' }
      );

      if (result.exitCode !== 0) {
        throw new Error(`Failed to create snapshot: ${result.stderr}`);
      }

      const snapshot = {
        id: snapshotId,
        environmentId: envId,
        userId: environment.userId,
        description,
        createdAt: new Date(timestamp),
        version: environment.version,
        size: 0, // Would get actual size from container
        archivePath: `/tmp/snapshot-${snapshotId}.tar.gz`
      };

      // Store snapshot info
      this.snapshots.set(snapshotId, snapshot);
      
      // Add to environment versions
      environment.versions.push(snapshot);
      
      // Keep only last N versions
      if (environment.versions.length > this.config.maxVersions) {
        const oldSnapshot = environment.versions.shift();
        this.snapshots.delete(oldSnapshot.id);
      }
      
      environment.version++;
      this.stats.snapshotsTaken++;

      this.emit('snapshotCreated', snapshot);
      
      return snapshot;
      
    } catch (error) {
      this.emit('snapshotError', { envId, error });
      throw error;
    }
  }

  // Restore environment from snapshot
  async restoreFromSnapshot(userId, envId, snapshotId) {
    try {
      const environment = this.environments.get(envId);
      if (!environment || environment.userId !== userId) {
        throw new Error('Environment not found or unauthorized');
      }

      const snapshot = this.snapshots.get(snapshotId);
      if (!snapshot || snapshot.environmentId !== envId) {
        throw new Error('Snapshot not found');
      }

      // Create current snapshot before restore
      await this.createSnapshot(envId, 'Before restore operation');

      // Clear workspace and restore from archive
      const restoreCommands = [
        'cd /workspace',
        'rm -rf *',
        `tar -xzf ${snapshot.archivePath}`
      ];

      for (const command of restoreCommands) {
        const result = await this.containerManager.executeCode(
          userId,
          environment.container.id,
          command,
          { language: 'bash' }
        );

        if (result.exitCode !== 0) {
          throw new Error(`Restore failed at step "${command}": ${result.stderr}`);
        }
      }

      environment.lastActivity = new Date();
      
      this.emit('environmentRestored', { 
        environmentId: envId, 
        snapshotId,
        restoredVersion: snapshot.version
      });
      
      return { success: true, restoredVersion: snapshot.version };
      
    } catch (error) {
      this.emit('restoreError', { userId, envId, snapshotId, error });
      throw error;
    }
  }

  // Start environment service
  async startEnvironmentService(userId, envId, serviceType = 'start') {
    try {
      const environment = this.environments.get(envId);
      if (!environment || environment.userId !== userId) {
        throw new Error('Environment not found or unauthorized');
      }

      const template = environment.template;
      const command = template.commands?.[serviceType];
      
      if (!command) {
        throw new Error(`Service command "${serviceType}" not defined in template`);
      }

      // Execute service start command
      const result = await this.containerManager.executeCode(
        userId,
        environment.container.id,
        command,
        {
          language: 'bash',
          workingDir: '/workspace',
          timeout: 60
        }
      );

      environment.lastActivity = new Date();
      
      this.emit('serviceStarted', { 
        environmentId: envId, 
        serviceType, 
        result 
      });
      
      return result;
      
    } catch (error) {
      this.emit('serviceError', { userId, envId, serviceType, error });
      throw error;
    }
  }

  // Get environment info
  getEnvironmentInfo(userId, envId) {
    const environment = this.environments.get(envId);
    if (!environment || environment.userId !== userId) {
      return null;
    }

    return {
      id: environment.id,
      name: environment.name,
      description: environment.description,
      status: environment.status,
      createdAt: environment.createdAt,
      lastActivity: environment.lastActivity,
      version: environment.version,
      template: {
        id: environment.template.id,
        name: environment.template.name,
        language: environment.template.language,
        framework: environment.template.framework
      },
      metadata: environment.metadata,
      snapshots: environment.versions.length,
      container: {
        id: environment.container.id,
        name: environment.container.name
      }
    };
  }

  // Get user environments
  getUserEnvironments(userId) {
    const envIds = this.userEnvironments.get(userId) || new Set();
    return Array.from(envIds)
      .map(envId => this.getEnvironmentInfo(userId, envId))
      .filter(env => env !== null);
  }

  // Delete environment
  async deleteEnvironment(userId, envId) {
    try {
      const environment = this.environments.get(envId);
      if (!environment || environment.userId !== userId) {
        throw new Error('Environment not found or unauthorized');
      }

      // Remove container
      await this.containerManager.removeContainer(userId, environment.container.id);
      
      // Clean up snapshots
      for (const snapshot of environment.versions) {
        this.snapshots.delete(snapshot.id);
      }

      // Remove from tracking
      this.environments.delete(envId);
      const userEnvs = this.userEnvironments.get(userId);
      if (userEnvs) {
        userEnvs.delete(envId);
        if (userEnvs.size === 0) {
          this.userEnvironments.delete(userId);
        }
      }

      this.stats.activeEnvironments--;
      this.stats.environmentsDestroyed++;

      this.emit('environmentDeleted', { 
        environmentId: envId, 
        userId 
      });
      
      return { success: true };
      
    } catch (error) {
      this.emit('environmentDeletionError', { userId, envId, error });
      throw error;
    }
  }

  // Utility methods
  buildExposedPorts(ports) {
    const exposedPorts = {};
    for (const port of ports) {
      exposedPorts[`${port}/tcp`] = {};
    }
    return exposedPorts;
  }

  parseLsOutput(output) {
    const lines = output.trim().split('\n').filter(line => line.length > 0);
    const files = [];
    
    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 9) {
        const permissions = parts[0];
        const size = parseInt(parts[4]) || 0;
        const name = parts.slice(8).join(' ');
        
        files.push({
          name,
          size,
          permissions,
          isDirectory: permissions.startsWith('d'),
          isFile: permissions.startsWith('-')
        });
      }
    }
    
    return files;
  }

  // Template content getters
  getNodePackageJson() {
    return JSON.stringify({
      "name": "sandbox-environment",
      "version": "1.0.0",
      "main": "server.js",
      "scripts": {
        "start": "node server.js",
        "dev": "nodemon server.js",
        "test": "echo \"Error: no test specified\" && exit 1"
      },
      "dependencies": {
        "express": "^4.19.2",
        "cors": "^2.8.5"
      },
      "devDependencies": {
        "nodemon": "^3.1.0"
      }
    }, null, 2);
  }

  getBasicExpressServer() {
    return `const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.json({ message: 'Hello from your sandbox environment!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(\`Server running on port \${PORT}\`);
});`;
  }

  getBasicFlaskApp() {
    return `from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello():
    return jsonify({
        'message': 'Hello from your Python sandbox environment!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)`;
  }

  getReactPackageJson() {
    return JSON.stringify({
      "name": "react-sandbox",
      "version": "1.0.0",
      "type": "module",
      "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview",
        "test": "echo \"No tests specified\""
      },
      "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0"
      },
      "devDependencies": {
        "@vitejs/plugin-react": "^4.0.0",
        "vite": "^4.0.0"
      }
    }, null, 2);
  }

  getViteConfig() {
    return `import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173
  }
});`;
  }

  getReactIndexHtml() {
    return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>React Sandbox</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>`;
  }

  getBasicReactApp() {
    return `import React, { useState } from 'react';

function App() {
  const [count, setCount] = useState(0);

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>React Sandbox Environment</h1>
      <p>Welcome to your React development environment!</p>
      
      <div style={{ margin: '2rem 0' }}>
        <button onClick={() => setCount(count + 1)}>
          Count: {count}
        </button>
      </div>
      
      <p style={{ color: '#666' }}>
        Edit src/App.jsx to get started
      </p>
    </div>
  );
}

export default App;`;
  }

  getReactMain() {
    return `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);`;
  }

  getBasicGoAPI() {
    return `package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

func main() {
    r := gin.Default()
    
    r.GET("/", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "message": "Hello from your Go sandbox environment!",
        })
    })
    
    r.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "status": "healthy",
        })
    })
    
    r.Run(":8080")
}`;
  }

  // Get service statistics
  getServiceStats() {
    return {
      ...this.stats,
      templatesAvailable: this.templates.size,
      environmentsByTier: this.getEnvironmentsByTier(),
      snapshotsStored: this.snapshots.size,
      avgEnvironmentsPerUser: this.stats.activeEnvironments / Math.max(this.userEnvironments.size, 1)
    };
  }

  getEnvironmentsByTier() {
    const tierCount = { free: 0, pro: 0, enterprise: 0 };
    
    for (const environment of this.environments.values()) {
      tierCount[environment.userTier] = (tierCount[environment.userTier] || 0) + 1;
    }
    
    return tierCount;
  }

  // Health check
  async healthCheck() {
    try {
      return {
        healthy: true,
        stats: this.getServiceStats(),
        templatesLoaded: this.templates.size > 0,
        containerManagerHealthy: await this.containerManager.healthCheck().then(h => h.healthy)
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Clean up expired environments
  async cleanupExpiredEnvironments() {
    const now = Date.now();
    const expiredEnvironments = [];
    
    for (const [envId, environment] of this.environments.entries()) {
      const age = now - environment.createdAt.getTime();
      const idleTime = now - environment.lastActivity.getTime();
      
      if (age > this.config.environmentTTL || idleTime > this.config.environmentTTL / 2) {
        expiredEnvironments.push({ userId: environment.userId, envId });
      }
    }

    for (const { userId, envId } of expiredEnvironments) {
      try {
        await this.deleteEnvironment(userId, envId);
      } catch (error) {
        console.error(`Failed to cleanup environment ${envId}:`, error);
      }
    }

    this.emit('environmentsCleanedUp', { count: expiredEnvironments.length });
  }
}

module.exports = EnvironmentManager;