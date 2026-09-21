/**
 * File Uploader Component with Drag & Drop and Progress
 */

import { ApiClient } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';
import { GlobalEvents } from '../../utils/events.js';

export class FileUploader {
    constructor() {
        this.isVisible = false;
        this.uploads = new Map(); // Track ongoing uploads
        this.allowedTypes = ['*']; // Allow all types by default
        this.maxFileSize = 100 * 1024 * 1024; // 100MB default
    }

    async show() {
        if (this.isVisible) return;
        
        this.isVisible = true;
        this.createModal();
        this.attachEventListeners();
    }

    hide() {
        if (!this.isVisible) return;
        
        this.isVisible = false;
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.remove();
        }
    }

    createModal() {
        const modal = document.createElement('div');
        modal.id = 'upload-modal';
        modal.className = 'modal-overlay';
        
        modal.innerHTML = `
            <div class="modal-content upload-modal">
                <div class="modal-header">
                    <h2>Upload Files</h2>
                    <button class="modal-close" id="upload-modal-close">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
                
                <div class="modal-body">
                    <div class="upload-section">
                        <div class="upload-drop-zone" id="upload-drop-zone">
                            <div class="drop-zone-content">
                                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                    <polyline points="17,8 12,3 7,8"/>
                                    <line x1="12" y1="3" x2="12" y2="15"/>
                                </svg>
                                <h3>Drop files here or click to browse</h3>
                                <p>Maximum file size: ${this.formatFileSize(this.maxFileSize)}</p>
                                <input type="file" id="file-input" multiple style="display: none;">
                                <button class="browse-button" id="browse-button">Browse Files</button>
                            </div>
                        </div>
                        
                        <div class="upload-options">
                            <div class="option-group">
                                <label>
                                    <input type="checkbox" id="auto-tag" checked>
                                    Automatically generate tags
                                </label>
                            </div>
                            
                            <div class="option-group">
                                <label>
                                    <input type="checkbox" id="auto-sync" checked>
                                    Auto-sync to cloud
                                </label>
                            </div>
                            
                            <div class="option-group">
                                <label for="folder-select">Upload to folder:</label>
                                <select id="folder-select">
                                    <option value="/">Root</option>
                                    <option value="/Documents">Documents</option>
                                    <option value="/Images">Images</option>
                                    <option value="/Projects">Projects</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    
                    <div class="upload-queue" id="upload-queue" style="display: none;">
                        <div class="queue-header">
                            <h3>Upload Progress</h3>
                            <div class="queue-actions">
                                <button class="action-button small" id="pause-all">Pause All</button>
                                <button class="action-button small" id="cancel-all">Cancel All</button>
                            </div>
                        </div>
                        
                        <div class="queue-summary">
                            <div class="summary-item">
                                <span class="summary-label">Total:</span>
                                <span id="total-files">0</span> files
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Completed:</span>
                                <span id="completed-files">0</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Speed:</span>
                                <span id="upload-speed">0 KB/s</span>
                            </div>
                        </div>
                        
                        <div class="overall-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" id="overall-progress-fill"></div>
                            </div>
                            <div class="progress-text">
                                <span id="overall-progress-text">0%</span>
                            </div>
                        </div>
                        
                        <div class="upload-items" id="upload-items">
                            <!-- Upload items will be added here -->
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="action-button secondary" id="upload-cancel">Cancel</button>
                    <button class="action-button primary" id="upload-start" disabled>Start Upload</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    attachEventListeners() {
        const modal = document.getElementById('upload-modal');
        const closeBtn = document.getElementById('upload-modal-close');
        const cancelBtn = document.getElementById('upload-cancel');
        const startBtn = document.getElementById('upload-start');
        const browseBtn = document.getElementById('browse-button');
        const fileInput = document.getElementById('file-input');
        const dropZone = document.getElementById('upload-drop-zone');
        
        // Close modal
        closeBtn.addEventListener('click', () => this.hide());
        cancelBtn.addEventListener('click', () => this.hide());
        
        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hide();
            }
        });
        
        // Browse files
        browseBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files));
        
        // Drag and drop
        dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        dropZone.addEventListener('drop', this.handleDrop.bind(this));
        dropZone.addEventListener('click', () => fileInput.click());
        
        // Start upload
        startBtn.addEventListener('click', () => this.startUpload());
        
        // Queue actions
        document.getElementById('pause-all')?.addEventListener('click', () => this.pauseAll());
        document.getElementById('cancel-all')?.addEventListener('click', () => this.cancelAll());
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        e.currentTarget.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        this.handleFileSelect(files);
    }

    handleFileSelect(files) {
        if (!files || files.length === 0) return;
        
        const validFiles = this.validateFiles(files);
        if (validFiles.length === 0) return;
        
        this.addFilesToQueue(validFiles);
        this.showUploadQueue();
        this.updateStartButton();
    }

    validateFiles(files) {
        const validFiles = [];
        
        for (const file of files) {
            // Check file size
            if (file.size > this.maxFileSize) {
                NotificationManager.warning(`File "${file.name}" is too large (max: ${this.formatFileSize(this.maxFileSize)})`);
                continue;
            }
            
            // Check file type (if restrictions exist)
            if (this.allowedTypes.length > 0 && !this.allowedTypes.includes('*')) {
                const fileType = file.type || 'application/octet-stream';
                const isAllowed = this.allowedTypes.some(type => 
                    fileType.startsWith(type.replace('*', ''))
                );
                
                if (!isAllowed) {
                    NotificationManager.warning(`File type not allowed: ${file.name}`);
                    continue;
                }
            }
            
            validFiles.push(file);
        }
        
        return validFiles;
    }

    addFilesToQueue(files) {
        const uploadItems = document.getElementById('upload-items');
        const totalFiles = document.getElementById('total-files');
        
        files.forEach(file => {
            const uploadId = this.generateUploadId();
            const uploadItem = this.createUploadItem(uploadId, file);
            
            this.uploads.set(uploadId, {
                id: uploadId,
                file: file,
                status: 'pending',
                progress: 0,
                speed: 0,
                element: uploadItem
            });
            
            uploadItems.appendChild(uploadItem);
        });
        
        totalFiles.textContent = this.uploads.size;
    }

    createUploadItem(uploadId, file) {
        const div = document.createElement('div');
        div.className = 'upload-item';
        div.dataset.uploadId = uploadId;
        
        div.innerHTML = `
            <div class="upload-item-info">
                <div class="file-icon">${this.getFileIcon(file)}</div>
                <div class="file-details">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                        <span class="upload-status">Pending</span>
                    </div>
                </div>
            </div>
            
            <div class="upload-progress">
                <div class="progress-bar small">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-details">
                    <span class="progress-percent">0%</span>
                    <span class="upload-speed">0 KB/s</span>
                </div>
            </div>
            
            <div class="upload-actions">
                <button class="upload-action-button pause" title="Pause" style="display: none;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="6" y="4" width="4" height="16"/>
                        <rect x="14" y="4" width="4" height="16"/>
                    </svg>
                </button>
                <button class="upload-action-button cancel" title="Cancel">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        `;
        
        // Attach item event listeners
        const pauseBtn = div.querySelector('.pause');
        const cancelBtn = div.querySelector('.cancel');
        
        pauseBtn.addEventListener('click', () => this.pauseUpload(uploadId));
        cancelBtn.addEventListener('click', () => this.cancelUpload(uploadId));
        
        return div;
    }

    showUploadQueue() {
        const uploadSection = document.querySelector('.upload-section');
        const uploadQueue = document.getElementById('upload-queue');
        
        uploadSection.style.display = 'none';
        uploadQueue.style.display = 'block';
    }

    updateStartButton() {
        const startBtn = document.getElementById('upload-start');
        startBtn.disabled = this.uploads.size === 0;
        startBtn.textContent = `Upload ${this.uploads.size} file${this.uploads.size !== 1 ? 's' : ''}`;
    }

    async startUpload() {
        const startBtn = document.getElementById('upload-start');
        startBtn.disabled = true;
        startBtn.textContent = 'Uploading...';
        
        const autoTag = document.getElementById('auto-tag').checked;
        const autoSync = document.getElementById('auto-sync').checked;
        const folder = document.getElementById('folder-select').value;
        
        // Start all uploads
        const uploadPromises = Array.from(this.uploads.values()).map(upload => 
            this.uploadFile(upload, { autoTag, autoSync, folder })
        );
        
        try {
            await Promise.all(uploadPromises);
            NotificationManager.success('All files uploaded successfully!');
            
            // Emit global event
            GlobalEvents.emit('filesUploaded', Array.from(this.uploads.values()));
            
            // Close modal after a short delay
            setTimeout(() => this.hide(), 1000);
        } catch (error) {
            console.error('Upload error:', error);
            NotificationManager.error('Some uploads failed');
        }
    }

    async uploadFile(upload, options = {}) {
        const { file } = upload;
        
        this.updateUploadStatus(upload.id, 'uploading', 0);
        
        try {
            const result = await ApiClient.uploadFile(
                '/metadata/upload',
                file,
                (progress, loaded, total) => {
                    this.updateUploadProgress(upload.id, progress, loaded, total);
                },
                {
                    folder: options.folder || '/',
                    auto_tag: options.autoTag || false,
                    auto_sync: options.autoSync || false
                }
            );
            
            this.updateUploadStatus(upload.id, 'completed', 100);
            this.updateCompletedCount();
            
            return result;
        } catch (error) {
            this.updateUploadStatus(upload.id, 'error', 0);
            throw error;
        }
    }

    updateUploadStatus(uploadId, status, progress) {
        const upload = this.uploads.get(uploadId);
        if (!upload) return;
        
        upload.status = status;
        upload.progress = progress;
        
        const statusElement = upload.element.querySelector('.upload-status');
        const progressFill = upload.element.querySelector('.progress-fill');
        const progressPercent = upload.element.querySelector('.progress-percent');
        
        statusElement.textContent = this.getStatusText(status);
        statusElement.className = `upload-status ${status}`;
        
        progressFill.style.width = `${progress}%`;
        progressPercent.textContent = `${Math.round(progress)}%`;
        
        this.updateOverallProgress();
    }

    updateUploadProgress(uploadId, progress, loaded, total) {
        const upload = this.uploads.get(uploadId);
        if (!upload) return;
        
        upload.progress = progress;
        upload.loaded = loaded;
        upload.total = total;
        
        // Calculate speed
        const now = Date.now();
        if (upload.lastUpdate) {
            const timeDiff = (now - upload.lastUpdate) / 1000; // seconds
            const bytesDiff = loaded - (upload.lastLoaded || 0);
            upload.speed = bytesDiff / timeDiff; // bytes per second
        }
        
        upload.lastUpdate = now;
        upload.lastLoaded = loaded;
        
        const progressFill = upload.element.querySelector('.progress-fill');
        const progressPercent = upload.element.querySelector('.progress-percent');
        const speedElement = upload.element.querySelector('.upload-speed');
        
        progressFill.style.width = `${progress}%`;
        progressPercent.textContent = `${Math.round(progress)}%`;
        speedElement.textContent = this.formatSpeed(upload.speed);
        
        this.updateOverallProgress();
        this.updateOverallSpeed();
    }

    updateOverallProgress() {
        const totalProgress = Array.from(this.uploads.values())
            .reduce((sum, upload) => sum + upload.progress, 0);
        const avgProgress = this.uploads.size > 0 ? totalProgress / this.uploads.size : 0;
        
        const progressFill = document.getElementById('overall-progress-fill');
        const progressText = document.getElementById('overall-progress-text');
        
        progressFill.style.width = `${avgProgress}%`;
        progressText.textContent = `${Math.round(avgProgress)}%`;
    }

    updateOverallSpeed() {
        const totalSpeed = Array.from(this.uploads.values())
            .filter(upload => upload.status === 'uploading')
            .reduce((sum, upload) => sum + (upload.speed || 0), 0);
        
        const speedElement = document.getElementById('upload-speed');
        speedElement.textContent = this.formatSpeed(totalSpeed);
    }

    updateCompletedCount() {
        const completedCount = Array.from(this.uploads.values())
            .filter(upload => upload.status === 'completed').length;
        
        const completedElement = document.getElementById('completed-files');
        completedElement.textContent = completedCount;
    }

    pauseUpload(uploadId) {
        // Implementation depends on your upload mechanism
        // For now, just update status
        this.updateUploadStatus(uploadId, 'paused', this.uploads.get(uploadId)?.progress || 0);
    }

    cancelUpload(uploadId) {
        const upload = this.uploads.get(uploadId);
        if (!upload) return;
        
        this.uploads.delete(uploadId);
        upload.element.remove();
        
        this.updateStartButton();
        this.updateOverallProgress();
        
        const totalFiles = document.getElementById('total-files');
        totalFiles.textContent = this.uploads.size;
    }

    pauseAll() {
        this.uploads.forEach((upload, uploadId) => {
            if (upload.status === 'uploading') {
                this.pauseUpload(uploadId);
            }
        });
    }

    cancelAll() {
        const confirmed = confirm('Cancel all uploads?');
        if (!confirmed) return;
        
        Array.from(this.uploads.keys()).forEach(uploadId => {
            this.cancelUpload(uploadId);
        });
    }

    // Utility methods for external use
    async uploadFiles(files) {
        const validFiles = this.validateFiles(files);
        if (validFiles.length === 0) return [];
        
        const results = [];
        
        for (const file of validFiles) {
            try {
                const result = await ApiClient.uploadFile('/metadata/upload', file);
                results.push({ file: file.name, success: true, result });
                GlobalEvents.emit('fileUploaded', result);
            } catch (error) {
                results.push({ file: file.name, success: false, error: error.message });
            }
        }
        
        return results;
    }

    // Helper methods
    generateUploadId() {
        return 'upload_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    getFileIcon(file) {
        const type = file.type.split('/')[0];
        const iconMap = {
            'image': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'application': '📄',
            'text': '📝'
        };
        return iconMap[type] || '📄';
    }

    getStatusText(status) {
        const statusMap = {
            'pending': 'Pending',
            'uploading': 'Uploading',
            'completed': 'Completed',
            'paused': 'Paused',
            'error': 'Error'
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

    formatSpeed(bytesPerSecond) {
        if (!bytesPerSecond || bytesPerSecond === 0) return '0 KB/s';
        return this.formatFileSize(bytesPerSecond) + '/s';
    }
}