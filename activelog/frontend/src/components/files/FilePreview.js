/**
 * Comprehensive File Preview Component
 * Supports images, videos, documents, audio, and more
 */

import { API } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class FilePreview {
    constructor(options = {}) {
        this.container = null;
        this.currentFile = null;
        this.isOpen = false;
        this.isFullscreen = false;
        this.scale = 1;
        
        this.onClose = options.onClose || (() => {});
        this.onNavigate = options.onNavigate || (() => {});
        this.onAction = options.onAction || (() => {});
        
        this.supportedTypes = {
            image: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'],
            video: ['mp4', 'webm', 'ogg', 'avi', 'mov', 'wmv', 'flv', 'm4v'],
            audio: ['mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac', 'wma'],
            document: ['pdf', 'txt', 'md', 'rtf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
            code: ['js', 'ts', 'jsx', 'tsx', 'html', 'css', 'scss', 'json', 'xml', 'py', 'java', 'cpp', 'c', 'php', 'rb', 'go', 'rs'],
            archive: ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'],
            model: ['glb', 'gltf', 'obj', 'fbx', 'dae', 'stl'],
            cad: ['dwg', 'dxf', 'step', 'iges']
        };
        
        this.setupKeyboardListeners();
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="file-preview ${this.isOpen ? 'open' : ''}" id="file-preview">
                <div class="preview-backdrop"></div>
                <div class="preview-container">
                    <div class="preview-header">
                        <div class="preview-info">
                            <div class="file-name" id="preview-file-name">Loading...</div>
                            <div class="file-meta" id="preview-file-meta">
                                <span class="file-size">0 KB</span>
                                <span class="file-type">Unknown</span>
                                <span class="file-modified">Unknown</span>
                            </div>
                        </div>
                        
                        <div class="preview-actions">
                            <button class="btn-icon download-btn" title="Download">
                                <i data-lucide="download"></i>
                            </button>
                            <button class="btn-icon share-btn" title="Share">
                                <i data-lucide="share"></i>
                            </button>
                            <button class="btn-icon fullscreen-btn" title="Fullscreen">
                                <i data-lucide="maximize"></i>
                            </button>
                            <button class="btn-icon more-btn" title="More actions">
                                <i data-lucide="more-horizontal"></i>
                            </button>
                            <button class="btn-icon close-btn" title="Close">
                                <i data-lucide="x"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="preview-content" id="preview-content">
                        <div class="preview-loading">
                            <i data-lucide="loader" class="spin"></i>
                            <span>Loading preview...</span>
                        </div>
                    </div>
                    
                    <div class="preview-controls" id="preview-controls" style="display: none;">
                        <!-- Dynamic controls based on file type -->
                    </div>
                    
                    <div class="preview-navigation" id="preview-navigation" style="display: none;">
                        <button class="nav-btn prev-btn" title="Previous">
                            <i data-lucide="chevron-left"></i>
                        </button>
                        <div class="nav-info">
                            <span class="nav-current">1</span> of <span class="nav-total">1</span>
                        </div>
                        <button class="nav-btn next-btn" title="Next">
                            <i data-lucide="chevron-right"></i>
                        </button>
                    </div>
                </div>
                
                <!-- Context Menu -->
                <div class="preview-context-menu" id="preview-context-menu" style="display: none;">
                    <div class="context-menu-item" data-action="download">
                        <i data-lucide="download"></i>
                        <span>Download</span>
                    </div>
                    <div class="context-menu-item" data-action="copy">
                        <i data-lucide="copy"></i>
                        <span>Copy</span>
                    </div>
                    <div class="context-menu-item" data-action="share">
                        <i data-lucide="share"></i>
                        <span>Share</span>
                    </div>
                    <div class="context-menu-separator"></div>
                    <div class="context-menu-item" data-action="edit">
                        <i data-lucide="edit"></i>
                        <span>Edit</span>
                    </div>
                    <div class="context-menu-item" data-action="rename">
                        <i data-lucide="edit-2"></i>
                        <span>Rename</span>
                    </div>
                    <div class="context-menu-item" data-action="delete">
                        <i data-lucide="trash"></i>
                        <span>Delete</span>
                    </div>
                </div>
            </div>
        `;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Close handlers
        this.container.querySelector('.preview-backdrop').addEventListener('click', () => {
            this.close();
        });
        
        this.container.querySelector('.close-btn').addEventListener('click', () => {
            this.close();
        });
        
        // Action buttons
        this.container.querySelector('.download-btn').addEventListener('click', () => {
            this.downloadFile();
        });
        
        this.container.querySelector('.share-btn').addEventListener('click', () => {
            this.shareFile();
        });
        
        this.container.querySelector('.fullscreen-btn').addEventListener('click', () => {
            this.toggleFullscreen();
        });
        
        this.container.querySelector('.more-btn').addEventListener('click', (e) => {
            this.showContextMenu(e);
        });
        
        // Navigation
        this.container.querySelector('.prev-btn').addEventListener('click', () => {
            this.navigatePrevious();
        });
        
        this.container.querySelector('.next-btn').addEventListener('click', () => {
            this.navigateNext();
        });
        
        // Context menu
        this.container.addEventListener('contextmenu', (e) => {
            if (e.target.closest('.preview-content')) {
                e.preventDefault();
                this.showContextMenu(e);
            }
        });
        
        this.container.querySelector('#preview-context-menu').addEventListener('click', (e) => {
            const action = e.target.closest('.context-menu-item')?.dataset.action;
            if (action) {
                this.handleContextAction(action);
                this.hideContextMenu();
            }
        });
        
        // Hide context menu on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#preview-context-menu')) {
                this.hideContextMenu();
            }
        });
        
        // Zoom controls for images
        this.container.addEventListener('wheel', (e) => {
            if (e.target.closest('.image-viewer')) {
                e.preventDefault();
                this.handleZoom(e);
            }
        });
        
        // Drag for images
        this.setupImageDrag();
    }
    
    setupKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            
            switch (e.key) {
                case 'Escape':
                    this.close();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.navigatePrevious();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.navigateNext();
                    break;
                case 'F11':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
                case '+':
                case '=':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomIn();
                    }
                    break;
                case '-':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomOut();
                    }
                    break;
                case '0':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.resetZoom();
                    }
                    break;
                case ' ':
                    if (this.currentFile && this.getFileType(this.currentFile) === 'video') {
                        e.preventDefault();
                        this.togglePlayPause();
                    }
                    break;
            }
        });
    }
    
    async open(file, options = {}) {
        this.currentFile = file;
        this.isOpen = true;
        
        const previewContainer = this.container.querySelector('#file-preview');
        previewContainer.classList.add('open');
        document.body.classList.add('file-preview-open');
        
        this.updateFileInfo(file);
        this.updateNavigation(options.currentIndex, options.totalFiles);
        
        try {
            await this.loadPreview(file);
        } catch (error) {
            console.error('Failed to load preview:', error);
            this.showError('Failed to load file preview');
        }
    }
    
    close() {
        this.isOpen = false;
        this.scale = 1;
        
        const previewContainer = this.container.querySelector('#file-preview');
        previewContainer.classList.remove('open');
        document.body.classList.remove('file-preview-open');
        
        // Stop any media playback
        const mediaElements = this.container.querySelectorAll('video, audio');
        mediaElements.forEach(el => {
            el.pause();
            el.currentTime = 0;
        });
        
        // Clean up preview content
        const contentContainer = this.container.querySelector('#preview-content');
        contentContainer.innerHTML = `
            <div class="preview-loading">
                <i data-lucide="loader" class="spin"></i>
                <span>Loading preview...</span>
            </div>
        `;
        
        this.hideContextMenu();
        this.onClose();
    }
    
    async loadPreview(file) {
        const contentContainer = this.container.querySelector('#preview-content');
        const fileType = this.getFileType(file);
        
        // Show loading
        contentContainer.innerHTML = `
            <div class="preview-loading">
                <i data-lucide="loader" class="spin"></i>
                <span>Loading ${fileType} preview...</span>
            </div>
        `;
        
        try {
            switch (fileType) {
                case 'image':
                    await this.loadImagePreview(file, contentContainer);
                    break;
                case 'video':
                    await this.loadVideoPreview(file, contentContainer);
                    break;
                case 'audio':
                    await this.loadAudioPreview(file, contentContainer);
                    break;
                case 'document':
                    await this.loadDocumentPreview(file, contentContainer);
                    break;
                case 'code':
                    await this.loadCodePreview(file, contentContainer);
                    break;
                case 'archive':
                    await this.loadArchivePreview(file, contentContainer);
                    break;
                case 'model':
                    await this.loadModelPreview(file, contentContainer);
                    break;
                default:
                    this.loadGenericPreview(file, contentContainer);
            }
        } catch (error) {
            throw error;
        }
    }
    
    async loadImagePreview(file, container) {
        const imageUrl = await this.getFileUrl(file);
        
        container.innerHTML = `
            <div class="image-viewer">
                <div class="image-container" id="image-container">
                    <img src="${imageUrl}" alt="${file.name}" id="preview-image">
                </div>
            </div>
        `;
        
        const img = container.querySelector('#preview-image');
        
        return new Promise((resolve, reject) => {
            img.onload = () => {
                this.showImageControls();
                this.updateImageInfo(img);
                resolve();
            };
            
            img.onerror = () => {
                reject(new Error('Failed to load image'));
            };
        });
    }
    
    async loadVideoPreview(file, container) {
        const videoUrl = await this.getFileUrl(file);
        
        container.innerHTML = `
            <div class="video-viewer">
                <video controls preload="metadata" id="preview-video">
                    <source src="${videoUrl}" type="${file.mimeType || 'video/mp4'}">
                    Your browser does not support the video tag.
                </video>
            </div>
        `;
        
        const video = container.querySelector('#preview-video');
        this.showVideoControls(video);
        
        video.addEventListener('loadedmetadata', () => {
            this.updateVideoInfo(video);
        });
    }
    
    async loadAudioPreview(file, container) {
        const audioUrl = await this.getFileUrl(file);
        
        container.innerHTML = `
            <div class="audio-viewer">
                <div class="audio-cover">
                    <i data-lucide="music"></i>
                </div>
                <div class="audio-info">
                    <h3 class="audio-title">${file.name}</h3>
                    <p class="audio-artist">Unknown Artist</p>
                </div>
                <audio controls preload="metadata" id="preview-audio">
                    <source src="${audioUrl}" type="${file.mimeType || 'audio/mpeg'}">
                    Your browser does not support the audio tag.
                </audio>
            </div>
        `;
        
        const audio = container.querySelector('#preview-audio');
        this.showAudioControls(audio);
    }
    
    async loadDocumentPreview(file, container) {
        const extension = this.getFileExtension(file.name);
        
        if (extension === 'pdf') {
            await this.loadPdfPreview(file, container);
        } else if (['txt', 'md', 'rtf'].includes(extension)) {
            await this.loadTextPreview(file, container);
        } else if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(extension)) {
            await this.loadOfficePreview(file, container);
        } else {
            this.loadGenericPreview(file, container);
        }
    }
    
    async loadPdfPreview(file, container) {
        const pdfUrl = await this.getFileUrl(file);
        
        container.innerHTML = `
            <div class="pdf-viewer">
                <iframe src="${pdfUrl}" 
                        type="application/pdf" 
                        width="100%" 
                        height="100%">
                    <p>Your browser does not support PDF preview. 
                       <a href="${pdfUrl}" target="_blank">Click here to view the PDF</a>
                    </p>
                </iframe>
            </div>
        `;
        
        this.showPdfControls();
    }
    
    async loadTextPreview(file, container) {
        try {
            const content = await this.getFileContent(file);
            const extension = this.getFileExtension(file.name);
            
            container.innerHTML = `
                <div class="text-viewer">
                    <div class="text-content">
                        <pre><code class="language-${extension}">${this.escapeHtml(content)}</code></pre>
                    </div>
                </div>
            `;
            
            // Apply syntax highlighting if available
            this.applySyntaxHighlighting(container);
            
        } catch (error) {
            throw new Error('Failed to load text content');
        }
    }
    
    async loadCodePreview(file, container) {
        try {
            const content = await this.getFileContent(file);
            const extension = this.getFileExtension(file.name);
            
            container.innerHTML = `
                <div class="code-viewer">
                    <div class="code-header">
                        <div class="code-language">${extension.toUpperCase()}</div>
                        <div class="code-actions">
                            <button class="btn-icon copy-code" title="Copy code">
                                <i data-lucide="copy"></i>
                            </button>
                        </div>
                    </div>
                    <div class="code-content">
                        <pre><code class="language-${extension}">${this.escapeHtml(content)}</code></pre>
                    </div>
                </div>
            `;
            
            // Setup copy functionality
            container.querySelector('.copy-code').addEventListener('click', () => {
                navigator.clipboard.writeText(content);
                NotificationManager.success('Code copied to clipboard');
            });
            
            // Apply syntax highlighting
            this.applySyntaxHighlighting(container);
            
        } catch (error) {
            throw new Error('Failed to load code content');
        }
    }
    
    async loadArchivePreview(file, container) {
        try {
            const contents = await this.getArchiveContents(file);
            
            container.innerHTML = `
                <div class="archive-viewer">
                    <div class="archive-header">
                        <h3>Archive Contents</h3>
                        <div class="archive-stats">
                            ${contents.length} item(s)
                        </div>
                    </div>
                    <div class="archive-contents">
                        ${this.renderArchiveContents(contents)}
                    </div>
                </div>
            `;
            
        } catch (error) {
            this.loadGenericPreview(file, container);
        }
    }
    
    async loadModelPreview(file, container) {
        const modelUrl = await this.getFileUrl(file);
        
        container.innerHTML = `
            <div class="model-viewer">
                <div class="model-container" id="model-container">
                    <div class="model-placeholder">
                        <i data-lucide="box"></i>
                        <p>3D Model Preview</p>
                        <p class="model-info">Use mouse to rotate, wheel to zoom</p>
                    </div>
                </div>
                <div class="model-controls">
                    <button class="btn-icon reset-view" title="Reset view">
                        <i data-lucide="refresh-cw"></i>
                    </button>
                    <button class="btn-icon wireframe-toggle" title="Toggle wireframe">
                        <i data-lucide="grid-3x3"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Initialize 3D viewer (would require Three.js or similar)
        this.init3DViewer(modelUrl, container.querySelector('#model-container'));
    }
    
    loadGenericPreview(file, container) {
        const fileType = this.getFileType(file);
        const extension = this.getFileExtension(file.name);
        const icon = this.getFileIcon(fileType, extension);
        
        container.innerHTML = `
            <div class="generic-viewer">
                <div class="generic-content">
                    <div class="generic-icon">
                        <i data-lucide="${icon}"></i>
                    </div>
                    <div class="generic-info">
                        <h3>${file.name}</h3>
                        <p>Preview not available for this file type</p>
                        <div class="generic-actions">
                            <button class="btn-primary download-action">
                                <i data-lucide="download"></i>
                                Download File
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.querySelector('.download-action').addEventListener('click', () => {
            this.downloadFile();
        });
    }
    
    // Control panels for different file types
    showImageControls() {
        const controlsContainer = this.container.querySelector('#preview-controls');
        controlsContainer.style.display = 'flex';
        controlsContainer.innerHTML = `
            <div class="image-controls">
                <button class="btn-icon zoom-out" title="Zoom out">
                    <i data-lucide="zoom-out"></i>
                </button>
                <div class="zoom-level">${Math.round(this.scale * 100)}%</div>
                <button class="btn-icon zoom-in" title="Zoom in">
                    <i data-lucide="zoom-in"></i>
                </button>
                <button class="btn-icon reset-zoom" title="Reset zoom">
                    <i data-lucide="move-3d"></i>
                </button>
            </div>
        `;
        
        // Setup zoom controls
        controlsContainer.querySelector('.zoom-in').addEventListener('click', () => this.zoomIn());
        controlsContainer.querySelector('.zoom-out').addEventListener('click', () => this.zoomOut());
        controlsContainer.querySelector('.reset-zoom').addEventListener('click', () => this.resetZoom());
    }
    
    showVideoControls(video) {
        const controlsContainer = this.container.querySelector('#preview-controls');
        controlsContainer.style.display = 'flex';
        controlsContainer.innerHTML = `
            <div class="video-controls">
                <button class="btn-icon playback-speed" title="Playback speed">
                    1x
                </button>
                <button class="btn-icon pip-btn" title="Picture in picture">
                    <i data-lucide="picture-in-picture"></i>
                </button>
            </div>
        `;
        
        // Setup video controls
        const speedBtn = controlsContainer.querySelector('.playback-speed');
        const pipBtn = controlsContainer.querySelector('.pip-btn');
        
        speedBtn.addEventListener('click', () => this.cyclePlaybackSpeed(video, speedBtn));
        pipBtn.addEventListener('click', () => this.togglePictureInPicture(video));
    }
    
    showAudioControls(audio) {
        const controlsContainer = this.container.querySelector('#preview-controls');
        controlsContainer.style.display = 'flex';
        controlsContainer.innerHTML = `
            <div class="audio-controls">
                <button class="btn-icon loop-btn" title="Toggle loop">
                    <i data-lucide="repeat"></i>
                </button>
                <button class="btn-icon shuffle-btn" title="Shuffle">
                    <i data-lucide="shuffle"></i>
                </button>
            </div>
        `;
    }
    
    showPdfControls() {
        const controlsContainer = this.container.querySelector('#preview-controls');
        controlsContainer.style.display = 'flex';
        controlsContainer.innerHTML = `
            <div class="pdf-controls">
                <button class="btn-icon print-btn" title="Print">
                    <i data-lucide="printer"></i>
                </button>
            </div>
        `;
        
        controlsContainer.querySelector('.print-btn').addEventListener('click', () => {
            window.print();
        });
    }
    
    // Helper methods
    getFileType(file) {
        const extension = this.getFileExtension(file.name);
        
        for (const [type, extensions] of Object.entries(this.supportedTypes)) {
            if (extensions.includes(extension)) {
                return type;
            }
        }
        
        return 'unknown';
    }
    
    getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }
    
    getFileIcon(type, extension) {
        const icons = {
            image: 'image',
            video: 'video',
            audio: 'music',
            document: 'file-text',
            code: 'code',
            archive: 'archive',
            model: 'box',
            cad: 'compass'
        };
        
        return icons[type] || 'file';
    }
    
    async getFileUrl(file) {
        // Generate or get URL for file preview
        if (file.url) {
            return file.url;
        }
        
        try {
            const response = await API.get(`/files/${file.id}/url`);
            return response.url;
        } catch (error) {
            throw new Error('Failed to get file URL');
        }
    }
    
    async getFileContent(file) {
        try {
            const response = await API.get(`/files/${file.id}/content`);
            return response.content;
        } catch (error) {
            throw new Error('Failed to get file content');
        }
    }
    
    async getArchiveContents(file) {
        try {
            const response = await API.get(`/files/${file.id}/archive-contents`);
            return response.contents || [];
        } catch (error) {
            throw new Error('Failed to get archive contents');
        }
    }
    
    renderArchiveContents(contents) {
        return contents.map(item => `
            <div class="archive-item">
                <div class="item-icon">
                    <i data-lucide="${item.type === 'directory' ? 'folder' : 'file'}"></i>
                </div>
                <div class="item-info">
                    <div class="item-name">${item.name}</div>
                    <div class="item-meta">
                        ${item.size ? this.formatFileSize(item.size) : ''}
                        ${item.modified ? this.formatDate(item.modified) : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    updateFileInfo(file) {
        this.container.querySelector('#preview-file-name').textContent = file.name;
        
        const metaContainer = this.container.querySelector('#preview-file-meta');
        metaContainer.innerHTML = `
            <span class="file-size">${this.formatFileSize(file.size || 0)}</span>
            <span class="file-type">${this.getFileType(file)}</span>
            <span class="file-modified">${this.formatDate(file.modified)}</span>
        `;
    }
    
    updateNavigation(currentIndex, totalFiles) {
        const navContainer = this.container.querySelector('#preview-navigation');
        
        if (totalFiles && totalFiles > 1) {
            navContainer.style.display = 'flex';
            navContainer.querySelector('.nav-current').textContent = currentIndex + 1;
            navContainer.querySelector('.nav-total').textContent = totalFiles;
            
            navContainer.querySelector('.prev-btn').disabled = currentIndex === 0;
            navContainer.querySelector('.next-btn').disabled = currentIndex === totalFiles - 1;
        } else {
            navContainer.style.display = 'none';
        }
    }
    
    updateImageInfo(img) {
        // Add image dimensions to meta info
        const dimensions = `${img.naturalWidth} × ${img.naturalHeight}`;
        const metaContainer = this.container.querySelector('#preview-file-meta');
        metaContainer.innerHTML += `<span class="image-dimensions">${dimensions}</span>`;
    }
    
    updateVideoInfo(video) {
        // Add video duration and dimensions to meta info
        const duration = this.formatDuration(video.duration);
        const dimensions = `${video.videoWidth} × ${video.videoHeight}`;
        const metaContainer = this.container.querySelector('#preview-file-meta');
        metaContainer.innerHTML += `
            <span class="video-duration">${duration}</span>
            <span class="video-dimensions">${dimensions}</span>
        `;
    }
    
    // Zoom and pan functionality
    setupImageDrag() {
        let isDragging = false;
        let startX, startY, startLeft, startTop;
        
        this.container.addEventListener('mousedown', (e) => {
            const imageContainer = e.target.closest('#image-container');
            if (!imageContainer) return;
            
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            
            const transform = imageContainer.style.transform || '';
            const matches = transform.match(/translate\(([^,]+),([^)]+)\)/);
            startLeft = matches ? parseFloat(matches[1]) : 0;
            startTop = matches ? parseFloat(matches[2]) : 0;
            
            imageContainer.style.cursor = 'grabbing';
        });
        
        this.container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const imageContainer = this.container.querySelector('#image-container');
            if (!imageContainer) return;
            
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            
            const newLeft = startLeft + deltaX;
            const newTop = startTop + deltaY;
            
            imageContainer.style.transform = `translate(${newLeft}px, ${newTop}px) scale(${this.scale})`;
        });
        
        this.container.addEventListener('mouseup', () => {
            isDragging = false;
            const imageContainer = this.container.querySelector('#image-container');
            if (imageContainer) {
                imageContainer.style.cursor = 'grab';
            }
        });
    }
    
    handleZoom(e) {
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        this.scale = Math.max(0.1, Math.min(5, this.scale + delta));
        this.applyZoom();
    }
    
    zoomIn() {
        this.scale = Math.min(5, this.scale * 1.25);
        this.applyZoom();
    }
    
    zoomOut() {
        this.scale = Math.max(0.1, this.scale / 1.25);
        this.applyZoom();
    }
    
    resetZoom() {
        this.scale = 1;
        const imageContainer = this.container.querySelector('#image-container');
        if (imageContainer) {
            imageContainer.style.transform = 'translate(0px, 0px) scale(1)';
        }
        this.updateZoomLevel();
    }
    
    applyZoom() {
        const imageContainer = this.container.querySelector('#image-container');
        if (imageContainer) {
            const transform = imageContainer.style.transform || '';
            const matches = transform.match(/translate\(([^,]+),([^)]+)\)/);
            const translateX = matches ? matches[1] : '0px';
            const translateY = matches ? matches[2] : '0px';
            
            imageContainer.style.transform = `translate(${translateX}, ${translateY}) scale(${this.scale})`;
        }
        this.updateZoomLevel();
    }
    
    updateZoomLevel() {
        const zoomLevel = this.container.querySelector('.zoom-level');
        if (zoomLevel) {
            zoomLevel.textContent = Math.round(this.scale * 100) + '%';
        }
    }
    
    // Media controls
    togglePlayPause() {
        const video = this.container.querySelector('#preview-video');
        const audio = this.container.querySelector('#preview-audio');
        const media = video || audio;
        
        if (media) {
            if (media.paused) {
                media.play();
            } else {
                media.pause();
            }
        }
    }
    
    cyclePlaybackSpeed(video, button) {
        const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
        const currentSpeed = video.playbackRate;
        const currentIndex = speeds.indexOf(currentSpeed);
        const nextIndex = (currentIndex + 1) % speeds.length;
        
        video.playbackRate = speeds[nextIndex];
        button.textContent = speeds[nextIndex] + 'x';
    }
    
    async togglePictureInPicture(video) {
        try {
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
            } else {
                await video.requestPictureInPicture();
            }
        } catch (error) {
            console.error('Picture in picture failed:', error);
        }
    }
    
    // Context menu
    showContextMenu(e) {
        const contextMenu = this.container.querySelector('#preview-context-menu');
        contextMenu.style.display = 'block';
        contextMenu.style.left = e.clientX + 'px';
        contextMenu.style.top = e.clientY + 'px';
        
        // Adjust position if menu goes off screen
        const rect = contextMenu.getBoundingClientRect();
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };
        
        if (rect.right > viewport.width) {
            contextMenu.style.left = (e.clientX - rect.width) + 'px';
        }
        
        if (rect.bottom > viewport.height) {
            contextMenu.style.top = (e.clientY - rect.height) + 'px';
        }
    }
    
    hideContextMenu() {
        const contextMenu = this.container.querySelector('#preview-context-menu');
        contextMenu.style.display = 'none';
    }
    
    handleContextAction(action) {
        switch (action) {
            case 'download':
                this.downloadFile();
                break;
            case 'copy':
                this.copyFile();
                break;
            case 'share':
                this.shareFile();
                break;
            case 'edit':
                this.editFile();
                break;
            case 'rename':
                this.renameFile();
                break;
            case 'delete':
                this.deleteFile();
                break;
        }
    }
    
    // File actions
    async downloadFile() {
        if (!this.currentFile) return;
        
        try {
            const url = await this.getFileUrl(this.currentFile);
            const a = document.createElement('a');
            a.href = url;
            a.download = this.currentFile.name;
            a.click();
        } catch (error) {
            NotificationManager.error('Failed to download file');
        }
    }
    
    async copyFile() {
        // Implementation depends on file type and browser capabilities
        NotificationManager.info('Copy functionality not implemented yet');
    }
    
    async shareFile() {
        if (navigator.share && this.currentFile) {
            try {
                await navigator.share({
                    title: this.currentFile.name,
                    url: await this.getFileUrl(this.currentFile)
                });
            } catch (error) {
                // Fallback to copying link
                this.copyFileLink();
            }
        } else {
            this.copyFileLink();
        }
    }
    
    async copyFileLink() {
        try {
            const url = await this.getFileUrl(this.currentFile);
            await navigator.clipboard.writeText(url);
            NotificationManager.success('File link copied to clipboard');
        } catch (error) {
            NotificationManager.error('Failed to copy file link');
        }
    }
    
    editFile() {
        this.onAction('edit', this.currentFile);
    }
    
    renameFile() {
        this.onAction('rename', this.currentFile);
    }
    
    deleteFile() {
        this.onAction('delete', this.currentFile);
    }
    
    // Navigation
    navigatePrevious() {
        this.onNavigate('previous');
    }
    
    navigateNext() {
        this.onNavigate('next');
    }
    
    toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen();
            this.isFullscreen = false;
        } else {
            this.container.querySelector('#file-preview').requestFullscreen();
            this.isFullscreen = true;
        }
        
        const fullscreenBtn = this.container.querySelector('.fullscreen-btn i');
        fullscreenBtn.setAttribute('data-lucide', this.isFullscreen ? 'minimize' : 'maximize');
    }
    
    // Utility methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    formatDate(dateStr) {
        if (!dateStr) return 'Unknown';
        
        const date = new Date(dateStr);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
    
    formatDuration(seconds) {
        if (isNaN(seconds)) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    applySyntaxHighlighting(container) {
        // Implementation would require a syntax highlighting library like Prism.js or highlight.js
        // For now, we'll just add basic styling classes
        const codeBlocks = container.querySelectorAll('code[class*="language-"]');
        codeBlocks.forEach(block => {
            block.classList.add('syntax-highlighted');
        });
    }
    
    init3DViewer(modelUrl, container) {
        // Implementation would require Three.js or similar 3D library
        container.innerHTML = `
            <div class="model-placeholder">
                <i data-lucide="box"></i>
                <p>3D Model Preview (Not Implemented)</p>
                <p>Would require Three.js integration</p>
            </div>
        `;
    }
    
    showError(message) {
        const contentContainer = this.container.querySelector('#preview-content');
        contentContainer.innerHTML = `
            <div class="preview-error">
                <i data-lucide="alert-circle"></i>
                <span>${message}</span>
                <button class="btn-secondary retry-btn">Try Again</button>
            </div>
        `;
        
        contentContainer.querySelector('.retry-btn').addEventListener('click', () => {
            if (this.currentFile) {
                this.loadPreview(this.currentFile);
            }
        });
    }
    
    // Public API
    getCurrentFile() {
        return this.currentFile;
    }
    
    isVisible() {
        return this.isOpen;
    }
    
    getScale() {
        return this.scale;
    }
    
    getSupportedTypes() {
        return { ...this.supportedTypes };
    }
}