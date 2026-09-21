#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Set environment variables
process.env.NODE_ENV = process.env.NODE_ENV || 'development';

// Add TypeScript paths
require('tsconfig-paths/register');

// Compile TypeScript and start server
const isDevelopment = process.env.NODE_ENV === 'development';

if (isDevelopment) {
  // Development mode with ts-node and watch
  const child = spawn('ts-node-dev', [
    '--transpile-only',
    '--ignore-watch', 'node_modules',
    '--respawn',
    '--clear',
    '--notify',
    '--exit-child',
    'src/server.ts'
  ], {
    cwd: __dirname,
    stdio: 'inherit',
    env: {
      ...process.env,
      TS_NODE_PROJECT: path.resolve(__dirname, '../tsconfig.json')
    }
  });

  child.on('close', (code) => {
    console.log(`Development server exited with code ${code}`);
    process.exit(code);
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\nReceived SIGINT. Graceful shutdown...');
    child.kill('SIGTERM');
  });

  process.on('SIGTERM', () => {
    console.log('\nReceived SIGTERM. Graceful shutdown...');
    child.kill('SIGTERM');
  });
} else {
  // Production mode - assume TypeScript is already compiled
  require('../dist/server.js');
}