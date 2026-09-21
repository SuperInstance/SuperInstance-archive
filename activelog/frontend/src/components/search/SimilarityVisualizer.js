/**
 * Similarity Visualizer for Cluster View
 */

export class SimilarityVisualizer {
    constructor() {
        this.clusters = [];
        this.selectedCluster = null;
        this.zoom = 1;
        this.pan = { x: 0, y: 0 };
    }

    async renderClusters(container, files, queryAnalysis) {
        // Generate clusters from files
        this.clusters = await this.generateClusters(files, queryAnalysis);
        
        container.innerHTML = `
            <div class="cluster-visualization">
                <div class="cluster-controls">
                    <div class="cluster-stats">
                        <span class="stat-item">
                            <span class="stat-value">${this.clusters.length}</span>
                            <span class="stat-label">Clusters</span>
                        </span>
                        <span class="stat-item">
                            <span class="stat-value">${files.length}</span>
                            <span class="stat-label">Files</span>
                        </span>
                        <span class="stat-item">
                            <span class="stat-value">${this.getAverageSimilarity(files)}%</span>
                            <span class="stat-label">Avg Similarity</span>
                        </span>
                    </div>
                    
                    <div class="cluster-view-controls">
                        <button class="control-btn" id="zoom-in" title="Zoom In">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"/>
                                <path d="M21 21l-4.35-4.35"/>
                                <line x1="8" y1="11" x2="14" y2="11"/>
                                <line x1="11" y1="8" x2="11" y2="14"/>
                            </svg>
                        </button>
                        <button class="control-btn" id="zoom-out" title="Zoom Out">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"/>
                                <path d="M21 21l-4.35-4.35"/>
                                <line x1="8" y1="11" x2="14" y2="11"/>
                            </svg>
                        </button>
                        <button class="control-btn" id="reset-view" title="Reset View">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                                <path d="M21 3v5h-5"/>
                                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                                <path d="M3 21v-5h5"/>
                            </svg>
                        </button>
                        <button class="control-btn" id="layout-toggle" title="Switch Layout">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="7" height="7"/>
                                <rect x="14" y="3" width="7" height="7"/>
                                <rect x="14" y="14" width="7" height="7"/>
                                <rect x="3" y="14" width="7" height="7"/>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="cluster-canvas-container">
                    <svg class="cluster-canvas" id="cluster-canvas" viewBox="0 0 800 600">
                        <!-- Cluster visualization will be rendered here -->
                    </svg>
                    
                    <div class="cluster-legend">
                        <h4>Cluster Types</h4>
                        <div class="legend-items">
                            <div class="legend-item">
                                <div class="legend-color" style="background: #667eea;"></div>
                                <span>Content Similarity</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-color" style="background: #f093fb;"></div>
                                <span>Visual Similarity</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-color" style="background: #4ecdc4;"></div>
                                <span>Semantic Similarity</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-color" style="background: #45b7d1;"></div>
                                <span>Tag Similarity</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="cluster-details" id="cluster-details" style="display: none;">
                    <!-- Cluster details will be shown here -->
                </div>
            </div>
        `;

        this.attachEventListeners();
        this.renderClusterVisualization();
    }

    async generateClusters(files, queryAnalysis) {
        // Group files by similarity metrics
        const clusters = [];
        const clusterThreshold = 0.7;
        const processed = new Set();

        // Create similarity matrix
        const similarities = await this.calculateSimilarities(files);

        for (let i = 0; i < files.length; i++) {
            if (processed.has(i)) continue;

            const cluster = {
                id: `cluster_${clusters.length}`,
                type: this.determineClusterType(files[i], queryAnalysis),
                center: files[i],
                files: [files[i]],
                avgSimilarity: 0,
                position: this.generateClusterPosition(clusters.length),
                color: this.getClusterColor(this.determineClusterType(files[i], queryAnalysis))
            };

            processed.add(i);

            // Find similar files for this cluster
            for (let j = i + 1; j < files.length; j++) {
                if (processed.has(j)) continue;

                const similarity = similarities[i][j];
                if (similarity >= clusterThreshold) {
                    cluster.files.push(files[j]);
                    processed.add(j);
                }
            }

            // Calculate average similarity for cluster
            if (cluster.files.length > 1) {
                cluster.avgSimilarity = this.calculateClusterSimilarity(cluster.files, similarities);
            }

            clusters.push(cluster);
        }

        return clusters;
    }

