/**
 * Responsive Mobile Layout Manager
 */

export class MobileLayout {
    constructor(options = {}) {
        this.container = null;
        this.isMobile = false;
        this.isTablet = false;
        this.orientation = 'portrait';
        this.viewportWidth = window.innerWidth;
        this.viewportHeight = window.innerHeight;
        
        this.breakpoints = {
            mobile: 768,
            tablet: 1024,
            desktop: 1440
        };
        
        this.sidebarOpen = false;
        this.bottomSheetOpen = false;
        this.currentView = null;
        
        this.onViewChange = options.onViewChange || (() => {});
        this.onOrientationChange = options.onOrientationChange || (() => {});
        
        this.setupResponsiveListeners();
        this.detectDevice();
    }
    
    async render(container) {
        this.container = container;
        
        if (this.isMobile) {
            await this.renderMobileLayout();
        } else if (this.isTablet) {
            await this.renderTabletLayout();
        } else {
            await this.renderDesktopLayout();
        }
        
        this.setupEventListeners();
        this.applyResponsiveStyles();
    }
    
    async renderMobileLayout() {
        this.container.innerHTML = `
            <div class="mobile-layout">
                <!-- Mobile Header -->
                <header class="mobile-header">
                    <div class="header-left">
                        <button class="mobile-menu-btn" aria-label="Open menu">
                            <i data-lucide="menu"></i>
                        </button>
                        <div class="mobile-logo">
                            <span>ActiveLog</span>
                        </div>
                    </div>
                    
                    <div class="header-center">
                        <div class="mobile-search-trigger">
                            <i data-lucide="search"></i>
                        </div>
                    </div>
                    
                    <div class="header-right">
                        <button class="mobile-notifications-btn">
                            <i data-lucide="bell"></i>
                            <span class="notification-badge">3</span>
                        </button>
                        <button class="mobile-profile-btn">
                            <div class="profile-avatar"></div>
                        </button>
                    </div>
                </header>
                
                <!-- Mobile Sidebar -->
                <div class="mobile-sidebar ${this.sidebarOpen ? 'open' : ''}">
                    <div class="sidebar-header">
                        <div class="sidebar-logo">ActiveLog</div>
                        <button class="sidebar-close" aria-label="Close menu">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    
                    <nav class="mobile-nav">
                        <div class="nav-section">
                            <div class="nav-item active" data-view="dashboard">
                                <i data-lucide="layout-dashboard"></i>
                                <span>Dashboard</span>
                            </div>
                            <div class="nav-item" data-view="files">
                                <i data-lucide="folder"></i>
                                <span>Files</span>
                                <span class="nav-count">1,234</span>
                            </div>
                            <div class="nav-item" data-view="recent">
                                <i data-lucide="clock"></i>
                                <span>Recent</span>
                            </div>
                            <div class="nav-item" data-view="favorites">
                                <i data-lucide="star"></i>
                                <span>Favorites</span>
                                <span class="nav-count">42</span>
                            </div>
                        </div>
                        
                        <div class="nav-section">
                            <div class="nav-section-title">Quick Actions</div>
                            <div class="nav-item" data-action="upload">
                                <i data-lucide="upload"></i>
                                <span>Upload Files</span>
                            </div>
                            <div class="nav-item" data-action="camera">
                                <i data-lucide="camera"></i>
                                <span>Take Photo</span>
                            </div>
                            <div class="nav-item" data-action="new-folder">
                                <i data-lucide="folder-plus"></i>
                                <span>New Folder</span>
                            </div>
                        </div>
                        
                        <div class="nav-section">
                            <div class="nav-item" data-view="settings">
                                <i data-lucide="settings"></i>
                                <span>Settings</span>
                            </div>
                            <div class="nav-item" data-action="help">
                                <i data-lucide="help-circle"></i>
                                <span>Help & Support</span>
                            </div>
                        </div>
                    </nav>
                    
                    <div class="sidebar-footer">
                        <div class="storage-indicator">
                            <div class="storage-bar">
                                <div class="storage-used" style="width: 65%"></div>
                            </div>
                            <div class="storage-text">
                                <span>6.5 GB of 10 GB used</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Mobile Main Content -->
                <main class="mobile-main">
                    <div class="mobile-content" id="mobile-content">
                        <!-- Content will be dynamically loaded here -->
                    </div>
                </main>
                
                <!-- Mobile Bottom Navigation -->
                <nav class="mobile-bottom-nav">
                    <div class="bottom-nav-item active" data-view="dashboard">
                        <i data-lucide="layout-dashboard"></i>
                        <span>Home</span>
                    </div>
                    <div class="bottom-nav-item" data-view="files">
                        <i data-lucide="folder"></i>
                        <span>Files</span>
                    </div>
                    <div class="bottom-nav-item" data-action="upload">
                        <div class="fab-icon">
                            <i data-lucide="plus"></i>
                        </div>
                    </div>
                    <div class="bottom-nav-item" data-view="search">
                        <i data-lucide="search"></i>
                        <span>Search</span>
                    </div>
                    <div class="bottom-nav-item" data-view="profile">
                        <i data-lucide="user"></i>
                        <span>Profile</span>
                    </div>
                </nav>
                
                <!-- Mobile Search Overlay -->
                <div class="mobile-search-overlay" id="mobile-search-overlay">
                    <div class="search-header">
                        <button class="search-back" aria-label="Close search">
                            <i data-lucide="arrow-left"></i>
                        </button>
                        <div class="search-input-container">
                            <input type="text" class="mobile-search-input" placeholder="Search files...">
                            <button class="search-clear" style="display: none;">
                                <i data-lucide="x"></i>
                            </button>
                        </div>
                        <button class="search-voice" aria-label="Voice search">
                            <i data-lucide="mic"></i>
                        </button>
                    </div>
                    
                    <div class="search-content">
                        <div class="search-suggestions">
                            <div class="suggestion-item">
                                <i data-lucide="clock"></i>
                                <span>Recent presentations</span>
                            </div>
                            <div class="suggestion-item">
                                <i data-lucide="image"></i>
                                <span>Photos from last week</span>
                            </div>
                            <div class="suggestion-item">
                                <i data-lucide="file-text"></i>
                                <span>Documents</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Mobile Upload Sheet -->
                <div class="mobile-upload-sheet" id="mobile-upload-sheet">
                    <div class="sheet-handle"></div>
                    <div class="sheet-content">
                        <div class="sheet-title">Upload Files</div>
                        
                        <div class="upload-options">
                            <div class="upload-option" data-type="files">
                                <div class="option-icon">
                                    <i data-lucide="file"></i>
                                </div>
                                <div class="option-content">
                                    <div class="option-title">Select Files</div>
                                    <div class="option-description">Choose files from device</div>
                                </div>
                            </div>
                            
                            <div class="upload-option" data-type="camera">
                                <div class="option-icon">
                                    <i data-lucide="camera"></i>
                                </div>
                                <div class="option-content">
                                    <div class="option-title">Take Photo</div>
                                    <div class="option-description">Use camera to capture</div>
                                </div>
                            </div>
                            
                            <div class="upload-option" data-type="folder">
                                <div class="option-icon">
                                    <i data-lucide="folder"></i>
                                </div>
                                <div class="option-content">
                                    <div class="option-title">Select Folder</div>
                                    <div class="option-description">Upload entire folder</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="upload-progress" style="display: none;">
                            <div class="progress-header">
                                <span>Uploading files...</span>
                                <span class="progress-count">2 of 5</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 40%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Mobile Action Sheet -->
                <div class="mobile-action-sheet" id="mobile-action-sheet">
                    <div class="sheet-backdrop"></div>
                    <div class="sheet-container">
                        <div class="sheet-header">
                            <div class="sheet-title">File Actions</div>
                            <button class="sheet-close">
                                <i data-lucide="x"></i>
                            </button>
                        </div>
                        <div class="sheet-actions">
                            <!-- Actions will be dynamically populated -->
                        </div>
                    </div>
                </div>
                
                <!-- Mobile Overlay -->
                <div class="mobile-overlay" id="mobile-overlay"></div>
            </div>
        `;
    }
    
