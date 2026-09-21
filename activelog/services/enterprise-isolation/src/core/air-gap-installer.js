const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const tar = require('tar');
const archiver = require('archiver');
const { exec } = require('child_process');
const { promisify } = require('util');
const EventEmitter = require('events');

class AirGapInstaller extends EventEmitter {
    constructor() {
        super();
        this.installationState = {
            status: 'not_initialized',
            progress: 0,
            stage: null,
            errors: [],
            warnings: []
        };
        
        this.installationStages = [
            'pre_flight_checks',
            'environment_validation', 
            'dependency_verification',
            'security_initialization',
            'database_setup',
            'configuration_deployment',
            'service_installation',
            'security_hardening',
            'verification_tests',
            'post_installation_setup'
        ];

        this.networkCheckResults = {
            hasInternetAccess: null,
            openPorts: [],
            networkInterfaces: [],
            dnsResolution: null,
            lastChecked: null
        };

        this.securityRequirements = {
            minDiskEncryption: true,
            requiredFilePermissions: '600',
            mandatoryFirewallRules: true,
            disableUnnecessaryServices: true,
            hardenedSSHConfig: true,
            auditLoggingEnabled: true,
            selinuxEnforcing: true
        };
    }

    async initialize() {
        try {
            await this.verifyAirGapStatus();
            await this.setupInstallationEnvironment();
            this.emit('initialized');
        } catch (error) {
            this.emit('error', { phase: 'initialization', error });
            throw error;
        }
    }

    async verifyAirGapStatus() {
        this.emit('statusCheck', { message: 'Verifying air-gap status...' });
        
        const checks = await Promise.allSettled([
            this.checkNetworkConnectivity(),
            this.checkRunningServices(),
            this.checkSystemPorts(),
            this.checkDNSResolution(),
            this.checkSystemUpdates()
        ]);

        const results = {
            networkIsolated: true,
            timestamp: new Date(),
            checks: {}
        };

        // Process check results
        checks.forEach((result, index) => {
            const checkNames = ['network', 'services', 'ports', 'dns', 'updates'];
            results.checks[checkNames[index]] = result.status === 'fulfilled' ? 
                result.value : { error: result.reason.message };
        });

        // Evaluate air-gap status
        if (results.checks.network?.hasInternet || 
            results.checks.dns?.canResolveExternal ||
            results.checks.ports?.externalPortsOpen?.length > 0) {
            
            results.networkIsolated = false;
            results.violations = [];

            if (results.checks.network?.hasInternet) {
                results.violations.push('Internet connectivity detected');
            }
            if (results.checks.dns?.canResolveExternal) {
                results.violations.push('External DNS resolution possible');
            }
            if (results.checks.ports?.externalPortsOpen?.length > 0) {
                results.violations.push(`External ports open: ${results.checks.ports.externalPortsOpen.join(', ')}`);
            }
        }

        this.networkCheckResults = results;
        
        if (!results.networkIsolated) {
            throw new Error(`Air-gap violation detected: ${results.violations.join(', ')}`);
        }

        this.emit('airGapVerified', results);
        return results;
    }

