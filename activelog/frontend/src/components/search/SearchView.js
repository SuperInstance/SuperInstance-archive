/**
 * Search View Component
 */

export class SearchView {
    constructor() {
        this.searchResults = [];
        this.currentQuery = '';
        this.searchType = 'all';
    }

    async render(container) {
        container.innerHTML = `
            <div class="search-view">
                <div class="search-header">
                    <h2>Search & Discovery</h2>
                    <div class="search-stats" id="search-stats"></div>
                </div>
                
                <div class="search-controls">
                    <div class="search-input-container">
                        <input type="text" id="main-search" placeholder="Search files, content, tags..." class="main-search-input">
                        <button id="search-btn" class="search-button">Search</button>
                    </div>
                    
                    <div class="search-filters">
                        <select id="search-type" class="filter-select">
                            <option value="all">All Content</option>
                            <option value="files">Files Only</option>
                            <option value="content">Content</option>
                            <option value="tags">Tags</option>
                        </select>
                        
                        <select id="sort-by" class="filter-select">
                            <option value="relevance">Relevance</option>
                            <option value="date">Date Modified</option>
                            <option value="name">Name</option>
                            <option value="size">Size</option>
                        </select>
                        
                        <button id="advanced-search-btn" class="btn-secondary">Advanced</button>
                    </div>
                </div>
                
                <div class="search-results-container">
                    <div class="results-sidebar">
                        <h4>Search Filters</h4>
                        <div class="filter-group">
                            <h5>File Types</h5>
                            <div class="checkbox-group" id="file-type-filters">
                                <label><input type="checkbox" value="documents"> Documents</label>
                                <label><input type="checkbox" value="images"> Images</label>
                                <label><input type="checkbox" value="videos"> Videos</label>
                                <label><input type="checkbox" value="code"> Code</label>
                            </div>
                        </div>
                        
                        <div class="filter-group">
                            <h5>Date Range</h5>
                            <select id="date-filter" class="filter-select">
                                <option value="">Any Time</option>
                                <option value="today">Today</option>
                                <option value="week">This Week</option>
                                <option value="month">This Month</option>
                                <option value="year">This Year</option>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <h5>Size</h5>
                            <select id="size-filter" class="filter-select">
                                <option value="">Any Size</option>
                                <option value="small">Small (< 1MB)</option>
                                <option value="medium">Medium (1-10MB)</option>
                                <option value="large">Large (> 10MB)</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="search-results" id="search-results">
                        <div class="empty-search">
                            <div class="empty-icon">🔍</div>
                            <h3>Start Your Search</h3>
                            <p>Enter a search term to find files, content, and more</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>
                .search-view {
                    padding: 20px;
                    max-width: 1400px;
                    margin: 0 auto;
                    height: calc(100vh - 40px);
                    display: flex;
                    flex-direction: column;
                }
                
                .search-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e9ecef;
                }
                
                .search-stats {
                    color: #666;
                    font-size: 14px;
                }
                
                .search-controls {
                    margin-bottom: 30px;
                }
                
                .search-input-container {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 15px;
                }
                
                .main-search-input {
                    flex: 1;
                    padding: 15px 20px;
                    border: 2px solid #ddd;
                    border-radius: 12px;
                    font-size: 16px;
                    transition: border-color 0.2s;
                }
                
                .main-search-input:focus {
                    border-color: #007bff;
                    outline: none;
                }
                
                .search-button {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 12px;
                    cursor: pointer;
                    font-size: 16px;
                    transition: background 0.2s;
                }
                
                .search-button:hover {
                    background: #0056b3;
                }
                
                .search-filters {
                    display: flex;
                    gap: 15px;
                    align-items: center;
                    flex-wrap: wrap;
                }
                
                .filter-select {
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                }
                
                .btn-secondary {
                    background: #6c757d;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                .search-results-container {
                    display: flex;
                    gap: 20px;
                    flex: 1;
                    overflow: hidden;
                }
                
                .results-sidebar {
                    width: 250px;
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 12px;
                    height: fit-content;
                }
                
                .filter-group {
                    margin-bottom: 25px;
                }
                
                .filter-group h5 {
                    margin: 0 0 10px 0;
                    font-weight: 600;
                    color: #333;
                }
                
                .checkbox-group {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .checkbox-group label {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 14px;
                    cursor: pointer;
                }
                
                .search-results {
                    flex: 1;
                    overflow-y: auto;
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                }
                
                .empty-search {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 400px;
                    text-align: center;
                }
                
                .empty-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                }
                
                .empty-search h3 {
                    margin: 0 0 10px 0;
                    color: #333;
                }
                
                .empty-search p {
                    color: #666;
                    margin: 0;
                }
                
                .search-result-item {
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 10px;
                    transition: box-shadow 0.2s;
                }
                
                .search-result-item:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .result-title {
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 5px;
                    cursor: pointer;
                }
                
                .result-path {
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 8px;
                }
                
                .result-preview {
                    color: #333;
                    line-height: 1.4;
                    margin-bottom: 10px;
                }
                
                .result-meta {
                    font-size: 12px;
                    color: #888;
                    display: flex;
                    gap: 15px;
                }
                
                .loading-state {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 200px;
                    font-size: 18px;
                    color: #666;
                }
                
                @media (max-width: 768px) {
                    .search-results-container {
                        flex-direction: column;
                    }
                    
                    .results-sidebar {
                        width: 100%;
                        order: 2;
                    }
                    
                    .search-filters {
                        flex-direction: column;
                        align-items: stretch;
                    }
                }
            </style>
        `;

        this.setupEventListeners();
    }

