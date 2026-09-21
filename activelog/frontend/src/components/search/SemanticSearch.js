/**
 * Semantic Search Component with Natural Language Processing
 */

import { ApiClient } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';
import { GlobalEvents } from '../../utils/events.js';
import { SearchHistory } from './SearchHistory.js';
import { SimilarityVisualizer } from './SimilarityVisualizer.js';

export class SemanticSearch {
    constructor() {
        this.searchHistory = new SearchHistory();
        this.visualizer = new SimilarityVisualizer();
        this.currentQuery = '';
        this.currentResults = [];
        this.similarityThreshold = 0.7;
        this.searchFilters = {
            fileTypes: [],
            dateRange: null,
            tags: [],
            similarity: 0.7
        };
        this.isSearching = false;
    }

    async render(container) {
        container.innerHTML = `
            <div class="semantic-search">
                <div class="search-header">
                    <h1>Semantic Search</h1>
                    <p class="search-subtitle">Find files using natural language and visual similarity</p>
                </div>

                <div class="search-main">
                    <!-- Natural Language Search Input -->
                    <div class="search-input-section">
                        <div class="search-input-container">
                            <div class="search-input-wrapper">
                                <textarea 
                                    id="semantic-search-input" 
                                    placeholder="Describe what you're looking for... (e.g., 'photos from my vacation in Italy' or 'documents about project planning')"
                                    rows="2"></textarea>
                                <div class="search-input-actions">
                                    <button class="search-action-btn" id="voice-search" title="Voice search">
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                                            <line x1="12" y1="19" x2="12" y2="23"/>
                                            <line x1="8" y1="23" x2="16" y2="23"/>
                                        </svg>
                                    </button>
                                    <button class="search-action-btn" id="image-search" title="Search by image">
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
                                            <circle cx="9" cy="9" r="2"/>
                                            <path d="M21 15l-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
                                        </svg>
                                    </button>
                                    <button class="search-btn primary" id="semantic-search-btn">
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <circle cx="11" cy="11" r="8"/>
                                            <path d="m21 21-4.35-4.35"/>
                                        </svg>
                                        Search
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Search Suggestions -->
                            <div class="search-suggestions" id="search-suggestions" style="display: none;">
                                <!-- Suggestions will be populated here -->
                            </div>
                        </div>

                        <!-- Quick Search Examples -->
                        <div class="search-examples">
                            <span class="examples-label">Try these:</span>
                            <button class="example-query" data-query="photos of people smiling">photos of people smiling</button>
                            <button class="example-query" data-query="financial documents from last quarter">financial documents from last quarter</button>
                            <button class="example-query" data-query="presentations about machine learning">presentations about machine learning</button>
                            <button class="example-query" data-query="images with blue sky and mountains">images with blue sky and mountains</button>
                        </div>
                    </div>

                    <!-- Search Filters -->
                    <div class="search-filters-section">
                        <div class="filters-header">
                            <h3>Filters</h3>
                            <button class="filters-toggle" id="filters-toggle">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"/>
                                </svg>
                                Advanced
                            </button>
                        </div>
                        
                        <div class="filters-content" id="filters-content">
                            <!-- Similarity Threshold -->
                            <div class="filter-group">
                                <label for="similarity-slider">Similarity Threshold: <span id="similarity-value">70%</span></label>
                                <input type="range" id="similarity-slider" min="0" max="100" value="70" class="similarity-slider">
                                <div class="slider-labels">
                                    <span>Broader</span>
                                    <span>Exact Match</span>
                                </div>
                            </div>

                            <!-- File Types -->
                            <div class="filter-group">
                                <label>File Types</label>
                                <div class="filter-checkboxes">
                                    <label class="checkbox-label">
                                        <input type="checkbox" value="image" class="file-type-filter">
                                        <span>📷 Images</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" value="document" class="file-type-filter">
                                        <span>📄 Documents</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" value="video" class="file-type-filter">
                                        <span>🎥 Videos</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" value="audio" class="file-type-filter">
                                        <span>🎵 Audio</span>
                                    </label>
                                </div>
                            </div>

                            <!-- Date Range -->
                            <div class="filter-group">
                                <label>Date Range</label>
                                <div class="date-range-inputs">
                                    <input type="date" id="date-from" placeholder="From">
                                    <input type="date" id="date-to" placeholder="To">
                                </div>
                                <div class="date-presets">
                                    <button class="date-preset" data-days="7">Last 7 days</button>
                                    <button class="date-preset" data-days="30">Last month</button>
                                    <button class="date-preset" data-days="365">Last year</button>
                                </div>
                            </div>

                            <!-- Tags Filter -->
                            <div class="filter-group">
                                <label>Tags</label>
                                <div class="tags-input-container">
                                    <input type="text" id="tags-filter" placeholder="Filter by tags..." class="tags-input">
                                    <div class="selected-tags" id="selected-tags"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Search Results -->
                    <div class="search-results-section">
                        <div class="results-header" id="results-header" style="display: none;">
                            <div class="results-info">
                                <span class="results-count" id="results-count">0 results</span>
                                <span class="search-time" id="search-time">in 0ms</span>
                            </div>
                            <div class="results-actions">
                                <div class="view-toggle">
                                    <button class="view-btn active" data-view="grid">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <rect x="3" y="3" width="7" height="7"/>
                                            <rect x="14" y="3" width="7" height="7"/>
                                            <rect x="14" y="14" width="7" height="7"/>
                                            <rect x="3" y="14" width="7" height="7"/>
                                        </svg>
                                    </button>
                                    <button class="view-btn" data-view="list">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <line x1="8" y1="6" x2="21" y2="6"/>
                                            <line x1="8" y1="12" x2="21" y2="12"/>
                                            <line x1="8" y1="18" x2="21" y2="18"/>
                                            <line x1="3" y1="6" x2="3.01" y2="6"/>
                                            <line x1="3" y1="12" x2="3.01" y2="12"/>
                                            <line x1="3" y1="18" x2="3.01" y2="18"/>
                                        </svg>
                                    </button>
                                    <button class="view-btn" data-view="cluster">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <circle cx="12" cy="12" r="3"/>
                                            <circle cx="7" cy="7" r="2"/>
                                            <circle cx="17" cy="7" r="2"/>
                                            <circle cx="7" cy="17" r="2"/>
                                            <circle cx="17" cy="17" r="2"/>
                                            <line x1="10.5" y1="10.5" x2="8.5" y2="8.5"/>
                                            <line x1="13.5" y1="10.5" x2="15.5" y2="8.5"/>
                                            <line x1="10.5" y1="13.5" x2="8.5" y2="15.5"/>
                                            <line x1="13.5" y1="13.5" x2="15.5" y2="15.5"/>
                                        </svg>
                                    </button>
                                </div>
                                <button class="action-btn" id="save-search">Save Search</button>
                            </div>
                        </div>

                        <div class="search-results" id="search-results">
                            <!-- Default state -->
                            <div class="search-empty-state" id="empty-state">
                                <div class="empty-icon">
                                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                                        <circle cx="11" cy="11" r="8"/>
                                        <path d="m21 21-4.35-4.35"/>
                                        <circle cx="11" cy="11" r="3"/>
                                    </svg>
                                </div>
                                <h3>Start your semantic search</h3>
                                <p>Use natural language to find files by content, context, or visual similarity</p>
                            </div>

                            <!-- Loading state -->
                            <div class="search-loading" id="loading-state" style="display: none;">
                                <div class="loading-spinner">
                                    <div class="spinner"></div>
                                </div>
                                <p>Analyzing your query and searching files...</p>
                                <div class="search-progress">
                                    <div class="progress-bar">
                                        <div class="progress-fill" id="search-progress"></div>
                                    </div>
                                    <span class="progress-text" id="progress-text">Processing natural language...</span>
                                </div>
                            </div>

                            <!-- Results container -->
                            <div class="results-container" id="results-container" style="display: none;">
                                <!-- Results will be rendered here -->
                            </div>
                        </div>
                    </div>

                    <!-- Sidebar with Search History and Recommendations -->
                    <div class="search-sidebar">
                        <div class="sidebar-section">
                            <h3>Search History</h3>
                            <div class="search-history-list" id="search-history">
                                <!-- History items will be populated here -->
                            </div>
                        </div>

                        <div class="sidebar-section">
                            <h3>Saved Searches</h3>
                            <div class="saved-searches-list" id="saved-searches">
                                <!-- Saved searches will be populated here -->
                            </div>
                        </div>

                        <div class="sidebar-section">
                            <h3>Similar Files</h3>
                            <div class="similar-files-list" id="similar-files">
                                <div class="similar-files-empty">
                                    Select a file to see similar content
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Image Search Modal -->
                <div class="modal-overlay" id="image-search-modal" style="display: none;">
                    <div class="modal-content image-search-modal">
                        <div class="modal-header">
                            <h2>Search by Image</h2>
                            <button class="modal-close" id="close-image-search">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div class="image-upload-area" id="image-upload-area">
                                <input type="file" id="search-image-input" accept="image/*" style="display: none;">
                                <div class="upload-content">
                                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
                                        <circle cx="9" cy="9" r="2"/>
                                        <path d="M21 15l-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
                                    </svg>
                                    <h3>Upload an image to find similar files</h3>
                                    <p>Drag and drop or click to browse</p>
                                    <button class="upload-btn" id="browse-image">Browse Images</button>
                                </div>
                            </div>
                            <div class="image-preview" id="image-preview" style="display: none;">
                                <!-- Image preview will be shown here -->
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="action-btn secondary" id="cancel-image-search">Cancel</button>
                            <button class="action-btn primary" id="start-image-search" disabled>Find Similar Images</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        await this.attachEventListeners();
        await this.loadSearchHistory();
        await this.loadSavedSearches();
        this.setupVoiceSearch();
        this.setupImageSearch();
    }

    async attachEventListeners() {
        // Main search functionality
        const searchInput = document.getElementById('semantic-search-input');
        const searchBtn = document.getElementById('semantic-search-btn');
        
        searchInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                this.performSearch();
            }
        });

        searchInput?.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });

        searchBtn?.addEventListener('click', () => this.performSearch());

        // Example queries
        document.querySelectorAll('.example-query').forEach(button => {
            button.addEventListener('click', (e) => {
                const query = e.target.dataset.query;
                searchInput.value = query;
                this.performSearch();
            });
        });

        // Filters
        const filtersToggle = document.getElementById('filters-toggle');
        const filtersContent = document.getElementById('filters-content');
        
        filtersToggle?.addEventListener('click', () => {
            const isVisible = filtersContent.style.display !== 'none';
            filtersContent.style.display = isVisible ? 'none' : 'block';
            filtersToggle.classList.toggle('active', !isVisible);
        });

        // Similarity threshold
        const similaritySlider = document.getElementById('similarity-slider');
        const similarityValue = document.getElementById('similarity-value');
        
        similaritySlider?.addEventListener('input', (e) => {
            const value = e.target.value;
            similarityValue.textContent = `${value}%`;
            this.similarityThreshold = value / 100;
            this.updateSearchFilters();
        });

        // File type filters
        document.querySelectorAll('.file-type-filter').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateFileTypeFilters();
            });
        });

        // Date presets
        document.querySelectorAll('.date-preset').forEach(button => {
            button.addEventListener('click', (e) => {
                const days = parseInt(e.target.dataset.days);
                this.setDateRange(days);
            });
        });

        // View toggle
        document.querySelectorAll('.view-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const view = e.target.closest('.view-btn').dataset.view;
                this.setResultsView(view);
            });
        });

        // Voice search
        document.getElementById('voice-search')?.addEventListener('click', () => {
            this.startVoiceSearch();
        });

        // Image search
        document.getElementById('image-search')?.addEventListener('click', () => {
            this.showImageSearchModal();
        });

        // Save search
        document.getElementById('save-search')?.addEventListener('click', () => {
            this.saveCurrentSearch();
        });

        // Global events
        GlobalEvents.on('fileSelected', (file) => {
            this.loadSimilarFiles(file);
        });
    }

    async handleSearchInput(query) {
        this.currentQuery = query;
        
        if (query.length > 3) {
            // Show search suggestions
            await this.showSearchSuggestions(query);
        } else {
            this.hideSearchSuggestions();
        }
    }

    async showSearchSuggestions(query) {
        try {
            const suggestions = await ApiClient.post('/ai/search-suggestions', { query });
            const container = document.getElementById('search-suggestions');
            
            if (suggestions.suggestions && suggestions.suggestions.length > 0) {
                container.innerHTML = suggestions.suggestions.map(suggestion => `
                    <div class="suggestion-item" data-query="${suggestion.text}">
                        <div class="suggestion-icon">${this.getSuggestionIcon(suggestion.type)}</div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${suggestion.text}</div>
                            <div class="suggestion-meta">${suggestion.description}</div>
                        </div>
                        <div class="suggestion-score">${Math.round(suggestion.confidence * 100)}%</div>
                    </div>
                `).join('');
                
                container.style.display = 'block';
                
                // Add click handlers
                container.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        document.getElementById('semantic-search-input').value = item.dataset.query;
                        this.hideSearchSuggestions();
                        this.performSearch();
                    });
                });
            } else {
                this.hideSearchSuggestions();
            }
        } catch (error) {
            console.error('Failed to get search suggestions:', error);
            this.hideSearchSuggestions();
        }
    }

    hideSearchSuggestions() {
        const container = document.getElementById('search-suggestions');
        container.style.display = 'none';
    }

    async performSearch() {
        if (!this.currentQuery.trim()) {
            NotificationManager.warning('Please enter a search query');
            return;
        }

        this.isSearching = true;
        this.showLoadingState();
        
        try {
            const searchParams = {
                query: this.currentQuery,
                similarity_threshold: this.similarityThreshold,
                file_types: this.searchFilters.fileTypes,
                date_range: this.searchFilters.dateRange,
                tags: this.searchFilters.tags,
                limit: 50
            };

            // Simulate search progress
            this.updateSearchProgress(0, 'Analyzing natural language...');
            await this.delay(500);
            
            this.updateSearchProgress(25, 'Generating embeddings...');
            const results = await ApiClient.post('/ai/semantic-search', searchParams);
            
            this.updateSearchProgress(75, 'Ranking results...');
            await this.delay(300);
            
            this.updateSearchProgress(100, 'Complete!');
            await this.delay(200);

            this.currentResults = results.files || [];
            this.renderSearchResults(this.currentResults, results.query_analysis);
            
            // Save to history
            await this.searchHistory.addSearch(this.currentQuery, this.currentResults.length);
            await this.loadSearchHistory();

        } catch (error) {
            console.error('Semantic search failed:', error);
            NotificationManager.error('Search failed. Please try again.');
            this.showEmptyState();
        } finally {
            this.isSearching = false;
        }
    }

    showLoadingState() {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('results-container').style.display = 'none';
        document.getElementById('loading-state').style.display = 'block';
        document.getElementById('results-header').style.display = 'none';
    }

    showEmptyState() {
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('results-container').style.display = 'none';
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('results-header').style.display = 'none';
    }

    updateSearchProgress(percent, text) {
        const progressFill = document.getElementById('search-progress');
        const progressText = document.getElementById('progress-text');
        
        progressFill.style.width = `${percent}%`;
        progressText.textContent = text;
    }

    renderSearchResults(results, queryAnalysis) {
        const startTime = Date.now();
        
        // Update results header
        const resultsHeader = document.getElementById('results-header');
        const resultsCount = document.getElementById('results-count');
        const searchTime = document.getElementById('search-time');
        
        resultsCount.textContent = `${results.length} result${results.length !== 1 ? 's' : ''}`;
        searchTime.textContent = `in ${Date.now() - startTime}ms`;
        resultsHeader.style.display = 'flex';

        // Show results container
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('results-container').style.display = 'block';

        // Render results based on current view
        const view = document.querySelector('.view-btn.active').dataset.view;
        this.renderResultsView(results, view, queryAnalysis);
    }

    renderResultsView(results, view, queryAnalysis) {
        const container = document.getElementById('results-container');
        
        switch (view) {
            case 'grid':
                this.renderGridResults(container, results);
                break;
            case 'list':
                this.renderListResults(container, results);
                break;
            case 'cluster':
                this.renderClusterResults(container, results, queryAnalysis);
                break;
        }
    }

    renderGridResults(container, results) {
        container.innerHTML = `
            <div class="results-grid">
                ${results.map(file => this.renderFileCard(file)).join('')}
            </div>
        `;
        
        this.attachResultEventListeners();
    }

    renderListResults(container, results) {
        container.innerHTML = `
            <div class="results-list">
                <div class="list-header">
                    <div class="col-name">Name</div>
                    <div class="col-similarity">Similarity</div>
                    <div class="col-size">Size</div>
                    <div class="col-modified">Modified</div>
                    <div class="col-actions">Actions</div>
                </div>
                <div class="list-body">
                    ${results.map(file => this.renderFileRow(file)).join('')}
                </div>
            </div>
        `;
        
        this.attachResultEventListeners();
    }

    async renderClusterResults(container, results, queryAnalysis) {
        container.innerHTML = `
            <div class="cluster-view">
                <div class="cluster-info">
                    <h3>Semantic Clusters</h3>
                    <p>Files grouped by content similarity and context</p>
                </div>
                <div class="cluster-container" id="cluster-container">
                    <!-- Cluster visualization will be rendered here -->
                </div>
            </div>
        `;

        // Render cluster visualization
        const clusterContainer = document.getElementById('cluster-container');
        await this.visualizer.renderClusters(clusterContainer, results, queryAnalysis);
    }

    renderFileCard(file) {
        const similarityScore = Math.round((file.similarity_score || 0) * 100);
        const highlightReasons = file.match_reasons || [];
        
        return `
            <div class="file-result-card" data-file-id="${file.id}">
                <div class="file-preview">
                    ${this.renderFilePreview(file)}
                    <div class="similarity-badge">${similarityScore}%</div>
                </div>
                <div class="file-info">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                        <span class="file-date">${this.formatRelativeDate(file.modified_at)}</span>
                    </div>
                    <div class="match-reasons">
                        ${highlightReasons.slice(0, 2).map(reason => `
                            <span class="match-reason" title="${reason.explanation}">
                                ${reason.type}: ${reason.snippet}
                            </span>
                        `).join('')}
                    </div>
                </div>
                <div class="file-actions">
                    <button class="action-btn small view-file" data-file-id="${file.id}">View</button>
                    <button class="action-btn small find-similar" data-file-id="${file.id}">Similar</button>
                </div>
            </div>
        `;
    }

    renderFileRow(file) {
        const similarityScore = Math.round((file.similarity_score || 0) * 100);
        
        return `
            <div class="file-result-row" data-file-id="${file.id}">
                <div class="col-name">
                    <div class="file-name-with-icon">
                        ${this.getFileIcon(file)}
                        <span class="file-name">${file.name}</span>
                    </div>
                </div>
                <div class="col-similarity">
                    <div class="similarity-indicator">
                        <div class="similarity-bar">
                            <div class="similarity-fill" style="width: ${similarityScore}%"></div>
                        </div>
                        <span class="similarity-score">${similarityScore}%</span>
                    </div>
                </div>
                <div class="col-size">${this.formatFileSize(file.size)}</div>
                <div class="col-modified">${this.formatRelativeDate(file.modified_at)}</div>
                <div class="col-actions">
                    <button class="action-btn small view-file" data-file-id="${file.id}">View</button>
                    <button class="action-btn small find-similar" data-file-id="${file.id}">Similar</button>
                </div>
            </div>
        `;
    }

    attachResultEventListeners() {
        // View file buttons
        document.querySelectorAll('.view-file').forEach(button => {
            button.addEventListener('click', (e) => {
                const fileId = e.target.dataset.fileId;
                this.viewFile(fileId);
            });
        });

        // Find similar buttons
        document.querySelectorAll('.find-similar').forEach(button => {
            button.addEventListener('click', (e) => {
                const fileId = e.target.dataset.fileId;
                this.findSimilarFiles(fileId);
            });
        });

        // File card clicks
        document.querySelectorAll('.file-result-card, .file-result-row').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.file-actions')) {
                    const fileId = card.dataset.fileId;
                    this.selectFile(fileId);
                }
            });
        });
    }

    async loadSimilarFiles(file) {
        try {
            const similar = await ApiClient.get(`/ai/similar-files/${file.id}?limit=10`);
            const container = document.getElementById('similar-files');
            
            if (similar.files && similar.files.length > 0) {
                container.innerHTML = similar.files.map(similarFile => `
                    <div class="similar-file-item" data-file-id="${similarFile.id}">
                        <div class="similar-file-preview">
                            ${this.getFileIcon(similarFile)}
                        </div>
                        <div class="similar-file-info">
                            <div class="similar-file-name">${similarFile.name}</div>
                            <div class="similarity-score">${Math.round(similarFile.similarity_score * 100)}% similar</div>
                        </div>
                    </div>
                `).join('');
                
                // Add click handlers
                container.querySelectorAll('.similar-file-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const fileId = item.dataset.fileId;
                        this.viewFile(fileId);
                    });
                });
            } else {
                container.innerHTML = '<div class="similar-files-empty">No similar files found</div>';
            }
        } catch (error) {
            console.error('Failed to load similar files:', error);
        }
    }

    // Continue with more methods in the next part...
    
    getSuggestionIcon(type) {
        const icons = {
            'content': '📄',
            'visual': '🖼️',
            'concept': '💡',
            'tag': '🏷️',
            'filename': '📝'
        };
        return icons[type] || '🔍';
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

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatRelativeDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return `${diffDays} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Placeholder methods for functionality to be implemented
    async loadSearchHistory() {
        await this.searchHistory.render(document.getElementById('search-history'));
    }

    async loadSavedSearches() {
        // Implementation for saved searches
    }

    setupVoiceSearch() {
        // Implementation for voice search
    }

    setupImageSearch() {
        // Implementation for image search
    }

    updateSearchFilters() {
        // Implementation for filter updates
    }

    updateFileTypeFilters() {
        // Implementation for file type filters
    }

    setDateRange(days) {
        // Implementation for date range setting
    }

    setResultsView(view) {
        // Update active view button
        document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-view="${view}"]`).classList.add('active');
        
        // Re-render results in new view
        if (this.currentResults.length > 0) {
            this.renderResultsView(this.currentResults, view);
        }
    }

    async viewFile(fileId) {
        GlobalEvents.emit('viewFile', fileId);
    }

    async findSimilarFiles(fileId) {
        // Implementation for finding similar files
    }

    selectFile(fileId) {
        const file = this.currentResults.find(f => f.id === fileId);
        if (file) {
            GlobalEvents.emit('fileSelected', file);
            this.loadSimilarFiles(file);
        }
    }

    async saveCurrentSearch() {
        // Implementation for saving searches
    }

    showImageSearchModal() {
        document.getElementById('image-search-modal').style.display = 'flex';
    }

    startVoiceSearch() {
        NotificationManager.info('Voice search feature coming soon!');
    }

    renderFilePreview(file) {
        if (file.type === 'image' && file.thumbnail_url) {
            return `<img src="${file.thumbnail_url}" alt="${file.name}" class="file-thumbnail">`;
        }
        return `<div class="file-icon-large">${this.getFileIcon(file)}</div>`;
    }
}