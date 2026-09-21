/**
 * Virtualized List Component for Large Datasets
 */

import { VirtualizerCore } from '@tanstack/virtual-core';

export class VirtualizedList {
    constructor(options = {}) {
        this.container = null;
        this.scrollElement = null;
        this.virtualizer = null;
        
        this.items = [];
        this.itemHeight = options.itemHeight || 40;
        this.overscan = options.overscan || 5;
        this.renderItem = options.renderItem || this.defaultRenderItem.bind(this);
        this.getItemKey = options.getItemKey || ((index, item) => item.id || index);
        
        this.onScroll = options.onScroll || (() => {});
        this.onSelectionChange = options.onSelectionChange || (() => {});
        
        this.selectedIndices = new Set();
        this.lastSelectedIndex = -1;
        
        this.isMultiSelectMode = false;
        this.enableSelection = options.enableSelection !== false;
        this.enableMultiSelect = options.enableMultiSelect !== false;
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="virtualized-list">
                <div class="virtual-scroll-container" style="position: relative; overflow: auto; height: 100%;">
                    <div class="virtual-list-inner" style="position: relative;"></div>
                </div>
            </div>
        `;
        
        this.scrollElement = container.querySelector('.virtual-scroll-container');
        this.listInner = container.querySelector('.virtual-list-inner');
        
        this.initializeVirtualizer();
        this.setupEventListeners();
        this.updateList();
    }
    
    initializeVirtualizer() {
        this.virtualizer = new VirtualizerCore({
            count: this.items.length,
            getScrollElement: () => this.scrollElement,
            estimateSize: () => this.itemHeight,
            overscan: this.overscan,
            getItemKey: (index) => this.getItemKey(index, this.items[index]),
        });
        
        this.virtualizer.setOptions({
            onChange: (instance) => {
                this.updateRenderedItems();
            },
        });
    }
    
    setupEventListeners() {
        if (!this.enableSelection) return;
        
        this.container.addEventListener('click', this.handleClick.bind(this));
        this.container.addEventListener('keydown', this.handleKeyDown.bind(this));
        
        // Enable keyboard navigation
        this.container.setAttribute('tabindex', '0');
        
        // Handle scrolling
        this.scrollElement.addEventListener('scroll', () => {
            this.onScroll(this.scrollElement.scrollTop);
        });
    }
    
    setItems(items) {
        this.items = items || [];
        
        if (this.virtualizer) {
            this.virtualizer.setOptions({
                count: this.items.length,
            });
        }
        
        this.selectedIndices.clear();
        this.lastSelectedIndex = -1;
        this.updateList();
        this.notifySelectionChange();
    }
    
    updateList() {
        if (!this.virtualizer) return;
        
        this.virtualizer.measure();
        this.updateRenderedItems();
    }
    
    updateRenderedItems() {
        const virtualItems = this.virtualizer.getVirtualItems();
        const totalSize = this.virtualizer.getTotalSize();
        
        // Update container height
        this.listInner.style.height = `${totalSize}px`;
        
        // Clear current items
        this.listInner.innerHTML = '';
        
        // Render visible items
        virtualItems.forEach((virtualItem) => {
            const item = this.items[virtualItem.index];
            const isSelected = this.selectedIndices.has(virtualItem.index);
            
            const itemElement = document.createElement('div');
            itemElement.className = `virtual-list-item ${isSelected ? 'selected' : ''}`;
            itemElement.style.position = 'absolute';
            itemElement.style.top = `${virtualItem.start}px`;
            itemElement.style.left = '0';
            itemElement.style.right = '0';
            itemElement.style.height = `${virtualItem.size}px`;
            itemElement.dataset.index = virtualItem.index;
            itemElement.dataset.key = virtualItem.key;
            
            const content = this.renderItem(item, virtualItem.index, isSelected);
            if (typeof content === 'string') {
                itemElement.innerHTML = content;
            } else {
                itemElement.appendChild(content);
            }
            
            this.listInner.appendChild(itemElement);
        });
        
        this.updateSelectionDisplay();
    }
    
    defaultRenderItem(item, index, isSelected) {
        return `
            <div class="default-item">
                <span class="item-index">${index}</span>
                <span class="item-content">${JSON.stringify(item)}</span>
            </div>
        `;
    }
    
    handleClick(event) {
        if (!this.enableSelection) return;
        
        const itemElement = event.target.closest('.virtual-list-item');
        if (!itemElement) return;
        
        const index = parseInt(itemElement.dataset.index);
        const isCtrlClick = event.ctrlKey || event.metaKey;
        const isShiftClick = event.shiftKey;
        
        if (isShiftClick && this.enableMultiSelect && this.lastSelectedIndex >= 0) {
            this.selectRange(this.lastSelectedIndex, index);
        } else if (isCtrlClick && this.enableMultiSelect) {
            this.toggleSelection(index);
        } else {
            this.selectSingle(index);
        }
        
        this.lastSelectedIndex = index;
        this.updateSelectionDisplay();
        this.notifySelectionChange();
    }
    
    handleKeyDown(event) {
        if (!this.enableSelection) return;
        
        const selectedArray = Array.from(this.selectedIndices).sort((a, b) => a - b);
        const currentIndex = selectedArray.length > 0 ? selectedArray[selectedArray.length - 1] : 0;
        
        switch (event.key) {
            case 'ArrowUp':
                event.preventDefault();
                this.selectByKeyboard(Math.max(0, currentIndex - 1), event.shiftKey);
                break;
                
            case 'ArrowDown':
                event.preventDefault();
                this.selectByKeyboard(Math.min(this.items.length - 1, currentIndex + 1), event.shiftKey);
                break;
                
            case 'Home':
                event.preventDefault();
                this.selectByKeyboard(0, event.shiftKey);
                break;
                
            case 'End':
                event.preventDefault();
                this.selectByKeyboard(this.items.length - 1, event.shiftKey);
                break;
                
            case 'PageUp':
                event.preventDefault();
                const pageUpIndex = Math.max(0, currentIndex - this.getVisibleItemCount());
                this.selectByKeyboard(pageUpIndex, event.shiftKey);
                break;
                
            case 'PageDown':
                event.preventDefault();
                const pageDownIndex = Math.min(this.items.length - 1, currentIndex + this.getVisibleItemCount());
                this.selectByKeyboard(pageDownIndex, event.shiftKey);
                break;
                
            case 'a':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    this.selectAll();
                }
                break;
                
            case 'Escape':
                event.preventDefault();
                this.clearSelection();
                break;
        }
    }
    
    selectByKeyboard(index, isShiftSelect) {
        if (isShiftSelect && this.enableMultiSelect && this.lastSelectedIndex >= 0) {
            this.selectRange(this.lastSelectedIndex, index);
        } else {
            this.selectSingle(index);
        }
        
        this.lastSelectedIndex = index;
        this.scrollToIndex(index);
        this.updateSelectionDisplay();
        this.notifySelectionChange();
    }
    
    selectSingle(index) {
        this.selectedIndices.clear();
        this.selectedIndices.add(index);
    }
    
    toggleSelection(index) {
        if (this.selectedIndices.has(index)) {
            this.selectedIndices.delete(index);
        } else {
            this.selectedIndices.add(index);
        }
    }
    
    selectRange(startIndex, endIndex) {
        const start = Math.min(startIndex, endIndex);
        const end = Math.max(startIndex, endIndex);
        
        if (!this.isMultiSelectMode) {
            this.selectedIndices.clear();
        }
        
        for (let i = start; i <= end; i++) {
            this.selectedIndices.add(i);
        }
    }
    
    selectAll() {
        if (!this.enableMultiSelect) return;
        
        this.selectedIndices.clear();
        for (let i = 0; i < this.items.length; i++) {
            this.selectedIndices.add(i);
        }
        
        this.updateSelectionDisplay();
        this.notifySelectionChange();
    }
    
    clearSelection() {
        this.selectedIndices.clear();
        this.lastSelectedIndex = -1;
        this.updateSelectionDisplay();
        this.notifySelectionChange();
    }
    
    updateSelectionDisplay() {
        this.listInner.querySelectorAll('.virtual-list-item').forEach(item => {
            const index = parseInt(item.dataset.index);
            item.classList.toggle('selected', this.selectedIndices.has(index));
        });
    }
    
    notifySelectionChange() {
        const selectedItems = Array.from(this.selectedIndices)
            .sort((a, b) => a - b)
            .map(index => ({
                index,
                item: this.items[index]
            }));
        
        this.onSelectionChange(selectedItems);
    }
    
    scrollToIndex(index, behavior = 'smooth') {
        if (index < 0 || index >= this.items.length) return;
        
        this.virtualizer.scrollToIndex(index, {
            align: 'auto',
            behavior: behavior === 'smooth' ? 'smooth' : 'auto'
        });
    }
    
    scrollToOffset(offset, behavior = 'smooth') {
        this.scrollElement.scrollTo({
            top: offset,
            behavior: behavior
        });
    }
    
    getVisibleItemCount() {
        const containerHeight = this.scrollElement.clientHeight;
        return Math.floor(containerHeight / this.itemHeight);
    }
    
    getScrollOffset() {
        return this.scrollElement.scrollTop;
    }
    
    getSelectedItems() {
        return Array.from(this.selectedIndices)
            .sort((a, b) => a - b)
            .map(index => this.items[index]);
    }
    
    getSelectedIndices() {
        return Array.from(this.selectedIndices).sort((a, b) => a - b);
    }
    
    setSelection(indices) {
        this.selectedIndices.clear();
        
        if (Array.isArray(indices)) {
            indices.forEach(index => {
                if (index >= 0 && index < this.items.length) {
                    this.selectedIndices.add(index);
                }
            });
        }
        
        this.updateSelectionDisplay();
        this.notifySelectionChange();
    }
    
    isItemSelected(index) {
        return this.selectedIndices.has(index);
    }
    
    getItemAt(index) {
        return this.items[index] || null;
    }
    
    findItemIndex(predicate) {
        return this.items.findIndex(predicate);
    }
    
    scrollToItem(predicate, behavior = 'smooth') {
        const index = this.findItemIndex(predicate);
        if (index >= 0) {
            this.scrollToIndex(index, behavior);
        }
    }
    
    refresh() {
        this.updateList();
    }
    
    destroy() {
        if (this.virtualizer) {
            this.virtualizer.destroy();
            this.virtualizer = null;
        }
        
        this.selectedIndices.clear();
        this.items = [];
    }
    
    // Performance monitoring
    getMetrics() {
        return {
            totalItems: this.items.length,
            visibleItems: this.virtualizer?.getVirtualItems().length || 0,
            selectedItems: this.selectedIndices.size,
            scrollOffset: this.getScrollOffset(),
            containerHeight: this.scrollElement?.clientHeight || 0,
            totalHeight: this.virtualizer?.getTotalSize() || 0
        };
    }
    
    // Batch operations for better performance
    batchUpdate(callback) {
        // Disable updates during batch operation
        const originalUpdateList = this.updateList;
        this.updateList = () => {};
        
        try {
            callback();
        } finally {
            // Re-enable updates and perform a single update
            this.updateList = originalUpdateList;
            this.updateList();
        }
    }
}