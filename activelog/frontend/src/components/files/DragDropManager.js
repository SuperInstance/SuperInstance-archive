/**
 * Drag and Drop File Organization Manager
 */

import Sortable from 'sortablejs';
import { API } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class DragDropManager {
    constructor(options = {}) {
        this.container = null;
        this.dropZones = new Map();
        this.sortableInstances = new Map();
        this.draggedItem = null;
        this.draggedItems = [];
        
        this.onFileDrop = options.onFileDrop || (() => {});
        this.onFileMove = options.onFileMove || (() => {});
        this.onFolderCreate = options.onFolderCreate || (() => {});
        this.onError = options.onError || (() => {});
        
        this.enableFolderDrop = options.enableFolderDrop !== false;
        this.enableFileUpload = options.enableFileUpload !== false;
        this.enableReorder = options.enableReorder !== false;
        this.enableMultiSelect = options.enableMultiSelect !== false;
        
        this.maxFileSize = options.maxFileSize || 100 * 1024 * 1024; // 100MB
        this.allowedFileTypes = options.allowedFileTypes || []; // Empty = all types
        
        this.uploadQueue = [];
        this.isUploading = false;
        
        this.setupGlobalDragListeners();
    }
    
    setupGlobalDragListeners() {
        // Prevent default drag behaviors on document
        document.addEventListener('dragover', this.handleGlobalDragOver.bind(this));
        document.addEventListener('drop', this.handleGlobalDrop.bind(this));
        document.addEventListener('dragenter', this.handleGlobalDragEnter.bind(this));
        document.addEventListener('dragleave', this.handleGlobalDragLeave.bind(this));
    }
    
    handleGlobalDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'none';
    }
    
    handleGlobalDrop(e) {
        e.preventDefault();
    }
    
    handleGlobalDragEnter(e) {
        e.preventDefault();
        if (this.hasFiles(e.dataTransfer)) {
            document.body.classList.add('drag-active');
        }
    }
    
    handleGlobalDragLeave(e) {
        if (!document.body.contains(e.relatedTarget)) {
            document.body.classList.remove('drag-active');
        }
    }
    
    createDropZone(element, options = {}) {
        const zoneId = options.id || this.generateId();
        
        const dropZone = {
            id: zoneId,
            element: element,
            accepts: options.accepts || ['files', 'folders'],
            path: options.path || '/',
            onDrop: options.onDrop || (() => {}),
            onDragOver: options.onDragOver || (() => {}),
            onDragEnter: options.onDragEnter || (() => {}),
            onDragLeave: options.onDragLeave || (() => {}),
            multiple: options.multiple !== false,
            autoUpload: options.autoUpload !== false
        };
        
        this.setupDropZone(dropZone);
        this.dropZones.set(zoneId, dropZone);
        
        return zoneId;
    }
    
    setupDropZone(dropZone) {
        const { element } = dropZone;
        
        element.classList.add('drop-zone');
        element.setAttribute('data-drop-zone', dropZone.id);
        
        // Drag event listeners
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const dropEffect = this.getDropEffect(e, dropZone);
            e.dataTransfer.dropEffect = dropEffect;
            
            element.classList.add('drag-over');
            dropZone.onDragOver(e, dropZone);
        });
        
        element.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            element.classList.add('drag-enter');
            dropZone.onDragEnter(e, dropZone);
        });
        
        element.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // Only remove styles if leaving the drop zone entirely
            if (!element.contains(e.relatedTarget)) {
                element.classList.remove('drag-over', 'drag-enter');
                dropZone.onDragLeave(e, dropZone);
            }
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            element.classList.remove('drag-over', 'drag-enter');
            document.body.classList.remove('drag-active');
            
            this.handleDrop(e, dropZone);
        });
    }
    
    createSortable(element, options = {}) {
        const sortableId = options.id || this.generateId();
        
        const sortableConfig = {
            group: options.group || 'default',
            animation: options.animation || 150,
            handle: options.handle || null,
            filter: options.filter || null,
            preventOnFilter: false,
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            ghostClass: 'sortable-ghost',
            multiDrag: this.enableMultiSelect,
            selectedClass: 'sortable-selected',
            
            onStart: (evt) => {
                this.handleSortableStart(evt, sortableId);
                if (options.onStart) options.onStart(evt);
            },
            
            onEnd: (evt) => {
                this.handleSortableEnd(evt, sortableId);
                if (options.onEnd) options.onEnd(evt);
            },
            
            onMove: (evt) => {
                const result = this.handleSortableMove(evt, sortableId);
                if (options.onMove) {
                    return options.onMove(evt) && result;
                }
                return result;
            },
            
            onChange: (evt) => {
                this.handleSortableChange(evt, sortableId);
                if (options.onChange) options.onChange(evt);
            }
        };
        
        const sortableInstance = Sortable.create(element, sortableConfig);
        this.sortableInstances.set(sortableId, {
            instance: sortableInstance,
            element: element,
            options: options
        });
        
        return sortableId;
    }
    
    handleDrop(e, dropZone) {
        const files = Array.from(e.dataTransfer.files);
        const items = Array.from(e.dataTransfer.items);
        
        // Handle file uploads
        if (files.length > 0 && this.enableFileUpload) {
            this.handleFileUpload(files, dropZone);
            return;
        }
        
        // Handle internal drag and drop
        const dragData = this.getDragData(e);
        if (dragData) {
            this.handleInternalDrop(dragData, dropZone);
            return;
        }
        
        // Handle folder drops (if supported by browser)
        if (items.length > 0) {
            this.handleDirectoryDrop(items, dropZone);
            return;
        }
        
        dropZone.onDrop(e, dropZone);
    }
    
    async handleFileUpload(files, dropZone) {
        // Validate files
        const validFiles = this.validateFiles(files);
        
        if (validFiles.length === 0) {
            this.onError(new Error('No valid files to upload'));
            return;
        }
        
        // Add to upload queue
        const uploadItems = validFiles.map(file => ({
            id: this.generateId(),
            file: file,
            path: dropZone.path,
            status: 'pending',
            progress: 0,
            error: null
        }));
        
        this.uploadQueue.push(...uploadItems);
        
        // Show upload progress
        this.showUploadProgress(uploadItems);
        
        if (dropZone.autoUpload) {
            await this.processUploadQueue();
        }
        
        this.onFileDrop(validFiles, dropZone);
    }
    
    async handleDirectoryDrop(items, dropZone) {
        const entries = [];
        
        for (const item of items) {
            if (item.webkitGetAsEntry) {
                const entry = item.webkitGetAsEntry();
                if (entry) {
                    entries.push(entry);
                }
            }
        }
        
        if (entries.length === 0) return;
        
        // Process directory entries
        const files = await this.processDirectoryEntries(entries);
        
        if (files.length > 0) {
            await this.handleFileUpload(files, dropZone);
        }
    }
    
    async processDirectoryEntries(entries) {
        const files = [];
        
        for (const entry of entries) {
            if (entry.isFile) {
                const file = await this.getFileFromEntry(entry);
                if (file) files.push(file);
            } else if (entry.isDirectory && this.enableFolderDrop) {
                const dirFiles = await this.processDirectory(entry);
                files.push(...dirFiles);
            }
        }
        
        return files;
    }
    
    async processDirectory(directoryEntry) {
        const files = [];
        const reader = directoryEntry.createReader();
        
        return new Promise((resolve) => {
            const readEntries = () => {
                reader.readEntries(async (entries) => {
                    if (entries.length === 0) {
                        resolve(files);
                        return;
                    }
                    
                    for (const entry of entries) {
                        if (entry.isFile) {
                            const file = await this.getFileFromEntry(entry);
                            if (file) {
                                // Preserve directory structure
                                file.relativePath = directoryEntry.fullPath + '/' + file.name;
                                files.push(file);
                            }
                        } else if (entry.isDirectory) {
                            const subFiles = await this.processDirectory(entry);
                            files.push(...subFiles);
                        }
                    }
                    
                    readEntries(); // Continue reading
                });
            };
            
            readEntries();
        });
    }
    
    getFileFromEntry(fileEntry) {
        return new Promise((resolve) => {
            fileEntry.file((file) => {
                resolve(file);
            }, () => {
                resolve(null);
            });
        });
    }
    
    handleInternalDrop(dragData, dropZone) {
        if (dragData.type === 'file-item') {
            this.handleFileMove(dragData.items, dropZone);
        } else if (dragData.type === 'folder-item') {
            this.handleFolderMove(dragData.items, dropZone);
        }
    }
    
    async handleFileMove(items, dropZone) {
        try {
            const moves = items.map(item => ({
                from: item.path,
                to: dropZone.path + '/' + item.name
            }));
            
            await API.post('/files/move', { moves });
            
            this.onFileMove(moves, dropZone);
            NotificationManager.success(`Moved ${items.length} item(s)`);
            
        } catch (error) {
            console.error('Failed to move files:', error);
            this.onError(error);
            NotificationManager.error('Failed to move files');
        }
    }
    
    async handleFolderMove(items, dropZone) {
        try {
            const moves = items.map(item => ({
                from: item.path,
                to: dropZone.path + '/' + item.name,
                type: 'folder'
            }));
            
            await API.post('/files/move', { moves });
            
            this.onFileMove(moves, dropZone);
            NotificationManager.success(`Moved ${items.length} folder(s)`);
            
        } catch (error) {
            console.error('Failed to move folders:', error);
            this.onError(error);
            NotificationManager.error('Failed to move folders');
        }
    }
    
    validateFiles(files) {
        return files.filter(file => {
            // Check file size
            if (file.size > this.maxFileSize) {
                NotificationManager.warning(`File "${file.name}" is too large (max ${this.formatFileSize(this.maxFileSize)})`);
                return false;
            }
            
            // Check file type
            if (this.allowedFileTypes.length > 0) {
                const fileType = file.type || this.getFileTypeFromName(file.name);
                const isAllowed = this.allowedFileTypes.some(type => {
                    if (type.includes('*')) {
                        const baseType = type.split('/')[0];
                        return fileType.startsWith(baseType);
                    }
                    return fileType === type;
                });
                
                if (!isAllowed) {
                    NotificationManager.warning(`File type "${fileType}" is not allowed for "${file.name}"`);
                    return false;
                }
            }
            
            return true;
        });
    }
    
    async processUploadQueue() {
        if (this.isUploading) return;
        
        this.isUploading = true;
        
        try {
            while (this.uploadQueue.length > 0) {
                const item = this.uploadQueue.shift();
                await this.uploadFile(item);
            }
        } finally {
            this.isUploading = false;
        }
    }
    
    async uploadFile(uploadItem) {
        try {
            uploadItem.status = 'uploading';
            this.updateUploadProgress(uploadItem);
            
            const formData = new FormData();
            formData.append('file', uploadItem.file);
            formData.append('path', uploadItem.path);
            
            if (uploadItem.file.relativePath) {
                formData.append('relativePath', uploadItem.file.relativePath);
            }
            
            const response = await API.post('/files/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                onUploadProgress: (progressEvent) => {
                    uploadItem.progress = Math.round((progressEvent.loaded / progressEvent.total) * 100);
                    this.updateUploadProgress(uploadItem);
                }
            });
            
            uploadItem.status = 'completed';
            uploadItem.progress = 100;
            this.updateUploadProgress(uploadItem);
            
            return response;
            
        } catch (error) {
            uploadItem.status = 'error';
            uploadItem.error = error.message;
            this.updateUploadProgress(uploadItem);
            throw error;
        }
    }
    
    showUploadProgress(uploadItems) {
        // Create or update upload progress modal
        let modal = document.querySelector('.upload-progress-modal');
        
        if (!modal) {
            modal = document.createElement('div');
            modal.className = 'upload-progress-modal';
            modal.innerHTML = `
                <div class="upload-modal-content">
                    <div class="upload-modal-header">
                        <h3>Uploading Files</h3>
                        <button class="close-upload-modal">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    <div class="upload-progress-list"></div>
                    <div class="upload-modal-footer">
                        <button class="cancel-uploads">Cancel All</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Setup event listeners
            modal.querySelector('.close-upload-modal').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            modal.querySelector('.cancel-uploads').addEventListener('click', () => {
                this.cancelUploads();
            });
        }
        
        const progressList = modal.querySelector('.upload-progress-list');
        
        uploadItems.forEach(item => {
            const progressItem = document.createElement('div');
            progressItem.className = 'upload-progress-item';
            progressItem.dataset.uploadId = item.id;
            progressItem.innerHTML = `
                <div class="upload-file-info">
                    <div class="upload-file-name">${item.file.name}</div>
                    <div class="upload-file-size">${this.formatFileSize(item.file.size)}</div>
                </div>
                <div class="upload-progress">
                    <div class="upload-progress-bar">
                        <div class="upload-progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="upload-status">Pending</div>
                </div>
            `;
            
            progressList.appendChild(progressItem);
        });
        
        modal.style.display = 'block';
    }
    
    updateUploadProgress(uploadItem) {
        const progressItem = document.querySelector(`[data-upload-id="${uploadItem.id}"]`);
        if (!progressItem) return;
        
        const progressFill = progressItem.querySelector('.upload-progress-fill');
        const statusElement = progressItem.querySelector('.upload-status');
        
        progressFill.style.width = uploadItem.progress + '%';
        
        switch (uploadItem.status) {
            case 'pending':
                statusElement.textContent = 'Pending';
                progressItem.className = 'upload-progress-item pending';
                break;
            case 'uploading':
                statusElement.textContent = `${uploadItem.progress}%`;
                progressItem.className = 'upload-progress-item uploading';
                break;
            case 'completed':
                statusElement.textContent = 'Completed';
                progressItem.className = 'upload-progress-item completed';
                break;
            case 'error':
                statusElement.textContent = `Error: ${uploadItem.error}`;
                progressItem.className = 'upload-progress-item error';
                break;
        }
    }
    
    cancelUploads() {
        this.uploadQueue = [];
        // Abort any ongoing uploads here
        document.querySelector('.upload-progress-modal').style.display = 'none';
        NotificationManager.info('Uploads cancelled');
    }
    
    handleSortableStart(evt, sortableId) {
        this.draggedItem = evt.item;
        
        // Handle multi-select
        if (this.enableMultiSelect) {
            const selectedItems = evt.items || [evt.item];
            this.draggedItems = selectedItems;
        }
        
        // Store drag data
        this.setDragData(evt, {
            type: 'sortable-item',
            sortableId: sortableId,
            items: this.getDraggedItemsData()
        });
    }
    
    handleSortableEnd(evt, sortableId) {
        // Reset drag state
        this.draggedItem = null;
        this.draggedItems = [];
        
        // Handle reorder if within same container
        if (evt.from === evt.to) {
            this.handleReorder(evt, sortableId);
        }
    }
    
    handleSortableMove(evt, sortableId) {
        // Implement move validation logic
        return true;
    }
    
    handleSortableChange(evt, sortableId) {
        // Handle order change
    }
    
    async handleReorder(evt, sortableId) {
        if (!this.enableReorder) return;
        
        const sortableConfig = this.sortableInstances.get(sortableId);
        if (!sortableConfig || !sortableConfig.options.onReorder) return;
        
        const items = Array.from(evt.to.children).map((element, index) => ({
            element: element,
            id: element.dataset.id || element.dataset.path,
            order: index
        }));
        
        try {
            await sortableConfig.options.onReorder(items, evt);
        } catch (error) {
            console.error('Failed to reorder items:', error);
            this.onError(error);
            
            // Revert the DOM change
            if (evt.oldIndex !== undefined && evt.newIndex !== undefined) {
                const item = evt.to.children[evt.newIndex];
                if (evt.oldIndex < evt.newIndex) {
                    evt.to.insertBefore(item, evt.to.children[evt.oldIndex]);
                } else {
                    evt.to.insertBefore(item, evt.to.children[evt.oldIndex + 1]);
                }
            }
        }
    }
    
    getDraggedItemsData() {
        const items = this.draggedItems.length > 0 ? this.draggedItems : [this.draggedItem];
        
        return items.map(element => ({
            id: element.dataset.id,
            path: element.dataset.path,
            name: element.dataset.name,
            type: element.dataset.type,
            element: element
        }));
    }
    
    setDragData(evt, data) {
        if (evt.dataTransfer) {
            evt.dataTransfer.setData('application/json', JSON.stringify(data));
        }
        
        // Store in global state as fallback
        window.dragData = data;
    }
    
    getDragData(evt) {
        try {
            const jsonData = evt.dataTransfer.getData('application/json');
            if (jsonData) {
                return JSON.parse(jsonData);
            }
        } catch (e) {
            // Fallback to global state
            return window.dragData;
        }
        
        return null;
    }
    
    getDropEffect(evt, dropZone) {
        if (this.hasFiles(evt.dataTransfer)) {
            return dropZone.accepts.includes('files') ? 'copy' : 'none';
        }
        
        const dragData = this.getDragData(evt);
        if (dragData && dragData.type === 'sortable-item') {
            return 'move';
        }
        
        return 'none';
    }
    
    hasFiles(dataTransfer) {
        return dataTransfer.types.includes('Files');
    }
    
    getFileTypeFromName(fileName) {
        const ext = fileName.split('.').pop().toLowerCase();
        const mimeTypes = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        };
        
        return mimeTypes[ext] || 'application/octet-stream';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    removeDropZone(zoneId) {
        const dropZone = this.dropZones.get(zoneId);
        if (dropZone) {
            dropZone.element.classList.remove('drop-zone');
            dropZone.element.removeAttribute('data-drop-zone');
            this.dropZones.delete(zoneId);
        }
    }
    
    removeSortable(sortableId) {
        const sortableConfig = this.sortableInstances.get(sortableId);
        if (sortableConfig) {
            sortableConfig.instance.destroy();
            this.sortableInstances.delete(sortableId);
        }
    }
    
    destroy() {
        // Remove global listeners
        document.removeEventListener('dragover', this.handleGlobalDragOver);
        document.removeEventListener('drop', this.handleGlobalDrop);
        document.removeEventListener('dragenter', this.handleGlobalDragEnter);
        document.removeEventListener('dragleave', this.handleGlobalDragLeave);
        
        // Clean up drop zones
        this.dropZones.forEach((_, zoneId) => {
            this.removeDropZone(zoneId);
        });
        
        // Clean up sortable instances
        this.sortableInstances.forEach((_, sortableId) => {
            this.removeSortable(sortableId);
        });
        
        // Clear upload queue
        this.uploadQueue = [];
        
        // Remove upload modal
        const modal = document.querySelector('.upload-progress-modal');
        if (modal) {
            modal.remove();
        }
    }
}