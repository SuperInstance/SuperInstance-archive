/**
 * File Manager Component with Grid/List Views
 */

import { ApiClient } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';
import { GlobalEvents } from '../../utils/events.js';
import { FileUploader } from './FileUploader.js';
import { FileViewer } from './FileViewer.js';

export class FileManager {
    constructor() {
        this.files = [];
        this.filteredFiles = [];
        this.currentPath = '/';
        this.viewMode = localStorage.getItem('file_view_mode') || 'grid';
        this.sortBy = 'name';
        this.sortOrder = 'asc';
        this.selectedFiles = new Set();
        this.isLoading = false;
        
        this.fileUploader = new FileUploader();
        this.fileViewer = new FileViewer();
    }

    async render(container) {
        container.innerHTML = `
            <div class="file-manager">
                <div class="file-manager-header">
                    <div class="breadcrumb">
                        <div class="breadcrumb-items" id="breadcrumb">
                            <span class="breadcrumb-item active">Files</span>
                        </div>
                    </div>
                    
                    <div class="file-actions">
                        <button class="action-button primary" id="upload-button">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="17,8 12,3 7,8"/>
                                <line x1="12" y1="3" x2="12" y2="15"/>
                            </svg>
                            Upload
                        </button>
                        
                        <button class="action-button" id="new-folder-button">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                                <line x1="12" y1="10" x2="12" y2="16"/>
                                <line x1="9" y1="13" x2="15" y2="13"/>
                            </svg>
                            New Folder
                        </button>
                        
                        <div class="action-separator"></div>
                        
                        <div class="view-toggle" id="view-toggle">
                            <button class="view-button ${this.viewMode === 'grid' ? 'active' : ''}" data-view="grid">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="3" y="3" width="7" height="7"/>
                                    <rect x="14" y="3" width="7" height="7"/>
                                    <rect x="14" y="14" width="7" height="7"/>
                                    <rect x="3" y="14" width="7" height="7"/>
                                </svg>
                            </button>
                            <button class="view-button ${this.viewMode === 'list' ? 'active' : ''}" data-view="list">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="8" y1="6" x2="21" y2="6"/>
                                    <line x1="8" y1="12" x2="21" y2="12"/>
                                    <line x1="8" y1="18" x2="21" y2="18"/>
                                    <line x1="3" y1="6" x2="3.01" y2="6"/>
                                    <line x1="3" y1="12" x2="3.01" y2="12"/>
                                    <line x1="3" y1="18" x2="3.01" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        
                        <div class="sort-dropdown">
                            <button class="sort-button" id="sort-button">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 6h18"/>
                                    <path d="M7 12h10"/>
                                    <path d="M10 18h4"/>
                                </svg>
                                Sort
                            </button>
                            <div class="sort-menu" id="sort-menu" style="display: none;">
                                <div class="sort-option" data-sort="name">Name</div>
                                <div class="sort-option" data-sort="modified">Modified</div>
                                <div class="sort-option" data-sort="size">Size</div>
                                <div class="sort-option" data-sort="type">Type</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="file-manager-toolbar">
                    <div class="search-bar">
                        <input type="text" id="file-search" placeholder="Search files..." />
                        <button class="search-clear" id="search-clear" style="display: none;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                    
                    <div class="selection-info" id="selection-info" style="display: none;">
                        <span id="selection-count">0</span> selected
                        <div class="selection-actions">
                            <button class="action-button small" id="download-selected">Download</button>
                            <button class="action-button small" id="delete-selected">Delete</button>
                            <button class="action-button small" id="tag-selected">Tag</button>
                        </div>
                    </div>
                </div>
                
                <div class="file-manager-content">
                    <div class="file-list ${this.viewMode}-view" id="file-list">
                        <!-- Files will be rendered here -->
                    </div>
                    
                    <div class="file-manager-empty" id="empty-state" style="display: none;">
                        <div class="empty-icon">
                            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                            </svg>
                        </div>
                        <h3>No files found</h3>
                        <p>Upload files or create folders to get started</p>
                        <button class="action-button primary" id="empty-upload">Upload Files</button>
                    </div>
                    
                    <div class="loading-spinner" id="loading-spinner" style="display: none;">
                        <div class="spinner"></div>
                        <p>Loading files...</p>
                    </div>
                </div>
                
                <!-- File Upload Drop Zone -->
                <div class="upload-drop-zone" id="upload-drop-zone" style="display: none;">
                    <div class="drop-zone-content">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="17,8 12,3 7,8"/>
                            <line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                        <h3>Drop files here to upload</h3>
                    </div>
                </div>
            </div>
        `;

        await this.attachEventListeners();
        await this.loadFiles();
        this.setupDragAndDrop();
    }