    async renderTabletLayout() {
        this.container.innerHTML = `
            <div class="tablet-layout">
                <!-- Tablet Header -->
                <header class="tablet-header">
                    <div class="header-left">
                        <button class="tablet-sidebar-toggle">
                            <i data-lucide="menu"></i>
                        </button>
                        <div class="tablet-logo">ActiveLog</div>
                    </div>
                    
                    <div class="header-center">
                        <div class="tablet-search-container">
                            <div class="search-input-wrapper">
                                <i data-lucide="search" class="search-icon"></i>
                                <input type="text" class="tablet-search-input" placeholder="Search files and folders...">
                                <button class="search-filters" title="Search filters">
                                    <i data-lucide="filter"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="header-right">
                        <button class="tablet-notifications">
                            <i data-lucide="bell"></i>
                            <span class="notification-badge">5</span>
                        </button>
                        <button class="tablet-profile">
                            <div class="profile-avatar"></div>
                        </button>
                    </div>
                </header>
                
                <!-- Tablet Sidebar -->
                <aside class="tablet-sidebar ${this.sidebarOpen ? 'expanded' : 'collapsed'}">
                    <nav class="tablet-nav">
                        <div class="nav-item active" data-view="dashboard">
                            <i data-lucide="layout-dashboard"></i>
                            <span class="nav-label">Dashboard</span>
                        </div>
                        <div class="nav-item" data-view="files">
                            <i data-lucide="folder"></i>
                            <span class="nav-label">Files</span>
                        </div>
                        <div class="nav-item" data-view="recent">
                            <i data-lucide="clock"></i>
                            <span class="nav-label">Recent</span>
                        </div>
                        <div class="nav-item" data-view="favorites">
                            <i data-lucide="star"></i>
                            <span class="nav-label">Favorites</span>
                        </div>
                        <div class="nav-item" data-view="shared">
                            <i data-lucide="share"></i>
                            <span class="nav-label">Shared</span>
                        </div>
                        <div class="nav-item" data-view="trash">
                            <i data-lucide="trash"></i>
                            <span class="nav-label">Trash</span>
                        </div>
                    </nav>
                    
                    <div class="sidebar-actions">
                        <button class="fab-btn" data-action="upload">
                            <i data-lucide="plus"></i>
                            <span class="fab-label">New</span>
                        </button>
                    </div>
                </aside>
                
                <!-- Tablet Main Content -->
                <main class="tablet-main">
                    <div class="tablet-content" id="tablet-content">
                        <!-- Content will be dynamically loaded here -->
                    </div>
                </main>
                
                <!-- Tablet Upload Panel -->
                <div class="tablet-upload-panel" id="tablet-upload-panel">
                    <div class="upload-panel-content">
                        <!-- Upload progress and controls -->
                    </div>
                </div>
            </div>
        `;
    }
    