    async calculateSimilarities(files) {
        // Create similarity matrix (simplified version)
        const matrix = [];
        
        for (let i = 0; i < files.length; i++) {
            matrix[i] = [];
            for (let j = 0; j < files.length; j++) {
                if (i === j) {
                    matrix[i][j] = 1.0;
                } else {
                    // Calculate similarity based on multiple factors
                    matrix[i][j] = this.calculateFileSimilarity(files[i], files[j]);
                }
            }
        }

        return matrix;
    }

    calculateFileSimilarity(file1, file2) {
        let similarity = 0;
        let factors = 0;

        // Type similarity
        if (file1.type === file2.type) {
            similarity += 0.3;
        }
        factors++;

        // Tag similarity
        const tags1 = new Set(file1.tags || []);
        const tags2 = new Set(file2.tags || []);
        const commonTags = new Set([...tags1].filter(x => tags2.has(x)));
        const tagSimilarity = commonTags.size / Math.max(tags1.size, tags2.size, 1);
        similarity += tagSimilarity * 0.4;
        factors++;

        // Content similarity (from search results)
        if (file1.similarity_score && file2.similarity_score) {
            const scoreDiff = Math.abs(file1.similarity_score - file2.similarity_score);
            similarity += (1 - scoreDiff) * 0.3;
            factors++;
        }

        return factors > 0 ? similarity / factors : 0;
    }

    determineClusterType(file, queryAnalysis) {
        // Determine cluster type based on file properties and query
        if (file.type === 'image' && queryAnalysis?.visual_keywords?.length > 0) {
            return 'visual';
        } else if (file.tags && file.tags.length > 0) {
            return 'tag';
        } else if (queryAnalysis?.semantic_concepts?.length > 0) {
            return 'semantic';
        } else {
            return 'content';
        }
    }

    generateClusterPosition(index) {
        // Generate position using circle packing algorithm
        const radius = 50 + Math.sqrt(index + 1) * 80;
        const angle = (index * 2.4) % (2 * Math.PI); // Golden angle for better distribution
        
        return {
            x: 400 + radius * Math.cos(angle),
            y: 300 + radius * Math.sin(angle)
        };
    }

    getClusterColor(type) {
        const colors = {
            'content': '#667eea',
            'visual': '#f093fb',
            'semantic': '#4ecdc4',
            'tag': '#45b7d1'
        };
        return colors[type] || '#667eea';
    }

    calculateClusterSimilarity(files, similarities) {
        let totalSimilarity = 0;
        let comparisons = 0;

        for (let i = 0; i < files.length; i++) {
            for (let j = i + 1; j < files.length; j++) {
                totalSimilarity += similarities[i][j] || 0;
                comparisons++;
            }
        }

        return comparisons > 0 ? totalSimilarity / comparisons : 0;
    }

    renderClusterVisualization() {
        const canvas = document.getElementById('cluster-canvas');
        
        // Clear existing content
        canvas.innerHTML = '';

        // Create connections between related clusters
        this.renderClusterConnections(canvas);

        // Render clusters
        this.clusters.forEach(cluster => {
            this.renderCluster(canvas, cluster);
        });
    }

    renderClusterConnections(canvas) {
        // Find clusters that should be connected
        for (let i = 0; i < this.clusters.length; i++) {
            for (let j = i + 1; j < this.clusters.length; j++) {
                const similarity = this.calculateInterClusterSimilarity(
                    this.clusters[i], 
                    this.clusters[j]
                );

                if (similarity > 0.5) {
                    this.renderConnection(canvas, this.clusters[i], this.clusters[j], similarity);
                }
            }
        }
    }

    renderConnection(canvas, cluster1, cluster2, similarity) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', cluster1.position.x);
        line.setAttribute('y1', cluster1.position.y);
        line.setAttribute('x2', cluster2.position.x);
        line.setAttribute('y2', cluster2.position.y);
        line.setAttribute('stroke', '#e2e8f0');
        line.setAttribute('stroke-width', Math.max(1, similarity * 3));
        line.setAttribute('opacity', similarity * 0.6);
        line.classList.add('cluster-connection');
        