    async attachEventListeners() {
        // Upload button
        document.getElementById('upload-button')?.addEventListener('click', () => {
            this.showUploadDialog();
        });

        // New folder button
        document.getElementById('new-folder-button')?.addEventListener('click', () => {
            this.createNewFolder();
        });

        // View toggle
        document.querySelectorAll('.view-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const newView = e.target.closest('.view-button').dataset.view;
                this.setViewMode(newView);
            });
        });

        // Sort functionality
        const sortButton = document.getElementById('sort-button');
        const sortMenu = document.getElementById('sort-menu');
        
        sortButton?.addEventListener('click', (e) => {
            e.stopPropagation();
            sortMenu.style.display = sortMenu.style.display === 'none' ? 'block' : 'none';
        });

        document.querySelectorAll('.sort-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const sortBy = e.target.dataset.sort;
                this.setSortBy(sortBy);
                sortMenu.style.display = 'none';
            });
        });

        // Search functionality
        const searchInput = document.getElementById('file-search');
        const searchClear = document.getElementById('search-clear');
        
        searchInput?.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        searchClear?.addEventListener('click', () => {
            searchInput.value = '';
            this.handleSearch('');
        });

        // Selection actions
        document.getElementById('download-selected')?.addEventListener('click', () => {
            this.downloadSelectedFiles();
        });

        document.getElementById('delete-selected')?.addEventListener('click', () => {
            this.deleteSelectedFiles();
        });

        document.getElementById('tag-selected')?.addEventListener('click', () => {
            this.tagSelectedFiles();
        });

        // Empty state upload
        document.getElementById('empty-upload')?.addEventListener('click', () => {
            this.showUploadDialog();
        });

        // Global events
        GlobalEvents.on('showUploadDialog', () => this.showUploadDialog());
        GlobalEvents.on('fileUploaded', (file) => this.handleFileUploaded(file));
        GlobalEvents.on('fileDeleted', (fileId) => this.handleFileDeleted(fileId));

        // Close dropdowns when clicking outside
        document.addEventListener('click', () => {
            sortMenu.style.display = 'none';
        });
    }

    setupDragAndDrop() {
        const dropZone = document.getElementById('upload-drop-zone');
        const fileManager = document.querySelector('.file-manager');

        const handleDragOver = (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            dropZone.style.display = 'flex';
        };

        const handleDragLeave = (e) => {
            if (!fileManager.contains(e.relatedTarget)) {
                dropZone.style.display = 'none';
            }
        };

        const handleDrop = async (e) => {
            e.preventDefault();
            dropZone.style.display = 'none';
            
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                await this.uploadFiles(files);
            }
        };

        fileManager.addEventListener('dragover', handleDragOver);
        fileManager.addEventListener('dragleave', handleDragLeave);
        fileManager.addEventListener('drop', handleDrop);
    }

    async loadFiles() {
        this.setLoading(true);
        
        try {
            const response = await ApiClient.get(`/metadata/files?path=${encodeURIComponent(this.currentPath)}`);
            this.files = response.files || [];
            this.filteredFiles = [...this.files];
            this.renderFiles();
            
        } catch (error) {
            console.error('Failed to load files:', error);
            NotificationManager.error('Failed to load files');
        } finally {
            this.setLoading(false);
        }
    }

    renderFiles() {
        const fileList = document.getElementById('file-list');
        const emptyState = document.getElementById('empty-state');
        
        if (this.filteredFiles.length === 0) {
            fileList.style.display = 'none';
            emptyState.style.display = 'flex';
            return;
        }
        
        fileList.style.display = 'block';
        emptyState.style.display = 'none';
        
        fileList.className = `file-list ${this.viewMode}-view`;
        
        if (this.viewMode === 'grid') {
            this.renderGridView(fileList);
        } else {
            this.renderListView(fileList);
        }
    }

    renderGridView(container) {
        container.innerHTML = this.filteredFiles.map(file => `
            <div class="file-item grid-item ${this.selectedFiles.has(file.id) ? 'selected' : ''}" 
                 data-file-id="${file.id}" data-file-type="${file.type}">
                <div class="file-checkbox">
                    <input type="checkbox" ${this.selectedFiles.has(file.id) ? 'checked' : ''}>
                </div>
                
                <div class="file-icon">
                    ${this.getFileIcon(file)}
                </div>
                
                <div class="file-info">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                        <span class="file-date">${this.formatDate(file.modified_at)}</span>
                    </div>
                </div>
                
                <div class="file-sync-status">
                    ${this.getSyncStatusIcon(file.sync_status)}
                </div>
                
                <div class="file-actions">
                    <button class="file-action-button" data-action="download" title="Download">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-15"/>
                            <polyline points="7,10 12,15 17,10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                    </button>
                    <button class="file-action-button" data-action="share" title="Share">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="18" cy="5" r="3"/>
                            <circle cx="6" cy="12" r="3"/>
                            <circle cx="18" cy="19" r="3"/>
                            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                        </svg>
                    </button>
                    <button class="file-action-button" data-action="more" title="More">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="1"/>
                            <circle cx="19" cy="12" r="1"/>
                            <circle cx="5" cy="12" r="1"/>
                        </svg>
                    </button>
                </div>
            </div>
        `).join('');
        
        this.attachFileEventListeners();
    }

    renderListView(container) {
        container.innerHTML = `
            <div class="list-header">
                <div class="list-column checkbox-column">
                    <input type="checkbox" id="select-all">
                </div>
                <div class="list-column name-column sortable" data-sort="name">
                    Name ${this.getSortIcon('name')}
                </div>
                <div class="list-column size-column sortable" data-sort="size">
                    Size ${this.getSortIcon('size')}
                </div>
                <div class="list-column date-column sortable" data-sort="modified">
                    Modified ${this.getSortIcon('modified')}
                </div>
                <div class="list-column status-column">Status</div>
                <div class="list-column actions-column">Actions</div>
            </div>
            
            <div class="list-body">
                ${this.filteredFiles.map(file => `
                    <div class="file-item list-item ${this.selectedFiles.has(file.id) ? 'selected' : ''}" 
                         data-file-id="${file.id}" data-file-type="${file.type}">
                        <div class="list-column checkbox-column">
                            <input type="checkbox" ${this.selectedFiles.has(file.id) ? 'checked' : ''}>
                        </div>
                        <div class="list-column name-column">
                            <div class="file-name-with-icon">
                                ${this.getFileIcon(file)}
                                <span class="file-name" title="${file.name}">${file.name}</span>
                            </div>
                        </div>
                        <div class="list-column size-column">
                            ${this.formatFileSize(file.size)}
                        </div>
                        <div class="list-column date-column">
                            ${this.formatDate(file.modified_at)}
                        </div>
                        <div class="list-column status-column">
                            ${this.getSyncStatusIcon(file.sync_status)}
                        </div>
                        <div class="list-column actions-column">
                            <button class="file-action-button" data-action="download" title="Download">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-15"/>
                                    <polyline points="7,10 12,15 17,10"/>
                                    <line x1="12" y1="15" x2="12" y2="3"/>
                                </svg>
                            </button>
                            <button class="file-action-button" data-action="share" title="Share">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="18" cy="5" r="3"/>
                                    <circle cx="6" cy="12" r="3"/>
                                    <circle cx="18" cy="19" r="3"/>
                                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                                    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                                </svg>
                            </button>
                            <button class="file-action-button" data-action="more" title="More">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="1"/>
                                    <circle cx="19" cy="12" r="1"/>
                                    <circle cx="5" cy="12" r="1"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        this.attachFileEventListeners();
        this.attachListEventListeners();
    }

    attachFileEventListeners() {
        // File selection
        document.querySelectorAll('.file-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const fileItem = e.target.closest('.file-item');
                const fileId = fileItem.dataset.fileId;
                
                if (e.target.checked) {
                    this.selectedFiles.add(fileId);
                    fileItem.classList.add('selected');
                } else {
                    this.selectedFiles.delete(fileId);
                    fileItem.classList.remove('selected');
                }
                
                this.updateSelectionInfo();
            });
        });

        // File double-click (open/preview)
        document.querySelectorAll('.file-item .file-name').forEach(nameElement => {
            nameElement.addEventListener('dblclick', (e) => {
                const fileItem = e.target.closest('.file-item');
                const fileId = fileItem.dataset.fileId;
                this.openFile(fileId);
            });
        });

        // File action buttons
        document.querySelectorAll('.file-action-button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.target.closest('.file-action-button').dataset.action;
                const fileItem = e.target.closest('.file-item');
                const fileId = fileItem.dataset.fileId;
                
                this.handleFileAction(action, fileId);
            });
        });
    }

    attachListEventListeners() {
        // Select all checkbox
        const selectAllCheckbox = document.getElementById('select-all');
        selectAllCheckbox?.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            
            document.querySelectorAll('.file-item input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = isChecked;
                const fileItem = checkbox.closest('.file-item');
                const fileId = fileItem.dataset.fileId;
                
                if (isChecked) {
                    this.selectedFiles.add(fileId);
                    fileItem.classList.add('selected');
                } else {
                    this.selectedFiles.delete(fileId);
                    fileItem.classList.remove('selected');
                }
            });
            
            this.updateSelectionInfo();
        });

        // Column sorting
        document.querySelectorAll('.sortable').forEach(column => {
            column.addEventListener('click', (e) => {
                const sortBy = e.target.dataset.sort;
                this.setSortBy(sortBy);
            });
        });
    }

    // Utility methods continue in next part...
    getFileIcon(file) {
        const iconMap = {
            'folder': '📁',
            'image': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'document': '📄',
            'pdf': '📕',
            'archive': '📦',
            'code': '💻',
            'default': '📄'
        };
        
        return iconMap[file.type] || iconMap.default;
    }

    getSyncStatusIcon(status) {
        const statusMap = {
            'local': 'L',      // Local only
            'cloud': 'C',      // Cloud only
            'synced': 'S',     // Synced
            'error': '!',      // Error
            'syncing': '⏳'    // Syncing
        };
        
        const icon = statusMap[status] || '?';
        return `<span class="sync-status sync-${status}" title="${status}">${icon}</span>`;
    }

    getSortIcon(column) {
        if (this.sortBy !== column) {
            return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 9l4-4 4 4"/><path d="M16 15l-4 4-4-4"/></svg>';
        }
        
        if (this.sortOrder === 'asc') {
            return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 15l4-4 4 4"/></svg>';
        } else {
            return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 9l4 4 4-4"/></svg>';
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
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

    setViewMode(viewMode) {
        this.viewMode = viewMode;
        localStorage.setItem('file_view_mode', viewMode);
        
        // Update button states
        document.querySelectorAll('.view-button').forEach(button => {
            button.classList.toggle('active', button.dataset.view === viewMode);
        });
        
        this.renderFiles();
    }

    setSortBy(sortBy) {
        if (this.sortBy === sortBy) {
            this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortBy = sortBy;
            this.sortOrder = 'asc';
        }
        
        this.sortFiles();
        this.renderFiles();
    }

    sortFiles() {
        this.filteredFiles.sort((a, b) => {
            let aVal = a[this.sortBy];
            let bVal = b[this.sortBy];
            
            if (this.sortBy === 'size') {
                aVal = parseInt(aVal) || 0;
                bVal = parseInt(bVal) || 0;
            } else if (this.sortBy === 'modified') {
                aVal = new Date(aVal);
                bVal = new Date(bVal);
            } else {
                aVal = aVal?.toString().toLowerCase() || '';
                bVal = bVal?.toString().toLowerCase() || '';
            }
            
            if (aVal < bVal) return this.sortOrder === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
    }

    handleSearch(query) {
        const searchClear = document.getElementById('search-clear');
        
        if (query.trim() === '') {
            this.filteredFiles = [...this.files];
            searchClear.style.display = 'none';
        } else {
            this.filteredFiles = this.files.filter(file =>
                file.name.toLowerCase().includes(query.toLowerCase()) ||
                file.tags?.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
            );
            searchClear.style.display = 'block';
        }
        
        this.renderFiles();
    }

    updateSelectionInfo() {
        const selectionInfo = document.getElementById('selection-info');
        const selectionCount = document.getElementById('selection-count');
        
        if (this.selectedFiles.size > 0) {
            selectionInfo.style.display = 'flex';
            selectionCount.textContent = this.selectedFiles.size;
        } else {
            selectionInfo.style.display = 'none';
        }
    }

    setLoading(loading) {
        this.isLoading = loading;
        const spinner = document.getElementById('loading-spinner');
        const fileList = document.getElementById('file-list');
        
        spinner.style.display = loading ? 'flex' : 'none';
        fileList.style.display = loading ? 'none' : 'block';
    }

    async showUploadDialog() {
        await this.fileUploader.show();
    }

    async uploadFiles(files) {
        try {
            const results = await this.fileUploader.uploadFiles(files);
            // Refresh file list after upload
            await this.loadFiles();
            return results;
        } catch (error) {
            console.error('Upload failed:', error);
            NotificationManager.error('Upload failed');
        }
    }

    async openFile(fileId) {
        const file = this.files.find(f => f.id === fileId);
        if (file) {
            await this.fileViewer.show(file);
        }
    }

    async handleFileAction(action, fileId) {
        const file = this.files.find(f => f.id === fileId);
        if (!file) return;

        switch (action) {
            case 'download':
                await this.downloadFile(file);
                break;
            case 'share':
                await this.shareFile(file);
                break;
            case 'more':
                this.showFileContextMenu(file);
                break;
        }
    }

    async downloadFile(file) {
        try {
            const response = await ApiClient.get(`/file-sync/download/${file.id}`);
            // Handle download logic
            NotificationManager.success(`Downloaded ${file.name}`);
        } catch (error) {
            NotificationManager.error('Download failed');
        }
    }

    async shareFile(file) {
        // Implement share functionality
        NotificationManager.info('Share functionality coming soon!');
    }

    async deleteSelectedFiles() {
        if (this.selectedFiles.size === 0) return;
        
        const confirmed = confirm(`Delete ${this.selectedFiles.size} files?`);
        if (!confirmed) return;
        
        try {
            for (const fileId of this.selectedFiles) {
                await ApiClient.delete(`/metadata/files/${fileId}`);
            }
            
            this.selectedFiles.clear();
            await this.loadFiles();
            NotificationManager.success('Files deleted successfully');
        } catch (error) {
            NotificationManager.error('Failed to delete files');
        }
    }

    async downloadSelectedFiles() {
        if (this.selectedFiles.size === 0) return;
        
        NotificationManager.info('Downloading selected files...');
        // Implement batch download
    }

    async tagSelectedFiles() {
        if (this.selectedFiles.size === 0) return;
        
        // Show tag dialog
        GlobalEvents.emit('showTagDialog', Array.from(this.selectedFiles));
    }

    async createNewFolder() {
        const folderName = prompt('Enter folder name:');
        if (!folderName) return;
        
        try {
            await ApiClient.post('/metadata/folders', {
                name: folderName,
                parent_path: this.currentPath
            });
            
            await this.loadFiles();
            NotificationManager.success('Folder created successfully');
        } catch (error) {
            NotificationManager.error('Failed to create folder');
        }
    }

    showFileContextMenu(file) {
        // Implement context menu
        console.log('Context menu for:', file);
    }

    // Event handlers for global events
    handleFileUploaded(file) {
        this.files.push(file);
        this.filteredFiles = [...this.files];
        this.renderFiles();
    }

    handleFileDeleted(fileId) {
        this.files = this.files.filter(f => f.id !== fileId);
        this.filteredFiles = this.filteredFiles.filter(f => f.id !== fileId);
        this.selectedFiles.delete(fileId);
        this.renderFiles();
        this.updateSelectionInfo();
    }
}