    async checkNetworkConnectivity() {
        const execAsync = promisify(exec);
        
        try {
            // Test common external destinations
            const testHosts = [
                '8.8.8.8',      // Google DNS
                '1.1.1.1',      // Cloudflare DNS  
                'google.com',   // Popular website
                'github.com',   // Development resource
                'npmjs.org'     // Package repository
            ];

            const connectivityResults = await Promise.allSettled(
                testHosts.map(async (host) => {
                    try {
                        const timeout = 5000; // 5 second timeout
                        const result = await execAsync(`ping -c 1 -W ${timeout/1000} ${host}`, {
                            timeout: timeout + 1000
                        });
                        return { host, reachable: true, output: result.stdout };
                    } catch (error) {
                        return { host, reachable: false, error: error.message };
                    }
                })
            );

            const reachableHosts = connectivityResults
                .filter(result => result.status === 'fulfilled' && result.value.reachable)
                .map(result => result.value.host);

            return {
                hasInternet: reachableHosts.length > 0,
                reachableHosts,
                testedHosts: testHosts,
                timestamp: new Date()
            };
        } catch (error) {
            return {
                hasInternet: false,
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async checkRunningServices() {
        const execAsync = promisify(exec);
        
        try {
            // Check for services that might provide external connectivity
            const suspiciousServices = [
                'nginx', 'apache2', 'httpd',        // Web servers
                'openssh-server', 'ssh', 'sshd',   // SSH servers
                'cups', 'cups-browsed',             // Print services
                'avahi-daemon',                     // Network discovery
                'bluetooth', 'bluetoothd',         // Bluetooth
                'wpa_supplicant',                   // WiFi
                'NetworkManager', 'networking'      // Network management
            ];

            const { stdout } = await execAsync('systemctl list-units --type=service --state=running --no-pager');
            const runningServices = stdout.split('\n')
                .filter(line => line.includes('.service'))
                .map(line => line.trim().split(/\s+/)[0]);

            const suspiciousRunning = runningServices.filter(service =>
                suspiciousServices.some(suspicious => service.includes(suspicious))
            );

            return {
                runningServices,
                suspiciousServices: suspiciousRunning,
                servicesToReview: suspiciousRunning.length > 0,
                timestamp: new Date()
            };
        } catch (error) {
            return {
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async checkSystemPorts() {
        const execAsync = promisify(exec);
        
        try {
            // Check for listening ports
            const { stdout } = await execAsync('netstat -tuln');
            const ports = stdout.split('\n')
                .filter(line => line.includes('LISTEN'))
                .map(line => {
                    const parts = line.trim().split(/\s+/);
                    const address = parts[3];
                    return {
                        protocol: parts[0],
                        address: address,
                        port: address.split(':').pop(),
                        binding: address.startsWith('0.0.0.0:') ? 'all-interfaces' : 'localhost-only'
                    };
                });

            const externalPortsOpen = ports.filter(port => port.binding === 'all-interfaces');
            const restrictedPorts = ports.filter(port => port.binding === 'localhost-only');

            return {
                allPorts: ports,
                externalPortsOpen,
                restrictedPorts,
                securityReview: externalPortsOpen.length > 0,
                timestamp: new Date()
            };
        } catch (error) {
            return {
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async checkDNSResolution() {
        const execAsync = promisify(exec);
        
        try {
            // Test external DNS resolution
            const testDomains = ['google.com', 'github.com', 'npmjs.org'];
            
            const resolutionResults = await Promise.allSettled(
                testDomains.map(async (domain) => {
                    try {
                        const result = await execAsync(`nslookup ${domain}`, { timeout: 5000 });
                        return { domain, resolved: true, output: result.stdout };
                    } catch (error) {
                        return { domain, resolved: false, error: error.message };
                    }
                })
            );

            const resolvedDomains = resolutionResults
                .filter(result => result.status === 'fulfilled' && result.value.resolved)
                .map(result => result.value.domain);

            return {
                canResolveExternal: resolvedDomains.length > 0,
                resolvedDomains,
                testedDomains: testDomains,
                timestamp: new Date()
            };
        } catch (error) {
            return {
                canResolveExternal: false,
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async checkSystemUpdates() {
        const execAsync = promisify(exec);
        
        try {
            // Check for package manager activity
            const packageManagers = [
                { cmd: 'apt list --upgradable 2>/dev/null | wc -l', type: 'apt' },
                { cmd: 'yum check-update 2>/dev/null | wc -l', type: 'yum' },
                { cmd: 'dnf check-update 2>/dev/null | wc -l', type: 'dnf' }
            ];

            const results = await Promise.allSettled(
                packageManagers.map(async (pm) => {
                    try {
                        const result = await execAsync(pm.cmd, { timeout: 10000 });
                        return {
                            type: pm.type,
                            availableUpdates: parseInt(result.stdout.trim()),
                            available: true
                        };
                    } catch (error) {
                        return {
                            type: pm.type,
                            available: false,
                            error: error.message
                        };
                    }
                })
            );

            const workingPackageManager = results
                .filter(result => result.status === 'fulfilled' && result.value.available)
                .map(result => result.value)[0];

            return {
                packageManager: workingPackageManager,
                hasUpdateCapability: !!workingPackageManager,
                availableUpdates: workingPackageManager?.availableUpdates || 0,
                timestamp: new Date()
            };
        } catch (error) {
            return {
                hasUpdateCapability: false,
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async setupInstallationEnvironment() {
        const installDir = path.join(process.cwd(), 'installation');
        
        try {
            await fs.mkdir(installDir, { recursive: true });
            await fs.mkdir(path.join(installDir, 'packages'), { recursive: true });
            await fs.mkdir(path.join(installDir, 'configs'), { recursive: true });
            await fs.mkdir(path.join(installDir, 'scripts'), { recursive: true });
            await fs.mkdir(path.join(installDir, 'certificates'), { recursive: true });
            await fs.mkdir(path.join(installDir, 'logs'), { recursive: true });

            // Create installation manifest
            const manifest = {
                version: '1.0.0',
                created: new Date().toISOString(),
                installationId: crypto.randomBytes(16).toString('hex'),
                targetSystem: {
                    platform: process.platform,
                    arch: process.arch,
                    nodeVersion: process.version
                },
                securityRequirements: this.securityRequirements,
                stages: this.installationStages
            };

            await fs.writeFile(
                path.join(installDir, 'manifest.json'),
                JSON.stringify(manifest, null, 2)
            );

            this.installationManifest = manifest;
            this.emit('environmentSetup', { installDir, manifest });

        } catch (error) {
            throw new Error(`Failed to setup installation environment: ${error.message}`);
        }
    }

    async createOfflinePackage(sourceDirectory, outputPath) {
        this.emit('packageCreation', { status: 'starting', sourceDirectory, outputPath });

        try {
            const packageInfo = {
                id: crypto.randomBytes(16).toString('hex'),
                created: new Date().toISOString(),
                version: '1.0.0',
                platform: process.platform,
                architecture: process.arch,
                nodeVersion: process.version,
                contents: {}
            };

            // Create archive
            const output = await fs.createWriteStream(outputPath);
            const archive = archiver('tar', {
                gzip: true,
                gzipOptions: { level: 9 }
            });

            output.on('close', () => {
                this.emit('packageCreation', { 
                    status: 'completed', 
                    size: archive.pointer(),
                    packageInfo 
                });
            });

            archive.on('error', (err) => {
                throw err;
            });

            archive.pipe(output);

            // Add source files
            archive.directory(sourceDirectory, 'app');

            // Add Node.js runtime (if needed for true air-gap)
            if (process.env.INCLUDE_RUNTIME === 'true') {
                archive.directory(process.execPath, 'runtime');
            }

            // Add npm dependencies
            if (await fs.access(path.join(sourceDirectory, 'node_modules')).then(() => true).catch(() => false)) {
                archive.directory(path.join(sourceDirectory, 'node_modules'), 'node_modules');
            }

            // Add installation scripts
            const installScript = this.generateInstallScript();
            archive.append(installScript, { name: 'install.sh' });

            const configScript = this.generateConfigScript();
            archive.append(configScript, { name: 'configure.sh' });

            // Add package metadata
            archive.append(JSON.stringify(packageInfo, null, 2), { name: 'package.json' });

            // Add security checksums
            const checksums = await this.generateChecksums(sourceDirectory);
            archive.append(JSON.stringify(checksums, null, 2), { name: 'checksums.json' });

            await archive.finalize();

            return {
                packagePath: outputPath,
                packageInfo,
                checksums
            };

        } catch (error) {
            this.emit('packageCreation', { status: 'failed', error: error.message });
            throw error;
        }
    }

    async installFromPackage(packagePath, installationConfig) {
        this.installationState.status = 'installing';
        this.installationState.progress = 0;

        try {
            // Verify package integrity
            await this.verifyPackageIntegrity(packagePath);
            this.updateProgress(10, 'Package verified');

            // Extract package
            const extractPath = await this.extractPackage(packagePath);
            this.updateProgress(20, 'Package extracted');

            // Run installation stages
            for (let i = 0; i < this.installationStages.length; i++) {
                const stage = this.installationStages[i];
                this.installationState.stage = stage;
                
                await this.executeInstallationStage(stage, extractPath, installationConfig);
                
                const progress = 20 + ((i + 1) / this.installationStages.length) * 70;
                this.updateProgress(progress, `Completed: ${stage}`);
            }

            // Final verification
            await this.verifyInstallation();
            this.updateProgress(100, 'Installation completed');

            this.installationState.status = 'completed';
            this.emit('installationCompleted', this.installationState);

            return {
                success: true,
                installationId: this.installationManifest?.installationId,
                completedAt: new Date()
            };

        } catch (error) {
            this.installationState.status = 'failed';
            this.installationState.errors.push({
                stage: this.installationState.stage,
                error: error.message,
                timestamp: new Date()
            });
            
            this.emit('installationFailed', {
                stage: this.installationState.stage,
                error: error.message
            });

            throw error;
        }
    }

    async executeInstallationStage(stage, extractPath, config) {
        this.emit('stageStarted', { stage });

        switch (stage) {
            case 'pre_flight_checks':
                await this.preFlightChecks();
                break;

            case 'environment_validation':
                await this.validateEnvironment();
                break;

            case 'dependency_verification':
                await this.verifyDependencies(extractPath);
                break;

            case 'security_initialization':
                await this.initializeSecurity(config);
                break;

            case 'database_setup':
                await this.setupDatabase(config);
                break;

            case 'configuration_deployment':
                await this.deployConfiguration(config);
                break;

            case 'service_installation':
                await this.installServices(extractPath, config);
                break;

            case 'security_hardening':
                await this.hardenSecurity();
                break;

            case 'verification_tests':
                await this.runVerificationTests();
                break;

            case 'post_installation_setup':
                await this.postInstallationSetup(config);
                break;

            default:
                throw new Error(`Unknown installation stage: ${stage}`);
        }

        this.emit('stageCompleted', { stage });
    }

    async preFlightChecks() {
        const checks = {
            diskSpace: await this.checkDiskSpace(),
            systemResources: await this.checkSystemResources(),
            permissions: await this.checkPermissions(),
            existingInstallation: await this.checkExistingInstallation()
        };

        // Validate requirements
        if (checks.diskSpace.available < 5000000000) { // 5GB minimum
            throw new Error('Insufficient disk space (minimum 5GB required)');
        }

        if (checks.systemResources.memoryMB < 2048) { // 2GB minimum
            throw new Error('Insufficient memory (minimum 2GB required)');
        }

        if (!checks.permissions.canWriteInstallDir) {
            throw new Error('Insufficient permissions for installation directory');
        }

        if (checks.existingInstallation.found) {
            throw new Error('Existing installation found. Please uninstall first.');
        }
    }

    async validateEnvironment() {
        const execAsync = promisify(exec);

        // Check Node.js version
        const nodeVersion = process.version;
        const requiredVersion = 'v18.0.0';
        
        if (this.compareVersions(nodeVersion, requiredVersion) < 0) {
            throw new Error(`Node.js version ${requiredVersion} or higher required (current: ${nodeVersion})`);
        }

        // Check system architecture
        if (!['x64', 'arm64'].includes(process.arch)) {
            throw new Error(`Unsupported architecture: ${process.arch}`);
        }

        // Check operating system
        if (!['linux', 'darwin'].includes(process.platform)) {
            throw new Error(`Unsupported platform: ${process.platform}`);
        }

        // Check critical system tools
        const requiredTools = ['tar', 'gzip', 'openssl', 'systemctl'];
        
        for (const tool of requiredTools) {
            try {
                await execAsync(`which ${tool}`);
            } catch (error) {
                throw new Error(`Required system tool not found: ${tool}`);
            }
        }
    }

    generateInstallScript() {
        return `#!/bin/bash
set -euo pipefail

echo "Starting ActiveLog Enterprise Installation..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Set secure permissions
umask 077

# Create installation user
if ! id "activelog" &>/dev/null; then
    useradd -r -s /bin/false -d /opt/activelog activelog
fi

# Create directories
mkdir -p /opt/activelog/{app,data,logs,config,certificates}
chown -R activelog:activelog /opt/activelog
chmod -R 750 /opt/activelog

# Extract application
tar -xzf app.tar.gz -C /opt/activelog/app
chown -R activelog:activelog /opt/activelog/app

# Install dependencies
cd /opt/activelog/app
npm ci --only=production --no-audit --no-fund

# Setup systemd service
cp installation/activelog.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable activelog

# Configure firewall
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 8309/tcp

echo "Installation completed successfully"
echo "Use 'systemctl start activelog' to start the service"
`;
    }

    generateConfigScript() {
        return `#!/bin/bash
set -euo pipefail

echo "Configuring ActiveLog Enterprise..."

# Generate encryption keys
openssl rand -hex 32 > /opt/activelog/config/session-secret
openssl rand -hex 64 > /opt/activelog/config/encryption-key

# Set restrictive permissions
chmod 600 /opt/activelog/config/*
chown activelog:activelog /opt/activelog/config/*

# Generate SSL certificates
openssl req -x509 -newkey rsa:4096 -keyout /opt/activelog/certificates/server.key \
    -out /opt/activelog/certificates/server.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

chmod 600 /opt/activelog/certificates/*
chown activelog:activelog /opt/activelog/certificates/*

echo "Configuration completed successfully"
`;
    }

    updateProgress(progress, message) {
        this.installationState.progress = progress;
        this.emit('progress', { progress, message, stage: this.installationState.stage });
    }

    compareVersions(a, b) {
        const aParts = a.replace('v', '').split('.').map(Number);
        const bParts = b.replace('v', '').split('.').map(Number);
        
        for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
            const aPart = aParts[i] || 0;
            const bPart = bParts[i] || 0;
            
            if (aPart > bPart) return 1;
            if (aPart < bPart) return -1;
        }
        
        return 0;
    }

    async generateChecksums(directory) {
        const checksums = {};
        
        const files = await this.getFilesList(directory);
        
        for (const file of files) {
            const filePath = path.join(directory, file);
            const content = await fs.readFile(filePath);
            checksums[file] = crypto.createHash('sha256').update(content).digest('hex');
        }
        
        return checksums;
    }

    async getFilesList(directory, relativePath = '') {
        const files = [];
        const entries = await fs.readdir(directory, { withFileTypes: true });
        
        for (const entry of entries) {
            const fullPath = path.join(directory, entry.name);
            const entryPath = path.join(relativePath, entry.name);
            
            if (entry.isDirectory() && entry.name !== 'node_modules' && entry.name !== '.git') {
                const subFiles = await this.getFilesList(fullPath, entryPath);
                files.push(...subFiles);
            } else if (entry.isFile()) {
                files.push(entryPath);
            }
        }
        
        return files;
    }

    getRoutes() {
        const router = require('express').Router();

        // Air-gap status endpoint
        router.get('/status', async (req, res) => {
            try {
                const status = await this.verifyAirGapStatus();
                res.json(status);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // Installation status endpoint
        router.get('/installation/status', (req, res) => {
            res.json(this.installationState);
        });

        // Create offline package
        router.post('/package/create', async (req, res) => {
            try {
                const { sourceDirectory, outputPath } = req.body;
                const result = await this.createOfflinePackage(sourceDirectory, outputPath);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        return router;
    }

    // Placeholder implementations for remaining methods
    async checkDiskSpace() {
        return { available: 10000000000, used: 5000000000 }; // 10GB available
    }

    async checkSystemResources() {
        return { memoryMB: 4096, cpuCores: 4 };
    }

    async checkPermissions() {
        return { canWriteInstallDir: true };
    }

    async checkExistingInstallation() {
        return { found: false };
    }

    async verifyPackageIntegrity() {
        // Implementation for package integrity verification
        return true;
    }

    async extractPackage(packagePath) {
        // Implementation for package extraction
        return '/tmp/extracted';
    }

    async verifyDependencies() {
        // Implementation for dependency verification
        return true;
    }

    async initializeSecurity() {
        // Implementation for security initialization
        return true;
    }

    async setupDatabase() {
        // Implementation for database setup
        return true;
    }

    async deployConfiguration() {
        // Implementation for configuration deployment
        return true;
    }

    async installServices() {
        // Implementation for service installation
        return true;
    }

    async hardenSecurity() {
        // Implementation for security hardening
        return true;
    }

    async runVerificationTests() {
        // Implementation for verification tests
        return true;
    }

    async postInstallationSetup() {
        // Implementation for post-installation setup
        return true;
    }

    async verifyInstallation() {
        // Implementation for installation verification
        return true;
    }
}

module.exports = AirGapInstaller;