        canvas.appendChild(line);
    }

    renderCluster(canvas, cluster) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'cluster-group');
        group.setAttribute('data-cluster-id', cluster.id);

        // Cluster circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        const radius = Math.max(20, Math.sqrt(cluster.files.length) * 15);
        
        circle.setAttribute('cx', cluster.position.x);
        circle.setAttribute('cy', cluster.position.y);
        circle.setAttribute('r', radius);
        circle.setAttribute('fill', cluster.color);
        circle.setAttribute('fill-opacity', '0.2');
        circle.setAttribute('stroke', cluster.color);
        circle.setAttribute('stroke-width', '2');
        circle.classList.add('cluster-circle');

        // File count label
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', cluster.position.x);
        text.setAttribute('y', cluster.position.y);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('dominant-baseline', 'middle');
        text.setAttribute('font-size', '14');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('fill', cluster.color);
        text.textContent = cluster.files.length;

        // Cluster type label
        const typeLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        typeLabel.setAttribute('x', cluster.position.x);
        typeLabel.setAttribute('y', cluster.position.y + radius + 20);
        typeLabel.setAttribute('text-anchor', 'middle');
        typeLabel.setAttribute('font-size', '12');
        typeLabel.setAttribute('fill', '#4a5568');
        typeLabel.textContent = cluster.type;

        group.appendChild(circle);
        group.appendChild(text);
        group.appendChild(typeLabel);

        // Add click handler
        group.addEventListener('click', () => {
            this.selectCluster(cluster);
        });

        group.addEventListener('mouseenter', () => {
            this.showClusterPreview(cluster, group);
        });

        group.addEventListener('mouseleave', () => {
            this.hideClusterPreview();
        });

        canvas.appendChild(group);
    }

    calculateInterClusterSimilarity(cluster1, cluster2) {
        // Calculate similarity between cluster centers
        let similarity = 0;

        // Type similarity
        if (cluster1.type === cluster2.type) {
            similarity += 0.4;
        }

        // File similarity
        const file1 = cluster1.center;
        const file2 = cluster2.center;
        
        if (file1.type === file2.type) {
            similarity += 0.3;
        }

        // Tag overlap
        const tags1 = new Set(file1.tags || []);
        const tags2 = new Set(file2.tags || []);
        const commonTags = new Set([...tags1].filter(x => tags2.has(x)));
        const tagSimilarity = commonTags.size / Math.max(tags1.size, tags2.size, 1);
        similarity += tagSimilarity * 0.3;

        return Math.min(similarity, 1.0);
    }

    selectCluster(cluster) {
        this.selectedCluster = cluster;
        
        // Highlight selected cluster
        document.querySelectorAll('.cluster-group').forEach(group => {
            group.classList.remove('selected');
        });
        
        const selectedGroup = document.querySelector(`[data-cluster-id="${cluster.id}"]`);
        selectedGroup.classList.add('selected');

        // Show cluster details
        this.showClusterDetails(cluster);
    }

    showClusterDetails(cluster) {
        const detailsContainer = document.getElementById('cluster-details');
        
        detailsContainer.innerHTML = `
            <div class="cluster-detail-header">
                <h3>${cluster.type.charAt(0).toUpperCase() + cluster.type.slice(1)} Cluster</h3>
                <button class="close-details" id="close-cluster-details">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            
            <div class="cluster-detail-stats">
                <div class="detail-stat">
                    <span class="stat-value">${cluster.files.length}</span>
                    <span class="stat-label">Files</span>
                </div>
                <div class="detail-stat">
                    <span class="stat-value">${Math.round(cluster.avgSimilarity * 100)}%</span>
                    <span class="stat-label">Avg Similarity</span>
                </div>
                <div class="detail-stat">
                    <span class="stat-value">${cluster.type}</span>
                    <span class="stat-label">Type</span>
                </div>
            </div>
            
            <div class="cluster-files-list">
                <h4>Files in this cluster</h4>
                <div class="cluster-files">
                    ${cluster.files.map(file => `
                        <div class="cluster-file-item" data-file-id="${file.id}">
                            <div class="file-icon">${this.getFileIcon(file)}</div>
                            <div class="file-info">
                                <div class="file-name">${file.name}</div>
                                <div class="file-similarity">${Math.round((file.similarity_score || 0) * 100)}% match</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        detailsContainer.style.display = 'block';

        // Attach event listeners
        document.getElementById('close-cluster-details')?.addEventListener('click', () => {
            detailsContainer.style.display = 'none';
            this.selectedCluster = null;
            document.querySelectorAll('.cluster-group').forEach(group => {
                group.classList.remove('selected');
            });
        });

        detailsContainer.querySelectorAll('.cluster-file-item').forEach(item => {
            item.addEventListener('click', () => {
                const fileId = item.dataset.fileId;
                this.openFile(fileId);
            });
        });
    }

    showClusterPreview(cluster, groupElement) {
        // Create tooltip preview
        const tooltip = document.createElement('div');
        tooltip.className = 'cluster-tooltip';
        tooltip.innerHTML = `
            <div class="tooltip-header">${cluster.type.charAt(0).toUpperCase() + cluster.type.slice(1)} Cluster</div>
            <div class="tooltip-content">
                <div class="tooltip-stat">${cluster.files.length} files</div>
                <div class="tooltip-stat">${Math.round(cluster.avgSimilarity * 100)}% similarity</div>
                <div class="tooltip-files">
                    ${cluster.files.slice(0, 3).map(file => `
                        <span class="tooltip-file">${file.name}</span>
                    `).join('')}
                    ${cluster.files.length > 3 ? `<span class="tooltip-more">+${cluster.files.length - 3} more</span>` : ''}
                </div>
            </div>
        `;

        // Position tooltip
        const rect = groupElement.getBoundingClientRect();
        tooltip.style.position = 'absolute';
        tooltip.style.left = `${rect.right + 10}px`;
        tooltip.style.top = `${rect.top}px`;

        document.body.appendChild(tooltip);
        groupElement.setAttribute('data-tooltip-id', tooltip.id = `tooltip_${Date.now()}`);
    }

    hideClusterPreview() {
        document.querySelectorAll('.cluster-tooltip').forEach(tooltip => {
            tooltip.remove();
        });
    }

    attachEventListeners() {
        // Zoom controls
        document.getElementById('zoom-in')?.addEventListener('click', () => {
            this.zoom = Math.min(this.zoom * 1.2, 3);
            this.updateViewport();
        });

        document.getElementById('zoom-out')?.addEventListener('click', () => {
            this.zoom = Math.max(this.zoom / 1.2, 0.5);
            this.updateViewport();
        });

        document.getElementById('reset-view')?.addEventListener('click', () => {
            this.zoom = 1;
            this.pan = { x: 0, y: 0 };
            this.updateViewport();
        });

        // Pan functionality
        const canvas = document.getElementById('cluster-canvas');
        let isPanning = false;
        let lastPanPoint = null;

        canvas.addEventListener('mousedown', (e) => {
            if (e.button === 0) { // Left click
                isPanning = true;
                lastPanPoint = { x: e.clientX, y: e.clientY };
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (isPanning && lastPanPoint) {
                const deltaX = e.clientX - lastPanPoint.x;
                const deltaY = e.clientY - lastPanPoint.y;
                
                this.pan.x += deltaX / this.zoom;
                this.pan.y += deltaY / this.zoom;
                
                this.updateViewport();
                lastPanPoint = { x: e.clientX, y: e.clientY };
            }
        });

        document.addEventListener('mouseup', () => {
            isPanning = false;
            lastPanPoint = null;
        });
    }

    updateViewport() {
        const canvas = document.getElementById('cluster-canvas');
        const transform = `translate(${this.pan.x}, ${this.pan.y}) scale(${this.zoom})`;
        canvas.style.transform = transform;
    }

    getAverageSimilarity(files) {
        if (files.length === 0) return 0;
        const total = files.reduce((sum, file) => sum + (file.similarity_score || 0), 0);
        return Math.round((total / files.length) * 100);
    }

    getFileIcon(file) {
        const iconMap = {
            'image': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'document': '📄',
            'pdf': '📕',
            'code': '💻',
            'default': '📄'
        };
        return iconMap[file.type] || iconMap.default;
    }

    openFile(fileId) {
        // Emit event to open file
        document.dispatchEvent(new CustomEvent('openFile', {
            detail: { fileId }
        }));
    }
}