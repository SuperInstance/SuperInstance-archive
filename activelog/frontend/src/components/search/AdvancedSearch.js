/**
 * Advanced Search Interface with Filters and AI-powered Search
 */

import Fuse from 'fuse.js';
import { SearchBar } from '../common/SearchBar.js';
import { API } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class AdvancedSearch {
    constructor(options = {}) {
        this.container = null;
        this.searchBar = null;
        this.fuseInstance = null;
        
        this.onResults = options.onResults || (() => {});
        this.onError = options.onError || (() => {});
        
        this.searchMode = 'simple'; // 'simple', 'advanced', 'semantic', 'visual'
        this.searchFilters = {
            fileTypes: [],
            dateRange: null,
            sizeRange: null,
            locations: [],
            tags: [],
            metadata: {}
        };
        
        this.searchResults = [];
        this.searchHistory = [];
        this.savedSearches = this.loadSavedSearches();
        
        this.isSearching = false;
        this.searchAbortController = null;
        
        this.initializeFuse();
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="advanced-search">
                <div class="search-header">
                    <div class="search-modes">
                        <button class="search-mode-btn ${this.searchMode === 'simple' ? 'active' : ''}" 
                                data-mode="simple">
                            <i data-lucide="search"></i>
                            <span>Simple Search</span>
                        </button>
                        <button class="search-mode-btn ${this.searchMode === 'advanced' ? 'active' : ''}" 
                                data-mode="advanced">
                            <i data-lucide="filter"></i>
                            <span>Advanced</span>
                        </button>
                        <button class="search-mode-btn ${this.searchMode === 'semantic' ? 'active' : ''}" 
                                data-mode="semantic">
                            <i data-lucide="brain"></i>
                            <span>AI Search</span>
                        </button>
                        <button class="search-mode-btn ${this.searchMode === 'visual' ? 'active' : ''}" 
                                data-mode="visual">
                            <i data-lucide="image"></i>
                            <span>Visual Search</span>
                        </button>
                    </div>
                    
                    <div class="search-actions">
                        <button class="btn-icon save-search" title="Save current search">
                            <i data-lucide="bookmark"></i>
                        </button>
                        <button class="btn-icon search-settings" title="Search settings">
                            <i data-lucide="settings"></i>
                        </button>
                    </div>
                </div>
                
                <div class="search-interface">
                    <div id="search-bar-container"></div>
                    
                    <div class="search-panels">
                        <div id="simple-search" class="search-panel ${this.searchMode === 'simple' ? 'active' : ''}">
                            <!-- Simple search is just the search bar -->
                        </div>
                        
                        <div id="advanced-search" class="search-panel ${this.searchMode === 'advanced' ? 'active' : ''}">
                            <div class="advanced-filters">
                                <div class="filter-group">
                                    <label class="filter-label">File Types</label>
                                    <div class="file-type-filters">
                                        <label class="filter-checkbox">
                                            <input type="checkbox" value="image">
                                            <i data-lucide="image"></i>
                                            <span>Images</span>
                                        </label>
                                        <label class="filter-checkbox">
                                            <input type="checkbox" value="video">
                                            <i data-lucide="video"></i>
                                            <span>Videos</span>
                                        </label>
                                        <label class="filter-checkbox">
                                            <input type="checkbox" value="audio">
                                            <i data-lucide="music"></i>
                                            <span>Audio</span>
                                        </label>
                                        <label class="filter-checkbox">
                                            <input type="checkbox" value="document">
                                            <i data-lucide="file-text"></i>
                                            <span>Documents</span>
                                        </label>
                                        <label class="filter-checkbox">
                                            <input type="checkbox" value="archive">
                                            <i data-lucide="archive"></i>
                                            <span>Archives</span>
                                        </label>
                                        <label class="filter-checkbox">
                                            <input type="checkbox" value="code">
                                            <i data-lucide="code"></i>
                                            <span>Code</span>
                                        </label>
                                    </div>
                                </div>
                                
                                <div class="filter-group">
                                    <label class="filter-label">Date Range</label>
                                    <div class="date-range-filters">
                                        <select class="date-range-select">
                                            <option value="">Any time</option>
                                            <option value="today">Today</option>
                                            <option value="week">This week</option>
                                            <option value="month">This month</option>
                                            <option value="year">This year</option>
                                            <option value="custom">Custom range...</option>
                                        </select>
                                        <div class="custom-date-range" style="display: none;">
                                            <input type="date" class="date-from" placeholder="From">
                                            <input type="date" class="date-to" placeholder="To">
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="filter-group">
                                    <label class="filter-label">File Size</label>
                                    <div class="size-range-filters">
                                        <select class="size-range-select">
                                            <option value="">Any size</option>
                                            <option value="small">Small (< 1MB)</option>
                                            <option value="medium">Medium (1MB - 100MB)</option>
                                            <option value="large">Large (> 100MB)</option>
                                            <option value="custom">Custom range...</option>
                                        </select>
                                        <div class="custom-size-range" style="display: none;">
                                            <input type="number" class="size-from" placeholder="Min size (MB)">
                                            <input type="number" class="size-to" placeholder="Max size (MB)">
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="filter-group">
                                    <label class="filter-label">Tags</label>
                                    <div class="tags-filter">
                                        <input type="text" class="tags-input" placeholder="Enter tags...">
                                        <div class="selected-tags"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="semantic-search" class="search-panel ${this.searchMode === 'semantic' ? 'active' : ''}">
                            <div class="semantic-search-options">
                                <div class="search-quality">
                                    <label class="filter-label">Search Quality</label>
                                    <div class="quality-options">
                                        <label class="radio-option">
                                            <input type="radio" name="search-quality" value="fast" checked>
                                            <span>Fast</span>
                                            <small>Quick results with basic AI</small>
                                        </label>
                                        <label class="radio-option">
                                            <input type="radio" name="search-quality" value="balanced">
                                            <span>Balanced</span>
                                            <small>Good accuracy and speed</small>
                                        </label>
                                        <label class="radio-option">
                                            <input type="radio" name="search-quality" value="accurate">
                                            <span>Accurate</span>
                                            <small>Best results, slower processing</small>
                                        </label>
                                    </div>
                                </div>
                                
                                <div class="semantic-features">
                                    <label class="filter-checkbox">
                                        <input type="checkbox" checked>
                                        <span>Content understanding</span>
                                        <small>Analyze file contents for meaning</small>
                                    </label>
                                    <label class="filter-checkbox">
                                        <input type="checkbox" checked>
                                        <span>Context awareness</span>
                                        <small>Consider file relationships and context</small>
                                    </label>
                                    <label class="filter-checkbox">
                                        <input type="checkbox">
                                        <span>OCR text search</span>
                                        <small>Search text within images and PDFs</small>
                                    </label>
                                </div>
                            </div>
                        </div>
                        
                        <div id="visual-search" class="search-panel ${this.searchMode === 'visual' ? 'active' : ''}">
                            <div class="visual-search-options">
                                <div class="upload-area">
                                    <input type="file" id="visual-search-file" accept="image/*" style="display: none;">
                                    <label for="visual-search-file" class="upload-label">
                                        <i data-lucide="upload"></i>
                                        <span>Upload an image to find similar files</span>
                                        <small>Supports JPG, PNG, GIF, WebP</small>
                                    </label>
                                    <div class="uploaded-image" style="display: none;">
                                        <img class="preview-image" src="" alt="Search image">
                                        <button class="remove-image" title="Remove image">
                                            <i data-lucide="x"></i>
                                        </button>
                                    </div>
                                </div>
                                
                                <div class="similarity-threshold">
                                    <label class="filter-label">Similarity Threshold</label>
                                    <div class="threshold-slider">
                                        <input type="range" min="0" max="100" value="80" class="similarity-range">
                                        <span class="threshold-value">80%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="search-sidebar">
                    <div class="saved-searches">
                        <div class="sidebar-section">
                            <h3 class="sidebar-title">
                                <i data-lucide="bookmark"></i>
                                Saved Searches
                            </h3>
                            <div class="saved-searches-list">
                                <!-- Saved searches will be rendered here -->
                            </div>
                        </div>
                    </div>
                    
                    <div class="search-suggestions">
                        <div class="sidebar-section">
                            <h3 class="sidebar-title">
                                <i data-lucide="lightbulb"></i>
                                Suggestions
                            </h3>
                            <div class="suggestions-list">
                                <!-- Search suggestions will be rendered here -->
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="search-status">
                    <div class="status-info">
                        <span class="search-count">Ready to search</span>
                        <span class="search-time"></span>
                    </div>
                    <div class="search-progress" style="display: none;">
                        <div class="progress-bar">
                            <div class="progress-fill"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        await this.initializeComponents();
        this.setupEventListeners();
        this.renderSavedSearches();
        this.renderSuggestions();
    }
    
    async initializeComponents() {
        this.searchBar = new SearchBar({
            placeholder: 'Search your files...',
            onSearch: this.performSearch.bind(this),
            onFilter: this.updateFilters.bind(this),
            onClear: this.clearSearch.bind(this),
            showSuggestions: true,
            showHistory: true,
            showFilters: false
        });
        
        await this.searchBar.render(this.container.querySelector('#search-bar-container'));
    }
    
    setupEventListeners() {
        // Search mode buttons
        this.container.querySelectorAll('.search-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setSearchMode(btn.dataset.mode);
            });
        });
        
        // Save search button
        this.container.querySelector('.save-search').addEventListener('click', () => {
            this.saveCurrentSearch();
        });
        
        // Advanced filter changes
        this.setupAdvancedFilterListeners();
        
        // Visual search
        this.setupVisualSearchListeners();
        
        // Saved searches
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.saved-search-item')) {
                this.loadSavedSearch(e.target.closest('.saved-search-item'));
            }
        });
    }
    
    setupAdvancedFilterListeners() {
        const advancedPanel = this.container.querySelector('#advanced-search');
        
        // File type filters
        advancedPanel.querySelectorAll('.file-type-filters input').forEach(input => {
            input.addEventListener('change', () => {
                this.updateFileTypeFilters();
            });
        });
        
        // Date range filter
        const dateRangeSelect = advancedPanel.querySelector('.date-range-select');
        const customDateRange = advancedPanel.querySelector('.custom-date-range');
        
        dateRangeSelect.addEventListener('change', () => {
            const isCustom = dateRangeSelect.value === 'custom';
            customDateRange.style.display = isCustom ? 'flex' : 'none';
            this.updateDateRangeFilter();
        });
        
        customDateRange.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', () => {
                this.updateDateRangeFilter();
            });
        });
        
        // Size range filter
        const sizeRangeSelect = advancedPanel.querySelector('.size-range-select');
        const customSizeRange = advancedPanel.querySelector('.custom-size-range');
        
        sizeRangeSelect.addEventListener('change', () => {
            const isCustom = sizeRangeSelect.value === 'custom';
            customSizeRange.style.display = isCustom ? 'flex' : 'none';
            this.updateSizeRangeFilter();
        });
        
        customSizeRange.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', () => {
                this.updateSizeRangeFilter();
            });
        });
        
        // Tags filter
        const tagsInput = advancedPanel.querySelector('.tags-input');
        tagsInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                this.addTag(tagsInput.value.trim());
                tagsInput.value = '';
            }
        });
    }
    
    setupVisualSearchListeners() {
        const visualPanel = this.container.querySelector('#visual-search');
        const fileInput = visualPanel.querySelector('#visual-search-file');
        const uploadedImage = visualPanel.querySelector('.uploaded-image');
        const previewImage = visualPanel.querySelector('.preview-image');
        const removeButton = visualPanel.querySelector('.remove-image');
        const similarityRange = visualPanel.querySelector('.similarity-range');
        const thresholdValue = visualPanel.querySelector('.threshold-value');
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleVisualSearchImage(file, previewImage, uploadedImage);
            }
        });
        
        removeButton.addEventListener('click', () => {
            this.clearVisualSearchImage(fileInput, uploadedImage);
        });
        
        similarityRange.addEventListener('input', (e) => {
            thresholdValue.textContent = e.target.value + '%';
        });
    }
    
    initializeFuse() {
        this.fuseOptions = {
            keys: [
                { name: 'name', weight: 0.3 },
                { name: 'content', weight: 0.2 },
                { name: 'tags', weight: 0.2 },
                { name: 'metadata.description', weight: 0.1 },
                { name: 'path', weight: 0.1 },
                { name: 'metadata.keywords', weight: 0.1 }
            ],
            threshold: 0.3,
            includeScore: true,
            includeMatches: true,
            minMatchCharLength: 2
        };
    }
    
    setSearchMode(mode) {
        this.searchMode = mode;
        
        // Update active button
        this.container.querySelectorAll('.search-mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        
        // Update active panel
        this.container.querySelectorAll('.search-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `${mode}-search`);
        });
        
        // Update search bar placeholder based on mode
        const placeholders = {
            simple: 'Search your files...',
            advanced: 'Search with advanced filters...',
            semantic: 'Describe what you\'re looking for...',
            visual: 'Find visually similar files...'
        };
        
        if (this.searchBar) {
            this.searchBar.searchInput.placeholder = placeholders[mode];
        }
    }
    
    async performSearch(query, filters = {}) {
        if (!query && this.searchMode !== 'visual') {
            this.clearSearch();
            return;
        }
        
        this.setSearching(true);
        
        try {
            let results = [];
            
            switch (this.searchMode) {
                case 'simple':
                    results = await this.performSimpleSearch(query);
                    break;
                case 'advanced':
                    results = await this.performAdvancedSearch(query, this.searchFilters);
                    break;
                case 'semantic':
                    results = await this.performSemanticSearch(query);
                    break;
                case 'visual':
                    results = await this.performVisualSearch();
                    break;
            }
            
            this.searchResults = results;
            this.updateSearchStatus(results.length);
            this.onResults(results);
            
        } catch (error) {
            console.error('Search failed:', error);
            this.onError(error);
            NotificationManager.error('Search failed: ' + error.message);
        } finally {
            this.setSearching(false);
        }
    }
    
    async performSimpleSearch(query) {
        // Use Fuse.js for fast local search
        const searchData = await this.getSearchData();
        
        if (!this.fuseInstance) {
            this.fuseInstance = new Fuse(searchData, this.fuseOptions);
        }
        
        const fuseResults = this.fuseInstance.search(query);
        return fuseResults.map(result => ({
            ...result.item,
            score: result.score,
            matches: result.matches
        }));
    }
    
    async performAdvancedSearch(query, filters) {
        const params = {
            query: query,
            filters: filters,
            mode: 'advanced'
        };
        
        const response = await API.post('/search/advanced', params);
        return response.results || [];
    }
    
    async performSemanticSearch(query) {
        const qualitySettings = this.getSemanticQualitySettings();
        
        const params = {
            query: query,
            mode: 'semantic',
            quality: qualitySettings.quality,
            features: qualitySettings.features
        };
        
        const response = await API.post('/search/semantic', params);
        return response.results || [];
    }
    
    async performVisualSearch() {
        const imageFile = this.getVisualSearchImage();
        if (!imageFile) {
            throw new Error('No image provided for visual search');
        }
        
        const threshold = this.container.querySelector('.similarity-range').value;
        
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('threshold', threshold);
        formData.append('mode', 'visual');
        
        const response = await API.post('/search/visual', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        return response.results || [];
    }
    
    async getSearchData() {
        // This would typically come from a local cache or API
        try {
            const response = await API.get('/files/searchable');
            return response.files || [];
        } catch (error) {
            console.warn('Failed to load searchable data:', error);
            return [];
        }
    }
    
    getSemanticQualitySettings() {
        const semanticPanel = this.container.querySelector('#semantic-search');
        const qualityRadio = semanticPanel.querySelector('input[name="search-quality"]:checked');
        const featureCheckboxes = semanticPanel.querySelectorAll('.semantic-features input[type="checkbox"]');
        
        return {
            quality: qualityRadio ? qualityRadio.value : 'fast',
            features: Array.from(featureCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.nextElementSibling.textContent.trim())
        };
    }
    
    updateFileTypeFilters() {
        const checkedTypes = Array.from(
            this.container.querySelectorAll('.file-type-filters input:checked')
        ).map(input => input.value);
        
        this.searchFilters.fileTypes = checkedTypes;
        this.triggerFilteredSearch();
    }
    
    updateDateRangeFilter() {
        const dateRangeSelect = this.container.querySelector('.date-range-select');
        const customDateRange = this.container.querySelector('.custom-date-range');
        
        if (dateRangeSelect.value === 'custom') {
            const fromDate = customDateRange.querySelector('.date-from').value;
            const toDate = customDateRange.querySelector('.date-to').value;
            
            this.searchFilters.dateRange = {
                from: fromDate,
                to: toDate
            };
        } else if (dateRangeSelect.value) {
            this.searchFilters.dateRange = dateRangeSelect.value;
        } else {
            this.searchFilters.dateRange = null;
        }
        
        this.triggerFilteredSearch();
    }
    
    updateSizeRangeFilter() {
        const sizeRangeSelect = this.container.querySelector('.size-range-select');
        const customSizeRange = this.container.querySelector('.custom-size-range');
        
        if (sizeRangeSelect.value === 'custom') {
            const fromSize = customSizeRange.querySelector('.size-from').value;
            const toSize = customSizeRange.querySelector('.size-to').value;
            
            this.searchFilters.sizeRange = {
                from: fromSize ? parseInt(fromSize) * 1024 * 1024 : null,
                to: toSize ? parseInt(toSize) * 1024 * 1024 : null
            };
        } else if (sizeRangeSelect.value) {
            this.searchFilters.sizeRange = sizeRangeSelect.value;
        } else {
            this.searchFilters.sizeRange = null;
        }
        
        this.triggerFilteredSearch();
    }
    
    addTag(tag) {
        if (!tag || this.searchFilters.tags.includes(tag)) return;
        
        this.searchFilters.tags.push(tag);
        this.renderSelectedTags();
        this.triggerFilteredSearch();
    }
    
    removeTag(tag) {
        this.searchFilters.tags = this.searchFilters.tags.filter(t => t !== tag);
        this.renderSelectedTags();
        this.triggerFilteredSearch();
    }
    
    renderSelectedTags() {
        const selectedTagsContainer = this.container.querySelector('.selected-tags');
        
        const html = this.searchFilters.tags.map(tag => `
            <span class="selected-tag">
                ${tag}
                <button class="remove-tag" data-tag="${tag}">
                    <i data-lucide="x"></i>
                </button>
            </span>
        `).join('');
        
        selectedTagsContainer.innerHTML = html;
        
        selectedTagsContainer.querySelectorAll('.remove-tag').forEach(btn => {
            btn.addEventListener('click', () => {
                this.removeTag(btn.dataset.tag);
            });
        });
    }
    
    triggerFilteredSearch() {
        const query = this.searchBar.getValue();
        if (query || this.hasActiveFilters()) {
            this.performSearch(query);
        }
    }
    
    hasActiveFilters() {
        return this.searchFilters.fileTypes.length > 0 ||
               this.searchFilters.dateRange ||
               this.searchFilters.sizeRange ||
               this.searchFilters.tags.length > 0;
    }
    
    handleVisualSearchImage(file, previewImage, uploadedImage) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadedImage.style.display = 'block';
            uploadedImage.previousElementSibling.style.display = 'none';
        };
        reader.readAsDataURL(file);
        
        // Store file for search
        this.visualSearchFile = file;
    }
    
    clearVisualSearchImage(fileInput, uploadedImage) {
        fileInput.value = '';
        uploadedImage.style.display = 'none';
        uploadedImage.previousElementSibling.style.display = 'block';
        this.visualSearchFile = null;
    }
    
    getVisualSearchImage() {
        return this.visualSearchFile;
    }
    
    updateFilters(filters) {
        // Handle filters from search bar
        Object.assign(this.searchFilters, filters);
    }
    
    clearSearch() {
        this.searchResults = [];
        this.onResults([]);
        this.updateSearchStatus(0);
    }
    
    setSearching(searching) {
        this.isSearching = searching;
        
        const progressBar = this.container.querySelector('.search-progress');
        const statusInfo = this.container.querySelector('.status-info');
        
        if (searching) {
            progressBar.style.display = 'block';
            statusInfo.querySelector('.search-count').textContent = 'Searching...';
            this.container.classList.add('searching');
        } else {
            progressBar.style.display = 'none';
            this.container.classList.remove('searching');
        }
    }
    
    updateSearchStatus(resultCount) {
        const countEl = this.container.querySelector('.search-count');
        const timeEl = this.container.querySelector('.search-time');
        
        if (resultCount === 0) {
            countEl.textContent = 'No results found';
        } else if (resultCount === 1) {
            countEl.textContent = '1 result';
        } else {
            countEl.textContent = `${resultCount} results`;
        }
        
        // Show search time (would be calculated from actual search)
        timeEl.textContent = '(0.3s)';
    }
    
    saveCurrentSearch() {
        const query = this.searchBar.getValue();
        if (!query) return;
        
        const name = prompt('Enter a name for this search:');
        if (!name) return;
        
        const savedSearch = {
            id: Date.now().toString(),
            name: name,
            query: query,
            mode: this.searchMode,
            filters: { ...this.searchFilters },
            timestamp: Date.now()
        };
        
        this.savedSearches.unshift(savedSearch);
        this.savedSearches = this.savedSearches.slice(0, 10); // Limit to 10
        
        this.saveSavedSearches();
        this.renderSavedSearches();
        
        NotificationManager.success('Search saved successfully');
    }
    
    loadSavedSearch(searchItem) {
        const searchId = searchItem.dataset.id;
        const savedSearch = this.savedSearches.find(s => s.id === searchId);
        
        if (!savedSearch) return;
        
        this.setSearchMode(savedSearch.mode);
        this.searchBar.setValue(savedSearch.query);
        this.searchFilters = { ...savedSearch.filters };
        
        // Update UI to reflect loaded filters
        this.applyFiltersToUI();
        
        this.performSearch(savedSearch.query);
    }
    
    applyFiltersToUI() {
        // Apply file type filters
        this.container.querySelectorAll('.file-type-filters input').forEach(input => {
            input.checked = this.searchFilters.fileTypes.includes(input.value);
        });
        
        // Apply other filters...
        this.renderSelectedTags();
    }
    
    renderSavedSearches() {
        const container = this.container.querySelector('.saved-searches-list');
        
        if (this.savedSearches.length === 0) {
            container.innerHTML = '<p class="empty-message">No saved searches</p>';
            return;
        }
        
        const html = this.savedSearches.map(search => `
            <div class="saved-search-item" data-id="${search.id}">
                <div class="search-info">
                    <div class="search-name">${search.name}</div>
                    <div class="search-query">"${search.query}"</div>
                    <div class="search-meta">${search.mode} • ${this.formatTimestamp(search.timestamp)}</div>
                </div>
                <button class="remove-saved-search" data-id="${search.id}" title="Remove">
                    <i data-lucide="trash-2"></i>
                </button>
            </div>
        `).join('');
        
        container.innerHTML = html;
        
        // Setup remove buttons
        container.querySelectorAll('.remove-saved-search').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeSavedSearch(btn.dataset.id);
            });
        });
    }
    
    removeSavedSearch(searchId) {
        this.savedSearches = this.savedSearches.filter(s => s.id !== searchId);
        this.saveSavedSearches();
        this.renderSavedSearches();
    }
    
    renderSuggestions() {
        const container = this.container.querySelector('.suggestions-list');
        
        const suggestions = [
            'Recent files',
            'Large files',
            'Untagged files',
            'Duplicate files',
            'Files without thumbnails'
        ];
        
        const html = suggestions.map(suggestion => `
            <div class="suggestion-item" data-query="${suggestion}">
                <i data-lucide="search"></i>
                <span>${suggestion}</span>
            </div>
        `).join('');
        
        container.innerHTML = html;
        
        container.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                this.searchBar.setValue(item.dataset.query);
                this.performSearch(item.dataset.query);
            });
        });
    }
    
    loadSavedSearches() {
        try {
            const stored = localStorage.getItem('savedSearches');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }
    
    saveSavedSearches() {
        try {
            localStorage.setItem('savedSearches', JSON.stringify(this.savedSearches));
        } catch {
            // Ignore storage errors
        }
    }
    
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        
        return date.toLocaleDateString();
    }
    
    getResults() {
        return this.searchResults;
    }
    
    getFilters() {
        return { ...this.searchFilters };
    }
    
    focus() {
        if (this.searchBar) {
            this.searchBar.focus();
        }
    }
}