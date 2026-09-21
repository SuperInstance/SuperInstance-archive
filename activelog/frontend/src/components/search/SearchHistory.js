/**
 * Search History Management Component
 */

export class SearchHistory {
    constructor() {
        this.maxHistoryItems = 50;
        this.storageKey = 'activelog_search_history';
        this.history = this.loadHistory();
    }

    loadHistory() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            return stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.error('Failed to load search history:', error);
            return [];
        }
    }

    saveHistory() {
        try {
            // Keep only the most recent items
            const historyToSave = this.history.slice(0, this.maxHistoryItems);
            localStorage.setItem(this.storageKey, JSON.stringify(historyToSave));
        } catch (error) {
            console.error('Failed to save search history:', error);
        }
    }

    async addSearch(query, resultCount = 0, filters = {}) {
        const searchItem = {
            id: Date.now().toString(),
            query: query.trim(),
            resultCount,
            filters,
            timestamp: new Date().toISOString(),
            frequency: 1
        };

        // Check if this exact query already exists
        const existingIndex = this.history.findIndex(item => 
            item.query.toLowerCase() === query.toLowerCase()
        );

        if (existingIndex !== -1) {
            // Update existing item
            const existing = this.history[existingIndex];
            existing.frequency += 1;
            existing.timestamp = searchItem.timestamp;
            existing.resultCount = resultCount;
            
            // Move to front
            this.history.splice(existingIndex, 1);
            this.history.unshift(existing);
        } else {
            // Add new item to front
            this.history.unshift(searchItem);
        }

        this.saveHistory();
    }

    async removeSearch(searchId) {
        this.history = this.history.filter(item => item.id !== searchId);
        this.saveHistory();
    }

    async clearHistory() {
        this.history = [];
        this.saveHistory();
    }

    getRecentSearches(limit = 10) {
        return this.history
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, limit);
    }

    getPopularSearches(limit = 5) {
        return this.history
            .sort((a, b) => b.frequency - a.frequency)
            .slice(0, limit);
    }

    searchHistory(query) {
        const searchTerm = query.toLowerCase();
        return this.history.filter(item =>
            item.query.toLowerCase().includes(searchTerm)
        );
    }

    async render(container) {
        const recentSearches = this.getRecentSearches();
        
        if (recentSearches.length === 0) {
            container.innerHTML = `
                <div class="history-empty">
                    <div class="empty-icon">🔍</div>
                    <p>No search history yet</p>
                    <span class="empty-hint">Your recent searches will appear here</span>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="search-history-container">
                <div class="history-header">
                    <span class="history-count">${recentSearches.length} recent searches</span>
                    <button class="clear-history-btn" id="clear-history">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18"/>
                            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
                            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
                
                <div class="history-list">
                    ${recentSearches.map(item => this.renderHistoryItem(item)).join('')}
                </div>
            </div>
        `;

        this.attachEventListeners(container);
    }

    renderHistoryItem(item) {
        const timeAgo = this.getTimeAgo(item.timestamp);
        const hasFilters = Object.keys(item.filters || {}).length > 0;
        
        return `
            <div class="history-item" data-search-id="${item.id}">
                <div class="history-main">
                    <div class="history-query" title="${item.query}">${item.query}</div>
                    <div class="history-meta">
                        <span class="history-time">${timeAgo}</span>
                        <span class="history-results">${item.resultCount} results</span>
                        ${item.frequency > 1 ? `<span class="history-frequency">${item.frequency}x</span>` : ''}
                        ${hasFilters ? '<span class="history-filters">📌</span>' : ''}
                    </div>
                </div>
                <div class="history-actions">
                    <button class="history-action-btn repeat-search" title="Repeat search">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                            <path d="M21 3v5h-5"/>
                            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                            <path d="M3 21v-5h5"/>
                        </svg>
                    </button>
                    <button class="history-action-btn remove-search" title="Remove from history">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    attachEventListeners(container) {
        // Clear all history
        const clearBtn = container.querySelector('#clear-history');
        clearBtn?.addEventListener('click', async () => {
            const confirmed = confirm('Clear all search history?');
            if (confirmed) {
                await this.clearHistory();
                await this.render(container);
            }
        });

        // Repeat search
        container.querySelectorAll('.repeat-search').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const searchId = e.target.closest('.history-item').dataset.searchId;
                const item = this.history.find(h => h.id === searchId);
                if (item) {
                    this.repeatSearch(item);
                }
            });
        });

        // Remove search
        container.querySelectorAll('.remove-search').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.stopPropagation();
                const searchId = e.target.closest('.history-item').dataset.searchId;
                await this.removeSearch(searchId);
                await this.render(container);
            });
        });

        // Click on history item to repeat search
        container.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                const searchId = item.dataset.searchId;
                const historyItem = this.history.find(h => h.id === searchId);
                if (historyItem) {
                    this.repeatSearch(historyItem);
                }
            });
        });
    }

    repeatSearch(historyItem) {
        // Fill search input
        const searchInput = document.getElementById('semantic-search-input');
        if (searchInput) {
            searchInput.value = historyItem.query;
        }

        // Apply filters if they exist
        if (historyItem.filters) {
            this.applyFilters(historyItem.filters);
        }

        // Trigger search
        import('../search/SemanticSearch.js').then(module => {
            // Emit event to trigger search
            document.dispatchEvent(new CustomEvent('repeatSearch', {
                detail: { query: historyItem.query, filters: historyItem.filters }
            }));
        });
    }

    applyFilters(filters) {
        // Apply file type filters
        if (filters.fileTypes) {
            filters.fileTypes.forEach(type => {
                const checkbox = document.querySelector(`input[value="${type}"].file-type-filter`);
                if (checkbox) checkbox.checked = true;
            });
        }

        // Apply similarity threshold
        if (filters.similarity) {
            const slider = document.getElementById('similarity-slider');
            const value = document.getElementById('similarity-value');
            if (slider && value) {
                slider.value = filters.similarity * 100;
                value.textContent = `${Math.round(filters.similarity * 100)}%`;
            }
        }

        // Apply date range
        if (filters.dateRange) {
            const fromInput = document.getElementById('date-from');
            const toInput = document.getElementById('date-to');
            if (fromInput && toInput) {
                fromInput.value = filters.dateRange.from;
                toInput.value = filters.dateRange.to;
            }
        }
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const past = new Date(timestamp);
        const diffInSeconds = Math.floor((now - past) / 1000);

        if (diffInSeconds < 60) {
            return 'Just now';
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes}m ago`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours}h ago`;
        } else if (diffInSeconds < 604800) {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days}d ago`;
        } else {
            return past.toLocaleDateString();
        }
    }

    getSearchTrends() {
        const trends = {};
        this.history.forEach(item => {
            const words = item.query.toLowerCase().split(/\s+/);
            words.forEach(word => {
                if (word.length > 2) {
                    trends[word] = (trends[word] || 0) + item.frequency;
                }
            });
        });

        return Object.entries(trends)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([word, count]) => ({ word, count }));
    }

    exportHistory() {
        const exportData = {
            exported_at: new Date().toISOString(),
            total_searches: this.history.length,
            searches: this.history
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `activelog-search-history-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        URL.revokeObjectURL(url);
    }

    async importHistory(file) {
        try {
            const text = await file.text();
            const data = JSON.parse(text);
            
            if (data.searches && Array.isArray(data.searches)) {
                // Merge with existing history
                const existingQueries = new Set(this.history.map(h => h.query.toLowerCase()));
                
                const newItems = data.searches.filter(item => 
                    !existingQueries.has(item.query.toLowerCase())
                );
                
                this.history = [...newItems, ...this.history];
                this.saveHistory();
                
                return {
                    success: true,
                    imported: newItems.length,
                    total: data.searches.length
                };
            } else {
                throw new Error('Invalid history file format');
            }
        } catch (error) {
            console.error('Failed to import history:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
}