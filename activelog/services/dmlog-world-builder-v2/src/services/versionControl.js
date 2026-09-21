const logger = require('../utils/logger');
const World = require('../models/World');
const { generateUniqueId } = require('../utils/helpers');
const { createHash } = require('crypto');

class VersionControlService {
  constructor() {
    this.pendingCommits = new Map(); // worldId -> commit data
    this.branchOperations = new Map(); // worldId -> operations
  }

  // Handle version control operations via websocket
  handleVersionControl(socket, io) {
    
    // Create a new version/commit
    socket.on('create-version', async (data) => {
      try {
        const { worldId, message, changes, author, branch = 'main' } = data;
        const userId = socket.userId;

        if (!userId) {
          socket.emit('version-error', { error: 'Authentication required' });
          return;
        }

        const world = await World.findOne({ worldId });
        if (!world) {
          socket.emit('version-error', { error: 'World not found' });
          return;
        }

        // Create new version
        const versionId = await this.createVersion(world, {
          author: author || userId,
          message,
          changes,
          branch
        });

        // Notify all collaborators
        socket.to(`world:${worldId}`).emit('version-created', {
          versionId,
          author,
          message,
          timestamp: new Date(),
          branch
        });

        socket.emit('version-created', { versionId, success: true });
        
        logger.info(`Version ${versionId} created for world ${worldId} by ${userId}`);

      } catch (error) {
        logger.error('Create version error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Create a new branch
    socket.on('create-branch', async (data) => {
      try {
        const { worldId, branchName, description, baseBranch = 'main' } = data;
        const userId = socket.userId;

        const world = await World.findOne({ worldId });
        if (!world) {
          socket.emit('version-error', { error: 'World not found' });
          return;
        }

        await this.createBranch(world, {
          name: branchName,
          description,
          creator: userId,
          baseBranch
        });

        socket.to(`world:${worldId}`).emit('branch-created', {
          branchName,
          creator: userId,
          description,
          timestamp: new Date()
        });

        socket.emit('branch-created', { branchName, success: true });

      } catch (error) {
        logger.error('Create branch error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Switch to different branch
    socket.on('switch-branch', async (data) => {
      try {
        const { worldId, branchName } = data;
        const userId = socket.userId;

        const result = await this.switchBranch(worldId, branchName, userId);

        socket.emit('branch-switched', {
          branchName,
          versionId: result.versionId,
          worldState: result.worldState
        });

        socket.to(`world:${worldId}`).emit('collaborator-branch-switched', {
          userId,
          branchName,
          timestamp: new Date()
        });

      } catch (error) {
        logger.error('Switch branch error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Merge branches
    socket.on('merge-branch', async (data) => {
      try {
        const { worldId, sourceBranch, targetBranch, message } = data;
        const userId = socket.userId;

        const result = await this.mergeBranches(worldId, {
          sourceBranch,
          targetBranch,
          message,
          author: userId
        });

        socket.to(`world:${worldId}`).emit('branches-merged', {
          sourceBranch,
          targetBranch,
          mergeCommit: result.mergeCommit,
          author: userId,
          timestamp: new Date()
        });

        socket.emit('branches-merged', { success: true, ...result });

      } catch (error) {
        logger.error('Merge branch error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Revert to previous version
    socket.on('revert-version', async (data) => {
      try {
        const { worldId, versionId, message } = data;
        const userId = socket.userId;

        const result = await this.revertToVersion(worldId, versionId, {
          author: userId,
          message: message || `Reverted to version ${versionId}`
        });

        socket.to(`world:${worldId}`).emit('version-reverted', {
          revertedTo: versionId,
          newVersionId: result.newVersionId,
          author: userId,
          timestamp: new Date()
        });

        socket.emit('version-reverted', { success: true, ...result });

      } catch (error) {
        logger.error('Revert version error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Get version history
    socket.on('get-version-history', async (data) => {
      try {
        const { worldId, branch, limit = 20, offset = 0 } = data;

        const history = await this.getVersionHistory(worldId, { branch, limit, offset });
        
        socket.emit('version-history', history);

      } catch (error) {
        logger.error('Get version history error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Compare versions
    socket.on('compare-versions', async (data) => {
      try {
        const { worldId, versionA, versionB } = data;

        const comparison = await this.compareVersions(worldId, versionA, versionB);
        
        socket.emit('version-comparison', comparison);

      } catch (error) {
        logger.error('Compare versions error:', error);
        socket.emit('version-error', { error: error.message });
      }
    });

    // Auto-commit (for auto-save functionality)
    socket.on('auto-commit', async (data) => {
      try {
        const { worldId, changes } = data;
        const userId = socket.userId;

        // Create auto-commit with timestamp
        await this.createAutoCommit(worldId, {
          author: userId,
          changes,
          timestamp: new Date()
        });

      } catch (error) {
        logger.error('Auto-commit error:', error);
        // Don't emit error for auto-commits to avoid spam
      }
    });
  }

  // Create a new version
  async createVersion(world, options) {
    const { author, message, changes, branch = 'main' } = options;
    
    const versionId = generateUniqueId();
    const currentBranch = world.branches.find(b => b.name === branch);
    
    if (!currentBranch && branch !== 'main') {
      throw new Error(`Branch '${branch}' does not exist`);
    }

    const version = {
      versionId,
      parentVersion: currentBranch ? currentBranch.currentVersion : world.currentVersion,
      branch,
      author,
      message,
      timestamp: new Date(),
      changes: changes || [],
      snapshot: this.createSnapshot(world) // For major versions
    };

    world.versions.push(version);
    world.currentVersion = versionId;

    // Update branch
    if (currentBranch) {
      currentBranch.currentVersion = versionId;
    }

    await world.save();
    
    return versionId;
  }

  // Create a new branch
  async createBranch(world, options) {
    const { name, description, creator, baseBranch = 'main' } = options;

    // Check if branch already exists
    if (world.branches.some(b => b.name === name)) {
      throw new Error(`Branch '${name}' already exists`);
    }

    const baseBranchObj = world.branches.find(b => b.name === baseBranch);
    const baseVersion = baseBranchObj ? baseBranchObj.currentVersion : world.currentVersion;

    world.branches.push({
      name,
      currentVersion: baseVersion,
      description,
      creator,
      created: new Date()
    });

    await world.save();
    
    return name;
  }

  // Switch to different branch
  async switchBranch(worldId, branchName, userId) {
    const world = await World.findOne({ worldId });
    if (!world) {
      throw new Error('World not found');
    }

    const branch = world.branches.find(b => b.name === branchName);
    if (!branch && branchName !== 'main') {
      throw new Error(`Branch '${branchName}' does not exist`);
    }

    const targetVersion = branch ? branch.currentVersion : world.currentVersion;
    
    // Load world state from target version
    const worldState = await this.loadVersionState(world, targetVersion);

    return {
      versionId: targetVersion,
      worldState
    };
  }

  // Merge branches
  async mergeBranches(worldId, options) {
    const { sourceBranch, targetBranch, message, author } = options;
    
    const world = await World.findOne({ worldId });
    if (!world) {
      throw new Error('World not found');
    }

    const sourceBranchObj = world.branches.find(b => b.name === sourceBranch);
    const targetBranchObj = world.branches.find(b => b.name === targetBranch);

    if (!sourceBranchObj) {
      throw new Error(`Source branch '${sourceBranch}' not found`);
    }
    if (!targetBranchObj && targetBranch !== 'main') {
      throw new Error(`Target branch '${targetBranch}' not found`);
    }

    // Create merge commit
    const mergeCommit = await this.createMergeCommit(world, {
      sourceBranch,
      targetBranch,
      sourceVersion: sourceBranchObj.currentVersion,
      targetVersion: targetBranchObj ? targetBranchObj.currentVersion : world.currentVersion,
      message,
      author
    });

    return { mergeCommit };
  }

  // Revert to previous version
  async revertToVersion(worldId, versionId, options) {
    const { author, message } = options;
    
    const world = await World.findOne({ worldId });
    if (!world) {
      throw new Error('World not found');
    }

    const targetVersion = world.versions.find(v => v.versionId === versionId);
    if (!targetVersion) {
      throw new Error(`Version '${versionId}' not found`);
    }

    // Load state from target version
    const versionState = await this.loadVersionState(world, versionId);
    
    // Apply state to current world
    this.applyVersionState(world, versionState);
    
    // Create new commit for the revert
    const newVersionId = await this.createVersion(world, {
      author,
      message,
      changes: [{
        type: 'revert',
        targetVersion: versionId,
        timestamp: new Date()
      }]
    });

    return { newVersionId, versionState };
  }

  // Get version history
  async getVersionHistory(worldId, options = {}) {
    const { branch, limit = 20, offset = 0 } = options;
    
    const world = await World.findOne({ worldId });
    if (!world) {
      throw new Error('World not found');
    }

    let versions = world.versions;
    
    // Filter by branch if specified
    if (branch) {
      versions = versions.filter(v => v.branch === branch);
    }

    // Sort by timestamp (newest first)
    versions.sort((a, b) => b.timestamp - a.timestamp);

    // Apply pagination
    const paginatedVersions = versions.slice(offset, offset + limit);

    return {
      versions: paginatedVersions,
      total: versions.length,
      hasMore: offset + limit < versions.length
    };
  }

  // Compare two versions
  async compareVersions(worldId, versionA, versionB) {
    const world = await World.findOne({ worldId });
    if (!world) {
      throw new Error('World not found');
    }

    const versionAObj = world.versions.find(v => v.versionId === versionA);
    const versionBObj = world.versions.find(v => v.versionId === versionB);

    if (!versionAObj || !versionBObj) {
      throw new Error('One or both versions not found');
    }

    const stateA = await this.loadVersionState(world, versionA);
    const stateB = await this.loadVersionState(world, versionB);

    const differences = this.computeDifferences(stateA, stateB);

    return {
      versionA: {
        id: versionA,
        timestamp: versionAObj.timestamp,
        author: versionAObj.author,
        message: versionAObj.message
      },
      versionB: {
        id: versionB,
        timestamp: versionBObj.timestamp,
        author: versionBObj.author,
        message: versionBObj.message
      },
      differences
    };
  }

  // Create auto-commit for continuous saves
  async createAutoCommit(worldId, options) {
    const { author, changes, timestamp } = options;
    
    const world = await World.findOne({ worldId });
    if (!world) return;

    // Only create auto-commit if there are actual changes
    if (!changes || changes.length === 0) return;

    // Create auto-commit with special naming
    await this.createVersion(world, {
      author,
      message: `Auto-save at ${timestamp.toISOString()}`,
      changes,
      branch: 'main' // Auto-commits always go to main
    });
  }

  // Create snapshot of current world state
  createSnapshot(world) {
    return {
      content: JSON.parse(JSON.stringify(world.content)),
      metadata: {
        name: world.name,
        description: world.description,
        theme: world.theme,
        lastModified: world.lastModified
      },
      hash: this.calculateHash(world.content)
    };
  }

  // Load world state from specific version
  async loadVersionState(world, versionId) {
    const version = world.versions.find(v => v.versionId === versionId);
    if (!version) {
      throw new Error(`Version '${versionId}' not found`);
    }

    // If version has full snapshot, use it
    if (version.snapshot) {
      return version.snapshot;
    }

    // Otherwise, reconstruct from changes (this is more complex)
    return await this.reconstructStateFromChanges(world, versionId);
  }

  // Apply version state to world
  applyVersionState(world, versionState) {
    world.content = JSON.parse(JSON.stringify(versionState.content));
    if (versionState.metadata) {
      world.name = versionState.metadata.name;
      world.description = versionState.metadata.description;
      world.theme = versionState.metadata.theme;
    }
  }

  // Create merge commit
  async createMergeCommit(world, options) {
    const { sourceBranch, targetBranch, sourceVersion, targetVersion, message, author } = options;
    
    // This is a simplified merge - in a full implementation,
    // you'd need to handle merge conflicts
    const mergeCommitId = generateUniqueId();
    
    const mergeCommit = {
      versionId: mergeCommitId,
      parentVersion: targetVersion,
      secondParent: sourceVersion, // For merge commits
      branch: targetBranch,
      author,
      message: message || `Merge ${sourceBranch} into ${targetBranch}`,
      timestamp: new Date(),
      changes: [{
        type: 'merge',
        sourceBranch,
        targetBranch,
        sourceVersion,
        targetVersion
      }],
      isMergeCommit: true
    };

    world.versions.push(mergeCommit);
    
    // Update target branch
    if (targetBranch === 'main') {
      world.currentVersion = mergeCommitId;
    } else {
      const branch = world.branches.find(b => b.name === targetBranch);
      if (branch) {
        branch.currentVersion = mergeCommitId;
      }
    }

    await world.save();
    
    return mergeCommitId;
  }

  // Reconstruct world state from version changes (simplified)
  async reconstructStateFromChanges(world, targetVersionId) {
    // This is a complex operation that would traverse the version tree
    // and apply changes in order. For now, we'll return current state
    return this.createSnapshot(world);
  }

  // Compute differences between two states
  computeDifferences(stateA, stateB) {
    const differences = [];
    
    // This would be a deep comparison function
    // For now, returning basic structure
    return differences;
  }

  // Calculate hash for content integrity
  calculateHash(content) {
    const contentString = JSON.stringify(content);
    return createHash('sha256').update(contentString).digest('hex');
  }

  // Get all branches for a world
  async getBranches(worldId) {
    const world = await World.findOne({ worldId });
    if (!world) {
      throw new Error('World not found');
    }

    return [
      { name: 'main', currentVersion: world.currentVersion, description: 'Main branch' },
      ...world.branches
    ];
  }

  // Get current branch for user session
  getCurrentBranch(worldId, userId) {
    // In a full implementation, you'd track which branch each user is on
    return 'main';
  }
}

// Export singleton
const versionControlService = new VersionControlService();

module.exports = {
  VersionControlService,
  handleVersionControl: (socket, io) => versionControlService.handleVersionControl(socket, io),
  createVersion: (world, options) => versionControlService.createVersion(world, options),
  createBranch: (world, options) => versionControlService.createBranch(world, options),
  getBranches: (worldId) => versionControlService.getBranches(worldId)
};