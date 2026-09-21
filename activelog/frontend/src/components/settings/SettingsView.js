/**
 * Settings View Component
 */

export class SettingsView {
    constructor() {
        this.currentTab = 'general';
        this.settings = {};
    }

    async render(container) {
        container.innerHTML = `
            <div class="settings-view">
                <div class="settings-header">
                    <h2>Settings</h2>
                    <button class="btn-primary" id="save-settings">Save Changes</button>
                </div>
                
                <div class="settings-container">
                    <div class="settings-sidebar">
                        <div class="settings-nav">
                            <div class="nav-item active" data-tab="general">
                                <span class="nav-icon">⚙️</span>
                                General
                            </div>
                            <div class="nav-item" data-tab="appearance">
                                <span class="nav-icon">🎨</span>
                                Appearance
                            </div>
                            <div class="nav-item" data-tab="privacy">
                                <span class="nav-icon">🔒</span>
                                Privacy
                            </div>
                            <div class="nav-item" data-tab="notifications">
                                <span class="nav-icon">🔔</span>
                                Notifications
                            </div>
                            <div class="nav-item" data-tab="storage">
                                <span class="nav-icon">💾</span>
                                Storage
                            </div>
                            <div class="nav-item" data-tab="advanced">
                                <span class="nav-icon">🔧</span>
                                Advanced
                            </div>
                        </div>
                    </div>
                    
                    <div class="settings-content" id="settings-content">
                        <!-- Settings panels will be rendered here -->
                    </div>
                </div>
            </div>
            
            <style>
                .settings-view {
                    padding: 20px;
                    max-width: 1200px;
                    margin: 0 auto;
                    height: calc(100vh - 40px);
                    display: flex;
                    flex-direction: column;
                }
                
                .settings-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e9ecef;
                }
                
                .settings-container {
                    display: flex;
                    gap: 30px;
                    flex: 1;
                    overflow: hidden;
                }
                
                .settings-sidebar {
                    width: 250px;
                    background: #f8f9fa;
                    border-radius: 12px;
                    padding: 20px 0;
                    height: fit-content;
                }
                
                .settings-nav {
                    display: flex;
                    flex-direction: column;
                }
                
                .nav-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 15px 20px;
                    cursor: pointer;
                    border-radius: 0;
                    transition: background 0.2s;
                    color: #666;
                }
                
                .nav-item:hover {
                    background: rgba(0,123,255,0.1);
                    color: #007bff;
                }
                
                .nav-item.active {
                    background: #007bff;
                    color: white;
                }
                
                .nav-icon {
                    font-size: 18px;
                }
                
                .settings-content {
                    flex: 1;
                    background: white;
                    border-radius: 12px;
                    padding: 30px;
                    overflow-y: auto;
                }
                
                .settings-panel {
                    display: none;
                }
                
                .settings-panel.active {
                    display: block;
                }
                
                .setting-group {
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #e9ecef;
                }
                
                .setting-group:last-child {
                    border-bottom: none;
                }
                
                .setting-group h3 {
                    margin: 0 0 15px 0;
                    color: #333;
                    font-size: 18px;
                }
                
                .setting-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 0;
                    border-bottom: 1px solid #f1f3f4;
                }
                
                .setting-item:last-child {
                    border-bottom: none;
                }
                
                .setting-label {
                    display: flex;
                    flex-direction: column;
                    flex: 1;
                }
                
                .setting-title {
                    font-weight: 500;
                    margin-bottom: 4px;
                }
                
                .setting-description {
                    font-size: 14px;
                    color: #666;
                }
                
                .setting-control {
                    margin-left: 20px;
                }
                
                .toggle-switch {
                    position: relative;
                    width: 50px;
                    height: 24px;
                    background: #ccc;
                    border-radius: 12px;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                
                .toggle-switch.active {
                    background: #007bff;
                }
                
                .toggle-handle {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    background: white;
                    border-radius: 50%;
                    top: 2px;
                    left: 2px;
                    transition: transform 0.2s;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                
                .toggle-switch.active .toggle-handle {
                    transform: translateX(26px);
                }
                
                .form-select, .form-input {
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                }
                
                .btn-primary {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 16px;
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
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                .storage-usage {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                
                .usage-bar {
                    width: 100%;
                    height: 8px;
                    background: #e9ecef;
                    border-radius: 4px;
                    overflow: hidden;
                    margin: 10px 0;
                }
                
                .usage-fill {
                    height: 100%;
                    background: #007bff;
                    transition: width 0.3s;
                }
                
                @media (max-width: 768px) {
                    .settings-container {
                        flex-direction: column;
                    }
                    
                    .settings-sidebar {
                        width: 100%;
                    }
                    
                    .settings-nav {
                        flex-direction: row;
                        overflow-x: auto;
                    }
                    
                    .nav-item {
                        white-space: nowrap;
                        min-width: 120px;
                    }
                }
            </style>
        `;

        await this.loadSettings();
        this.setupEventListeners();
        this.renderSettingsPanel();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tab = e.currentTarget.getAttribute('data-tab');
                this.switchTab(tab);
            });
        });

        // Save button
        document.getElementById('save-settings').addEventListener('click', () => {
            this.saveSettings();
        });
    }

    switchTab(tab) {
        this.currentTab = tab;
        
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
        
        // Render panel
        this.renderSettingsPanel();
    }

    renderSettingsPanel() {
        const content = document.getElementById('settings-content');
        
        switch(this.currentTab) {
            case 'general':
                content.innerHTML = this.renderGeneralSettings();
                break;
            case 'appearance':
                content.innerHTML = this.renderAppearanceSettings();
                break;
            case 'privacy':
                content.innerHTML = this.renderPrivacySettings();
                break;
            case 'notifications':
                content.innerHTML = this.renderNotificationSettings();
                break;
            case 'storage':
                content.innerHTML = this.renderStorageSettings();
                break;
            case 'advanced':
                content.innerHTML = this.renderAdvancedSettings();
                break;
        }
        
        this.bindSettingControls();
    }

    renderGeneralSettings() {
        return `
            <div class="setting-group">
                <h3>General Preferences</h3>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Language</div>
                        <div class="setting-description">Choose your preferred language</div>
                    </div>
                    <div class="setting-control">
                        <select class="form-select" data-setting="language">
                            <option value="en">English</option>
                            <option value="es">Spanish</option>
                            <option value="fr">French</option>
                        </select>
                    </div>
                </div>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Auto-save</div>
                        <div class="setting-description">Automatically save changes</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="autoSave">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderAppearanceSettings() {
        return `
            <div class="setting-group">
                <h3>Theme</h3>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Dark Mode</div>
                        <div class="setting-description">Use dark theme</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="darkMode">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Accent Color</div>
                        <div class="setting-description">Choose accent color</div>
                    </div>
                    <div class="setting-control">
                        <select class="form-select" data-setting="accentColor">
                            <option value="blue">Blue</option>
                            <option value="green">Green</option>
                            <option value="purple">Purple</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    }

    renderPrivacySettings() {
        return `
            <div class="setting-group">
                <h3>Privacy Controls</h3>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Analytics</div>
                        <div class="setting-description">Allow usage analytics</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="analytics">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Data Encryption</div>
                        <div class="setting-description">Encrypt stored data</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch active" data-setting="encryption">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderNotificationSettings() {
        return `
            <div class="setting-group">
                <h3>Notification Preferences</h3>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Push Notifications</div>
                        <div class="setting-description">Receive push notifications</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch active" data-setting="pushNotifications">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Email Notifications</div>
                        <div class="setting-description">Receive email updates</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="emailNotifications">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderStorageSettings() {
        return `
            <div class="setting-group">
                <h3>Storage Usage</h3>
                <div class="storage-usage">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>Used: 2.4 GB</span>
                        <span>Available: 7.6 GB</span>
                    </div>
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: 24%"></div>
                    </div>
                </div>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Auto Cleanup</div>
                        <div class="setting-description">Automatically remove old files</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="autoCleanup">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderAdvancedSettings() {
        return `
            <div class="setting-group">
                <h3>Advanced Options</h3>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Developer Mode</div>
                        <div class="setting-description">Enable developer features</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="developerMode">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
                <div class="setting-item">
                    <div class="setting-label">
                        <div class="setting-title">Debug Logging</div>
                        <div class="setting-description">Enable debug logs</div>
                    </div>
                    <div class="setting-control">
                        <div class="toggle-switch" data-setting="debugLogging">
                            <div class="toggle-handle"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    bindSettingControls() {
        // Toggle switches
        document.querySelectorAll('.toggle-switch').forEach(toggle => {
            toggle.addEventListener('click', () => {
                toggle.classList.toggle('active');
                const setting = toggle.getAttribute('data-setting');
                this.settings[setting] = toggle.classList.contains('active');
            });
        });

        // Select dropdowns
        document.querySelectorAll('.form-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const setting = e.target.getAttribute('data-setting');
                this.settings[setting] = e.target.value;
            });
        });
    }

    async loadSettings() {
        // Mock settings data
        this.settings = {
            language: 'en',
            autoSave: false,
            darkMode: false,
            accentColor: 'blue',
            analytics: false,
            encryption: true,
            pushNotifications: true,
            emailNotifications: false,
            autoCleanup: false,
            developerMode: false,
            debugLogging: false
        };
    }

    async saveSettings() {
        try {
            // Mock API call
            console.log('Saving settings:', this.settings);
            
            // Show success message
            const saveBtn = document.getElementById('save-settings');
            const originalText = saveBtn.textContent;
            saveBtn.textContent = 'Saved!';
            saveBtn.style.background = '#28a745';
            
            setTimeout(() => {
                saveBtn.textContent = originalText;
                saveBtn.style.background = '#007bff';
            }, 2000);
            
        } catch (error) {
            console.error('Failed to save settings:', error);
        }
    }
}