/**
 * Command Palette with Keyboard Shortcuts (Cmd+K style)
 */

export class CommandPalette {
    constructor(options = {}) {
        this.container = null;
        this.isOpen = false;
        this.searchInput = null;
        this.resultsList = null;
        
        this.commands = new Map();
        this.commandHistory = [];
        this.filteredCommands = [];
        this.selectedIndex = 0;
        
        this.searchQuery = '';
        this.debounceTimer = null;
        
        this.onExecute = options.onExecute || (() => {});
        this.onClose = options.onClose || (() => {});
        
        this.shortcuts = new Map();
        this.activeShortcuts = new Set();
        
        this.setupKeyboardListeners();
        this.registerDefaultCommands();
        this.registerDefaultShortcuts();
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="command-palette ${this.isOpen ? 'open' : ''}" id="command-palette">
                <div class="command-backdrop"></div>
                <div class="command-container">
                    <div class="command-header">
                        <div class="command-search">
                            <i data-lucide="search" class="search-icon"></i>
                            <input type="text" 
                                   class="command-input" 
                                   placeholder="Type a command or search..."
                                   autocomplete="off"
                                   spellcheck="false">
                            <div class="command-shortcut">
                                <span class="shortcut-key">Esc</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="command-content">
                        <div class="command-results" id="command-results">
                            <div class="results-section">
                                <div class="section-title">Recent Commands</div>
                                <div class="results-list" id="results-list">
                                    <!-- Results will be populated here -->
                                </div>
                            </div>
                        </div>
                        
                        <div class="command-footer">
                            <div class="command-tips">
                                <div class="tip">
                                    <span class="tip-keys">
                                        <span class="key">↵</span>
                                    </span>
                                    <span class="tip-text">Execute</span>
                                </div>
                                <div class="tip">
                                    <span class="tip-keys">
                                        <span class="key">↑</span>
                                        <span class="key">↓</span>
                                    </span>
                                    <span class="tip-text">Navigate</span>
                                </div>
                                <div class="tip">
                                    <span class="tip-keys">
                                        <span class="key">Esc</span>
                                    </span>
                                    <span class="tip-text">Close</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Keyboard Shortcuts Help Modal -->
            <div class="shortcuts-help-modal" id="shortcuts-help-modal">
                <div class="modal-backdrop"></div>
                <div class="modal-container">
                    <div class="modal-header">
                        <h2>Keyboard Shortcuts</h2>
                        <button class="modal-close">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    <div class="modal-content">
                        <div class="shortcuts-grid" id="shortcuts-grid">
                            <!-- Shortcuts will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.setupElements();
        this.setupEventListeners();
        this.renderRecentCommands();
    }
    
    setupElements() {
        this.searchInput = this.container.querySelector('.command-input');
        this.resultsList = this.container.querySelector('#results-list');
        this.commandContainer = this.container.querySelector('#command-palette');
        this.shortcutsModal = this.container.querySelector('#shortcuts-help-modal');
    }
    
