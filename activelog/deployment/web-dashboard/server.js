const express = require('express');
const expressWs = require('express-ws');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs').promises;
const path = require('path');
const { spawn, exec } = require('child_process');
const chokidar = require('chokidar');
const cron = require('node-cron');
const axios = require('axios');

const app = express();
const wsInstance = expressWs(app);

const PORT = process.env.PORT || 3001;
const DEPLOYMENT_DIR = path.join(__dirname, '..');
const LOGS_DIR = path.join(DEPLOYMENT_DIR, 'logs');
const PROGRESS_DIR = '/tmp';

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Store WebSocket connections
const wsConnections = new Set();

// Ensure directories exist
async function ensureDirectories() {
    try {
        await fs.mkdir(LOGS_DIR, { recursive: true });
        console.log('📁 Directories initialized');
    } catch (error) {
        console.error('Error creating directories:', error);
    }
}

// Broadcast to all WebSocket clients
function broadcast(data) {
    wsConnections.forEach(ws => {
        if (ws.readyState === ws.OPEN) {
            try {
                ws.send(JSON.stringify(data));
            } catch (error) {
                console.error('WebSocket send error:', error);
                wsConnections.delete(ws);
            }
        }
    });
}

// WebSocket connection handler
app.ws('/ws', (ws, req) => {
    wsConnections.add(ws);
    console.log(`📡 WebSocket connected (${wsConnections.size} active)`);
    
    ws.on('close', () => {
        wsConnections.delete(ws);
        console.log(`📡 WebSocket disconnected (${wsConnections.size} active)`);
    });
    
    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            await handleWebSocketMessage(ws, data);
        } catch (error) {
            console.error('WebSocket message error:', error);
        }
    });
    
    // Send initial data
    ws.send(JSON.stringify({
        type: 'connected',
        timestamp: new Date().toISOString(),
        message: 'Connected to ActiveLog Deployment Dashboard'
    }));
});

// Handle WebSocket messages
async function handleWebSocketMessage(ws, data) {
    switch (data.type) {
        case 'get_deployments':
            const deployments = await getActiveDeployments();
            ws.send(JSON.stringify({
                type: 'deployments_list',
                data: deployments
            }));
            break;
            
        case 'get_deployment_status':
            const status = await getDeploymentStatus(data.deploymentId);
            ws.send(JSON.stringify({
                type: 'deployment_status',
                deploymentId: data.deploymentId,
                data: status
            }));
            break;
            
        case 'subscribe_deployment':
            // Subscribe to deployment updates
            subscribeToDeployment(data.deploymentId);
            break;
            
        case 'start_deployment':
            await startDeployment(data.config);
            break;
            
        case 'cancel_deployment':
            await cancelDeployment(data.deploymentId);
            break;
    }
}

// API Routes