    setupEventListeners() {
        const searchInput = document.getElementById('main-search');
        const searchBtn = document.getElementById('search-btn');
        const searchType = document.getElementById('search-type');
        
        searchBtn.addEventListener('click', () => this.performSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
        
        searchType.addEventListener('change', () => {
            if (this.currentQuery) {
                this.performSearch();
            }
        });

        // Filter change listeners
        document.querySelectorAll('.filter-select, input[type="checkbox"]').forEach(element => {
            element.addEventListener('change', () => {
                if (this.currentQuery) {
                    this.performSearch();
                }
            });
        });
    }

    async performSearch() {
        const query = document.getElementById('main-search').value.trim();
        const searchType = document.getElementById('search-type').value;
        
        if (!query) {
            return;
        }
        
        this.currentQuery = query;
        this.searchType = searchType;
        
        this.showLoadingState();
        
        try {
            // Simulate search API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Mock search results
            this.searchResults = this.generateMockResults(query, searchType);
            this.renderSearchResults();
            this.updateSearchStats();
            
        } catch (error) {
            console.error('Search failed:', error);
            this.showErrorState();
        }
    }

    generateMockResults(query, type) {
        const mockResults = [
            {
                title: `Document containing "${query}"`,
                path: '/documents/reports/analysis.pdf',
                preview: `This document contains several references to ${query} and provides detailed analysis...`,
                type: 'document',
                size: '2.5MB',
                modified: '2 days ago',
                relevance: 0.95
            },
            {
                title: `Project file with ${query}`,
                path: '/projects/webapp/src/components/search.js',
                preview: `// Implementation of ${query} functionality\nconst searchHandler = () => {...`,
                type: 'code',
                size: '15KB',
                modified: '5 hours ago',
                relevance: 0.87
            },
            {
                title: `Image tagged with ${query}`,
                path: '/media/images/screenshot-2024.png',
                preview: 'Screenshot showing application interface',
                type: 'image',
                size: '1.2MB',
                modified: '1 week ago',
                relevance: 0.72
            }
        ];

        return mockResults.filter(result => {
            if (type === 'all') return true;
            return result.type === type;
        }).slice(0, 10);
    }

    showLoadingState() {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = `
            <div class="loading-state">
                <div>🔍 Searching...</div>
            </div>
        `;
    }

    showErrorState() {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = `
            <div class="empty-search">
                <div class="empty-icon">⚠️</div>
                <h3>Search Failed</h3>
                <p>There was an error performing your search. Please try again.</p>
            </div>
        `;
    }

    renderSearchResults() {
        const resultsContainer = document.getElementById('search-results');
        
        if (this.searchResults.length === 0) {
            resultsContainer.innerHTML = `
                <div class="empty-search">
                    <div class="empty-icon">📝</div>
                    <h3>No Results Found</h3>
                    <p>Try adjusting your search terms or filters</p>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = this.searchResults.map(result => `
            <div class="search-result-item">
                <div class="result-title">${result.title}</div>
                <div class="result-path">${result.path}</div>
                <div class="result-preview">${result.preview}</div>
                <div class="result-meta">
                    <span>Type: ${result.type}</span>
                    <span>Size: ${result.size}</span>
                    <span>Modified: ${result.modified}</span>
                    <span>Relevance: ${Math.round(result.relevance * 100)}%</span>
                </div>
            </div>
        `).join('');
    }

    updateSearchStats() {
        const statsElement = document.getElementById('search-stats');
        const totalResults = this.searchResults.length;
        const searchTime = '0.12 seconds'; // Mock timing
        
        statsElement.textContent = `${totalResults} results found in ${searchTime}`;
    }
}