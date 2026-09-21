/**
 * Advanced Search Bar Component
 */

export class SearchBar {
    constructor(options = {}) {
        this.container = null;
        this.searchInput = null;
        this.searchDropdown = null;
        
        this.placeholder = options.placeholder || 'Search...';
        this.debounce = options.debounce || 300;
        this.minSearchLength = options.minSearchLength || 1;
        this.showSuggestions = options.showSuggestions !== false;
        this.showHistory = options.showHistory !== false;
        this.showFilters = options.showFilters !== false;
        
        this.onSearch = options.onSearch || (() => {});
        this.onFilter = options.onFilter || (() => {});
        this.onClear = options.onClear || (() => {});
        
        this.searchHistory = this.loadSearchHistory();
        this.suggestions = [];
        this.filters = {};
        this.currentQuery = '';
        
        this.debounceTimer = null;
        this.isDropdownOpen = false;
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="search-bar">
                <div class="search-input-container">
                    <div class="search-input-wrapper">
                        <i class="search-icon" data-lucide="search"></i>
                        <input type="text" 
                               class="search-input" 
                               placeholder="${this.placeholder}"
                               autocomplete="off"
                               spellcheck="false">
                        <button class="search-clear" style="display: none;" title="Clear search">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    
                    ${this.showFilters ? `
                        <button class="search-filters-toggle" title="Search filters">
                            <i data-lucide="filter"></i>
                        </button>
                    ` : ''}
                </div>
                
                <div class="search-dropdown" style="display: none;">
                    <div class="search-suggestions"></div>
                    <div class="search-history"></div>
                    ${this.showFilters ? '<div class="search-filters"></div>' : ''}
                </div>
            </div>
        `;
        
        this.setupElements();
        this.setupEventListeners();
        this.renderHistory();
        
        if (this.showFilters) {
            this.renderFilters();
        }
    }
    
    setupElements() {
        this.searchInput = this.container.querySelector('.search-input');
        this.searchClear = this.container.querySelector('.search-clear');
        this.searchDropdown = this.container.querySelector('.search-dropdown');
        this.suggestionsContainer = this.container.querySelector('.search-suggestions');
        this.historyContainer = this.container.querySelector('.search-history');
        this.filtersContainer = this.container.querySelector('.search-filters');
        this.filtersToggle = this.container.querySelector('.search-filters-toggle');
    }
    
    setupEventListeners() {
        // Search input events
        this.searchInput.addEventListener('input', this.handleInput.bind(this));
        this.searchInput.addEventListener('keydown', this.handleKeyDown.bind(this));
        this.searchInput.addEventListener('focus', this.handleFocus.bind(this));
        this.searchInput.addEventListener('blur', this.handleBlur.bind(this));
        
        // Clear button
        this.searchClear.addEventListener('click', this.clearSearch.bind(this));
        
        // Filters toggle
        if (this.filtersToggle) {
            this.filtersToggle.addEventListener('click', this.toggleFilters.bind(this));
        }
        
        // Dropdown events
        this.searchDropdown.addEventListener('click', this.handleDropdownClick.bind(this));
        this.searchDropdown.addEventListener('mousedown', (e) => e.preventDefault());
        
        // Outside click to close dropdown
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.closeDropdown();
            }
        });
    }
    
    handleInput(e) {
        const query = e.target.value;
        this.currentQuery = query;
        
        // Show/hide clear button
        this.searchClear.style.display = query ? 'flex' : 'none';
        
        // Debounced search
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.performSearch(query);
        }, this.debounce);
        
        // Update suggestions
        if (query.length >= this.minSearchLength && this.showSuggestions) {
            this.updateSuggestions(query);
        }
        
        // Show dropdown if query exists
        if (query) {
            this.openDropdown();
        } else {
            this.renderHistory();
            if (this.searchHistory.length > 0) {
                this.openDropdown();
            } else {
                this.closeDropdown();
            }
        }
    }
    
    handleKeyDown(e) {
        switch (e.key) {
            case 'Enter':
                e.preventDefault();
                this.submitSearch();
                break;
            case 'Escape':
                this.closeDropdown();
                this.searchInput.blur();
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.navigateDropdown('down');
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateDropdown('up');
                break;
        }
    }
    
    handleFocus(e) {
        if (this.currentQuery || this.searchHistory.length > 0) {
            this.openDropdown();
        }
    }
    
    handleBlur(e) {
        // Delay to allow dropdown clicks
        setTimeout(() => {
            if (!this.container.contains(document.activeElement)) {
                this.closeDropdown();
            }
        }, 150);
    }
    
    handleDropdownClick(e) {
        const suggestionItem = e.target.closest('.suggestion-item');
        const historyItem = e.target.closest('.history-item');
        const filterItem = e.target.closest('.filter-item');
        
        if (suggestionItem) {
            const query = suggestionItem.dataset.query;
            this.selectSuggestion(query);
        } else if (historyItem) {
            const query = historyItem.dataset.query;
            this.selectHistory(query);
        } else if (filterItem) {
            this.toggleFilter(filterItem);
        }
    }
    
    performSearch(query) {
        if (query.length < this.minSearchLength) {
            this.onClear();
            return;
        }
        
        this.onSearch(query, this.filters);
    }
    
    submitSearch() {
        const query = this.searchInput.value.trim();
        
        if (query && query.length >= this.minSearchLength) {
            this.addToHistory(query);
            this.performSearch(query);
            this.closeDropdown();
        }
    }
    
    selectSuggestion(query) {
        this.searchInput.value = query;
        this.currentQuery = query;
        this.searchClear.style.display = 'flex';
        this.submitSearch();
    }
    
    selectHistory(query) {
        this.searchInput.value = query;
        this.currentQuery = query;
        this.searchClear.style.display = 'flex';
        this.submitSearch();
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.currentQuery = '';
        this.searchClear.style.display = 'none';
        this.closeDropdown();
        this.onClear();
        this.searchInput.focus();
    }
    
    openDropdown() {
        if (this.isDropdownOpen) return;
        
        this.isDropdownOpen = true;
        this.searchDropdown.style.display = 'block';
        this.container.classList.add('dropdown-open');
        
        // Position dropdown
        this.positionDropdown();
    }
    
    closeDropdown() {
        if (!this.isDropdownOpen) return;
        
        this.isDropdownOpen = false;
        this.searchDropdown.style.display = 'none';
        this.container.classList.remove('dropdown-open');
    }
    
    positionDropdown() {
        const inputRect = this.searchInput.getBoundingClientRect();
        const dropdownRect = this.searchDropdown.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        
        // Check if dropdown fits below input
        const spaceBelow = viewportHeight - inputRect.bottom;
        const spaceAbove = inputRect.top;
        
        if (spaceBelow >= dropdownRect.height || spaceBelow >= spaceAbove) {
            // Show below
            this.searchDropdown.style.top = '100%';
            this.searchDropdown.style.bottom = 'auto';
        } else {
            // Show above
            this.searchDropdown.style.top = 'auto';
            this.searchDropdown.style.bottom = '100%';
        }
    }
    
    navigateDropdown(direction) {
        const items = this.searchDropdown.querySelectorAll('.suggestion-item, .history-item');
        const activeItem = this.searchDropdown.querySelector('.dropdown-item-active');
        
        let newIndex = -1;
        
        if (activeItem) {
            const currentIndex = Array.from(items).indexOf(activeItem);
            if (direction === 'down') {
                newIndex = Math.min(currentIndex + 1, items.length - 1);
            } else {
                newIndex = Math.max(currentIndex - 1, 0);
            }
        } else {
            newIndex = direction === 'down' ? 0 : items.length - 1;
        }
        
        // Remove active class from all items
        items.forEach(item => item.classList.remove('dropdown-item-active'));
        
        // Add active class to new item
        if (items[newIndex]) {
            items[newIndex].classList.add('dropdown-item-active');
            items[newIndex].scrollIntoView({ block: 'nearest' });
            
            // Update input value with selected item
            const query = items[newIndex].dataset.query;
            if (query) {
                this.searchInput.value = query;
            }
        }
    }
    
    updateSuggestions(query) {
        // This would typically fetch suggestions from an API
        // For now, we'll generate some basic suggestions
        const suggestions = this.generateSuggestions(query);
        this.renderSuggestions(suggestions);
    }
    
    generateSuggestions(query) {
        // Basic suggestion generation - in a real app, this would come from an API
        const commonTerms = [
            'documents', 'images', 'videos', 'audio', 'presentations',
            'spreadsheets', 'pdfs', 'photos', 'music', 'movies'
        ];
        
        return commonTerms
            .filter(term => term.toLowerCase().includes(query.toLowerCase()))
            .slice(0, 5)
            .map(term => ({
                query: term,
                type: 'suggestion',
                highlight: this.highlightMatch(term, query)
            }));
    }
    
    highlightMatch(text, query) {
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    renderSuggestions(suggestions) {
        if (!this.suggestionsContainer) return;
        
        if (suggestions.length === 0) {
            this.suggestionsContainer.innerHTML = '';
            return;
        }
        
        const html = `
            <div class="dropdown-section">
                <div class="dropdown-section-header">
                    <i data-lucide="search"></i>
                    <span>Suggestions</span>
                </div>
                <div class="dropdown-section-content">
                    ${suggestions.map(suggestion => `
                        <div class="dropdown-item suggestion-item" data-query="${suggestion.query}">
                            <i data-lucide="search" class="item-icon"></i>
                            <span class="item-text">${suggestion.highlight}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        this.suggestionsContainer.innerHTML = html;
    }
    
    renderHistory() {
        if (!this.historyContainer || !this.showHistory) return;
        
        if (this.searchHistory.length === 0) {
            this.historyContainer.innerHTML = '';
            return;
        }
        
        const html = `
            <div class="dropdown-section">
                <div class="dropdown-section-header">
                    <i data-lucide="clock"></i>
                    <span>Recent Searches</span>
                    <button class="clear-history-btn" title="Clear history">
                        <i data-lucide="trash-2"></i>
                    </button>
                </div>
                <div class="dropdown-section-content">
                    ${this.searchHistory.slice(0, 5).map(item => `
                        <div class="dropdown-item history-item" data-query="${item.query}">
                            <i data-lucide="clock" class="item-icon"></i>
                            <span class="item-text">${item.query}</span>
                            <span class="item-time">${this.formatTime(item.timestamp)}</span>
                            <button class="remove-history-item" data-query="${item.query}" title="Remove">
                                <i data-lucide="x"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        this.historyContainer.innerHTML = html;
        
        // Setup history event listeners
        this.historyContainer.querySelector('.clear-history-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.clearHistory();
        });
        
        this.historyContainer.querySelectorAll('.remove-history-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeFromHistory(btn.dataset.query);
            });
        });
    }
    
    renderFilters() {
        if (!this.filtersContainer || !this.showFilters) return;
        
        const filterOptions = [
            { key: 'type', label: 'File Type', options: ['images', 'videos', 'documents', 'audio'] },
            { key: 'date', label: 'Date Range', options: ['today', 'week', 'month', 'year'] },
            { key: 'size', label: 'File Size', options: ['small', 'medium', 'large'] },
            { key: 'location', label: 'Location', options: ['desktop', 'documents', 'downloads'] }
        ];
        
        const html = `
            <div class="dropdown-section">
                <div class="dropdown-section-header">
                    <i data-lucide="filter"></i>
                    <span>Filters</span>
                    <button class="clear-filters-btn" title="Clear filters">
                        <i data-lucide="x"></i>
                    </button>
                </div>
                <div class="dropdown-section-content">
                    ${filterOptions.map(filter => `
                        <div class="filter-group">
                            <div class="filter-group-label">${filter.label}</div>
                            <div class="filter-options">
                                ${filter.options.map(option => `
                                    <label class="filter-item" data-filter="${filter.key}" data-value="${option}">
                                        <input type="checkbox" ${this.filters[filter.key]?.includes(option) ? 'checked' : ''}>
                                        <span>${option}</span>
                                    </label>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        this.filtersContainer.innerHTML = html;
        
        // Setup filter event listeners
        this.filtersContainer.querySelector('.clear-filters-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.clearFilters();
        });
    }
    
    toggleFilters() {
        this.container.classList.toggle('filters-visible');
        
        if (this.container.classList.contains('filters-visible')) {
            this.openDropdown();
        }
    }
    
    toggleFilter(filterItem) {
        const checkbox = filterItem.querySelector('input[type="checkbox"]');
        const filterKey = filterItem.dataset.filter;
        const filterValue = filterItem.dataset.value;
        
        if (!this.filters[filterKey]) {
            this.filters[filterKey] = [];
        }
        
        if (checkbox.checked) {
            if (!this.filters[filterKey].includes(filterValue)) {
                this.filters[filterKey].push(filterValue);
            }
        } else {
            this.filters[filterKey] = this.filters[filterKey].filter(v => v !== filterValue);
        }
        
        this.onFilter(this.filters);
        this.updateFiltersToggleState();
    }
    
    clearFilters() {
        this.filters = {};
        this.renderFilters();
        this.updateFiltersToggleState();
        this.onFilter(this.filters);
    }
    
    updateFiltersToggleState() {
        if (!this.filtersToggle) return;
        
        const hasActiveFilters = Object.values(this.filters).some(values => 
            Array.isArray(values) && values.length > 0
        );
        
        this.filtersToggle.classList.toggle('active', hasActiveFilters);
    }
    
    addToHistory(query) {
        // Remove if already exists
        this.searchHistory = this.searchHistory.filter(item => item.query !== query);
        
        // Add to beginning
        this.searchHistory.unshift({
            query: query,
            timestamp: Date.now()
        });
        
        // Limit history size
        this.searchHistory = this.searchHistory.slice(0, 20);
        
        this.saveSearchHistory();
        this.renderHistory();
    }
    
    removeFromHistory(query) {
        this.searchHistory = this.searchHistory.filter(item => item.query !== query);
        this.saveSearchHistory();
        this.renderHistory();
    }
    
    clearHistory() {
        this.searchHistory = [];
        this.saveSearchHistory();
        this.renderHistory();
    }
    
    loadSearchHistory() {
        try {
            const stored = localStorage.getItem('searchHistory');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }
    
    saveSearchHistory() {
        try {
            localStorage.setItem('searchHistory', JSON.stringify(this.searchHistory));
        } catch {
            // Ignore storage errors
        }
    }
    
    formatTime(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        
        const minutes = Math.floor(diff / (1000 * 60));
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (minutes < 1) return 'now';
        if (minutes < 60) return `${minutes}m`;
        if (hours < 24) return `${hours}h`;
        return `${days}d`;
    }
    
    setValue(value) {
        this.searchInput.value = value;
        this.currentQuery = value;
        this.searchClear.style.display = value ? 'flex' : 'none';
    }
    
    getValue() {
        return this.currentQuery;
    }
    
    focus() {
        this.searchInput.focus();
    }
    
    getFilters() {
        return { ...this.filters };
    }
    
    setFilters(filters) {
        this.filters = { ...filters };
        this.renderFilters();
        this.updateFiltersToggleState();
    }
}