    setupEventListeners() {
        // Search input
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });
        
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleInputKeydown(e);
        });
        
        // Backdrop click
        this.container.querySelector('.command-backdrop').addEventListener('click', () => {
            this.close();
        });
        
        // Results list
        this.resultsList.addEventListener('click', (e) => {
            this.handleResultClick(e);
        });
        
        // Shortcuts modal
        this.container.querySelector('.modal-backdrop').addEventListener('click', () => {
            this.closeShortcutsModal();
        });
        
        this.container.querySelector('.modal-close').addEventListener('click', () => {
            this.closeShortcutsModal();
        });
    }
    
    setupKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            this.handleGlobalKeydown(e);
        });
        
        document.addEventListener('keyup', (e) => {
            this.handleGlobalKeyup(e);
        });
    }
    
    registerDefaultCommands() {
        // Navigation commands
        this.registerCommand({
            id: 'navigate.dashboard',
            title: 'Go to Dashboard',
            category: 'Navigation',
            keywords: ['dashboard', 'home', 'overview'],
            icon: 'layout-dashboard',
            action: () => this.navigate('/dashboard')
        });
        
        this.registerCommand({
            id: 'navigate.files',
            title: 'Go to Files',
            category: 'Navigation',
            keywords: ['files', 'browse', 'explorer'],
            icon: 'folder',
            action: () => this.navigate('/files')
        });
        
        this.registerCommand({
            id: 'navigate.search',
            title: 'Go to Search',
            category: 'Navigation',
            keywords: ['search', 'find'],
            icon: 'search',
            action: () => this.navigate('/search')
        });
        
        this.registerCommand({
            id: 'navigate.settings',
            title: 'Go to Settings',
            category: 'Navigation',
            keywords: ['settings', 'preferences', 'config'],
            icon: 'settings',
            action: () => this.navigate('/settings')
        });
        
        // File operations
        this.registerCommand({
            id: 'file.upload',
            title: 'Upload Files',
            category: 'Files',
            keywords: ['upload', 'add', 'import'],
            icon: 'upload',
            action: () => this.triggerFileUpload()
        });
        
        this.registerCommand({
            id: 'file.new-folder',
            title: 'Create New Folder',
            category: 'Files',
            keywords: ['folder', 'directory', 'create', 'new'],
            icon: 'folder-plus',
            action: () => this.createNewFolder()
        });
        
        this.registerCommand({
            id: 'file.refresh',
            title: 'Refresh File List',
            category: 'Files',
            keywords: ['refresh', 'reload', 'update'],
            icon: 'refresh-cw',
            action: () => this.refreshFiles()
        });
        
        // Theme commands
        this.registerCommand({
            id: 'theme.toggle',
            title: 'Toggle Dark Mode',
            category: 'Appearance',
            keywords: ['theme', 'dark', 'light', 'mode'],
            icon: 'moon',
            action: () => this.toggleTheme()
        });
        
        this.registerCommand({
            id: 'theme.light',
            title: 'Switch to Light Theme',
            category: 'Appearance',
            keywords: ['theme', 'light'],
            icon: 'sun',
            action: () => this.setTheme('light')
        });
        
        this.registerCommand({
            id: 'theme.dark',
            title: 'Switch to Dark Theme',
            category: 'Appearance',
            keywords: ['theme', 'dark'],
            icon: 'moon',
            action: () => this.setTheme('dark')
        });
        
        // Search commands
        this.registerCommand({
            id: 'search.files',
            title: 'Search Files',
            category: 'Search',
            keywords: ['search', 'find', 'files'],
            icon: 'search',
            shortcut: 'Ctrl+F',
            action: () => this.focusSearch()
        });
        
        this.registerCommand({
            id: 'search.semantic',
            title: 'AI Semantic Search',
            category: 'Search',
            keywords: ['ai', 'semantic', 'smart', 'search'],
            icon: 'brain',
            action: () => this.openSemanticSearch()
        });
        
        // Help commands
        this.registerCommand({
            id: 'help.shortcuts',
            title: 'Show Keyboard Shortcuts',
            category: 'Help',
            keywords: ['shortcuts', 'keyboard', 'hotkeys', 'help'],
            icon: 'keyboard',
            shortcut: '?',
            action: () => this.showShortcutsModal()
        });
        
        this.registerCommand({
            id: 'help.docs',
            title: 'Open Documentation',
            category: 'Help',
            keywords: ['help', 'docs', 'documentation'],
            icon: 'book',
            action: () => this.openDocumentation()
        });
        
        // System commands
        this.registerCommand({
            id: 'system.logout',
            title: 'Sign Out',
            category: 'System',
            keywords: ['logout', 'signout', 'exit'],
            icon: 'log-out',
            action: () => this.logout()
        });
        
        this.registerCommand({
            id: 'system.fullscreen',
            title: 'Toggle Fullscreen',
            category: 'System',
            keywords: ['fullscreen', 'full', 'screen'],
            icon: 'maximize',
            shortcut: 'F11',
            action: () => this.toggleFullscreen()
        });
    }
    
    registerDefaultShortcuts() {
        // Global shortcuts
        this.registerShortcut('Ctrl+K', () => this.toggle());
        this.registerShortcut('Cmd+K', () => this.toggle());
        this.registerShortcut('Ctrl+/', () => this.showShortcutsModal());
        this.registerShortcut('Cmd+/', () => this.showShortcutsModal());
        this.registerShortcut('?', () => this.showShortcutsModal());
        
        // Navigation shortcuts
        this.registerShortcut('G D', () => this.navigate('/dashboard'));
        this.registerShortcut('G F', () => this.navigate('/files'));
        this.registerShortcut('G S', () => this.navigate('/search'));
        this.registerShortcut('G ,', () => this.navigate('/settings'));
        
        // File shortcuts
        this.registerShortcut('Ctrl+U', () => this.triggerFileUpload());
        this.registerShortcut('Cmd+U', () => this.triggerFileUpload());
        this.registerShortcut('Ctrl+Shift+N', () => this.createNewFolder());
        this.registerShortcut('Cmd+Shift+N', () => this.createNewFolder());
        this.registerShortcut('F5', () => this.refreshFiles());
        this.registerShortcut('Ctrl+R', () => this.refreshFiles());
        this.registerShortcut('Cmd+R', () => this.refreshFiles());
        
        // Search shortcuts
        this.registerShortcut('Ctrl+F', () => this.focusSearch());
        this.registerShortcut('Cmd+F', () => this.focusSearch());
        this.registerShortcut('/', () => this.focusSearch());
        
        // Theme shortcuts
        this.registerShortcut('Ctrl+Shift+T', () => this.toggleTheme());
        this.registerShortcut('Cmd+Shift+T', () => this.toggleTheme());
        
        // System shortcuts
        this.registerShortcut('F11', () => this.toggleFullscreen());
        this.registerShortcut('Alt+F4', () => this.logout());
    }
    
    registerCommand(command) {
        this.commands.set(command.id, {
            ...command,
            lastUsed: null,
            useCount: 0
        });
    }
    
    registerShortcut(keys, action, description) {
        const normalizedKeys = this.normalizeShortcut(keys);
        this.shortcuts.set(normalizedKeys, {
            keys: keys,
            action: action,
            description: description || ''
        });
    }
    
    normalizeShortcut(keys) {
        return keys.toLowerCase()
            .replace(/\s+/g, ' ')
            .replace(/cmd/g, 'meta')
            .replace(/ctrl/g, 'control');
    }
    
    handleGlobalKeydown(e) {
        const shortcut = this.buildShortcutString(e);
        
        // Handle multi-key sequences (like 'G D')
        if (this.activeShortcuts.size > 0 || this.isSequenceStarter(e.key.toLowerCase())) {
            this.handleSequenceKey(e);
            return;
        }
        
        // Handle single-key shortcuts
        const shortcutAction = this.shortcuts.get(shortcut);
        if (shortcutAction && !this.isInputFocused() && !this.isOpen) {
            e.preventDefault();
            shortcutAction.action();
            return;
        }
        
        // Command palette specific shortcuts
        if (this.isOpen) {
            switch (e.key) {
                case 'Escape':
                    e.preventDefault();
                    this.close();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.selectPrevious();
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.selectNext();
                    break;
                case 'Enter':
                    e.preventDefault();
                    this.executeSelected();
                    break;
                case 'Tab':
                    e.preventDefault();
                    this.selectNext();
                    break;
            }
        }
    }
    
    handleGlobalKeyup(e) {
        // Handle key combinations release
        this.updateActiveModifiers(e);
    }
    
    handleSequenceKey(e) {
        const key = e.key.toLowerCase();
        
        if (this.activeShortcuts.size === 0 && this.isSequenceStarter(key)) {
            this.activeShortcuts.add(key);
            e.preventDefault();
            
            // Show sequence indicator
            this.showSequenceIndicator();
            
            // Clear sequence after timeout
            setTimeout(() => {
                this.clearSequence();
            }, 2000);
            
            return;
        }
        
        if (this.activeShortcuts.size > 0) {
            const sequence = Array.from(this.activeShortcuts).join(' ') + ' ' + key;
            const shortcutAction = this.shortcuts.get(sequence);
            
            if (shortcutAction) {
                e.preventDefault();
                shortcutAction.action();
                this.clearSequence();
            } else {
                // Invalid sequence, clear it
                this.clearSequence();
            }
        }
    }
    
    isSequenceStarter(key) {
        return key === 'g' || key === 'c';
    }
    
    clearSequence() {
        this.activeShortcuts.clear();
        this.hideSequenceIndicator();
    }
    
    showSequenceIndicator() {
        // Create or update sequence indicator
        let indicator = document.querySelector('.sequence-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'sequence-indicator';
            document.body.appendChild(indicator);
        }
        
        indicator.textContent = Array.from(this.activeShortcuts).join(' ').toUpperCase() + ' ...';
        indicator.classList.add('visible');
    }
    
    hideSequenceIndicator() {
        const indicator = document.querySelector('.sequence-indicator');
        if (indicator) {
            indicator.classList.remove('visible');
        }
    }
    
    buildShortcutString(e) {
        const parts = [];
        
        if (e.ctrlKey) parts.push('control');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        if (e.metaKey) parts.push('meta');
        
        const key = e.key.toLowerCase();
        if (!['control', 'alt', 'shift', 'meta'].includes(key)) {
            parts.push(key);
        }
        
        return parts.join('+');
    }
    
    updateActiveModifiers(e) {
        // Update state based on released modifier keys
    }
    
    isInputFocused() {
        const activeElement = document.activeElement;
        return activeElement && (
            activeElement.tagName === 'INPUT' ||
            activeElement.tagName === 'TEXTAREA' ||
            activeElement.contentEditable === 'true'
        );
    }
    
    handleSearch(query) {
        this.searchQuery = query.toLowerCase().trim();
        
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.updateResults();
        }, 100);
    }
    
    updateResults() {
        if (this.searchQuery === '') {
            this.renderRecentCommands();
            return;
        }
        
        this.filteredCommands = this.searchCommands(this.searchQuery);
        this.selectedIndex = 0;
        this.renderSearchResults();
    }
    
    searchCommands(query) {
        const results = [];
        
        for (const [id, command] of this.commands) {
            const score = this.calculateMatchScore(command, query);
            if (score > 0) {
                results.push({ ...command, score });
            }
        }
        
        return results.sort((a, b) => {
            // Sort by score first, then by usage, then alphabetically
            if (b.score !== a.score) return b.score - a.score;
            if (b.useCount !== a.useCount) return b.useCount - a.useCount;
            return a.title.localeCompare(b.title);
        });
    }
    
    calculateMatchScore(command, query) {
        let score = 0;
        const titleLower = command.title.toLowerCase();
        const keywords = command.keywords || [];
        
        // Exact title match
        if (titleLower === query) {
            score += 100;
        }
        // Title starts with query
        else if (titleLower.startsWith(query)) {
            score += 80;
        }
        // Title contains query
        else if (titleLower.includes(query)) {
            score += 60;
        }
        
        // Check keywords
        for (const keyword of keywords) {
            const keywordLower = keyword.toLowerCase();
            if (keywordLower === query) {
                score += 70;
            } else if (keywordLower.startsWith(query)) {
                score += 50;
            } else if (keywordLower.includes(query)) {
                score += 30;
            }
        }
        
        // Boost score for frequently used commands
        score += command.useCount * 5;
        
        // Boost score for recently used commands
        if (command.lastUsed) {
            const hoursSinceUsed = (Date.now() - command.lastUsed) / (1000 * 60 * 60);
            if (hoursSinceUsed < 24) {
                score += Math.max(0, 20 - hoursSinceUsed);
            }
        }
        
        return score;
    }
    
    renderRecentCommands() {
        const recentCommands = this.getRecentCommands();
        
        if (recentCommands.length === 0) {
            this.renderDefaultCommands();
            return;
        }
        
        this.filteredCommands = recentCommands;
        this.selectedIndex = 0;
        
        const html = `
            <div class="results-section">
                <div class="section-title">Recent Commands</div>
                ${this.renderCommandList(recentCommands)}
            </div>
        `;
        
        this.resultsList.innerHTML = html;
        this.updateSelection();
    }
    
    renderDefaultCommands() {
        const categories = this.groupCommandsByCategory();
        const popularCommands = this.getPopularCommands();
        
        let html = '';
        
        if (popularCommands.length > 0) {
            html += `
                <div class="results-section">
                    <div class="section-title">Popular Commands</div>
                    ${this.renderCommandList(popularCommands)}
                </div>
            `;
        }
        
        for (const [category, commands] of categories) {
            if (commands.length > 0) {
                html += `
                    <div class="results-section">
                        <div class="section-title">${category}</div>
                        ${this.renderCommandList(commands.slice(0, 5))}
                    </div>
                `;
            }
        }
        
        this.resultsList.innerHTML = html;
        this.filteredCommands = [...popularCommands, ...Array.from(this.commands.values())];
        this.updateSelection();
    }
    
    renderSearchResults() {
        const categories = new Map();
        
        this.filteredCommands.forEach(command => {
            const category = command.category || 'Other';
            if (!categories.has(category)) {
                categories.set(category, []);
            }
            categories.get(category).push(command);
        });
        
        let html = '';
        
        for (const [category, commands] of categories) {
            html += `
                <div class="results-section">
                    <div class="section-title">${category}</div>
                    ${this.renderCommandList(commands)}
                </div>
            `;
        }
        
        if (html === '') {
            html = `
                <div class="no-results">
                    <i data-lucide="search-x"></i>
                    <span>No commands found for "${this.searchQuery}"</span>
                </div>
            `;
        }
        
        this.resultsList.innerHTML = html;
        this.updateSelection();
    }
    
    renderCommandList(commands) {
        return commands.map((command, index) => `
            <div class="command-result" data-command-id="${command.id}" data-index="${index}">
                <div class="command-icon">
                    <i data-lucide="${command.icon || 'terminal'}"></i>
                </div>
                <div class="command-content">
                    <div class="command-title">${this.highlightMatch(command.title, this.searchQuery)}</div>
                    ${command.description ? `<div class="command-description">${command.description}</div>` : ''}
                </div>
                <div class="command-meta">
                    ${command.shortcut ? `
                        <div class="command-shortcut">
                            ${this.renderShortcutKeys(command.shortcut)}
                        </div>
                    ` : ''}
                    ${command.category ? `
                        <div class="command-category">${command.category}</div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }
    
    highlightMatch(text, query) {
        if (!query) return text;
        
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    renderShortcutKeys(shortcut) {
        return shortcut.split('+').map(key => 
            `<span class="shortcut-key">${key}</span>`
        ).join('');
    }
    
    getRecentCommands() {
        return this.commandHistory
            .slice(-10)
            .reverse()
            .map(id => this.commands.get(id))
            .filter(Boolean);
    }
    
    getPopularCommands() {
        return Array.from(this.commands.values())
            .sort((a, b) => b.useCount - a.useCount)
            .slice(0, 5);
    }
    
    groupCommandsByCategory() {
        const categories = new Map();
        
        for (const command of this.commands.values()) {
            const category = command.category || 'Other';
            if (!categories.has(category)) {
                categories.set(category, []);
            }
            categories.get(category).push(command);
        }
        
        return categories;
    }
    
    handleInputKeydown(e) {
        // Prevent default behavior for navigation keys
        if (['ArrowUp', 'ArrowDown', 'Tab', 'Enter'].includes(e.key)) {
            e.preventDefault();
        }
    }
    
    handleResultClick(e) {
        const resultElement = e.target.closest('.command-result');
        if (!resultElement) return;
        
        const commandId = resultElement.dataset.commandId;
        this.executeCommand(commandId);
    }
    
    selectNext() {
        if (this.filteredCommands.length === 0) return;
        
        this.selectedIndex = (this.selectedIndex + 1) % this.filteredCommands.length;
        this.updateSelection();
    }
    
    selectPrevious() {
        if (this.filteredCommands.length === 0) return;
        
        this.selectedIndex = this.selectedIndex === 0 
            ? this.filteredCommands.length - 1 
            : this.selectedIndex - 1;
        this.updateSelection();
    }
    
    updateSelection() {
        const results = this.resultsList.querySelectorAll('.command-result');
        results.forEach((result, index) => {
            result.classList.toggle('selected', index === this.selectedIndex);
        });
        
        // Scroll selected item into view
        const selectedResult = results[this.selectedIndex];
        if (selectedResult) {
            selectedResult.scrollIntoView({ block: 'nearest' });
        }
    }
    
    executeSelected() {
        if (this.filteredCommands.length === 0) return;
        
        const selectedCommand = this.filteredCommands[this.selectedIndex];
        if (selectedCommand) {
            this.executeCommand(selectedCommand.id);
        }
    }
    
    executeCommand(commandId) {
        const command = this.commands.get(commandId);
        if (!command) return;
        
        try {
            // Update command usage stats
            command.useCount++;
            command.lastUsed = Date.now();
            
            // Add to history
            this.commandHistory = this.commandHistory.filter(id => id !== commandId);
            this.commandHistory.push(commandId);
            
            // Execute the command
            command.action();
            
            // Notify listeners
            this.onExecute(command);
            
            // Close the palette
            this.close();
            
        } catch (error) {
            console.error('Command execution failed:', error);
        }
    }
    
    open() {
        this.isOpen = true;
        this.commandContainer.classList.add('open');
        document.body.classList.add('command-palette-open');
        
        // Focus search input
        setTimeout(() => {
            this.searchInput.focus();
            this.searchInput.select();
        }, 100);
        
        // Reset state
        this.searchQuery = '';
        this.selectedIndex = 0;
        this.renderRecentCommands();
    }
    
    close() {
        this.isOpen = false;
        this.commandContainer.classList.remove('open');
        document.body.classList.remove('command-palette-open');
        
        // Clear search
        this.searchInput.value = '';
        this.searchQuery = '';
        
        // Clear sequence
        this.clearSequence();
        
        this.onClose();
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    showShortcutsModal() {
        this.renderShortcuts();
        this.shortcutsModal.classList.add('open');
    }
    
    closeShortcutsModal() {
        this.shortcutsModal.classList.remove('open');
    }
    
    renderShortcuts() {
        const categories = new Map();
        
        // Group shortcuts by category
        for (const [keys, shortcut] of this.shortcuts) {
            const command = Array.from(this.commands.values())
                .find(cmd => cmd.shortcut && this.normalizeShortcut(cmd.shortcut) === keys);
            
            const category = command ? command.category : 'General';
            if (!categories.has(category)) {
                categories.set(category, []);
            }
            
            categories.get(category).push({
                keys: shortcut.keys,
                description: shortcut.description || (command ? command.title : 'Unknown'),
                action: shortcut.action
            });
        }
        
        let html = '';
        for (const [category, shortcuts] of categories) {
            html += `
                <div class="shortcuts-category">
                    <h3 class="category-title">${category}</h3>
                    <div class="shortcuts-list">
                        ${shortcuts.map(shortcut => `
                            <div class="shortcut-item">
                                <div class="shortcut-keys">
                                    ${this.renderShortcutKeys(shortcut.keys)}
                                </div>
                                <div class="shortcut-description">${shortcut.description}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        this.container.querySelector('#shortcuts-grid').innerHTML = html;
    }
    
    // Command actions
    navigate(path) {
        window.location.hash = path;
    }
    
    triggerFileUpload() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.click();
    }
    
    createNewFolder() {
        const name = prompt('Enter folder name:');
        if (name) {
            console.log('Creating folder:', name);
        }
    }
    
    refreshFiles() {
        location.reload();
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }
    
    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }
    
    focusSearch() {
        const searchInput = document.querySelector('.search-input, #global-search');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    openSemanticSearch() {
        // Navigate to semantic search
        this.navigate('/search?mode=semantic');
    }
    
    openDocumentation() {
        window.open('https://docs.example.com', '_blank');
    }
    
    logout() {
        if (confirm('Are you sure you want to sign out?')) {
            // Perform logout
            console.log('Logging out...');
        }
    }
    
    toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            document.documentElement.requestFullscreen();
        }
    }
    
    // Public API
    addCommand(command) {
        this.registerCommand(command);
    }
    
    removeCommand(commandId) {
        this.commands.delete(commandId);
    }
    
    addShortcut(keys, action, description) {
        this.registerShortcut(keys, action, description);
    }
    
    removeShortcut(keys) {
        const normalizedKeys = this.normalizeShortcut(keys);
        this.shortcuts.delete(normalizedKeys);
    }
    
    getCommands() {
        return Array.from(this.commands.values());
    }
    
    getShortcuts() {
        return Array.from(this.shortcuts.entries());
    }
    
    isVisible() {
        return this.isOpen;
    }
}