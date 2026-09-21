/**
 * File Tree Component with Drag & Drop Support
 */

import Sortable from 'sortablejs';

export class FileTree {
    constructor(options = {}) {
        this.container = null;
        this.data = {};
        this.expandedNodes = new Set();
        this.selectedNode = null;
        
        this.onNodeSelect = options.onNodeSelect || (() => {});
        this.onNodeExpand = options.onNodeExpand || (() => {});
        this.onNodeCollapse = options.onNodeCollapse || (() => {});
        this.onNodeMove = options.onNodeMove || (() => {});
        
        this.enableDragDrop = options.enableDragDrop !== false;
        this.showIcons = options.showIcons !== false;
        this.showCheckboxes = options.showCheckboxes || false;
        this.allowMultiSelect = options.allowMultiSelect || false;
        
        this.checkedNodes = new Set();
        this.selectedNodes = new Set();
    }
    
    async render(container) {
        this.container = container;
        this.container.className = 'file-tree';
        this.updateTree();
    }
    
    setData(data) {
        this.data = data;
        this.updateTree();
    }
    
    updateTree() {
        if (!this.container) return;
        
        const html = this.renderTreeNodes(this.data, '');
        this.container.innerHTML = html;
        
        this.setupEventListeners();
        this.initializeDragDrop();
    }
    
    renderTreeNodes(nodes, path = '', level = 0) {
        let html = '';
        
        Object.values(nodes).forEach(node => {
            const nodePath = path ? `${path}/${node.name}` : node.name;
            const isExpanded = this.expandedNodes.has(nodePath);
            const hasChildren = Object.keys(node.children || {}).length > 0;
            const isSelected = this.selectedNode === nodePath;
            const isChecked = this.checkedNodes.has(nodePath);
            
            html += `
                <div class="tree-node ${isSelected ? 'selected' : ''}" 
                     data-path="${nodePath}" 
                     data-type="${node.type}"
                     data-level="${level}"
                     style="padding-left: ${level * 20}px">
                    
                    <div class="tree-node-content">
                        ${hasChildren ? `
                            <button class="tree-toggle ${isExpanded ? 'expanded' : ''}" 
                                    data-path="${nodePath}">
                                <i data-lucide="${isExpanded ? 'chevron-down' : 'chevron-right'}"></i>
                            </button>
                        ` : '<span class="tree-spacer"></span>'}
                        
                        ${this.showCheckboxes ? `
                            <input type="checkbox" 
                                   class="tree-checkbox" 
                                   data-path="${nodePath}"
                                   ${isChecked ? 'checked' : ''}>
                        ` : ''}
                        
                        <div class="tree-node-label" data-path="${nodePath}">
                            ${this.showIcons ? `
                                <i class="tree-icon" data-lucide="${this.getNodeIcon(node)}"></i>
                            ` : ''}
                            <span class="tree-text">${node.name}</span>
                        </div>
                        
                        <div class="tree-node-actions">
                            <button class="btn-icon tree-action" 
                                    title="More options" 
                                    data-path="${nodePath}">
                                <i data-lucide="more-horizontal"></i>
                            </button>
                        </div>
                    </div>
                    
                    ${hasChildren && isExpanded ? `
                        <div class="tree-children" data-parent="${nodePath}">
                            ${this.renderTreeNodes(node.children, nodePath, level + 1)}
                        </div>
                    ` : ''}
                </div>
            `;
        });
        
        return html;
    }
    