// Get system status
app.get('/api/status', async (req, res) => {
    try {
        const status = await getSystemStatus();
        res.json(status);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get all deployments
app.get('/api/deployments', async (req, res) => {
    try {
        const deployments = await getActiveDeployments();
        res.json(deployments);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get specific deployment
app.get('/api/deployments/:id', async (req, res) => {
    try {
        const deployment = await getDeploymentStatus(req.params.id);
        if (!deployment) {
            return res.status(404).json({ error: 'Deployment not found' });
        }
        res.json(deployment);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Start new deployment
app.post('/api/deployments', async (req, res) => {
    try {
        const deploymentId = await startDeployment(req.body);
        res.json({ deploymentId, message: 'Deployment started' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Cancel deployment
app.delete('/api/deployments/:id', async (req, res) => {
    try {
        await cancelDeployment(req.params.id);
        res.json({ message: 'Deployment cancelled' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get deployment logs
app.get('/api/deployments/:id/logs', async (req, res) => {
    try {
        const logs = await getDeploymentLogs(req.params.id);
        res.json(logs);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get AWS resources
app.get('/api/aws/resources', async (req, res) => {
    try {
        const resources = await getAWSResources(req.query.environment);
        res.json(resources);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get cost estimates
app.post('/api/cost-estimate', async (req, res) => {
    try {
        const estimate = await calculateCostEstimate(req.body);
        res.json(estimate);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get CloudWatch metrics
app.get('/api/metrics', async (req, res) => {
    try {
        const metrics = await getCloudWatchMetrics(req.query);
        res.json(metrics);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Start interactive wizard
app.post('/api/wizard', async (req, res) => {
    try {
        const sessionId = await startWizardSession();
        res.json({ sessionId });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Implementation functions

async function getSystemStatus() {
    try {
        // Check prerequisites
        const prerequisites = await checkPrerequisites();
        
        // Check AWS connectivity
        const awsStatus = await checkAWSStatus();
        
        // Get system resources
        const systemResources = await getSystemResources();
        
        return {
            timestamp: new Date().toISOString(),
            prerequisites,
            aws: awsStatus,
            system: systemResources,
            status: prerequisites.allMet && awsStatus.connected ? 'healthy' : 'degraded'
        };
    } catch (error) {
        return {
            timestamp: new Date().toISOString(),
            status: 'error',
            error: error.message
        };
    }
}

async function checkPrerequisites() {
    const tools = ['aws', 'terraform', 'docker', 'jq'];
    const results = {};
    
    for (const tool of tools) {
        try {
            await execAsync(`command -v ${tool}`);
            results[tool] = { installed: true };
        } catch (error) {
            results[tool] = { installed: false, error: error.message };
        }
    }
    
    const allMet = Object.values(results).every(r => r.installed);
    
    return { tools: results, allMet };
}

async function checkAWSStatus() {
    try {
        const output = await execAsync('aws sts get-caller-identity');
        const identity = JSON.parse(output);
        
        return {
            connected: true,
            account: identity.Account,
            userId: identity.UserId,
            arn: identity.Arn
        };
    } catch (error) {
        return {
            connected: false,
            error: error.message
        };
    }
}

async function getSystemResources() {
    try {
        const cpuInfo = await execAsync("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1");
        const memInfo = await execAsync("free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2 }'");
        const diskInfo = await execAsync("df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1");
        
        return {
            cpu: parseFloat(cpuInfo.trim()),
            memory: parseFloat(memInfo.trim()),
            disk: parseFloat(diskInfo.trim())
        };
    } catch (error) {
        return {
            cpu: 0,
            memory: 0,
            disk: 0,
            error: error.message
        };
    }
}

async function getActiveDeployments() {
    try {
        const files = await fs.readdir(PROGRESS_DIR);
        const progressFiles = files.filter(f => f.startsWith('activelog_progress_') && f.endsWith('.json'));
        
        const deployments = [];
        
        for (const file of progressFiles) {
            try {
                const data = await fs.readFile(path.join(PROGRESS_DIR, file), 'utf8');
                const deployment = JSON.parse(data);
                deployments.push(deployment);
            } catch (error) {
                console.error(`Error reading deployment file ${file}:`, error);
            }
        }
        
        // Sort by started_at descending
        deployments.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
        
        return deployments;
    } catch (error) {
        console.error('Error getting deployments:', error);
        return [];
    }
}

async function getDeploymentStatus(deploymentId) {
    try {
        const progressFile = path.join(PROGRESS_DIR, `activelog_progress_${deploymentId}.json`);
        const data = await fs.readFile(progressFile, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        return null;
    }
}

async function startDeployment(config) {
    const deploymentId = `deploy-${Date.now()}`;
    
    // Create deployment configuration
    const deploymentConfig = {
        deployment_id: deploymentId,
        started_at: new Date().toISOString(),
        config: config,
        status: 'initializing'
    };
    
    // Save configuration
    const configFile = path.join(LOGS_DIR, `deployment_${deploymentId}.json`);
    await fs.writeFile(configFile, JSON.stringify(deploymentConfig, null, 2));
    
    // Start deployment process
    const scriptPath = path.join(DEPLOYMENT_DIR, 'scripts', 'deploy_activelog.sh');
    const args = [
        `--environment=${config.environment}`,
        `--region=${config.region}`,
        '--skip-confirmation'
    ];
    
    if (config.minResources) {
        args.push('--min-resources');
    }
    
    const deployment = spawn(scriptPath, args, {
        cwd: DEPLOYMENT_DIR,
        env: { ...process.env, DEPLOYMENT_ID: deploymentId }
    });
    
    // Monitor deployment output
    deployment.stdout.on('data', (data) => {
        const output = data.toString();
        broadcast({
            type: 'deployment_output',
            deploymentId: deploymentId,
            output: output,
            stream: 'stdout'
        });
    });
    
    deployment.stderr.on('data', (data) => {
        const output = data.toString();
        broadcast({
            type: 'deployment_output',
            deploymentId: deploymentId,
            output: output,
            stream: 'stderr'
        });
    });
    
    deployment.on('close', (code) => {
        broadcast({
            type: 'deployment_finished',
            deploymentId: deploymentId,
            exitCode: code,
            status: code === 0 ? 'completed' : 'failed'
        });
    });
    
    return deploymentId;
}

async function cancelDeployment(deploymentId) {
    // This is a simplified implementation
    // In a real scenario, you'd need to track process IDs and gracefully terminate
    broadcast({
        type: 'deployment_cancelled',
        deploymentId: deploymentId
    });
}

async function getDeploymentLogs(deploymentId) {
    try {
        const logFile = path.join('/tmp', `activelog_deployment_${deploymentId}.log`);
        const data = await fs.readFile(logFile, 'utf8');
        return {
            deploymentId: deploymentId,
            logs: data.split('\n').filter(line => line.trim())
        };
    } catch (error) {
        return {
            deploymentId: deploymentId,
            logs: [],
            error: error.message
        };
    }
}

async function getAWSResources(environment = 'beta') {
    try {
        // Get EC2 instances
        const ec2Cmd = `aws ec2 describe-instances --filters "Name=tag:Environment,Values=${environment}" --query "Reservations[].Instances[].[InstanceId,State.Name,InstanceType,PublicIpAddress,PrivateIpAddress]" --output json`;
        const ec2Output = await execAsync(ec2Cmd);
        const ec2Instances = JSON.parse(ec2Output);
        
        // Get Auto Scaling Groups
        const asgCmd = `aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[?contains(Tags[?Key=='Environment'].Value, '${environment}')].{Name:AutoScalingGroupName,Desired:DesiredCapacity,Min:MinSize,Max:MaxSize,Instances:length(Instances)}" --output json`;
        const asgOutput = await execAsync(asgCmd);
        const autoScalingGroups = JSON.parse(asgOutput);
        
        // Get Load Balancers
        const albCmd = `aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName, '${environment}')].{Name:LoadBalancerName,State:State.Code,Type:Type,DNSName:DNSName}" --output json`;
        const albOutput = await execAsync(albCmd);
        const loadBalancers = JSON.parse(albOutput);
        
        return {
            environment,
            timestamp: new Date().toISOString(),
            ec2Instances: ec2Instances.map(([id, state, type, publicIp, privateIp]) => ({
                instanceId: id,
                state,
                instanceType: type,
                publicIp,
                privateIp
            })),
            autoScalingGroups,
            loadBalancers
        };
    } catch (error) {
        return {
            environment,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
}

async function calculateCostEstimate(config) {
    // Simplified cost calculation based on configuration
    const instanceCosts = {
        't3.micro': 0.0104,
        't3.small': 0.0208,
        't3.medium': 0.0416,
        't3.large': 0.0832,
        'c5.large': 0.085,
        'c5.xlarge': 0.17,
        'g4dn.xlarge': 0.526
    };
    
    let monthlyCost = 0;
    
    // Calculate based on domains and instance types
    config.domains.forEach(domain => {
        const instanceType = config.instanceClass === 'minimal' ? 't3.micro' : 
                           config.instanceClass === 'balanced' ? 't3.small' :
                           config.instanceClass === 'performance' ? 't3.medium' : 't3.large';
        
        const instanceCost = instanceCosts[instanceType] || 0.05;
        const instances = config.autoScaling ? config.maxInstances : 1;
        
        monthlyCost += instanceCost * 24 * 30 * instances;
        
        // Add GPU cost for DMLog if enabled
        if (domain === 'DMLog' && config.enableGpu) {
            monthlyCost += instanceCosts['g4dn.xlarge'] * 24 * 30;
        }
    });
    
    // Add storage and bandwidth estimates
    monthlyCost += config.domains.length * 10; // Storage
    monthlyCost += config.domains.length * 5;  // Bandwidth
    
    // Cost optimization discount
    if (config.costOptimized) {
        monthlyCost *= 0.7; // 30% reduction
    }
    
    return {
        monthly: Math.round(monthlyCost),
        yearly: Math.round(monthlyCost * 12 * 0.9), // 10% annual discount
        breakdown: {
            compute: Math.round(monthlyCost * 0.7),
            storage: Math.round(monthlyCost * 0.2),
            network: Math.round(monthlyCost * 0.1)
        }
    };
}

async function getCloudWatchMetrics(params) {
    try {
        const environment = params.environment || 'beta';
        const metricName = params.metric || 'CPUUtilization';
        const namespace = params.namespace || 'AWS/EC2';
        
        const endTime = new Date().toISOString();
        const startTime = new Date(Date.now() - 3600000).toISOString(); // 1 hour ago
        
        const cmd = `aws cloudwatch get-metric-statistics --namespace "${namespace}" --metric-name "${metricName}" --start-time "${startTime}" --end-time "${endTime}" --period 300 --statistics Average --output json`;
        
        const output = await execAsync(cmd);
        const data = JSON.parse(output);
        
        return {
            metric: metricName,
            namespace,
            datapoints: data.Datapoints.sort((a, b) => new Date(a.Timestamp) - new Date(b.Timestamp))
        };
    } catch (error) {
        return {
            error: error.message
        };
    }
}

async function startWizardSession() {
    const sessionId = `wizard-${Date.now()}`;
    // Implementation for wizard session management
    return sessionId;
}

// Utility function for executing commands
function execAsync(command) {
    return new Promise((resolve, reject) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                reject(error);
            } else {
                resolve(stdout);
            }
        });
    });
}

// File watchers for real-time updates
function setupFileWatchers() {
    // Watch for progress file changes
    const progressWatcher = chokidar.watch(`${PROGRESS_DIR}/activelog_progress_*.json`);
    
    progressWatcher.on('change', async (filePath) => {
        const deploymentId = path.basename(filePath).replace('activelog_progress_', '').replace('.json', '');
        const status = await getDeploymentStatus(deploymentId);
        
        if (status) {
            broadcast({
                type: 'deployment_status_update',
                deploymentId: deploymentId,
                data: status
            });
        }
    });
    
    console.log('📁 File watchers initialized');
}

// Periodic tasks
function setupPeriodicTasks() {
    // Update system status every minute
    cron.schedule('*/1 * * * *', async () => {
        const status = await getSystemStatus();
        broadcast({
            type: 'system_status_update',
            data: status
        });
    });
    
    console.log('⏰ Periodic tasks initialized');
}

// Serve React app (in production)
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
async function startServer() {
    await ensureDirectories();
    setupFileWatchers();
    setupPeriodicTasks();
    
    app.listen(PORT, () => {
        console.log(`🚀 ActiveLog Deployment Dashboard server running on port ${PORT}`);
        console.log(`📊 Dashboard: http://localhost:${PORT}`);
        console.log(`🔌 WebSocket: ws://localhost:${PORT}/ws`);
    });
}

startServer().catch(console.error);