    async renderDesktopLayout() {
        // For desktop, we maintain the existing layout
        this.container.innerHTML = `
            <div class="desktop-layout">
                <!-- Use existing desktop components -->
                <div class="desktop-content" id="desktop-content">
                    <!-- Content will be loaded by existing components -->
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        if (this.isMobile) {
            this.setupMobileEventListeners();
        } else if (this.isTablet) {
            this.setupTabletEventListeners();
        }
        
        // Common responsive listeners
        this.setupSwipeGestures();
        this.setupTouchEvents();
    }
    
    setupMobileEventListeners() {
        // Mobile menu toggle
        const menuBtn = this.container.querySelector('.mobile-menu-btn');
        menuBtn?.addEventListener('click', () => {
            this.toggleSidebar();
        });
        
        // Sidebar close
        const sidebarClose = this.container.querySelector('.sidebar-close');
        sidebarClose?.addEventListener('click', () => {
            this.closeSidebar();
        });
        
        // Mobile search
        const searchTrigger = this.container.querySelector('.mobile-search-trigger');
        searchTrigger?.addEventListener('click', () => {
            this.openSearch();
        });
        
        const searchBack = this.container.querySelector('.search-back');
        searchBack?.addEventListener('click', () => {
            this.closeSearch();
        });
        
        // Bottom navigation
        this.container.querySelectorAll('.bottom-nav-item').forEach(item => {
            item.addEventListener('click', () => {
                this.handleBottomNavClick(item);
            });
        });
        
        // Navigation items
        this.container.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                this.handleNavClick(item);
            });
        });
        
        // Upload sheet
        this.setupUploadSheet();
        
        // Action sheet
        this.setupActionSheet();
        
        // Overlay
        const overlay = this.container.querySelector('#mobile-overlay');
        overlay?.addEventListener('click', () => {
            this.closeAllOverlays();
        });
    }
    
    setupTabletEventListeners() {
        // Tablet sidebar toggle
        const sidebarToggle = this.container.querySelector('.tablet-sidebar-toggle');
        sidebarToggle?.addEventListener('click', () => {
            this.toggleTabletSidebar();
        });
        
        // Navigation items
        this.container.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                this.handleNavClick(item);
            });
        });
        
        // Upload FAB
        const fabBtn = this.container.querySelector('.fab-btn');
        fabBtn?.addEventListener('click', () => {
            this.showUploadOptions();
        });
    }
    
    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        let currentX = 0;
        let currentY = 0;
        let isTracking = false;
        
        const handleTouchStart = (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isTracking = true;
        };
        
        const handleTouchMove = (e) => {
            if (!isTracking) return;
            
            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;
        };
        
        const handleTouchEnd = (e) => {
            if (!isTracking) return;
            
            const deltaX = currentX - startX;
            const deltaY = currentY - startY;
            const minSwipeDistance = 50;
            
            // Horizontal swipes
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    this.handleSwipeRight();
                } else {
                    this.handleSwipeLeft();
                }
            }
            
            // Vertical swipes
            if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > minSwipeDistance) {
                if (deltaY > 0) {
                    this.handleSwipeDown();
                } else {
                    this.handleSwipeUp();
                }
            }
            
            isTracking = false;
        };
        
        document.addEventListener('touchstart', handleTouchStart, { passive: true });
        document.addEventListener('touchmove', handleTouchMove, { passive: true });
        document.addEventListener('touchend', handleTouchEnd, { passive: true });
    }
    
    setupTouchEvents() {
        // Add touch-friendly interactions
        this.container.addEventListener('touchstart', (e) => {
            const target = e.target.closest('.touch-target, .nav-item, .upload-option');
            if (target) {
                target.classList.add('touch-active');
            }
        });
        
        this.container.addEventListener('touchend', (e) => {
            const target = e.target.closest('.touch-target, .nav-item, .upload-option');
            if (target) {
                setTimeout(() => {
                    target.classList.remove('touch-active');
                }, 150);
            }
        });
    }
    
    setupUploadSheet() {
        const uploadSheet = this.container.querySelector('#mobile-upload-sheet');
        const uploadOptions = this.container.querySelectorAll('.upload-option');
        
        uploadOptions.forEach(option => {
            option.addEventListener('click', () => {
                this.handleUploadOption(option.dataset.type);
            });
        });
        
        // Sheet drag to close
        let startY = 0;
        let currentY = 0;
        let isDragging = false;
        
        const handle = uploadSheet?.querySelector('.sheet-handle');
        handle?.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            isDragging = true;
        });
        
        handle?.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            
            currentY = e.touches[0].clientY;
            const deltaY = currentY - startY;
            
            if (deltaY > 0) {
                uploadSheet.style.transform = `translateY(${deltaY}px)`;
            }
        });
        
        handle?.addEventListener('touchend', () => {
            if (!isDragging) return;
            
            const deltaY = currentY - startY;
            
            if (deltaY > 100) {
                this.closeUploadSheet();
            } else {
                uploadSheet.style.transform = '';
            }
            
            isDragging = false;
        });
    }
    
    setupActionSheet() {
        const actionSheet = this.container.querySelector('#mobile-action-sheet');
        const backdrop = actionSheet?.querySelector('.sheet-backdrop');
        const closeBtn = actionSheet?.querySelector('.sheet-close');
        
        backdrop?.addEventListener('click', () => {
            this.closeActionSheet();
        });
        
        closeBtn?.addEventListener('click', () => {
            this.closeActionSheet();
        });
    }
    
    setupResponsiveListeners() {
        // Window resize
        window.addEventListener('resize', this.handleResize.bind(this));
        
        // Orientation change
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });
        
        // Viewport change for mobile browsers
        const initialViewportHeight = window.innerHeight;
        window.addEventListener('resize', () => {
            // Handle mobile browser viewport changes (keyboard show/hide)
            const heightDifference = initialViewportHeight - window.innerHeight;
            
            if (heightDifference > 150) {
                // Keyboard is likely open
                document.body.classList.add('keyboard-open');
            } else {
                document.body.classList.remove('keyboard-open');
            }
        });
    }
    
    detectDevice() {
        this.viewportWidth = window.innerWidth;
        this.viewportHeight = window.innerHeight;
        
        this.isMobile = this.viewportWidth <= this.breakpoints.mobile;
        this.isTablet = this.viewportWidth > this.breakpoints.mobile && 
                       this.viewportWidth <= this.breakpoints.tablet;
        
        // Detect orientation
        this.orientation = this.viewportWidth > this.viewportHeight ? 'landscape' : 'portrait';
        
        // Detect touch capability
        const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        // Update body classes
        document.body.classList.toggle('mobile', this.isMobile);
        document.body.classList.toggle('tablet', this.isTablet);
        document.body.classList.toggle('desktop', !this.isMobile && !this.isTablet);
        document.body.classList.toggle('touch', hasTouch);
        document.body.classList.toggle('landscape', this.orientation === 'landscape');
        document.body.classList.toggle('portrait', this.orientation === 'portrait');
    }
    
    handleResize() {
        const oldIsMobile = this.isMobile;
        const oldIsTablet = this.isTablet;
        
        this.detectDevice();
        
        // Re-render if device type changed
        if (oldIsMobile !== this.isMobile || oldIsTablet !== this.isTablet) {
            this.render(this.container);
        }
        
        this.applyResponsiveStyles();
    }
    
    handleOrientationChange() {
        const oldOrientation = this.orientation;
        this.detectDevice();
        
        if (oldOrientation !== this.orientation) {
            this.onOrientationChange(this.orientation, oldOrientation);
            
            // Adjust layout for orientation change
            if (this.isMobile && this.sidebarOpen) {
                this.closeSidebar();
            }
        }
    }
    
    applyResponsiveStyles() {
        const root = document.documentElement;
        
        // Set CSS custom properties for responsive design
        root.style.setProperty('--viewport-width', `${this.viewportWidth}px`);
        root.style.setProperty('--viewport-height', `${this.viewportHeight}px`);
        root.style.setProperty('--is-mobile', this.isMobile ? '1' : '0');
        root.style.setProperty('--is-tablet', this.isTablet ? '1' : '0');
        root.style.setProperty('--is-landscape', this.orientation === 'landscape' ? '1' : '0');
    }
    
    // Navigation handlers
    handleBottomNavClick(item) {
        const view = item.dataset.view;
        const action = item.dataset.action;
        
        if (action) {
            this.handleAction(action);
        } else if (view) {
            this.switchView(view);
        }
        
        // Update active state
        this.container.querySelectorAll('.bottom-nav-item').forEach(i => {
            i.classList.remove('active');
        });
        item.classList.add('active');
    }
    
    handleNavClick(item) {
        const view = item.dataset.view;
        const action = item.dataset.action;
        
        if (action) {
            this.handleAction(action);
        } else if (view) {
            this.switchView(view);
        }
        
        // Update active state
        item.closest('nav').querySelectorAll('.nav-item').forEach(i => {
            i.classList.remove('active');
        });
        item.classList.add('active');
        
        // Close sidebar on mobile after navigation
        if (this.isMobile) {
            this.closeSidebar();
        }
    }
    
    handleAction(action) {
        switch (action) {
            case 'upload':
                this.showUploadSheet();
                break;
            case 'camera':
                this.openCamera();
                break;
            case 'new-folder':
                this.createNewFolder();
                break;
            case 'help':
                this.showHelp();
                break;
        }
    }
    
    switchView(view) {
        this.currentView = view;
        this.onViewChange(view);
        
        // Update content based on view
        this.loadViewContent(view);
    }
    
    async loadViewContent(view) {
        const contentContainer = this.container.querySelector(
            this.isMobile ? '#mobile-content' : 
            this.isTablet ? '#tablet-content' : 
            '#desktop-content'
        );
        
        if (!contentContainer) return;
        
        // Show loading state
        contentContainer.innerHTML = `
            <div class="view-loading">
                <i data-lucide="loader" class="spin"></i>
                <span>Loading ${view}...</span>
            </div>
        `;
        
        // Simulate loading (in real app, this would load actual components)
        setTimeout(() => {
            this.renderViewContent(view, contentContainer);
        }, 500);
    }
    
    renderViewContent(view, container) {
        switch (view) {
            case 'dashboard':
                this.renderMobileDashboard(container);
                break;
            case 'files':
                this.renderMobileFiles(container);
                break;
            case 'search':
                this.renderMobileSearch(container);
                break;
            case 'profile':
                this.renderMobileProfile(container);
                break;
            default:
                container.innerHTML = `<div class="placeholder-content">Content for ${view} coming soon...</div>`;
        }
    }
    
    renderMobileDashboard(container) {
        container.innerHTML = `
            <div class="mobile-dashboard">
                <div class="dashboard-header">
                    <h1>Good morning, User!</h1>
                    <p>Here's what's happening today</p>
                </div>
                
                <div class="dashboard-stats">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i data-lucide="files"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">1,234</div>
                            <div class="stat-label">Files</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i data-lucide="hard-drive"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">6.5 GB</div>
                            <div class="stat-label">Storage</div>
                        </div>
                    </div>
                </div>
                
                <div class="dashboard-sections">
                    <section class="dashboard-section">
                        <div class="section-header">
                            <h2>Recent Files</h2>
                            <button class="section-action">See all</button>
                        </div>
                        <div class="file-grid">
                            ${this.generateRecentFiles()}
                        </div>
                    </section>
                    
                    <section class="dashboard-section">
                        <div class="section-header">
                            <h2>Quick Actions</h2>
                        </div>
                        <div class="action-grid">
                            <div class="action-item" data-action="upload">
                                <i data-lucide="upload"></i>
                                <span>Upload</span>
                            </div>
                            <div class="action-item" data-action="camera">
                                <i data-lucide="camera"></i>
                                <span>Photo</span>
                            </div>
                            <div class="action-item" data-action="scan">
                                <i data-lucide="scan"></i>
                                <span>Scan</span>
                            </div>
                            <div class="action-item" data-action="new-folder">
                                <i data-lucide="folder-plus"></i>
                                <span>Folder</span>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        `;
    }
    
    renderMobileFiles(container) {
        container.innerHTML = `
            <div class="mobile-files">
                <div class="files-header">
                    <div class="view-controls">
                        <button class="view-btn active" data-view="list">
                            <i data-lucide="list"></i>
                        </button>
                        <button class="view-btn" data-view="grid">
                            <i data-lucide="grid-3x3"></i>
                        </button>
                    </div>
                    <div class="sort-controls">
                        <button class="sort-btn">
                            <i data-lucide="arrow-up-down"></i>
                        </button>
                        <button class="filter-btn">
                            <i data-lucide="filter"></i>
                        </button>
                    </div>
                </div>
                
                <div class="files-content">
                    <div class="file-list">
                        ${this.generateFileList()}
                    </div>
                </div>
            </div>
        `;
    }
    
    generateRecentFiles() {
        const files = [
            { name: 'Presentation.pptx', type: 'presentation', time: '2 hours ago' },
            { name: 'Budget.xlsx', type: 'spreadsheet', time: 'Yesterday' },
            { name: 'Photo.jpg', type: 'image', time: '3 days ago' },
            { name: 'Report.pdf', type: 'document', time: '1 week ago' }
        ];
        
        return files.map(file => `
            <div class="file-card">
                <div class="file-thumbnail">
                    <i data-lucide="${this.getFileIcon(file.type)}"></i>
                </div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-time">${file.time}</div>
                </div>
            </div>
        `).join('');
    }
    
    generateFileList() {
        const files = [
            { name: 'Documents', type: 'folder', size: '45 items' },
            { name: 'Photos', type: 'folder', size: '128 items' },
            { name: 'Presentation.pptx', type: 'presentation', size: '2.4 MB' },
            { name: 'Budget.xlsx', type: 'spreadsheet', size: '845 KB' },
            { name: 'Photo.jpg', type: 'image', size: '1.2 MB' }
        ];
        
        return files.map(file => `
            <div class="file-item">
                <div class="file-icon">
                    <i data-lucide="${this.getFileIcon(file.type)}"></i>
                </div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${file.size}</div>
                </div>
                <button class="file-menu">
                    <i data-lucide="more-vertical"></i>
                </button>
            </div>
        `).join('');
    }
    
    getFileIcon(type) {
        const icons = {
            folder: 'folder',
            image: 'image',
            document: 'file-text',
            presentation: 'presentation',
            spreadsheet: 'file-spreadsheet',
            video: 'video',
            audio: 'music'
        };
        
        return icons[type] || 'file';
    }
    
    // Swipe gesture handlers
    handleSwipeRight() {
        if (this.isMobile && !this.sidebarOpen) {
            this.openSidebar();
        }
    }
    
    handleSwipeLeft() {
        if (this.isMobile && this.sidebarOpen) {
            this.closeSidebar();
        }
    }
    
    handleSwipeDown() {
        if (this.bottomSheetOpen) {
            this.closeUploadSheet();
        }
    }
    
    handleSwipeUp() {
        // Could be used for pull-to-refresh or other actions
    }
    
    // UI state management
    toggleSidebar() {
        if (this.sidebarOpen) {
            this.closeSidebar();
        } else {
            this.openSidebar();
        }
    }
    
    openSidebar() {
        this.sidebarOpen = true;
        this.container.querySelector('.mobile-sidebar')?.classList.add('open');
        this.container.querySelector('#mobile-overlay')?.classList.add('visible');
        document.body.classList.add('sidebar-open');
    }
    
    closeSidebar() {
        this.sidebarOpen = false;
        this.container.querySelector('.mobile-sidebar')?.classList.remove('open');
        this.container.querySelector('#mobile-overlay')?.classList.remove('visible');
        document.body.classList.remove('sidebar-open');
    }
    
    toggleTabletSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const sidebar = this.container.querySelector('.tablet-sidebar');
        sidebar?.classList.toggle('expanded');
        sidebar?.classList.toggle('collapsed');
    }
    
    openSearch() {
        const overlay = this.container.querySelector('#mobile-search-overlay');
        overlay?.classList.add('open');
        
        // Focus search input
        const input = overlay?.querySelector('.mobile-search-input');
        setTimeout(() => input?.focus(), 100);
    }
    
    closeSearch() {
        const overlay = this.container.querySelector('#mobile-search-overlay');
        overlay?.classList.remove('open');
    }
    
    showUploadSheet() {
        this.bottomSheetOpen = true;
        const sheet = this.container.querySelector('#mobile-upload-sheet');
        sheet?.classList.add('open');
        this.container.querySelector('#mobile-overlay')?.classList.add('visible');
    }
    
    closeUploadSheet() {
        this.bottomSheetOpen = false;
        const sheet = this.container.querySelector('#mobile-upload-sheet');
        sheet?.classList.remove('open');
        sheet?.style.removeProperty('transform');
        this.container.querySelector('#mobile-overlay')?.classList.remove('visible');
    }
    
    showActionSheet(actions) {
        const actionSheet = this.container.querySelector('#mobile-action-sheet');
        const actionsContainer = actionSheet?.querySelector('.sheet-actions');
        
        if (actionsContainer) {
            actionsContainer.innerHTML = actions.map(action => `
                <div class="action-item" data-action="${action.id}">
                    <i data-lucide="${action.icon}"></i>
                    <span>${action.label}</span>
                </div>
            `).join('');
        }
        
        actionSheet?.classList.add('open');
    }
    
    closeActionSheet() {
        const actionSheet = this.container.querySelector('#mobile-action-sheet');
        actionSheet?.classList.remove('open');
    }
    
    closeAllOverlays() {
        this.closeSidebar();
        this.closeSearch();
        this.closeUploadSheet();
        this.closeActionSheet();
    }
    
    // Action handlers
    handleUploadOption(type) {
        switch (type) {
            case 'files':
                this.selectFiles();
                break;
            case 'camera':
                this.openCamera();
                break;
            case 'folder':
                this.selectFolder();
                break;
        }
        
        this.closeUploadSheet();
    }
    
    selectFiles() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.click();
    }
    
    selectFolder() {
        const input = document.createElement('input');
        input.type = 'file';
        input.webkitdirectory = true;
        input.click();
    }
    
    openCamera() {
        // Implementation for camera access
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    // Handle camera stream
                    console.log('Camera opened successfully');
                })
                .catch(error => {
                    console.error('Camera access denied:', error);
                });
        }
    }
    
    createNewFolder() {
        const name = prompt('Enter folder name:');
        if (name) {
            console.log('Creating folder:', name);
        }
    }
    
    showHelp() {
        // Navigate to help page
        console.log('Opening help...');
    }
    
    showUploadOptions() {
        // Show upload options for tablet
        this.showUploadSheet();
    }
    
    // Public API
    getCurrentView() {
        return this.currentView;
    }
    
    isMobileDevice() {
        return this.isMobile;
    }
    
    isTabletDevice() {
        return this.isTablet;
    }
    
    getOrientation() {
        return this.orientation;
    }
    
    getViewportSize() {
        return {
            width: this.viewportWidth,
            height: this.viewportHeight
        };
    }
}