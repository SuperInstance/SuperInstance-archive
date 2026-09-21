const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');
const archiver = require('archiver');
const tar = require('tar');

class VersionControl extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        this.repositories = new Map();
        this.branches = new Map();
        this.commits = new Map();
        
        this.branchTypes = {
            MAIN: 'main',
            FEATURE: 'feature',
            HOTFIX: 'hotfix',
            RELEASE: 'release',
            EXPERIMENTAL: 'experimental'
        };
        
        this.fileStates = {
            ADDED: 'added',
            MODIFIED: 'modified',
            DELETED: 'deleted',
            RENAMED: 'renamed',
            UNTRACKED: 'untracked'
        };
        
        this.mergeStrategies = {
            AUTO: 'auto',
            MANUAL: 'manual',
            FAST_FORWARD: 'fast_forward',
            THREE_WAY: 'three_way',
            SQUASH: 'squash'
        };
        
        this.conflictResolutions = {
            ACCEPT_CURRENT: 'accept_current',
            ACCEPT_INCOMING: 'accept_incoming',
            MANUAL_MERGE: 'manual_merge',
            AUTO_MERGE: 'auto_merge'
        };
        
        this.setupEventListeners();
        this.logger.info('Version Control service initialized');
    }
    
    setupEventListeners() {
        this.on('repository_created', (data) => {
            this.io.emit('repository_created', data);
        });
        
        this.on('commit_created', (data) => {
            this.io.to(`repo_${data.repositoryId}`).emit('commit_created', data);
        });
        
        this.on('branch_created', (data) => {
            this.io.to(`repo_${data.repositoryId}`).emit('branch_created', data);
        });
        
        this.on('merge_completed', (data) => {
            this.io.to(`repo_${data.repositoryId}`).emit('merge_completed', data);
        });
        
        this.on('conflict_detected', (data) => {
            this.io.to(`repo_${data.repositoryId}`).emit('conflict_detected', data);
        });
    }
    
    async createRepository(repoData) {
        try {
            const repositoryId = uuidv4();
            const {
                projectId,
                name,
                description,
                ownerId,
                settings,
                initialFiles
            } = repoData;
            
            const repository = {
                id: repositoryId,
                projectId: projectId || 'unknown',
                name: name || 'Untitled Repository',
                description: description || '',
                ownerId: ownerId || 'system',
                status: 'active',
                branches: new Map(),
                tags: [],
                settings: {
                    defaultBranch: 'main',
                    mergeStrategy: settings?.mergeStrategy || this.mergeStrategies.AUTO,
                    autoBackup: settings?.autoBackup !== false,
                    compressionEnabled: settings?.compressionEnabled !== false,
                    maxFileSize: settings?.maxFileSize || 100 * 1024 * 1024, // 100MB
                    retentionDays: settings?.retentionDays || 30,
                    ...settings
                },
                metadata: {
                    created: new Date(),
                    lastCommit: null,
                    totalCommits: 0,
                    totalBranches: 0,
                    storageUsed: 0
                }
            };
            
            // Create main branch
            const mainBranch = await this.createMainBranch(repositoryId, initialFiles);
            repository.branches.set('main', mainBranch);
            repository.metadata.totalBranches = 1;
            
            this.repositories.set(repositoryId, repository);
            await this.redis.setEx(`version_repo:${repositoryId}`, 7200, JSON.stringify({
                ...repository,
                branches: Array.from(repository.branches.entries())
            }));
            
            this.emit('repository_created', { repositoryId, repository });
            this.logger.info(`Version control repository created: ${repositoryId}`);
            
            return { success: true, repositoryId, repository };
        } catch (error) {
            this.logger.error('Create repository error:', error);
            throw error;
        }
    }
    
    async createMainBranch(repositoryId, initialFiles = []) {
        const branchId = uuidv4();
        const branch = {
            id: branchId,
            name: 'main',
            type: this.branchTypes.MAIN,
            repositoryId: repositoryId,
            parentBranch: null,
            headCommit: null,
            commits: [],
            protected: true,
            metadata: {
                created: new Date(),
                lastCommit: null,
                totalCommits: 0,
                mergeRequests: []
            }
        };
        
        // Create initial commit if files provided
        if (initialFiles.length > 0) {
            const initialCommit = await this.createInitialCommit(repositoryId, branchId, initialFiles);
            branch.headCommit = initialCommit.id;
            branch.commits.push(initialCommit.id);
            branch.metadata.lastCommit = new Date();
            branch.metadata.totalCommits = 1;
        }
        
        this.branches.set(branchId, branch);
        await this.redis.setEx(`version_branch:${branchId}`, 7200, JSON.stringify(branch));
        
        return branch;
    }
    
    async createInitialCommit(repositoryId, branchId, files) {
        const commitId = uuidv4();
        const commit = {
            id: commitId,
            repositoryId: repositoryId,
            branchId: branchId,
            message: 'Initial commit',
            author: 'system',
            timestamp: new Date(),
            parentCommits: [],
            changes: files.map(file => ({
                path: file.path,
                type: this.fileStates.ADDED,
                content: file.content,
                hash: this.hashContent(file.content),
                size: Buffer.byteLength(file.content, 'utf8')
            })),
            metadata: {
                filesAdded: files.length,
                filesModified: 0,
                filesDeleted: 0,
                totalChanges: files.length
            }
        };
        
        this.commits.set(commitId, commit);
        await this.redis.setEx(`version_commit:${commitId}`, 7200, JSON.stringify(commit));
        
        return commit;
    }
    
    async createCommit(projectId, commitData) {
        try {
            const {
                repositoryId,
                branchName,
                message,
                author,
                changes,
                metadata
            } = commitData;
            
            const repository = await this.getRepository(repositoryId);
            if (!repository) {
                throw new Error(`Repository ${repositoryId} not found`);
            }
            
            const branch = repository.branches.get(branchName || repository.settings.defaultBranch);
            if (!branch) {
                throw new Error(`Branch ${branchName} not found`);
            }
            
            const commitId = uuidv4();
            const commit = {
                id: commitId,
                repositoryId: repositoryId,
                branchId: branch.id,
                message: message || 'Commit',
                author: author || 'unknown',
                timestamp: new Date(),
                parentCommits: branch.headCommit ? [branch.headCommit] : [],
                changes: this.processChanges(changes || []),
                metadata: {
                    filesAdded: 0,
                    filesModified: 0,
                    filesDeleted: 0,
                    totalChanges: changes ? changes.length : 0,
                    ...metadata
                }
            };
            
            // Calculate change statistics
            commit.changes.forEach(change => {
                switch (change.type) {
                    case this.fileStates.ADDED:
                        commit.metadata.filesAdded++;
                        break;
                    case this.fileStates.MODIFIED:
                        commit.metadata.filesModified++;
                        break;
                    case this.fileStates.DELETED:
                        commit.metadata.filesDeleted++;
                        break;
                }
            });
            
            // Create commit snapshot
            await this.createCommitSnapshot(commit);
            
            // Update branch
            branch.headCommit = commitId;
            branch.commits.push(commitId);
            branch.metadata.lastCommit = new Date();
            branch.metadata.totalCommits++;
            
            // Update repository
            repository.metadata.lastCommit = new Date();
            repository.metadata.totalCommits++;
            
            // Store commit and update caches
            this.commits.set(commitId, commit);
            await this.redis.setEx(`version_commit:${commitId}`, 7200, JSON.stringify(commit));
            await this.updateBranch(branch);
            await this.updateRepository(repository);
            
            this.emit('commit_created', { repositoryId, branchId: branch.id, commitId, commit });
            this.logger.info(`Commit created: ${commitId} in branch ${branchName}`);
            
            return { success: true, commitId, commit };
        } catch (error) {
            this.logger.error('Create commit error:', error);
            throw error;
        }
    }
    
    async createBranch(projectId, branchData) {
        try {
            const {
                repositoryId,
                name,
                type,
                sourceBranch,
                description
            } = branchData;
            
            const repository = await this.getRepository(repositoryId);
            if (!repository) {
                throw new Error(`Repository ${repositoryId} not found`);
            }
            
            const sourceBranchObj = repository.branches.get(sourceBranch || repository.settings.defaultBranch);
            if (!sourceBranchObj) {
                throw new Error(`Source branch ${sourceBranch} not found`);
            }
            
            const branchId = uuidv4();
            const branch = {
                id: branchId,
                name: name,
                type: type || this.branchTypes.FEATURE,
                repositoryId: repositoryId,
                parentBranch: sourceBranchObj.id,
                headCommit: sourceBranchObj.headCommit,
                commits: [...sourceBranchObj.commits],
                description: description || '',
                protected: false,
                metadata: {
                    created: new Date(),
                    lastCommit: sourceBranchObj.metadata.lastCommit,
                    totalCommits: sourceBranchObj.metadata.totalCommits,
                    mergeRequests: []
                }
            };
            
            repository.branches.set(name, branch);
            repository.metadata.totalBranches++;
            
            this.branches.set(branchId, branch);
            await this.redis.setEx(`version_branch:${branchId}`, 7200, JSON.stringify(branch));
            await this.updateRepository(repository);
            
            this.emit('branch_created', { repositoryId, branchId, branch });
            this.logger.info(`Branch created: ${name} from ${sourceBranch}`);
            
            return { success: true, branchId, branch };
        } catch (error) {
            this.logger.error('Create branch error:', error);
            throw error;
        }
    }
    
    async mergeBranch(mergeData) {
        try {
            const {
                repositoryId,
                sourceBranch,
                targetBranch,
                strategy,
                message,
                author
            } = mergeData;
            
            const repository = await this.getRepository(repositoryId);
            if (!repository) {
                throw new Error(`Repository ${repositoryId} not found`);
            }
            
            const source = repository.branches.get(sourceBranch);
            const target = repository.branches.get(targetBranch || repository.settings.defaultBranch);
            
            if (!source || !target) {
                throw new Error('Source or target branch not found');
            }
            
            const mergeId = uuidv4();
            const mergeStrategy = strategy || repository.settings.mergeStrategy;
            
            let mergeResult;
            
            switch (mergeStrategy) {
                case this.mergeStrategies.FAST_FORWARD:
                    mergeResult = await this.fastForwardMerge(source, target);
                    break;
                case this.mergeStrategies.THREE_WAY:
                    mergeResult = await this.threeWayMerge(source, target, mergeId);
                    break;
                case this.mergeStrategies.SQUASH:
                    mergeResult = await this.squashMerge(source, target, mergeId, message);
                    break;
                default:
                    mergeResult = await this.autoMerge(source, target, mergeId);
            }
            
            if (mergeResult.success) {
                // Create merge commit if needed
                if (mergeResult.createMergeCommit) {
                    const mergeCommit = await this.createMergeCommit({
                        repositoryId,
                        branchId: target.id,
                        sourceBranch: source.name,
                        targetBranch: target.name,
                        message: message || `Merge ${source.name} into ${target.name}`,
                        author: author || 'system',
                        parentCommits: [target.headCommit, source.headCommit],
                        changes: mergeResult.changes || []
                    });
                    
                    target.headCommit = mergeCommit.id;
                    target.commits.push(mergeCommit.id);
                    target.metadata.lastCommit = new Date();
                    target.metadata.totalCommits++;
                }
                
                await this.updateBranch(target);
                await this.updateRepository(repository);
                
                this.emit('merge_completed', {
                    repositoryId,
                    mergeId,
                    sourceBranch: source.name,
                    targetBranch: target.name,
                    strategy: mergeStrategy,
                    result: mergeResult
                });
                
                this.logger.info(`Merge completed: ${source.name} -> ${target.name}`);
                
                return { success: true, mergeId, result: mergeResult };
            } else {
                this.emit('conflict_detected', {
                    repositoryId,
                    mergeId,
                    sourceBranch: source.name,
                    targetBranch: target.name,
                    conflicts: mergeResult.conflicts
                });
                
                return { success: false, mergeId, conflicts: mergeResult.conflicts };
            }
        } catch (error) {
            this.logger.error('Merge branch error:', error);
            throw error;
        }
    }
    
    async fastForwardMerge(source, target) {
        // Fast-forward is possible if target is ancestor of source
        const canFastForward = await this.isAncestor(target.headCommit, source.headCommit);
        
        if (canFastForward) {
            target.headCommit = source.headCommit;
            target.commits = [...source.commits];
            target.metadata.lastCommit = source.metadata.lastCommit;
            target.metadata.totalCommits = source.metadata.totalCommits;
            
            return { success: true, createMergeCommit: false, type: 'fast_forward' };
        } else {
            return { success: false, error: 'Fast-forward not possible' };
        }
    }
    
    async threeWayMerge(source, target, mergeId) {
        try {
            const commonAncestor = await this.findCommonAncestor(source.headCommit, target.headCommit);
            const conflicts = await this.detectConflicts(source, target, commonAncestor);
            
            if (conflicts.length > 0) {
                return { success: false, conflicts };
            }
            
            const mergedChanges = await this.mergeChanges(source, target, commonAncestor);
            
            return {
                success: true,
                createMergeCommit: true,
                type: 'three_way',
                changes: mergedChanges
            };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async squashMerge(source, target, mergeId, message) {
        try {
            const squashedChanges = await this.squashCommits(source.commits, target.headCommit);
            
            return {
                success: true,
                createMergeCommit: true,
                type: 'squash',
                changes: squashedChanges,
                message: message || `Squash merge from ${source.name}`
            };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async autoMerge(source, target, mergeId) {
        // Try fast-forward first, then three-way merge
        const fastForwardResult = await this.fastForwardMerge(source, target);
        if (fastForwardResult.success) {
            return fastForwardResult;
        }
        
        return await this.threeWayMerge(source, target, mergeId);
    }
    
    async createMergeCommit(mergeData) {
        const commitId = uuidv4();
        const commit = {
            id: commitId,
            repositoryId: mergeData.repositoryId,
            branchId: mergeData.branchId,
            message: mergeData.message,
            author: mergeData.author,
            timestamp: new Date(),
            parentCommits: mergeData.parentCommits || [],
            changes: mergeData.changes || [],
            type: 'merge',
            metadata: {
                sourceBranch: mergeData.sourceBranch,
                targetBranch: mergeData.targetBranch,
                totalChanges: (mergeData.changes || []).length
            }
        };
        
        this.commits.set(commitId, commit);
        await this.redis.setEx(`version_commit:${commitId}`, 7200, JSON.stringify(commit));
        
        return commit;
    }
    
    processChanges(changes) {
        return changes.map(change => ({
            path: change.path,
            type: change.type || this.fileStates.MODIFIED,
            content: change.content || '',
            hash: this.hashContent(change.content || ''),
            size: Buffer.byteLength(change.content || '', 'utf8'),
            oldPath: change.oldPath,
            oldHash: change.oldContent ? this.hashContent(change.oldContent) : null
        }));
    }
    
    async createCommitSnapshot(commit) {
        try {
            const snapshotDir = `/tmp/version_snapshots/${commit.repositoryId}/${commit.id}`;
            await fs.mkdir(snapshotDir, { recursive: true });
            
            // Create files from changes
            for (const change of commit.changes) {
                if (change.type !== this.fileStates.DELETED) {
                    const filePath = path.join(snapshotDir, change.path);
                    const fileDir = path.dirname(filePath);
                    
                    await fs.mkdir(fileDir, { recursive: true });
                    await fs.writeFile(filePath, change.content || '');
                }
            }
            
            // Create compressed archive
            const archivePath = `/tmp/version_snapshots/${commit.repositoryId}/${commit.id}.tar.gz`;
            await this.createArchive(snapshotDir, archivePath);
            
            commit.snapshotPath = archivePath;
            
            return archivePath;
        } catch (error) {
            this.logger.warn(`Failed to create commit snapshot: ${commit.id}`, error);
            return null;
        }
    }
    
    async createArchive(sourceDir, outputPath) {
        return new Promise((resolve, reject) => {
            tar.create(
                {
                    gzip: true,
                    file: outputPath,
                    cwd: path.dirname(sourceDir)
                },
                [path.basename(sourceDir)]
            )
            .then(() => resolve(outputPath))
            .catch(reject);
        });
    }
    
    hashContent(content) {
        return crypto.createHash('sha256').update(content).digest('hex');
    }
    
    async isAncestor(ancestorCommitId, descendantCommitId) {
        // Simplified ancestor check
        if (!ancestorCommitId || !descendantCommitId) return false;
        if (ancestorCommitId === descendantCommitId) return true;
        
        const descendant = this.commits.get(descendantCommitId);
        if (!descendant) return false;
        
        // Check parent commits recursively
        for (const parentId of descendant.parentCommits) {
            if (parentId === ancestorCommitId) return true;
            if (await this.isAncestor(ancestorCommitId, parentId)) return true;
        }
        
        return false;
    }
    
    async findCommonAncestor(commit1Id, commit2Id) {
        // Simplified common ancestor finding
        if (!commit1Id || !commit2Id) return null;
        if (commit1Id === commit2Id) return commit1Id;
        
        const commit1 = this.commits.get(commit1Id);
        const commit2 = this.commits.get(commit2Id);
        
        if (!commit1 || !commit2) return null;
        
        // Find intersection of ancestor chains
        const ancestors1 = new Set();
        const ancestors2 = new Set();
        
        await this.collectAncestors(commit1Id, ancestors1);
        await this.collectAncestors(commit2Id, ancestors2);
        
        for (const ancestor of ancestors1) {
            if (ancestors2.has(ancestor)) {
                return ancestor;
            }
        }
        
        return null;
    }
    
    async collectAncestors(commitId, ancestors) {
        if (!commitId || ancestors.has(commitId)) return;
        
        ancestors.add(commitId);
        const commit = this.commits.get(commitId);
        
        if (commit && commit.parentCommits) {
            for (const parentId of commit.parentCommits) {
                await this.collectAncestors(parentId, ancestors);
            }
        }
    }
    
    async detectConflicts(source, target, commonAncestor) {
        const conflicts = [];
        
        // Get changes from common ancestor to both branches
        const sourceChanges = await this.getChangesSince(source.headCommit, commonAncestor);
        const targetChanges = await this.getChangesSince(target.headCommit, commonAncestor);
        
        // Find conflicting changes
        const sourceFiles = new Map(sourceChanges.map(c => [c.path, c]));
        const targetFiles = new Map(targetChanges.map(c => [c.path, c]));
        
        for (const [filePath, sourceChange] of sourceFiles) {
            const targetChange = targetFiles.get(filePath);
            
            if (targetChange && sourceChange.hash !== targetChange.hash) {
                conflicts.push({
                    path: filePath,
                    sourceChange,
                    targetChange,
                    type: 'content_conflict'
                });
            }
        }
        
        return conflicts;
    }
    
    async getChangesSince(fromCommitId, toCommitId) {
        const changes = [];
        
        // This is a simplified implementation
        // In practice, you'd traverse the commit tree and collect changes
        
        return changes;
    }
    
    async mergeChanges(source, target, commonAncestor) {
        // Simplified merge logic
        const mergedChanges = [];
        
        // This would implement actual three-way merge logic
        // For now, just return empty changes
        
        return mergedChanges;
    }
    
    async squashCommits(commitIds, baseCommitId) {
        const squashedChanges = [];
        
        // Collect all changes from the commits to be squashed
        for (const commitId of commitIds) {
            const commit = this.commits.get(commitId);
            if (commit && commit.changes) {
                squashedChanges.push(...commit.changes);
            }
        }
        
        return squashedChanges;
    }
    
    async getRepository(repositoryId) {
        try {
            if (this.repositories.has(repositoryId)) {
                return this.repositories.get(repositoryId);
            }
            
            const cached = await this.redis.get(`version_repo:${repositoryId}`);
            if (cached) {
                const repoData = JSON.parse(cached);
                repoData.branches = new Map(repoData.branches);
                this.repositories.set(repositoryId, repoData);
                return repoData;
            }
            
            return null;
        } catch (error) {
            this.logger.error('Get repository error:', error);
            return null;
        }
    }
    
    async updateRepository(repository) {
        try {
            this.repositories.set(repository.id, repository);
            await this.redis.setEx(`version_repo:${repository.id}`, 7200, JSON.stringify({
                ...repository,
                branches: Array.from(repository.branches.entries())
            }));
        } catch (error) {
            this.logger.error('Update repository error:', error);
        }
    }
    
    async updateBranch(branch) {
        try {
            this.branches.set(branch.id, branch);
            await this.redis.setEx(`version_branch:${branch.id}`, 7200, JSON.stringify(branch));
        } catch (error) {
            this.logger.error('Update branch error:', error);
        }
    }
    
    async getStats() {
        try {
            const stats = {
                branchTypes: this.branchTypes,
                fileStates: this.fileStates,
                mergeStrategies: this.mergeStrategies,
                totalRepositories: this.repositories.size,
                totalBranches: this.branches.size,
                totalCommits: this.commits.size,
                timestamp: new Date()
            };
            
            return stats;
        } catch (error) {
            this.logger.error('Get stats error:', error);
            throw error;
        }
    }
}

module.exports = VersionControl;