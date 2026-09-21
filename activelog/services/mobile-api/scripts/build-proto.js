#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const protoDir = path.join(__dirname, '..', 'proto');
const outputDir = path.join(__dirname, '..', 'src', 'protobuf');

// Ensure output directory exists
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// Get all proto files
const protoFiles = fs.readdirSync(protoDir)
  .filter(file => file.endsWith('.proto'))
  .map(file => path.join(protoDir, file));

if (protoFiles.length === 0) {
  console.log('No .proto files found in', protoDir);
  process.exit(0);
}

console.log('Building Protocol Buffers...');
console.log('Proto files:', protoFiles);

try {
  // Generate JavaScript files
  const jsCommand = [
    'npx pbjs',
    '-t static-module',
    '-w es6',
    '-o', path.join(outputDir, 'compiled.js'),
    ...protoFiles
  ].join(' ');
  
  console.log('Generating JavaScript:', jsCommand);
  execSync(jsCommand, { stdio: 'inherit' });
  
  // Generate TypeScript definitions
  const tsCommand = [
    'npx pbts',
    '-o', path.join(outputDir, 'compiled.d.ts'),
    path.join(outputDir, 'compiled.js')
  ].join(' ');
  
  console.log('Generating TypeScript definitions:', tsCommand);
  execSync(tsCommand, { stdio: 'inherit' });
  
  console.log('Protocol Buffers compiled successfully!');
  
} catch (error) {
  console.error('Error compiling Protocol Buffers:', error.message);
  process.exit(1);
}