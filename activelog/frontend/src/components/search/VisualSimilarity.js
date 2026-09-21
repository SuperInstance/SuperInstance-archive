/**
 * Visual Similarity Search Component
 */

import { ApiClient } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class VisualSimilarity {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.selectedImage = null;
        this.cropArea = null;
        this.isDragging = false;
        this.isResizing = false;
        this.resizeHandle = null;
    }

    async showImageSearchModal() {
        const modal = document.getElementById('image-search-modal');
        if (!modal) return;

        modal.style.display = 'flex';
        this.attachImageSearchListeners();
    }

    hideImageSearchModal() {
        const modal = document.getElementById('image-search-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.reset();
    }

    attachImageSearchListeners() {
        const modal = document.getElementById('image-search-modal');
        const uploadArea = document.getElementById('image-upload-area');
        const fileInput = document.getElementById('search-image-input');
        const browseBtn = document.getElementById('browse-image');
        const closeBtn = document.getElementById('close-image-search');
        const cancelBtn = document.getElementById('cancel-image-search');
        const searchBtn = document.getElementById('start-image-search');

        // Close modal
        closeBtn?.addEventListener('click', () => this.hideImageSearchModal());
        cancelBtn?.addEventListener('click', () => this.hideImageSearchModal());

        // Browse button
        browseBtn?.addEventListener('click', () => fileInput?.click());

        // File input
        fileInput?.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                this.handleImageUpload(e.target.files[0]);
            }
        });

        // Drag and drop
        uploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea?.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('image/')) {
                this.handleImageUpload(files[0]);
            }
        });

        // Search button
        searchBtn?.addEventListener('click', () => this.performImageSearch());

        // Close on overlay click
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideImageSearchModal();
            }
        });
    }

    async handleImageUpload(file) {
        try {
            // Validate file
            if (!file.type.startsWith('image/')) {
                NotificationManager.error('Please select an image file');
                return;
            }

            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                NotificationManager.error('Image file is too large (max 10MB)');
                return;
            }

            // Read file as data URL
            const reader = new FileReader();
            reader.onload = (e) => {
                this.displayImagePreview(e.target.result, file);
            };
            reader.readAsDataURL(file);

        } catch (error) {
            console.error('Error handling image upload:', error);
            NotificationManager.error('Failed to process image');
        }
    }

    displayImagePreview(dataUrl, file) {
        const uploadArea = document.getElementById('image-upload-area');
        const previewContainer = document.getElementById('image-preview');
        const searchBtn = document.getElementById('start-image-search');

        // Hide upload area, show preview
        uploadArea.style.display = 'none';
        previewContainer.style.display = 'block';

        previewContainer.innerHTML = `
            <div class="image-preview-container">
                <div class="preview-header">
                    <h3>Image Preview</h3>
                    <div class="preview-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                    </div>
                </div>
                
                <div class="preview-content">
                    <div class="image-container">
                        <canvas id="preview-canvas" class="preview-canvas"></canvas>
                        <div class="crop-overlay" id="crop-overlay" style="display: none;">
                            <div class="crop-area" id="crop-area">
                                <div class="crop-handle nw" data-handle="nw"></div>
                                <div class="crop-handle ne" data-handle="ne"></div>
                                <div class="crop-handle sw" data-handle="sw"></div>
                                <div class="crop-handle se" data-handle="se"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="preview-controls">
                        <div class="search-options">
                            <label class="option-label">
                                <input type="radio" name="search-mode" value="full" checked>
                                Search entire image
                            </label>
                            <label class="option-label">
                                <input type="radio" name="search-mode" value="crop">
                                Search specific area
                            </label>
                        </div>
                        
                        <div class="similarity-settings">
                            <label>Visual similarity threshold</label>
                            <input type="range" id="visual-similarity-slider" min="50" max="95" value="80" class="similarity-slider">
                            <span id="visual-similarity-value">80%</span>
                        </div>
                        
                        <div class="analysis-options">
                            <label class="checkbox-label">
                                <input type="checkbox" id="analyze-colors" checked>
                                Color analysis
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" id="analyze-objects" checked>
                                Object detection
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" id="analyze-composition" checked>
                                Composition analysis
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="preview-actions">
                    <button class="action-btn secondary" id="change-image">Change Image</button>
                    <button class="action-btn primary" id="analyze-image">Analyze & Search</button>
                </div>
            </div>
        `;

        // Load image into canvas
        this.loadImageToCanvas(dataUrl);
        
        // Enable search button
        searchBtn.disabled = false;
        
        // Attach preview event listeners
        this.attachPreviewListeners();
    }

    loadImageToCanvas(dataUrl) {
        const canvas = document.getElementById('preview-canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();

        img.onload = () => {
            // Calculate display size (max 400x300 maintaining aspect ratio)
            const maxWidth = 400;
            const maxHeight = 300;
            let { width, height } = img;

            if (width > maxWidth) {
                height = (height * maxWidth) / width;
                width = maxWidth;
            }
            if (height > maxHeight) {
                width = (width * maxHeight) / height;
                height = maxHeight;
            }

            canvas.width = width;
            canvas.height = height;
            
            // Draw image
            ctx.drawImage(img, 0, 0, width, height);
            
            this.canvas = canvas;
            this.ctx = ctx;
            this.selectedImage = img;
        };

        img.src = dataUrl;
    }

    attachPreviewListeners() {
        // Search mode radio buttons
        document.querySelectorAll('input[name="search-mode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const cropOverlay = document.getElementById('crop-overlay');
                if (e.target.value === 'crop') {
                    cropOverlay.style.display = 'block';
                    this.initializeCropArea();
                } else {
                    cropOverlay.style.display = 'none';
                }
            });
        });

        // Similarity slider
        const slider = document.getElementById('visual-similarity-slider');
        const value = document.getElementById('visual-similarity-value');
        slider?.addEventListener('input', (e) => {
            value.textContent = `${e.target.value}%`;
        });

        // Action buttons
        document.getElementById('change-image')?.addEventListener('click', () => {
            this.resetToUpload();
        });

        document.getElementById('analyze-image')?.addEventListener('click', () => {
            this.performImageAnalysis();
        });
    }

    initializeCropArea() {
        const canvas = this.canvas;
        const cropArea = document.getElementById('crop-area');
        const overlay = document.getElementById('crop-overlay');

        if (!canvas || !cropArea || !overlay) return;

        // Position overlay over canvas
        const canvasRect = canvas.getBoundingClientRect();
        overlay.style.width = `${canvas.width}px`;
        overlay.style.height = `${canvas.height}px`;

        // Initialize crop area (center 50% of image)
        const width = canvas.width * 0.5;
        const height = canvas.height * 0.5;
        const x = (canvas.width - width) / 2;
        const y = (canvas.height - height) / 2;

        this.cropArea = { x, y, width, height };
        this.updateCropAreaDisplay();

        // Add crop area interaction
        this.attachCropListeners();
    }

    attachCropListeners() {
        const cropArea = document.getElementById('crop-area');
        const handles = document.querySelectorAll('.crop-handle');

        // Drag crop area
        cropArea?.addEventListener('mousedown', (e) => {
            if (e.target === cropArea) {
                this.isDragging = true;
                this.dragStart = {
                    x: e.clientX - this.cropArea.x,
                    y: e.clientY - this.cropArea.y
                };
            }
        });

        // Resize handles
        handles.forEach(handle => {
            handle.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                this.isResizing = true;
                this.resizeHandle = e.target.dataset.handle;
                this.resizeStart = {
                    x: e.clientX,
                    y: e.clientY,
                    cropArea: { ...this.cropArea }
                };
            });
        });

        // Mouse move and up listeners
        document.addEventListener('mousemove', (e) => {
            if (this.isDragging) {
                this.updateCropPosition(e);
            } else if (this.isResizing) {
                this.updateCropSize(e);
            }
        });

        document.addEventListener('mouseup', () => {
            this.isDragging = false;
            this.isResizing = false;
            this.resizeHandle = null;
        });
    }

    updateCropPosition(e) {
        const newX = Math.max(0, Math.min(
            this.canvas.width - this.cropArea.width,
            e.clientX - this.dragStart.x
        ));
        const newY = Math.max(0, Math.min(
            this.canvas.height - this.cropArea.height,
            e.clientY - this.dragStart.y
        ));

        this.cropArea.x = newX;
        this.cropArea.y = newY;
        this.updateCropAreaDisplay();
    }

    updateCropSize(e) {
        const deltaX = e.clientX - this.resizeStart.x;
        const deltaY = e.clientY - this.resizeStart.y;
        const original = this.resizeStart.cropArea;

        switch (this.resizeHandle) {
            case 'nw':
                this.cropArea.x = Math.max(0, original.x + deltaX);
                this.cropArea.y = Math.max(0, original.y + deltaY);
                this.cropArea.width = Math.max(50, original.width - deltaX);
                this.cropArea.height = Math.max(50, original.height - deltaY);
                break;
            case 'ne':
                this.cropArea.y = Math.max(0, original.y + deltaY);
                this.cropArea.width = Math.max(50, original.width + deltaX);
                this.cropArea.height = Math.max(50, original.height - deltaY);
                break;
            case 'sw':
                this.cropArea.x = Math.max(0, original.x + deltaX);
                this.cropArea.width = Math.max(50, original.width - deltaX);
                this.cropArea.height = Math.max(50, original.height + deltaY);
                break;
            case 'se':
                this.cropArea.width = Math.max(50, original.width + deltaX);
                this.cropArea.height = Math.max(50, original.height + deltaY);
                break;
        }

        // Ensure crop area stays within canvas bounds
        this.cropArea.width = Math.min(this.cropArea.width, this.canvas.width - this.cropArea.x);
        this.cropArea.height = Math.min(this.cropArea.height, this.canvas.height - this.cropArea.y);

        this.updateCropAreaDisplay();
    }

    updateCropAreaDisplay() {
        const cropAreaElement = document.getElementById('crop-area');
        if (!cropAreaElement) return;

        cropAreaElement.style.left = `${this.cropArea.x}px`;
        cropAreaElement.style.top = `${this.cropArea.y}px`;
        cropAreaElement.style.width = `${this.cropArea.width}px`;
        cropAreaElement.style.height = `${this.cropArea.height}px`;
    }

    async performImageAnalysis() {
        try {
            // Show loading state
            const analyzeBtn = document.getElementById('analyze-image');
            const originalText = analyzeBtn.textContent;
            analyzeBtn.textContent = 'Analyzing...';
            analyzeBtn.disabled = true;

            // Get search parameters
            const searchMode = document.querySelector('input[name="search-mode"]:checked').value;
            const threshold = document.getElementById('visual-similarity-slider').value / 100;
            const analyzeColors = document.getElementById('analyze-colors').checked;
            const analyzeObjects = document.getElementById('analyze-objects').checked;
            const analyzeComposition = document.getElementById('analyze-composition').checked;

            // Prepare image data
            let imageData;
            if (searchMode === 'crop' && this.cropArea) {
                imageData = this.getCroppedImageData();
            } else {
                imageData = this.canvas.toDataURL('image/jpeg', 0.8);
            }

            // Send to backend for analysis
            const analysisResult = await ApiClient.post('/ai/analyze-image', {
                image_data: imageData,
                similarity_threshold: threshold,
                analyze_colors: analyzeColors,
                analyze_objects: analyzeObjects,
                analyze_composition: analyzeComposition
            });

            // Show analysis results and perform search
            await this.showAnalysisResults(analysisResult);
            
        } catch (error) {
            console.error('Image analysis failed:', error);
            NotificationManager.error('Image analysis failed. Please try again.');
        } finally {
            // Reset button
            const analyzeBtn = document.getElementById('analyze-image');
            analyzeBtn.textContent = originalText;
            analyzeBtn.disabled = false;
        }
    }

    getCroppedImageData() {
        // Create temporary canvas for cropped area
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        
        tempCanvas.width = this.cropArea.width;
        tempCanvas.height = this.cropArea.height;
        
        // Copy cropped area
        tempCtx.drawImage(
            this.canvas,
            this.cropArea.x, this.cropArea.y, this.cropArea.width, this.cropArea.height,
            0, 0, this.cropArea.width, this.cropArea.height
        );
        
        return tempCanvas.toDataURL('image/jpeg', 0.8);
    }

    async showAnalysisResults(analysisResult) {
        // Update modal content to show results
        const previewContainer = document.getElementById('image-preview');
        
        previewContainer.innerHTML = `
            <div class="analysis-results">
                <div class="results-header">
                    <h3>Analysis Complete</h3>
                    <div class="analysis-summary">
                        Found ${analysisResult.similar_images?.length || 0} visually similar images
                    </div>
                </div>
                
                <div class="analysis-details">
                    <div class="detected-features">
                        <h4>Detected Features</h4>
                        <div class="feature-tags">
                            ${(analysisResult.detected_objects || []).map(obj => `
                                <span class="feature-tag">${obj.name} (${Math.round(obj.confidence * 100)}%)</span>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="color-palette">
                        <h4>Dominant Colors</h4>
                        <div class="color-swatches">
                            ${(analysisResult.dominant_colors || []).map(color => `
                                <div class="color-swatch" style="background-color: ${color.hex};" title="${color.hex}"></div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="similar-images">
                    <h4>Similar Images</h4>
                    <div class="similar-images-grid">
                        ${(analysisResult.similar_images || []).slice(0, 8).map(img => `
                            <div class="similar-image-item" data-file-id="${img.id}">
                                <div class="image-thumbnail">
                                    <img src="${img.thumbnail_url}" alt="${img.name}">
                                    <div class="similarity-score">${Math.round(img.similarity_score * 100)}%</div>
                                </div>
                                <div class="image-name">${img.name}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="results-actions">
                    <button class="action-btn secondary" id="new-search">New Search</button>
                    <button class="action-btn primary" id="view-all-results">View All Results</button>
                </div>
            </div>
        `;

        // Attach result event listeners
        document.getElementById('new-search')?.addEventListener('click', () => {
            this.resetToUpload();
        });

        document.getElementById('view-all-results')?.addEventListener('click', () => {
            this.viewAllResults(analysisResult);
        });

        // Similar image clicks
        document.querySelectorAll('.similar-image-item').forEach(item => {
            item.addEventListener('click', () => {
                const fileId = item.dataset.fileId;
                this.viewSimilarImage(fileId);
            });
        });
    }

    resetToUpload() {
        const uploadArea = document.getElementById('image-upload-area');
        const previewContainer = document.getElementById('image-preview');
        const searchBtn = document.getElementById('start-image-search');

        uploadArea.style.display = 'block';
        previewContainer.style.display = 'none';
        searchBtn.disabled = true;

        this.reset();
    }

    viewAllResults(analysisResult) {
        // Close modal and show results in main search
        this.hideImageSearchModal();
        
        // Emit event to show results in main search interface
        document.dispatchEvent(new CustomEvent('showImageSearchResults', {
            detail: { results: analysisResult.similar_images, query: 'Visual similarity search' }
        }));
    }

    viewSimilarImage(fileId) {
        // Close modal and open file
        this.hideImageSearchModal();
        
        document.dispatchEvent(new CustomEvent('openFile', {
            detail: { fileId }
        }));
    }

    reset() {
        this.canvas = null;
        this.ctx = null;
        this.selectedImage = null;
        this.cropArea = null;
        this.isDragging = false;
        this.isResizing = false;
        this.resizeHandle = null;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
}