/**
 * Advanced File Explorer with Tree View
 */

import { FileTree } from './FileTree.js';
import { VirtualizedList } from '../common/VirtualizedList.js';
import { SearchBar } from '../common/SearchBar.js';
import { API } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class FileExplorer {
    constructor(options = {}) {
        this.container = null;
        this.currentPath = '/';
        this.viewMode = 'tree'; // 'tree', 'list', 'grid'
        this.selectedFiles = new Set();
        this.sortBy = 'name';
        this.sortOrder = 'asc';
        this.searchQuery = '';
        this.filterType = 'all';
        this.showHidden = false;
        
        this.onFileSelect = options.onFileSelect || (() => {});
        this.onFileOpen = options.onFileOpen || (() => {});
        this.onPathChange = options.onPathChange || (() => {});
        
        this.fileTree = new FileTree({
            onNodeSelect: this.handleNodeSelect.bind(this),
            onNodeExpand: this.handleNodeExpand.bind(this),
            onNodeCollapse: this.handleNodeCollapse.bind(this)
        });
        
        this.virtualList = new VirtualizedList({
            itemHeight: 40,
            renderItem: this.renderFileItem.bind(this)
        });
        
        this.searchBar = new SearchBar({
            placeholder: 'Search files and folders...',
            onSearch: this.handleSearch.bind(this),
            debounce: 300
        });
        
        this.files = [];
        this.filteredFiles = [];
        this.loading = false;
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="file-explorer">
                <div class="file-explorer-header">
                    <div class="search-section">
                        <div id="search-bar"></div>
                    </div>
                    <div class="toolbar">
                        <div class="view-controls">
                            <button class="btn-icon ${this.viewMode === 'tree' ? 'active' : ''}" 
                                    data-view="tree" title="Tree View">
                                <i data-lucide="folder-tree"></i>
                            </button>
                            <button class="btn-icon ${this.viewMode === 'list' ? 'active' : ''}" 
                                    data-view="list" title="List View">
                                <i data-lucide="list"></i>
                            </button>
                            <button class="btn-icon ${this.viewMode === 'grid' ? 'active' : ''}" 
                                    data-view="grid" title="Grid View">
                                <i data-lucide="grid-3x3"></i>
                            </button>
                        </div>
                        <div class="sort-controls">
                            <select class="sort-select" id="sort-by">
                                <option value="name">Name</option>
                                <option value="date">Date Modified</option>
                                <option value="size">Size</option>
                                <option value="type">Type</option>
                            </select>
                            <button class="btn-icon sort-order" data-order="${this.sortOrder}" title="Sort Order">
                                <i data-lucide="${this.sortOrder === 'asc' ? 'arrow-up' : 'arrow-down'}"></i>
                            </button>
                        </div>
                        <div class="filter-controls">
                            <select class="filter-select" id="filter-type">
                                <option value="all">All Files</option>
                                <option value="image">Images</option>
                                <option value="video">Videos</option>
                                <option value="audio">Audio</option>
                                <option value="document">Documents</option>
                                <option value="folder">Folders</option>
                            </select>
                            <button class="btn-icon toggle-hidden" title="Show Hidden Files">
                                <i data-lucide="eye${this.showHidden ? '' : '-off'}"></i>
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="breadcrumb">
                    <div class="breadcrumb-path" id="breadcrumb-path"></div>
                    <button class="btn-icon btn-refresh" title="Refresh">
                        <i data-lucide="refresh-cw"></i>
                    </button>
                </div>
                
                <div class="file-explorer-content">
                    <div id="file-tree" class="file-tree-container ${this.viewMode === 'tree' ? 'active' : ''}"></div>
                    <div id="file-list" class="file-list-container ${this.viewMode !== 'tree' ? 'active' : ''}"></div>
                </div>
                
                <div class="file-explorer-footer">
                    <div class="selection-info">
                        <span id="selection-count">0 items selected</span>
                    </div>
                    <div class="status-info">
                        <span id="total-count">0 items</span>
                        <span class="separator">•</span>
                        <span id="loading-status">Ready</span>
                    </div>
                </div>
            </div>
        `;
        
        await this.initializeComponents();
        this.setupEventListeners();
        await this.loadFiles();
    }
    
    async initializeComponents() {
        await this.searchBar.render(this.container.querySelector('#search-bar'));
        
        if (this.viewMode === 'tree') {
            await this.fileTree.render(this.container.querySelector('#file-tree'));
        } else {
            await this.virtualList.render(this.container.querySelector('#file-list'));
        }
        
        this.updateBreadcrumb();
    }
    
    setupEventListeners() {
        const container = this.container;
        
        // View mode controls
        container.querySelectorAll('[data-view]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setViewMode(e.target.closest('button').dataset.view);
            });
        });
        
        // Sort controls
        container.querySelector('#sort-by').addEventListener('change', (e) => {
            this.setSortBy(e.target.value);
        });
        
        container.querySelector('.sort-order').addEventListener('click', () => {
            this.toggleSortOrder();
        });
        
        // Filter controls
        container.querySelector('#filter-type').addEventListener('change', (e) => {
            this.setFilterType(e.target.value);
        });
        
        container.querySelector('.toggle-hidden').addEventListener('click', () => {
            this.toggleHiddenFiles();
        });
        
        // Refresh button
        container.querySelector('.btn-refresh').addEventListener('click', () => {
            this.refreshFiles();
        });
        
        // Keyboard shortcuts
        container.addEventListener('keydown', this.handleKeyboard.bind(this));
        
        // File list events
        container.addEventListener('click', this.handleFileClick.bind(this));
        container.addEventListener('dblclick', this.handleFileDoubleClick.bind(this));
        container.addEventListener('contextmenu', this.handleContextMenu.bind(this));
    }
    
    async loadFiles(path = this.currentPath) {
        this.setLoading(true);
        
        try {
            const response = await API.get('/files/list', {
                path: path,
                recursive: this.viewMode === 'tree',
                showHidden: this.showHidden,
                includeMetadata: true
            });
            
            this.files = response.files || [];
            this.applyFiltersAndSort();
            this.updateDisplay();
            this.updateStatus();
            
        } catch (error) {
            console.error('Failed to load files:', error);
            NotificationManager.error('Failed to load files');
        } finally {
            this.setLoading(false);
        }
    }
    
    applyFiltersAndSort() {
        let filtered = [...this.files];
        
        // Apply search filter
        if (this.searchQuery) {
            const query = this.searchQuery.toLowerCase();
            filtered = filtered.filter(file => 
                file.name.toLowerCase().includes(query) ||
                file.path.toLowerCase().includes(query)
            );
        }
        
        // Apply type filter
        if (this.filterType !== 'all') {
            filtered = filtered.filter(file => {
                switch (this.filterType) {
                    case 'folder':
                        return file.type === 'directory';
                    case 'image':
                        return file.mimeType && file.mimeType.startsWith('image/');
                    case 'video':
                        return file.mimeType && file.mimeType.startsWith('video/');
                    case 'audio':
                        return file.mimeType && file.mimeType.startsWith('audio/');
                    case 'document':
                        return file.mimeType && (
                            file.mimeType.includes('text/') ||
                            file.mimeType.includes('pdf') ||
                            file.mimeType.includes('document') ||
                            file.mimeType.includes('spreadsheet')
                        );
                    default:
                        return true;
                }
            });
        }
        
        // Apply sort
        filtered.sort((a, b) => {
            let aVal, bVal;
            
            switch (this.sortBy) {
                case 'name':
                    aVal = a.name.toLowerCase();
                    bVal = b.name.toLowerCase();
                    break;
                case 'date':
                    aVal = new Date(a.modified || 0);
                    bVal = new Date(b.modified || 0);
                    break;
                case 'size':
                    aVal = a.size || 0;
                    bVal = b.size || 0;
                    break;
                case 'type':
                    aVal = a.type || '';
                    bVal = b.type || '';
                    break;
                default:
                    return 0;
            }
            
            if (aVal < bVal) return this.sortOrder === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
        
        // Always show directories first
        filtered.sort((a, b) => {
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            return 0;
        });
        
        this.filteredFiles = filtered;
    }
    
    updateDisplay() {
        if (this.viewMode === 'tree') {
            this.fileTree.setData(this.buildTreeData());
        } else {
            this.virtualList.setItems(this.filteredFiles);
        }
    }
    
    buildTreeData() {
        const tree = {};
        
        this.filteredFiles.forEach(file => {
            const parts = file.path.replace(this.currentPath, '').split('/').filter(Boolean);
            let current = tree;
            
            parts.forEach((part, index) => {
                if (!current[part]) {
                    current[part] = {
                        name: part,
                        type: index === parts.length - 1 ? file.type : 'directory',
                        path: file.path.split('/').slice(0, -parts.length + index + 1).join('/') + '/' + part,
                        children: {},
                        file: index === parts.length - 1 ? file : null
                    };
                }
                current = current[part].children;
            });
        });
        
        return tree;
    }
    
    renderFileItem(file, index) {
        const isSelected = this.selectedFiles.has(file.path);
        const icon = this.getFileIcon(file);
        const size = this.formatFileSize(file.size);
        const date = this.formatDate(file.modified);
        
        return `
            <div class="file-item ${isSelected ? 'selected' : ''}" 
                 data-path="${file.path}" 
                 data-type="${file.type}"
                 data-index="${index}">
                <div class="file-icon">
                    <i data-lucide="${icon}"></i>
                </div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">
                        ${file.type === 'directory' ? 'Folder' : size} • ${date}
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn-icon" title="More options">
                        <i data-lucide="more-horizontal"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    getFileIcon(file) {
        if (file.type === 'directory') return 'folder';
        
        const ext = file.name.split('.').pop().toLowerCase();
        const mimeType = file.mimeType || '';
        
        if (mimeType.startsWith('image/')) return 'image';
        if (mimeType.startsWith('video/')) return 'video';
        if (mimeType.startsWith('audio/')) return 'music';
        
        switch (ext) {
            case 'pdf': return 'file-text';
            case 'doc':
            case 'docx': return 'file-text';
            case 'xls':
            case 'xlsx': return 'spreadsheet';
            case 'ppt':
            case 'pptx': return 'presentation';
            case 'zip':
            case 'rar':
            case '7z': return 'archive';
            case 'js':
            case 'ts':
            case 'jsx':
            case 'tsx': return 'file-code';
            case 'html':
            case 'css':
            case 'scss': return 'code';
            default: return 'file';
        }
    }
    
    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    formatDate(dateStr) {
        if (!dateStr) return 'Unknown';
        
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        
        return date.toLocaleDateString();
    }
    
    handleSearch(query) {
        this.searchQuery = query;
        this.applyFiltersAndSort();
        this.updateDisplay();
        this.updateStatus();
    }
    
    handleNodeSelect(node) {
        this.selectedFiles.clear();
        this.selectedFiles.add(node.path);
        this.updateSelectionInfo();
        this.onFileSelect(node.file || node);
    }
    
    handleNodeExpand(node) {
        // Load children if needed
    }
    
    handleNodeCollapse(node) {
        // Handle collapse
    }
    
    handleFileClick(e) {
        const fileItem = e.target.closest('.file-item');
        if (!fileItem) return;
        
        const path = fileItem.dataset.path;
        const isCtrlClick = e.ctrlKey || e.metaKey;
        const isShiftClick = e.shiftKey;
        
        if (isCtrlClick) {
            this.toggleFileSelection(path);
        } else if (isShiftClick) {
            this.selectRange(path);
        } else {
            this.selectSingleFile(path);
        }
        
        this.updateSelectionInfo();
    }
    
    handleFileDoubleClick(e) {
        const fileItem = e.target.closest('.file-item');
        if (!fileItem) return;
        
        const path = fileItem.dataset.path;
        const type = fileItem.dataset.type;
        const file = this.filteredFiles.find(f => f.path === path);
        
        if (type === 'directory') {
            this.navigateTo(path);
        } else {
            this.onFileOpen(file);
        }
    }
    
    handleContextMenu(e) {
        e.preventDefault();
        
        const fileItem = e.target.closest('.file-item');
        if (!fileItem) return;
        
        const path = fileItem.dataset.path;
        const file = this.filteredFiles.find(f => f.path === path);
        
        this.showContextMenu(e.clientX, e.clientY, file);
    }
    
    handleKeyboard(e) {
        switch (e.key) {
            case 'Delete':
                if (this.selectedFiles.size > 0) {
                    this.deleteSelectedFiles();
                }
                break;
            case 'Enter':
                if (this.selectedFiles.size === 1) {
                    const path = Array.from(this.selectedFiles)[0];
                    const file = this.filteredFiles.find(f => f.path === path);
                    if (file.type === 'directory') {
                        this.navigateTo(path);
                    } else {
                        this.onFileOpen(file);
                    }
                }
                break;
            case 'Backspace':
                if (e.ctrlKey || e.metaKey) {
                    this.navigateUp();
                }
                break;
        }
    }
    
    selectSingleFile(path) {
        this.selectedFiles.clear();
        this.selectedFiles.add(path);
        this.updateFileItemSelection();
    }
    
    toggleFileSelection(path) {
        if (this.selectedFiles.has(path)) {
            this.selectedFiles.delete(path);
        } else {
            this.selectedFiles.add(path);
        }
        this.updateFileItemSelection();
    }
    
    selectRange(endPath) {
        // Implementation for range selection
    }
    
    updateFileItemSelection() {
        this.container.querySelectorAll('.file-item').forEach(item => {
            const path = item.dataset.path;
            item.classList.toggle('selected', this.selectedFiles.has(path));
        });
    }
    
    updateSelectionInfo() {
        const count = this.selectedFiles.size;
        const countEl = this.container.querySelector('#selection-count');
        
        if (count === 0) {
            countEl.textContent = '0 items selected';
        } else if (count === 1) {
            countEl.textContent = '1 item selected';
        } else {
            countEl.textContent = `${count} items selected`;
        }
    }
    
    updateStatus() {
        const totalEl = this.container.querySelector('#total-count');
        const loadingEl = this.container.querySelector('#loading-status');
        
        totalEl.textContent = `${this.filteredFiles.length} items`;
        loadingEl.textContent = this.loading ? 'Loading...' : 'Ready';
    }
    
    updateBreadcrumb() {
        const breadcrumbEl = this.container.querySelector('#breadcrumb-path');
        const parts = this.currentPath.split('/').filter(Boolean);
        
        let html = '<button class="breadcrumb-item root" data-path="/">Home</button>';
        
        let currentPath = '';
        parts.forEach(part => {
            currentPath += '/' + part;
            html += `<span class="breadcrumb-separator">/</span>
                     <button class="breadcrumb-item" data-path="${currentPath}">${part}</button>`;
        });
        
        breadcrumbEl.innerHTML = html;
        
        breadcrumbEl.querySelectorAll('.breadcrumb-item').forEach(item => {
            item.addEventListener('click', () => {
                this.navigateTo(item.dataset.path);
            });
        });
    }
    
    setViewMode(mode) {
        if (this.viewMode === mode) return;
        
        this.viewMode = mode;
        this.container.querySelectorAll('[data-view]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });
        
        const treeContainer = this.container.querySelector('#file-tree');
        const listContainer = this.container.querySelector('#file-list');
        
        treeContainer.classList.toggle('active', mode === 'tree');
        listContainer.classList.toggle('active', mode !== 'tree');
        
        this.updateDisplay();
    }
    
    setSortBy(sortBy) {
        this.sortBy = sortBy;
        this.container.querySelector('#sort-by').value = sortBy;
        this.applyFiltersAndSort();
        this.updateDisplay();
        this.updateStatus();
    }
    
    toggleSortOrder() {
        this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        const btn = this.container.querySelector('.sort-order');
        btn.dataset.order = this.sortOrder;
        btn.querySelector('i').setAttribute('data-lucide', 
            this.sortOrder === 'asc' ? 'arrow-up' : 'arrow-down'
        );
        
        this.applyFiltersAndSort();
        this.updateDisplay();
    }
    
    setFilterType(filterType) {
        this.filterType = filterType;
        this.container.querySelector('#filter-type').value = filterType;
        this.applyFiltersAndSort();
        this.updateDisplay();
        this.updateStatus();
    }
    
    toggleHiddenFiles() {
        this.showHidden = !this.showHidden;
        const btn = this.container.querySelector('.toggle-hidden');
        btn.querySelector('i').setAttribute('data-lucide', 
            this.showHidden ? 'eye' : 'eye-off'
        );
        btn.title = this.showHidden ? 'Hide Hidden Files' : 'Show Hidden Files';
        
        this.loadFiles();
    }
    
    async navigateTo(path) {
        if (this.currentPath === path) return;
        
        this.currentPath = path;
        this.selectedFiles.clear();
        this.updateBreadcrumb();
        await this.loadFiles();
        this.onPathChange(path);
    }
    
    navigateUp() {
        const parentPath = this.currentPath.split('/').slice(0, -1).join('/') || '/';
        this.navigateTo(parentPath);
    }
    
    async refreshFiles() {
        await this.loadFiles();
        NotificationManager.success('Files refreshed');
    }
    
    setLoading(loading) {
        this.loading = loading;
        this.container.classList.toggle('loading', loading);
        this.updateStatus();
    }
    
    showContextMenu(x, y, file) {
        // Implementation for context menu
    }
    
    async deleteSelectedFiles() {
        if (this.selectedFiles.size === 0) return;
        
        const files = Array.from(this.selectedFiles);
        const confirmed = confirm(`Delete ${files.length} item(s)?`);
        
        if (!confirmed) return;
        
        try {
            await API.post('/files/delete', { files });
            await this.refreshFiles();
            NotificationManager.success('Files deleted');
        } catch (error) {
            console.error('Failed to delete files:', error);
            NotificationManager.error('Failed to delete files');
        }
    }
    
    getSelectedFiles() {
        return Array.from(this.selectedFiles).map(path => 
            this.filteredFiles.find(f => f.path === path)
        ).filter(Boolean);
    }
    
    clearSelection() {
        this.selectedFiles.clear();
        this.updateFileItemSelection();
        this.updateSelectionInfo();
    }
}