    getNodeIcon(node) {
        if (node.type === 'directory') {
            return this.expandedNodes.has(node.path) ? 'folder-open' : 'folder';
        }
        
        const ext = node.name.split('.').pop().toLowerCase();
        const mimeType = node.file?.mimeType || '';
        
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
    
    setupEventListeners() {
        if (!this.container) return;
        
        // Toggle expand/collapse
        this.container.querySelectorAll('.tree-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const path = toggle.dataset.path;
                this.toggleNode(path);
            });
        });
        
        // Node selection
        this.container.querySelectorAll('.tree-node-label').forEach(label => {
            label.addEventListener('click', (e) => {
                e.stopPropagation();
                const path = label.dataset.path;
                this.selectNode(path, e.ctrlKey || e.metaKey);
            });
        });
        
        // Checkbox handling
        if (this.showCheckboxes) {
            this.container.querySelectorAll('.tree-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    e.stopPropagation();
                    const path = checkbox.dataset.path;
                    this.toggleCheck(path, checkbox.checked);
                });
            });
        }
        
        // Action buttons
        this.container.querySelectorAll('.tree-action').forEach(action => {
            action.addEventListener('click', (e) => {
                e.stopPropagation();
                const path = action.dataset.path;
                this.showNodeMenu(e, path);
            });
        });
        
        // Double-click to toggle expand
        this.container.querySelectorAll('.tree-node-content').forEach(content => {
            content.addEventListener('dblclick', (e) => {
                const path = content.closest('.tree-node').dataset.path;
                const type = content.closest('.tree-node').dataset.type;
                
                if (type === 'directory') {
                    this.toggleNode(path);
                }
            });
        });
        
        // Keyboard navigation
        this.container.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
        
        this.container.setAttribute('tabindex', '0');
    }
    
    initializeDragDrop() {
        if (!this.enableDragDrop) return;
        
        // Make tree nodes draggable
        this.container.querySelectorAll('.tree-node').forEach(node => {
            node.draggable = true;
            
            node.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', node.dataset.path);
                node.classList.add('dragging');
            });
            
            node.addEventListener('dragend', (e) => {
                node.classList.remove('dragging');
            });
            
            node.addEventListener('dragover', (e) => {
                e.preventDefault();
                const type = node.dataset.type;
                
                if (type === 'directory') {
                    node.classList.add('drag-over');
                }
            });
            
            node.addEventListener('dragleave', (e) => {
                node.classList.remove('drag-over');
            });
            
            node.addEventListener('drop', (e) => {
                e.preventDefault();
                node.classList.remove('drag-over');
                
                const sourcePath = e.dataTransfer.getData('text/plain');
                const targetPath = node.dataset.path;
                const targetType = node.dataset.type;
                
                if (targetType === 'directory' && sourcePath !== targetPath) {
                    this.moveNode(sourcePath, targetPath);
                }
            });
        });
    }
    
    toggleNode(path) {
        const isExpanded = this.expandedNodes.has(path);
        
        if (isExpanded) {
            this.expandedNodes.delete(path);
            this.onNodeCollapse(this.getNodeByPath(path));
        } else {
            this.expandedNodes.add(path);
            this.onNodeExpand(this.getNodeByPath(path));
        }
        
        this.updateTree();
    }
    
    selectNode(path, multiSelect = false) {
        if (multiSelect && this.allowMultiSelect) {
            if (this.selectedNodes.has(path)) {
                this.selectedNodes.delete(path);
            } else {
                this.selectedNodes.add(path);
            }
        } else {
            this.selectedNodes.clear();
            this.selectedNodes.add(path);
            this.selectedNode = path;
        }
        
        this.updateSelection();
        this.onNodeSelect(this.getNodeByPath(path));
    }
    
    toggleCheck(path, checked) {
        if (checked) {
            this.checkedNodes.add(path);
        } else {
            this.checkedNodes.delete(path);
        }
        
        // Update parent/child relationships
        this.updateCheckState(path, checked);
        this.updateTree();
    }
    
    updateCheckState(path, checked) {
        // Check/uncheck all children
        const node = this.getNodeByPath(path);
        if (node && node.children) {
            Object.values(node.children).forEach(child => {
                const childPath = `${path}/${child.name}`;
                if (checked) {
                    this.checkedNodes.add(childPath);
                } else {
                    this.checkedNodes.delete(childPath);
                }
                this.updateCheckState(childPath, checked);
            });
        }
        
        // Update parent state
        const parentPath = path.split('/').slice(0, -1).join('/');
        if (parentPath) {
            this.updateParentCheckState(parentPath);
        }
    }
    
    updateParentCheckState(parentPath) {
        const parent = this.getNodeByPath(parentPath);
        if (!parent || !parent.children) return;
        
        const childPaths = Object.values(parent.children).map(child => 
            `${parentPath}/${child.name}`
        );
        
        const checkedChildren = childPaths.filter(path => 
            this.checkedNodes.has(path)
        );
        
        if (checkedChildren.length === 0) {
            this.checkedNodes.delete(parentPath);
        } else if (checkedChildren.length === childPaths.length) {
            this.checkedNodes.add(parentPath);
        }
    }
    
    updateSelection() {
        this.container.querySelectorAll('.tree-node').forEach(node => {
            const path = node.dataset.path;
            node.classList.toggle('selected', this.selectedNodes.has(path));
        });
    }
    
    moveNode(sourcePath, targetPath) {
        this.onNodeMove({
            source: sourcePath,
            target: targetPath,
            sourceNode: this.getNodeByPath(sourcePath),
            targetNode: this.getNodeByPath(targetPath)
        });
    }
    
    getNodeByPath(path) {
        const parts = path.split('/');
        let current = this.data;
        
        for (const part of parts) {
            if (!current[part]) return null;
            current = current[part];
            if (parts.indexOf(part) < parts.length - 1) {
                current = current.children || {};
            }
        }
        
        return current;
    }
    
    handleKeyNavigation(e) {
        const selected = this.selectedNode;
        if (!selected) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectNextNode();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectPreviousNode();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.expandSelectedNode();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                this.collapseSelectedNode();
                break;
            case 'Enter':
                e.preventDefault();
                this.activateSelectedNode();
                break;
            case ' ':
                e.preventDefault();
                if (this.showCheckboxes) {
                    this.toggleSelectedNodeCheck();
                }
                break;
        }
    }
    
    selectNextNode() {
        const nodes = Array.from(this.container.querySelectorAll('.tree-node'));
        const currentIndex = nodes.findIndex(node => 
            node.dataset.path === this.selectedNode
        );
        
        if (currentIndex < nodes.length - 1) {
            const nextNode = nodes[currentIndex + 1];
            this.selectNode(nextNode.dataset.path);
        }
    }
    
    selectPreviousNode() {
        const nodes = Array.from(this.container.querySelectorAll('.tree-node'));
        const currentIndex = nodes.findIndex(node => 
            node.dataset.path === this.selectedNode
        );
        
        if (currentIndex > 0) {
            const prevNode = nodes[currentIndex - 1];
            this.selectNode(prevNode.dataset.path);
        }
    }
    
    expandSelectedNode() {
        if (!this.selectedNode) return;
        
        const node = this.getNodeByPath(this.selectedNode);
        if (node && node.type === 'directory' && !this.expandedNodes.has(this.selectedNode)) {
            this.toggleNode(this.selectedNode);
        }
    }
    
    collapseSelectedNode() {
        if (!this.selectedNode) return;
        
        if (this.expandedNodes.has(this.selectedNode)) {
            this.toggleNode(this.selectedNode);
        } else {
            // Select parent
            const parentPath = this.selectedNode.split('/').slice(0, -1).join('/');
            if (parentPath) {
                this.selectNode(parentPath);
            }
        }
    }
    
    activateSelectedNode() {
        if (!this.selectedNode) return;
        
        const node = this.getNodeByPath(this.selectedNode);
        if (node) {
            if (node.type === 'directory') {
                this.toggleNode(this.selectedNode);
            } else {
                this.onNodeSelect(node);
            }
        }
    }
    
    toggleSelectedNodeCheck() {
        if (!this.selectedNode || !this.showCheckboxes) return;
        
        const isChecked = this.checkedNodes.has(this.selectedNode);
        this.toggleCheck(this.selectedNode, !isChecked);
    }
    
    showNodeMenu(event, path) {
        // Implementation for context menu
        event.preventDefault();
        event.stopPropagation();
        
        const node = this.getNodeByPath(path);
        if (!node) return;
        
        // Create and show context menu
        const menu = document.createElement('div');
        menu.className = 'tree-context-menu';
        menu.style.position = 'fixed';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        menu.style.zIndex = '1000';
        
        const menuItems = this.getMenuItems(node, path);
        menu.innerHTML = menuItems.map(item => `
            <button class="context-menu-item" data-action="${item.action}">
                <i data-lucide="${item.icon}"></i>
                <span>${item.label}</span>
            </button>
        `).join('');
        
        document.body.appendChild(menu);
        
        // Handle menu clicks
        menu.addEventListener('click', (e) => {
            const action = e.target.closest('.context-menu-item')?.dataset.action;
            if (action) {
                this.handleMenuAction(action, node, path);
            }
            menu.remove();
        });
        
        // Remove menu on outside click
        const removeMenu = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', removeMenu);
            }
        };
        
        setTimeout(() => {
            document.addEventListener('click', removeMenu);
        }, 100);
    }
    
    getMenuItems(node, path) {
        const items = [];
        
        if (node.type === 'directory') {
            items.push(
                { action: 'expand-all', icon: 'expand', label: 'Expand All' },
                { action: 'collapse-all', icon: 'collapse', label: 'Collapse All' },
                { action: 'new-folder', icon: 'folder-plus', label: 'New Folder' },
                { action: 'new-file', icon: 'file-plus', label: 'New File' }
            );
        }
        
        items.push(
            { action: 'rename', icon: 'edit', label: 'Rename' },
            { action: 'copy', icon: 'copy', label: 'Copy' },
            { action: 'cut', icon: 'scissors', label: 'Cut' },
            { action: 'delete', icon: 'trash', label: 'Delete' }
        );
        
        return items;
    }
    
    handleMenuAction(action, node, path) {
        switch (action) {
            case 'expand-all':
                this.expandAll(path);
                break;
            case 'collapse-all':
                this.collapseAll(path);
                break;
            case 'rename':
                this.renameNode(path);
                break;
            case 'copy':
                this.copyNode(path);
                break;
            case 'cut':
                this.cutNode(path);
                break;
            case 'delete':
                this.deleteNode(path);
                break;
            case 'new-folder':
                this.createFolder(path);
                break;
            case 'new-file':
                this.createFile(path);
                break;
        }
    }
    
    expandAll(path) {
        const addToExpanded = (nodePath, nodes) => {
            Object.values(nodes).forEach(node => {
                const childPath = nodePath ? `${nodePath}/${node.name}` : node.name;
                if (node.type === 'directory') {
                    this.expandedNodes.add(childPath);
                    if (node.children) {
                        addToExpanded(childPath, node.children);
                    }
                }
            });
        };
        
        addToExpanded(path, this.getNodeByPath(path)?.children || {});
        this.updateTree();
    }
    
    collapseAll(path) {
        const removeFromExpanded = (nodePath, nodes) => {
            Object.values(nodes).forEach(node => {
                const childPath = nodePath ? `${nodePath}/${node.name}` : node.name;
                if (node.type === 'directory') {
                    this.expandedNodes.delete(childPath);
                    if (node.children) {
                        removeFromExpanded(childPath, node.children);
                    }
                }
            });
        };
        
        removeFromExpanded(path, this.getNodeByPath(path)?.children || {});
        this.updateTree();
    }
    
    renameNode(path) {
        const node = this.getNodeByPath(path);
        if (!node) return;
        
        const newName = prompt('Enter new name:', node.name);
        if (newName && newName !== node.name) {
            // Trigger rename event
            this.onNodeMove({
                action: 'rename',
                source: path,
                newName: newName,
                node: node
            });
        }
    }
    
    copyNode(path) {
        // Store in clipboard or trigger copy event
        this.clipboard = { action: 'copy', path: path };
    }
    
    cutNode(path) {
        // Store in clipboard or trigger cut event
        this.clipboard = { action: 'cut', path: path };
    }
    
    deleteNode(path) {
        const node = this.getNodeByPath(path);
        if (!node) return;
        
        const confirmed = confirm(`Delete "${node.name}"?`);
        if (confirmed) {
            this.onNodeMove({
                action: 'delete',
                source: path,
                node: node
            });
        }
    }
    
    createFolder(parentPath) {
        const name = prompt('Enter folder name:');
        if (name) {
            this.onNodeMove({
                action: 'create-folder',
                parent: parentPath,
                name: name
            });
        }
    }
    
    createFile(parentPath) {
        const name = prompt('Enter file name:');
        if (name) {
            this.onNodeMove({
                action: 'create-file',
                parent: parentPath,
                name: name
            });
        }
    }
    
    getSelectedPaths() {
        return Array.from(this.selectedNodes);
    }
    
    getCheckedPaths() {
        return Array.from(this.checkedNodes);
    }
    
    expandPath(path) {
        const parts = path.split('/');
        let currentPath = '';
        
        parts.forEach(part => {
            currentPath = currentPath ? `${currentPath}/${part}` : part;
            this.expandedNodes.add(currentPath);
        });
        
        this.updateTree();
    }
    
    scrollToPath(path) {
        const nodeElement = this.container.querySelector(`[data-path="${path}"]`);
        if (nodeElement) {
            nodeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}