/**
 * Comprehensive Settings/Preferences Manager
 */

import { API } from '../../utils/api.js';
import { NotificationManager } from '../../utils/notifications.js';

export class SettingsManager {
    constructor(options = {}) {
        this.container = null;
        this.settings = {};
        this.originalSettings = {};
        this.hasUnsavedChanges = false;
        
        this.sections = [
            'general',
            'appearance',
            'files',
            'privacy',
            'notifications',
            'advanced',
            'storage',
            'integrations'
        ];
        
        this.currentSection = 'general';
        
        this.onSettingsChange = options.onSettingsChange || (() => {});
        this.onSettingsSave = options.onSettingsSave || (() => {});
        
        this.setupBeforeUnload();
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="settings-manager">
                <div class="settings-header">
                    <div class="settings-title">
                        <h1>Settings & Preferences</h1>
                        <p>Customize your ActiveLog experience</p>
                    </div>
                    
                    <div class="settings-actions">
                        <button class="btn-secondary reset-settings" title="Reset to defaults">
                            <i data-lucide="refresh-cw"></i>
                            Reset
                        </button>
                        <button class="btn-secondary export-settings" title="Export settings">
                            <i data-lucide="download"></i>
                            Export
                        </button>
                        <button class="btn-secondary import-settings" title="Import settings">
                            <i data-lucide="upload"></i>
                            Import
                        </button>
                        <button class="btn-primary save-settings" disabled>
                            <i data-lucide="save"></i>
                            Save Changes
                        </button>
                    </div>
                </div>
                
                <div class="settings-content">
                    <div class="settings-sidebar">
                        <nav class="settings-nav">
                            <div class="nav-section">
                                <div class="nav-item ${this.currentSection === 'general' ? 'active' : ''}" data-section="general">
                                    <i data-lucide="settings"></i>
                                    <span>General</span>
                                </div>
                                <div class="nav-item ${this.currentSection === 'appearance' ? 'active' : ''}" data-section="appearance">
                                    <i data-lucide="palette"></i>
                                    <span>Appearance</span>
                                </div>
                                <div class="nav-item ${this.currentSection === 'files' ? 'active' : ''}" data-section="files">
                                    <i data-lucide="folder"></i>
                                    <span>Files & Folders</span>
                                </div>
                                <div class="nav-item ${this.currentSection === 'privacy' ? 'active' : ''}" data-section="privacy">
                                    <i data-lucide="shield"></i>
                                    <span>Privacy & Security</span>
                                </div>
                            </div>
                            
                            <div class="nav-section">
                                <div class="nav-item ${this.currentSection === 'notifications' ? 'active' : ''}" data-section="notifications">
                                    <i data-lucide="bell"></i>
                                    <span>Notifications</span>
                                </div>
                                <div class="nav-item ${this.currentSection === 'storage' ? 'active' : ''}" data-section="storage">
                                    <i data-lucide="hard-drive"></i>
                                    <span>Storage</span>
                                </div>
                                <div class="nav-item ${this.currentSection === 'integrations' ? 'active' : ''}" data-section="integrations">
                                    <i data-lucide="plug"></i>
                                    <span>Integrations</span>
                                </div>
                                <div class="nav-item ${this.currentSection === 'advanced' ? 'active' : ''}" data-section="advanced">
                                    <i data-lucide="sliders"></i>
                                    <span>Advanced</span>
                                </div>
                            </div>
                        </nav>
                        
                        <div class="settings-info">
                            <div class="info-item">
                                <i data-lucide="info"></i>
                                <span>Changes are automatically saved</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="settings-main">
                        <div class="settings-panel" id="settings-panel">
                            <div class="loading-settings">
                                <i data-lucide="loader" class="spin"></i>
                                <span>Loading settings...</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="settings-footer">
                    <div class="settings-status">
                        <span class="status-text">All changes saved</span>
                        <span class="status-time"></span>
                    </div>
                </div>
            </div>
        `;
        
        this.setupEventListeners();
        await this.loadSettings();
        this.renderCurrentSection();
    }
    
    setupEventListeners() {
        // Navigation
        this.container.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                this.switchSection(item.dataset.section);
            });
        });
        
        // Actions
        this.container.querySelector('.save-settings').addEventListener('click', () => {
            this.saveSettings();
        });
        
        this.container.querySelector('.reset-settings').addEventListener('click', () => {
            this.resetSettings();
        });
        
        this.container.querySelector('.export-settings').addEventListener('click', () => {
            this.exportSettings();
        });
        
        this.container.querySelector('.import-settings').addEventListener('click', () => {
            this.importSettings();
        });
        
        // Form changes
        this.container.addEventListener('input', (e) => {
            if (e.target.matches('.setting-input, .setting-select, .setting-checkbox, .setting-radio')) {
                this.handleSettingChange(e);
            }
        });
        
        this.container.addEventListener('change', (e) => {
            if (e.target.matches('.setting-input, .setting-select, .setting-checkbox, .setting-radio')) {
                this.handleSettingChange(e);
            }
        });
    }
    
    setupBeforeUnload() {
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
    }
    
    async loadSettings() {
        try {
            const response = await API.get('/settings');
            this.settings = response.settings || this.getDefaultSettings();
            this.originalSettings = JSON.parse(JSON.stringify(this.settings));
            
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.settings = this.getDefaultSettings();
            this.originalSettings = JSON.parse(JSON.stringify(this.settings));
            NotificationManager.error('Failed to load settings, using defaults');
        }
    }
    
    getDefaultSettings() {
        return {
            general: {
                language: 'en',
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                dateFormat: 'MM/dd/yyyy',
                timeFormat: '12h',
                startupView: 'dashboard',
                itemsPerPage: 50,
                enableAnalytics: true,
                enableTelemetry: false
            },
            appearance: {
                theme: 'system',
                colorScheme: 'blue',
                fontSize: 'medium',
                density: 'comfortable',
                animations: true,
                transparentSidebar: false,
                showFileIcons: true,
                showThumbnails: true,
                gridSize: 'medium'
            },
            files: {
                defaultView: 'list',
                showHiddenFiles: false,
                showFileExtensions: true,
                sortBy: 'name',
                sortOrder: 'asc',
                confirmDelete: true,
                confirmMove: false,
                enableVersioning: true,
                autoSave: true,
                defaultUploadPath: '/uploads',
                maxFileSize: 100,
                allowedFileTypes: []
            },
            privacy: {
                enableEncryption: true,
                encryptionLevel: 'standard',
                shareAnalytics: false,
                enableCrashReports: true,
                sessionTimeout: 24,
                twoFactorAuth: false,
                passwordRequired: true,
                biometricAuth: false,
                ipRestrictions: false,
                allowedIPs: []
            },
            notifications: {
                enabled: true,
                desktop: true,
                email: true,
                sound: true,
                uploadComplete: true,
                processingComplete: true,
                errors: true,
                sharing: true,
                systemUpdates: false,
                digestEmail: 'weekly',
                quietHoursStart: '22:00',
                quietHoursEnd: '08:00'
            },
            storage: {
                autoCleanup: true,
                cleanupInterval: 30,
                compressionEnabled: true,
                compressionLevel: 'balanced',
                deduplication: true,
                cloudBackup: false,
                cloudProvider: 'none',
                localBackup: true,
                backupSchedule: 'daily',
                retentionPeriod: 90
            },
            integrations: {
                googleDrive: { enabled: false, autoSync: false },
                dropbox: { enabled: false, autoSync: false },
                oneDrive: { enabled: false, autoSync: false },
                slack: { enabled: false, notifications: false },
                discord: { enabled: false, notifications: false },
                webhooks: { enabled: false, urls: [] },
                apiAccess: { enabled: false, rateLimit: 1000 }
            },
            advanced: {
                debugMode: false,
                verboseLogging: false,
                experimentalFeatures: false,
                performanceMode: 'balanced',
                cacheSize: 500,
                maxConcurrentUploads: 3,
                chunkSize: 5,
                enableWebWorkers: true,
                enableServiceWorker: true,
                enablePWA: true
            }
        };
    }
    
    switchSection(section) {
        this.currentSection = section;
        
        // Update navigation
        this.container.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.section === section);
        });
        
        this.renderCurrentSection();
    }
    
    renderCurrentSection() {
        const panel = this.container.querySelector('#settings-panel');
        
        switch (this.currentSection) {
            case 'general':
                this.renderGeneralSettings(panel);
                break;
            case 'appearance':
                this.renderAppearanceSettings(panel);
                break;
            case 'files':
                this.renderFilesSettings(panel);
                break;
            case 'privacy':
                this.renderPrivacySettings(panel);
                break;
            case 'notifications':
                this.renderNotificationSettings(panel);
                break;
            case 'storage':
                this.renderStorageSettings(panel);
                break;
            case 'integrations':
                this.renderIntegrationsSettings(panel);
                break;
            case 'advanced':
                this.renderAdvancedSettings(panel);
                break;
        }
    }
    
    renderGeneralSettings(panel) {
        const settings = this.settings.general;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>General Settings</h2>
                    <p>Basic application preferences</p>
                </div>
                
                <div class="setting-group">
                    <div class="setting-item">
                        <label class="setting-label">Language</label>
                        <select class="setting-select" data-key="general.language" data-value="${settings.language}">
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                            <option value="de">Deutsch</option>
                            <option value="zh">中文</option>
                        </select>
                        <small class="setting-description">Interface language</small>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Timezone</label>
                        <select class="setting-select" data-key="general.timezone" data-value="${settings.timezone}">
                            ${this.getTimezoneOptions()}
                        </select>
                        <small class="setting-description">Used for displaying dates and times</small>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Date Format</label>
                        <select class="setting-select" data-key="general.dateFormat" data-value="${settings.dateFormat}">
                            <option value="MM/dd/yyyy">MM/DD/YYYY</option>
                            <option value="dd/MM/yyyy">DD/MM/YYYY</option>
                            <option value="yyyy-MM-dd">YYYY-MM-DD</option>
                            <option value="dd MMM yyyy">DD MMM YYYY</option>
                        </select>
                        <small class="setting-description">How dates are displayed</small>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Time Format</label>
                        <div class="setting-radio-group">
                            <label class="radio-option">
                                <input type="radio" name="timeFormat" value="12h" class="setting-radio" 
                                       data-key="general.timeFormat" ${settings.timeFormat === '12h' ? 'checked' : ''}>
                                <span>12 Hour (AM/PM)</span>
                            </label>
                            <label class="radio-option">
                                <input type="radio" name="timeFormat" value="24h" class="setting-radio" 
                                       data-key="general.timeFormat" ${settings.timeFormat === '24h' ? 'checked' : ''}>
                                <span>24 Hour</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Default View</label>
                        <select class="setting-select" data-key="general.startupView" data-value="${settings.startupView}">
                            <option value="dashboard">Dashboard</option>
                            <option value="files">Files</option>
                            <option value="recent">Recent Files</option>
                            <option value="favorites">Favorites</option>
                        </select>
                        <small class="setting-description">What to show when you open the app</small>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Items Per Page</label>
                        <select class="setting-select" data-key="general.itemsPerPage" data-value="${settings.itemsPerPage}">
                            <option value="25">25</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="200">200</option>
                        </select>
                        <small class="setting-description">Number of items to display per page</small>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Privacy & Analytics</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="general.enableAnalytics" 
                                   ${settings.enableAnalytics ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Enable Analytics</div>
                                <div class="toggle-description">Help improve the app by sharing usage analytics</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="general.enableTelemetry" 
                                   ${settings.enableTelemetry ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Enable Telemetry</div>
                                <div class="toggle-description">Share technical performance data</div>
                            </div>
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
    }
    
    renderAppearanceSettings(panel) {
        const settings = this.settings.appearance;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Appearance</h2>
                    <p>Customize the look and feel</p>
                </div>
                
                <div class="setting-group">
                    <div class="setting-item">
                        <label class="setting-label">Theme</label>
                        <div class="theme-selector">
                            <div class="theme-option ${settings.theme === 'light' ? 'selected' : ''}" 
                                 data-theme="light" data-key="appearance.theme">
                                <div class="theme-preview light"></div>
                                <span>Light</span>
                            </div>
                            <div class="theme-option ${settings.theme === 'dark' ? 'selected' : ''}" 
                                 data-theme="dark" data-key="appearance.theme">
                                <div class="theme-preview dark"></div>
                                <span>Dark</span>
                            </div>
                            <div class="theme-option ${settings.theme === 'system' ? 'selected' : ''}" 
                                 data-theme="system" data-key="appearance.theme">
                                <div class="theme-preview system"></div>
                                <span>System</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Color Scheme</label>
                        <div class="color-selector">
                            ${['blue', 'green', 'purple', 'red', 'orange', 'pink'].map(color => `
                                <div class="color-option ${settings.colorScheme === color ? 'selected' : ''}" 
                                     data-color="${color}" data-key="appearance.colorScheme">
                                    <div class="color-preview ${color}"></div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Font Size</label>
                        <div class="size-selector">
                            <div class="size-option ${settings.fontSize === 'small' ? 'selected' : ''}" 
                                 data-size="small" data-key="appearance.fontSize">Small</div>
                            <div class="size-option ${settings.fontSize === 'medium' ? 'selected' : ''}" 
                                 data-size="medium" data-key="appearance.fontSize">Medium</div>
                            <div class="size-option ${settings.fontSize === 'large' ? 'selected' : ''}" 
                                 data-size="large" data-key="appearance.fontSize">Large</div>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Density</label>
                        <select class="setting-select" data-key="appearance.density" data-value="${settings.density}">
                            <option value="compact">Compact</option>
                            <option value="comfortable">Comfortable</option>
                            <option value="spacious">Spacious</option>
                        </select>
                        <small class="setting-description">How much space between interface elements</small>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Interface Options</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="appearance.animations" 
                                   ${settings.animations ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Enable Animations</div>
                                <div class="toggle-description">Smooth transitions and effects</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="appearance.showFileIcons" 
                                   ${settings.showFileIcons ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Show File Icons</div>
                                <div class="toggle-description">Display icons for different file types</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="appearance.showThumbnails" 
                                   ${settings.showThumbnails ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Show Thumbnails</div>
                                <div class="toggle-description">Display image and video previews</div>
                            </div>
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
        this.setupThemeSelector(panel);
        this.setupColorSelector(panel);
        this.setupSizeSelector(panel);
    }
    
    renderFilesSettings(panel) {
        const settings = this.settings.files;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Files & Folders</h2>
                    <p>Configure file management preferences</p>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">View Settings</div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Default View</label>
                        <select class="setting-select" data-key="files.defaultView" data-value="${settings.defaultView}">
                            <option value="list">List</option>
                            <option value="grid">Grid</option>
                            <option value="tree">Tree</option>
                        </select>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="files.showHiddenFiles" 
                                   ${settings.showHiddenFiles ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Show Hidden Files</div>
                                <div class="toggle-description">Display files that start with a dot</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="files.showFileExtensions" 
                                   ${settings.showFileExtensions ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Show File Extensions</div>
                                <div class="toggle-description">Display file extensions (.txt, .jpg, etc.)</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Upload Settings</div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Default Upload Path</label>
                        <div class="path-input">
                            <input type="text" class="setting-input" 
                                   data-key="files.defaultUploadPath" 
                                   value="${settings.defaultUploadPath}">
                            <button class="browse-path">Browse</button>
                        </div>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Maximum File Size (MB)</label>
                        <input type="number" class="setting-input" 
                               data-key="files.maxFileSize" 
                               value="${settings.maxFileSize}" 
                               min="1" max="1000">
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="files.confirmDelete" 
                                   ${settings.confirmDelete ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Confirm Delete</div>
                                <div class="toggle-description">Show confirmation dialog when deleting files</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="files.enableVersioning" 
                                   ${settings.enableVersioning ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Enable Versioning</div>
                                <div class="toggle-description">Keep previous versions of files</div>
                            </div>
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
    }
    
    renderPrivacySettings(panel) {
        const settings = this.settings.privacy;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Privacy & Security</h2>
                    <p>Control your privacy and security settings</p>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Security</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="privacy.enableEncryption" 
                                   ${settings.enableEncryption ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Enable Encryption</div>
                                <div class="toggle-description">Encrypt files before storage</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Session Timeout (hours)</label>
                        <input type="number" class="setting-input" 
                               data-key="privacy.sessionTimeout" 
                               value="${settings.sessionTimeout}" 
                               min="1" max="168">
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="privacy.twoFactorAuth" 
                                   ${settings.twoFactorAuth ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Two-Factor Authentication</div>
                                <div class="toggle-description">Require additional verification for login</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Data Sharing</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="privacy.shareAnalytics" 
                                   ${settings.shareAnalytics ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Share Analytics</div>
                                <div class="toggle-description">Help improve the product by sharing usage data</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="privacy.enableCrashReports" 
                                   ${settings.enableCrashReports ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Crash Reports</div>
                                <div class="toggle-description">Send crash reports to help fix bugs</div>
                            </div>
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
    }
    
    renderNotificationSettings(panel) {
        const settings = this.settings.notifications;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Notifications</h2>
                    <p>Configure when and how you receive notifications</p>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">General</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="notifications.enabled" 
                                   ${settings.enabled ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Enable Notifications</div>
                                <div class="toggle-description">Receive notifications from the application</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="notifications.desktop" 
                                   ${settings.desktop ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Desktop Notifications</div>
                                <div class="toggle-description">Show desktop notifications</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="notifications.sound" 
                                   ${settings.sound ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Sound Notifications</div>
                                <div class="toggle-description">Play sounds for notifications</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Notification Types</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="notifications.uploadComplete" 
                                   ${settings.uploadComplete ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Upload Complete</div>
                                <div class="toggle-description">When file uploads finish</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="notifications.errors" 
                                   ${settings.errors ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Error Notifications</div>
                                <div class="toggle-description">When errors occur</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="notifications.sharing" 
                                   ${settings.sharing ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Sharing Notifications</div>
                                <div class="toggle-description">When files are shared with you</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Quiet Hours</div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Start Time</label>
                        <input type="time" class="setting-input" 
                               data-key="notifications.quietHoursStart" 
                               value="${settings.quietHoursStart}">
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">End Time</label>
                        <input type="time" class="setting-input" 
                               data-key="notifications.quietHoursEnd" 
                               value="${settings.quietHoursEnd}">
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
    }
    
    renderStorageSettings(panel) {
        const settings = this.settings.storage;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Storage Management</h2>
                    <p>Configure storage and backup options</p>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Optimization</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="storage.autoCleanup" 
                                   ${settings.autoCleanup ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Auto Cleanup</div>
                                <div class="toggle-description">Automatically clean up temporary files</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="storage.compressionEnabled" 
                                   ${settings.compressionEnabled ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">File Compression</div>
                                <div class="toggle-description">Compress files to save space</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="storage.deduplication" 
                                   ${settings.deduplication ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Deduplication</div>
                                <div class="toggle-description">Remove duplicate files automatically</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Backup</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="storage.localBackup" 
                                   ${settings.localBackup ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Local Backup</div>
                                <div class="toggle-description">Create local backups of your files</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Backup Schedule</label>
                        <select class="setting-select" data-key="storage.backupSchedule" data-value="${settings.backupSchedule}">
                            <option value="hourly">Hourly</option>
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                        </select>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Retention Period (days)</label>
                        <input type="number" class="setting-input" 
                               data-key="storage.retentionPeriod" 
                               value="${settings.retentionPeriod}" 
                               min="7" max="365">
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
    }
    
    renderIntegrationsSettings(panel) {
        const settings = this.settings.integrations;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Integrations</h2>
                    <p>Connect with external services</p>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Cloud Storage</div>
                    
                    <div class="integration-item">
                        <div class="integration-header">
                            <div class="integration-info">
                                <i data-lucide="cloud" class="integration-icon"></i>
                                <div class="integration-details">
                                    <div class="integration-name">Google Drive</div>
                                    <div class="integration-description">Sync files with Google Drive</div>
                                </div>
                            </div>
                            <div class="integration-status ${settings.googleDrive.enabled ? 'connected' : 'disconnected'}">
                                ${settings.googleDrive.enabled ? 'Connected' : 'Disconnected'}
                            </div>
                        </div>
                        <div class="integration-actions">
                            <button class="btn-integration ${settings.googleDrive.enabled ? 'disconnect' : 'connect'}" 
                                    data-integration="googleDrive">
                                ${settings.googleDrive.enabled ? 'Disconnect' : 'Connect'}
                            </button>
                        </div>
                    </div>
                    
                    <div class="integration-item">
                        <div class="integration-header">
                            <div class="integration-info">
                                <i data-lucide="cloud" class="integration-icon"></i>
                                <div class="integration-details">
                                    <div class="integration-name">Dropbox</div>
                                    <div class="integration-description">Sync files with Dropbox</div>
                                </div>
                            </div>
                            <div class="integration-status ${settings.dropbox.enabled ? 'connected' : 'disconnected'}">
                                ${settings.dropbox.enabled ? 'Connected' : 'Disconnected'}
                            </div>
                        </div>
                        <div class="integration-actions">
                            <button class="btn-integration ${settings.dropbox.enabled ? 'disconnect' : 'connect'}" 
                                    data-integration="dropbox">
                                ${settings.dropbox.enabled ? 'Disconnect' : 'Connect'}
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Notifications</div>
                    
                    <div class="integration-item">
                        <div class="integration-header">
                            <div class="integration-info">
                                <i data-lucide="message-square" class="integration-icon"></i>
                                <div class="integration-details">
                                    <div class="integration-name">Slack</div>
                                    <div class="integration-description">Send notifications to Slack</div>
                                </div>
                            </div>
                            <div class="integration-status ${settings.slack.enabled ? 'connected' : 'disconnected'}">
                                ${settings.slack.enabled ? 'Connected' : 'Disconnected'}
                            </div>
                        </div>
                        <div class="integration-actions">
                            <button class="btn-integration ${settings.slack.enabled ? 'disconnect' : 'connect'}" 
                                    data-integration="slack">
                                ${settings.slack.enabled ? 'Disconnect' : 'Connect'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
        this.setupIntegrationButtons(panel);
    }
    
    renderAdvancedSettings(panel) {
        const settings = this.settings.advanced;
        
        panel.innerHTML = `
            <div class="settings-section">
                <div class="section-header">
                    <h2>Advanced Settings</h2>
                    <p>Advanced configuration options</p>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Performance</div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Performance Mode</label>
                        <select class="setting-select" data-key="advanced.performanceMode" data-value="${settings.performanceMode}">
                            <option value="power-saver">Power Saver</option>
                            <option value="balanced">Balanced</option>
                            <option value="performance">High Performance</option>
                        </select>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Cache Size (MB)</label>
                        <input type="number" class="setting-input" 
                               data-key="advanced.cacheSize" 
                               value="${settings.cacheSize}" 
                               min="100" max="2000">
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-label">Max Concurrent Uploads</label>
                        <input type="number" class="setting-input" 
                               data-key="advanced.maxConcurrentUploads" 
                               value="${settings.maxConcurrentUploads}" 
                               min="1" max="10">
                    </div>
                </div>
                
                <div class="setting-group">
                    <div class="group-title">Developer Options</div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="advanced.debugMode" 
                                   ${settings.debugMode ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Debug Mode</div>
                                <div class="toggle-description">Enable debugging features</div>
                            </div>
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="setting-toggle">
                            <input type="checkbox" class="setting-checkbox" 
                                   data-key="advanced.experimentalFeatures" 
                                   ${settings.experimentalFeatures ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <div class="toggle-content">
                                <div class="toggle-title">Experimental Features</div>
                                <div class="toggle-description">Enable experimental features (may be unstable)</div>
                            </div>
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeFormElements(panel);
    }
    
    initializeFormElements(panel) {
        // Set selected values for selects
        panel.querySelectorAll('.setting-select').forEach(select => {
            const value = select.dataset.value;
            if (value) {
                select.value = value;
            }
        });
    }
    
    setupThemeSelector(panel) {
        panel.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', () => {
                panel.querySelectorAll('.theme-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                
                this.updateSetting(option.dataset.key, option.dataset.theme);
                this.applyTheme(option.dataset.theme);
            });
        });
    }
    
    setupColorSelector(panel) {
        panel.querySelectorAll('.color-option').forEach(option => {
            option.addEventListener('click', () => {
                panel.querySelectorAll('.color-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                
                this.updateSetting(option.dataset.key, option.dataset.color);
                this.applyColorScheme(option.dataset.color);
            });
        });
    }
    
    setupSizeSelector(panel) {
        panel.querySelectorAll('.size-option').forEach(option => {
            option.addEventListener('click', () => {
                panel.querySelectorAll('.size-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                
                this.updateSetting(option.dataset.key, option.dataset.size);
                this.applyFontSize(option.dataset.size);
            });
        });
    }
    
    setupIntegrationButtons(panel) {
        panel.querySelectorAll('.btn-integration').forEach(btn => {
            btn.addEventListener('click', async () => {
                const integration = btn.dataset.integration;
                const isConnect = btn.classList.contains('connect');
                
                if (isConnect) {
                    await this.connectIntegration(integration);
                } else {
                    await this.disconnectIntegration(integration);
                }
            });
        });
    }
    
    handleSettingChange(e) {
        const element = e.target;
        const key = element.dataset.key;
        
        if (!key) return;
        
        let value;
        
        if (element.type === 'checkbox') {
            value = element.checked;
        } else if (element.type === 'radio') {
            value = element.value;
        } else {
            value = element.value;
        }
        
        this.updateSetting(key, value);
    }
    
    updateSetting(key, value) {
        const keys = key.split('.');
        let current = this.settings;
        
        for (let i = 0; i < keys.length - 1; i++) {
            if (!current[keys[i]]) {
                current[keys[i]] = {};
            }
            current = current[keys[i]];
        }
        
        current[keys[keys.length - 1]] = value;
        
        this.hasUnsavedChanges = true;
        this.updateSaveButton();
        this.onSettingsChange(key, value, this.settings);
        
        // Auto-save after a delay
        clearTimeout(this.saveTimer);
        this.saveTimer = setTimeout(() => {
            this.saveSettings();
        }, 2000);
    }
    
    updateSaveButton() {
        const saveBtn = this.container.querySelector('.save-settings');
        saveBtn.disabled = !this.hasUnsavedChanges;
        
        if (this.hasUnsavedChanges) {
            saveBtn.textContent = 'Save Changes';
            saveBtn.classList.add('has-changes');
        } else {
            saveBtn.textContent = 'Saved';
            saveBtn.classList.remove('has-changes');
        }
    }
    
    async saveSettings() {
        try {
            await API.post('/settings', { settings: this.settings });
            
            this.originalSettings = JSON.parse(JSON.stringify(this.settings));
            this.hasUnsavedChanges = false;
            this.updateSaveButton();
            this.updateStatusMessage('All changes saved');
            
            this.onSettingsSave(this.settings);
            
        } catch (error) {
            console.error('Failed to save settings:', error);
            NotificationManager.error('Failed to save settings');
        }
    }
    
    async resetSettings() {
        const confirmed = confirm('Are you sure you want to reset all settings to defaults?');
        if (!confirmed) return;
        
        try {
            this.settings = this.getDefaultSettings();
            this.hasUnsavedChanges = true;
            
            await this.saveSettings();
            this.renderCurrentSection();
            
            NotificationManager.success('Settings reset to defaults');
            
        } catch (error) {
            console.error('Failed to reset settings:', error);
            NotificationManager.error('Failed to reset settings');
        }
    }
    
    exportSettings() {
        const dataStr = JSON.stringify(this.settings, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `activelog-settings-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        URL.revokeObjectURL(url);
        NotificationManager.success('Settings exported');
    }
    
    importSettings() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const importedSettings = JSON.parse(e.target.result);
                    this.settings = { ...this.getDefaultSettings(), ...importedSettings };
                    this.hasUnsavedChanges = true;
                    
                    this.saveSettings();
                    this.renderCurrentSection();
                    
                    NotificationManager.success('Settings imported successfully');
                    
                } catch (error) {
                    console.error('Failed to import settings:', error);
                    NotificationManager.error('Invalid settings file');
                }
            };
            reader.readAsText(file);
        };
        
        input.click();
    }
    
    async connectIntegration(integration) {
        try {
            // This would typically redirect to OAuth flow
            NotificationManager.info(`Connecting to ${integration}...`);
            
            // Simulate connection
            setTimeout(() => {
                this.settings.integrations[integration].enabled = true;
                this.hasUnsavedChanges = true;
                this.renderCurrentSection();
                this.saveSettings();
                
                NotificationManager.success(`Connected to ${integration}`);
            }, 2000);
            
        } catch (error) {
            console.error(`Failed to connect to ${integration}:`, error);
            NotificationManager.error(`Failed to connect to ${integration}`);
        }
    }
    
    async disconnectIntegration(integration) {
        const confirmed = confirm(`Disconnect from ${integration}?`);
        if (!confirmed) return;
        
        try {
            this.settings.integrations[integration].enabled = false;
            this.hasUnsavedChanges = true;
            this.renderCurrentSection();
            await this.saveSettings();
            
            NotificationManager.success(`Disconnected from ${integration}`);
            
        } catch (error) {
            console.error(`Failed to disconnect from ${integration}:`, error);
            NotificationManager.error(`Failed to disconnect from ${integration}`);
        }
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }
    
    applyColorScheme(color) {
        document.documentElement.setAttribute('data-color-scheme', color);
    }
    
    applyFontSize(size) {
        document.documentElement.setAttribute('data-font-size', size);
    }
    
    updateStatusMessage(message) {
        const statusElement = this.container.querySelector('.status-text');
        const timeElement = this.container.querySelector('.status-time');
        
        if (statusElement) {
            statusElement.textContent = message;
        }
        
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString();
        }
    }
    
    getTimezoneOptions() {
        const timezones = [
            'UTC',
            'America/New_York',
            'America/Chicago',
            'America/Denver',
            'America/Los_Angeles',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Australia/Sydney'
        ];
        
        return timezones.map(tz => 
            `<option value="${tz}" ${this.settings.general.timezone === tz ? 'selected' : ''}>${tz}</option>`
        ).join('');
    }
    
    getSettings() {
        return { ...this.settings };
    }
    
    getSetting(key) {
        const keys = key.split('.');
        let current = this.settings;
        
        for (const k of keys) {
            if (current[k] === undefined) return undefined;
            current = current[k];
        }
        
        return current;
    }
    
    setSetting(key, value) {
        this.updateSetting(key, value);
    }
}