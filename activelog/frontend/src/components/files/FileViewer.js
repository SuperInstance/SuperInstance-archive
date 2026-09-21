/**
 * File Viewer Component
 */

import { ApiClient } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class FileViewer {
    constructor() {
        this.isVisible = false;
        this.currentFile = null;
    }

    async show(file) {
        if (this.isVisible) return;
        
        this.isVisible = true;
        this.currentFile = file;
        this.createModal();
        this.attachEventListeners();
        await this.loadFileContent();
    }

    hide() {
        if (!this.isVisible) return;
        
        this.isVisible = false;
        const modal = document.getElementById('file-viewer-modal');
        if (modal) {
            modal.remove();
        }
        this.currentFile = null;
    }

    createModal() {
        const modal = document.createElement('div');
        modal.id = 'file-viewer-modal';
        modal.className = 'modal-overlay';
        
        modal.innerHTML = `
            <div class="modal-content file-viewer-modal">
                <div class="modal-header">
                    <div class="file-viewer-title">
                        <div class="file-icon">${this.getFileIcon(this.currentFile)}</div>
                        <div class="file-details">
                            <h2>${this.currentFile.name}</h2>
                            <div class="file-meta">
                                <span>${this.formatFileSize(this.currentFile.size)}</span>
                                <span>•</span>
                                <span>${this.formatDate(this.currentFile.modified_at)}</span>
                                <span>•</span>
                                <span class="sync-status sync-${this.currentFile.sync_status}">
                                    ${this.getSyncStatusText(this.currentFile.sync_status)}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="file-viewer-actions">
                        <button class="action-button" id="download-file" title="Download">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7,10 12,15 17,10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                        </button>
                        <button class="action-button" id="share-file" title="Share">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="18" cy="5" r="3"/>
                                <circle cx="6" cy="12" r="3"/>
                                <circle cx="18" cy="19" r="3"/>
                                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                            </svg>
                        </button>
                        <button class="modal-close" id="file-viewer-close">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div class="file-content" id="file-content">
                        <div class="loading-placeholder">Loading file content...</div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <div class="file-tags" id="file-tags">
                        <!-- Tags will be loaded here -->
                    </div>
                    <div class="file-actions">
                        <button class="action-button secondary" id="edit-tags">Edit Tags</button>
                        <button class="action-button primary" id="open-externally">Open Externally</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    attachEventListeners() {
        const modal = document.getElementById('file-viewer-modal');
        const closeBtn = document.getElementById('file-viewer-close');
        const downloadBtn = document.getElementById('download-file');
        const shareBtn = document.getElementById('share-file');
        const editTagsBtn = document.getElementById('edit-tags');
        const openExternallyBtn = document.getElementById('open-externally');
        
        // Close modal
        closeBtn.addEventListener('click', () => this.hide());
        
        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hide();
            }
        });
        
        // File actions
        downloadBtn.addEventListener('click', () => this.downloadFile());
        shareBtn.addEventListener('click', () => this.shareFile());
        editTagsBtn.addEventListener('click', () => this.editTags());
        openExternallyBtn.addEventListener('click', () => this.openExternally());
        
        // Keyboard navigation
        document.addEventListener('keydown', this.handleKeydown.bind(this));
    }

    async loadFileContent() {
        const contentContainer = document.getElementById('file-content');
        
        try {
            const fileType = this.getFileType(this.currentFile);
            
            switch (fileType) {
                case 'image':
                    await this.renderImagePreview(contentContainer);
                    break;
                case 'text':
                    await this.renderTextPreview(contentContainer);
                    break;
                case 'pdf':
                    await this.renderPDFPreview(contentContainer);
                    break;
                case 'video':
                    await this.renderVideoPreview(contentContainer);
                    break;
                case 'audio':
                    await this.renderAudioPreview(contentContainer);
                    break;
                default:
                    this.renderUnsupportedPreview(contentContainer);
            }
            
            // Load tags
            await this.loadFileTags();
            
        } catch (error) {
            console.error('Failed to load file content:', error);
            contentContainer.innerHTML = `
                <div class="preview-error">
                    <div class="error-icon">⚠️</div>
                    <h3>Unable to preview file</h3>
                    <p>There was an error loading the file content.</p>
                </div>
            `;
        }
    }

    async renderImagePreview(container) {
        const imageUrl = await this.getFileUrl();
        
        container.innerHTML = `
            <div class="image-preview">
                <img src="${imageUrl}" alt="${this.currentFile.name}" />
            </div>
        `;
    }

    async renderTextPreview(container) {
        const content = await this.getFileContent();
        
        container.innerHTML = `
            <div class="text-preview">
                <pre><code>${this.escapeHtml(content)}</code></pre>
            </div>
        `;
    }

    async renderPDFPreview(container) {
        const fileUrl = await this.getFileUrl();
        
        container.innerHTML = `
            <div class="pdf-preview">
                <iframe src="${fileUrl}" width="100%" height="600px"></iframe>
            </div>
        `;
    }

    async renderVideoPreview(container) {
        const videoUrl = await this.getFileUrl();
        
        container.innerHTML = `
            <div class="video-preview">
                <video controls width="100%">
                    <source src="${videoUrl}" type="${this.currentFile.mime_type}">
                    Your browser does not support the video tag.
                </video>
            </div>
        `;
    }

    async renderAudioPreview(container) {
        const audioUrl = await this.getFileUrl();
        
        container.innerHTML = `
            <div class="audio-preview">
                <audio controls>
                    <source src="${audioUrl}" type="${this.currentFile.mime_type}">
                    Your browser does not support the audio tag.
                </audio>
                <div class="audio-info">
                    <h3>${this.currentFile.name}</h3>
                    <p>Duration: ${this.currentFile.metadata?.duration || 'Unknown'}</p>
                </div>
            </div>
        `;
    }

    renderUnsupportedPreview(container) {
        container.innerHTML = `
            <div class="unsupported-preview">
                <div class="preview-icon">${this.getFileIcon(this.currentFile)}</div>
                <h3>Preview not available</h3>
                <p>This file type cannot be previewed in the browser.</p>
                <div class="file-info">
                    <div class="info-item">
                        <span class="info-label">Type:</span>
                        <span class="info-value">${this.currentFile.mime_type || 'Unknown'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Size:</span>
                        <span class="info-value">${this.formatFileSize(this.currentFile.size)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Modified:</span>
                        <span class="info-value">${this.formatDate(this.currentFile.modified_at)}</span>
                    </div>
                </div>
            </div>
        `;
    }

    async loadFileTags() {
        try {
            const response = await ApiClient.get(`/metadata/files/${this.currentFile.id}/tags`);
            const tags = response.tags || [];
            
            const tagsContainer = document.getElementById('file-tags');
            
            if (tags.length === 0) {
                tagsContainer.innerHTML = '<span class="no-tags">No tags</span>';
            } else {
                tagsContainer.innerHTML = tags.map(tag => `
                    <span class="file-tag" style="background-color: ${tag.color || '#ccc'}">
                        ${tag.name}
                    </span>
                `).join('');
            }
        } catch (error) {
            console.error('Failed to load file tags:', error);
        }
    }

    async getFileUrl() {
        try {
            const response = await ApiClient.get(`/metadata/files/${this.currentFile.id}/url`);
            return response.url;
        } catch (error) {
            throw new Error('Failed to get file URL');
        }
    }

    async getFileContent() {
        try {
            const response = await ApiClient.get(`/metadata/files/${this.currentFile.id}/content`);
            return response.content;
        } catch (error) {
            throw new Error('Failed to get file content');
        }
    }

    async downloadFile() {
        try {
            const url = await this.getFileUrl();
            const link = document.createElement('a');
            link.href = url;
            link.download = this.currentFile.name;
            link.click();
            
            NotificationManager.success('Download started');
        } catch (error) {
            NotificationManager.error('Download failed');
        }
    }

    async shareFile() {
        try {
            if (navigator.share) {
                await navigator.share({
                    title: this.currentFile.name,
                    text: `Check out this file: ${this.currentFile.name}`,
                    url: window.location.href
                });
            } else {
                // Fallback: copy link to clipboard
                await navigator.clipboard.writeText(window.location.href);
                NotificationManager.success('Link copied to clipboard');
            }
        } catch (error) {
            NotificationManager.error('Sharing failed');
        }
    }

    editTags() {
        // Emit event to show tag editor
        GlobalEvents.emit('editFileTags', this.currentFile);
    }

    openExternally() {
        this.downloadFile(); // For now, same as download
    }

    handleKeydown(event) {
        if (!this.isVisible) return;
        
        switch (event.key) {
            case 'Escape':
                event.preventDefault();
                this.hide();
                break;
            case 'd':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    this.downloadFile();
                }
                break;
        }
    }

    // Utility methods
    getFileType(file) {
        const mimeType = file.mime_type || '';
        
        if (mimeType.startsWith('image/')) return 'image';
        if (mimeType.startsWith('video/')) return 'video';
        if (mimeType.startsWith('audio/')) return 'audio';
        if (mimeType === 'application/pdf') return 'pdf';
        if (mimeType.startsWith('text/') || file.name.match(/\.(txt|md|js|css|html|json|xml|csv)$/i)) {
            return 'text';
        }
        
        return 'unknown';
    }

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

    getSyncStatusText(status) {
        const statusMap = {
            'local': 'Local Only',
            'cloud': 'Cloud Only',
            'synced': 'Synced',
            'error': 'Sync Error',
            'syncing': 'Syncing...'
        };
        return statusMap[status] || 'Unknown';
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
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
}