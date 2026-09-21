/**
 * Tag Manager Component
 */

export class TagManager {
    constructor() {
        this.tags = [];
        this.filteredTags = [];
        this.searchTerm = '';
    }

    async render(container) {
        container.innerHTML = `
            <div class="tag-manager">
                <div class="tag-header">
                    <h2>Tag Manager</h2>
                    <button class="btn-primary" id="create-tag-btn">Create New Tag</button>
                </div>
                
                <div class="search-section">
                    <input type="text" id="tag-search" placeholder="Search tags..." class="search-input">
                </div>
                
                <div class="tags-grid" id="tags-grid">
                    <!-- Tags will be rendered here -->
                </div>
                
                <div class="tag-modal" id="tag-modal" style="display: none;">
                    <div class="modal-content">
                        <h3>Create/Edit Tag</h3>
                        <input type="text" id="tag-name" placeholder="Tag name" class="form-input">
                        <input type="color" id="tag-color" class="color-input">
                        <textarea id="tag-description" placeholder="Description" class="form-textarea"></textarea>
                        <div class="modal-actions">
                            <button id="save-tag" class="btn-primary">Save</button>
                            <button id="cancel-tag" class="btn-secondary">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>
                .tag-manager {
                    padding: 20px;
                    max-width: 1200px;
                    margin: 0 auto;
                }
                
                .tag-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e9ecef;
                }
                
                .search-section {
                    margin-bottom: 20px;
                }
                
                .search-input {
                    width: 100%;
                    max-width: 400px;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    font-size: 16px;
                }
                
                .tags-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 20px;
                }
                
                .tag-card {
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                
                .tag-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
                }
                
                .tag-color-indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    margin-bottom: 10px;
                }
                
                .tag-name {
                    font-weight: bold;
                    font-size: 18px;
                    margin-bottom: 8px;
                }
                
                .tag-description {
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 15px;
                }
                
                .tag-actions {
                    display: flex;
                    gap: 10px;
                }
                
                .btn-primary {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                .btn-secondary {
                    background: #6c757d;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                .btn-danger {
                    background: #dc3545;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                }
                
                .tag-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.5);
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .modal-content {
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    width: 90%;
                    max-width: 500px;
                }
                
                .form-input, .form-textarea {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    margin-bottom: 15px;
                    font-size: 14px;
                }
                
                .color-input {
                    width: 50px;
                    height: 40px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    margin-bottom: 15px;
                }
                
                .modal-actions {
                    display: flex;
                    gap: 10px;
                    justify-content: flex-end;
                }
            </style>
        `;

        await this.loadTags();
        this.setupEventListeners();
        this.renderTags();
    }

    setupEventListeners() {
        document.getElementById('create-tag-btn').addEventListener('click', () => this.showTagModal());
        document.getElementById('tag-search').addEventListener('input', (e) => this.handleSearch(e.target.value));
        document.getElementById('save-tag').addEventListener('click', () => this.saveTag());
        document.getElementById('cancel-tag').addEventListener('click', () => this.hideTagModal());
    }

    async loadTags() {
        // Simulate loading tags
        this.tags = [
            { id: 1, name: 'Important', color: '#ff6b6b', description: 'High priority items' },
            { id: 2, name: 'Work', color: '#4ecdc4', description: 'Work-related content' },
            { id: 3, name: 'Personal', color: '#45b7d1', description: 'Personal files and notes' },
            { id: 4, name: 'Archive', color: '#96ceb4', description: 'Archived content' }
        ];
        this.filteredTags = [...this.tags];
    }

    handleSearch(searchTerm) {
        this.searchTerm = searchTerm.toLowerCase();
        this.filteredTags = this.tags.filter(tag => 
            tag.name.toLowerCase().includes(this.searchTerm) || 
            tag.description.toLowerCase().includes(this.searchTerm)
        );
        this.renderTags();
    }

    renderTags() {
        const grid = document.getElementById('tags-grid');
        
        if (this.filteredTags.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <p>No tags found</p>
                    ${this.searchTerm ? '<p>Try adjusting your search terms</p>' : ''}
                </div>
            `;
            return;
        }

        grid.innerHTML = this.filteredTags.map(tag => `
            <div class="tag-card">
                <div class="tag-color-indicator" style="background-color: ${tag.color}"></div>
                <div class="tag-name">${tag.name}</div>
                <div class="tag-description">${tag.description}</div>
                <div class="tag-actions">
                    <button class="btn-secondary" onclick="window.tagManager.editTag(${tag.id})">Edit</button>
                    <button class="btn-danger" onclick="window.tagManager.deleteTag(${tag.id})">Delete</button>
                </div>
            </div>
        `).join('');
        
        // Store reference for global access
        window.tagManager = this;
    }

    showTagModal(tag = null) {
        const modal = document.getElementById('tag-modal');
        const nameInput = document.getElementById('tag-name');
        const colorInput = document.getElementById('tag-color');
        const descInput = document.getElementById('tag-description');
        
        if (tag) {
            nameInput.value = tag.name;
            colorInput.value = tag.color;
            descInput.value = tag.description;
            this.editingTag = tag;
        } else {
            nameInput.value = '';
            colorInput.value = '#007bff';
            descInput.value = '';
            this.editingTag = null;
        }
        
        modal.style.display = 'flex';
    }

    hideTagModal() {
        document.getElementById('tag-modal').style.display = 'none';
        this.editingTag = null;
    }

    saveTag() {
        const name = document.getElementById('tag-name').value.trim();
        const color = document.getElementById('tag-color').value;
        const description = document.getElementById('tag-description').value.trim();
        
        if (!name) {
            alert('Tag name is required');
            return;
        }
        
        if (this.editingTag) {
            // Update existing tag
            const index = this.tags.findIndex(t => t.id === this.editingTag.id);
            this.tags[index] = { ...this.editingTag, name, color, description };
        } else {
            // Create new tag
            const newTag = {
                id: Date.now(),
                name,
                color,
                description
            };
            this.tags.push(newTag);
        }
        
        this.filteredTags = this.tags.filter(tag => 
            tag.name.toLowerCase().includes(this.searchTerm) || 
            tag.description.toLowerCase().includes(this.searchTerm)
        );
        
        this.renderTags();
        this.hideTagModal();
    }

    editTag(id) {
        const tag = this.tags.find(t => t.id === id);
        if (tag) {
            this.showTagModal(tag);
        }
    }

    deleteTag(id) {
        if (confirm('Are you sure you want to delete this tag?')) {
            this.tags = this.tags.filter(t => t.id !== id);
            this.filteredTags = this.filteredTags.filter(t => t.id !== id);
            this.renderTags();
        }
    }
}