import { BaseModule } from './BaseModule.js';

export default class SettingsModule extends BaseModule {
    constructor(props = {}) {
        super(props);
        this.activeSection = props.defaultSection || 'general';
        this.settings = new Map();
        this.unsavedChanges = false;
    }

    getTitle() {
        return 'Settings';
    }

    getHeaderActions() {
        return `
            <button class="module-action" data-action="save" title="Save Settings" ${!this.unsavedChanges ? 'disabled' : ''}>💾</button>
            <button class="module-action" data-action="reset" title="Reset to Defaults">🔄</button>
            <button class="module-action" data-action="export" title="Export Settings">📤</button>
        `;
    }

    getContent() {
        return `
            <div class="settings-container">
                <div class="settings-sidebar">
                    <nav class="settings-nav">
                        ${this.getSettingsSections()}
                    </nav>
                </div>
                <div class="settings-main">
                    <div class="settings-content">
                        <div class="settings-section active" data-section="general">
                            ${this.getGeneralSettings()}
                        </div>
                        <div class="settings-section" data-section="appearance">
                            ${this.getAppearanceSettings()}
                        </div>
                        <div class="settings-section" data-section="privacy">
                            ${this.getPrivacySettings()}
                        </div>
                        <div class="settings-section" data-section="notifications">
                            ${this.getNotificationSettings()}
                        </div>
                        <div class="settings-section" data-section="data">
                            ${this.getDataSettings()}
                        </div>
                        <div class="settings-section" data-section="advanced">
                            ${this.getAdvancedSettings()}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getSettingsSections() {
        return `
            <a href="#" class="settings-nav-item active" data-section="general">
                <i class="nav-icon">⚙️</i>
                <span>General</span>
            </a>
            <a href="#" class="settings-nav-item" data-section="appearance">
                <i class="nav-icon">🎨</i>
                <span>Appearance</span>
            </a>
            <a href="#" class="settings-nav-item" data-section="privacy">
                <i class="nav-icon">🔒</i>
                <span>Privacy</span>
            </a>
            <a href="#" class="settings-nav-item" data-section="notifications">
                <i class="nav-icon">🔔</i>
                <span>Notifications</span>
            </a>
            <a href="#" class="settings-nav-item" data-section="data">
                <i class="nav-icon">💾</i>
                <span>Data & Sync</span>
            </a>
            <a href="#" class="settings-nav-item" data-section="advanced">
                <i class="nav-icon">🔧</i>
                <span>Advanced</span>
            </a>
        `;
    }

    getGeneralSettings() {
        return `
            <div class="settings-group">
                <h3>General Settings</h3>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Application Name</span>
                        <input type="text" class="setting-input" name="appName" value="${this.config.name || ''}" />
                    </label>
                    <p class="setting-description">The display name for this application</p>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Default Language</span>
                        <select class="setting-select" name="language">
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                            <option value="de">Deutsch</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Timezone</span>
                        <select class="setting-select" name="timezone">
                            <option value="auto">Auto-detect</option>
                            <option value="UTC">UTC</option>
                            <option value="America/New_York">Eastern Time</option>
                            <option value="America/Los_Angeles">Pacific Time</option>
                            <option value="Europe/London">London</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="autoSave" />
                        <span class="checkbox-text">Enable auto-save</span>
                    </label>
                    <p class="setting-description">Automatically save changes as you work</p>
                </div>
            </div>
        `;
    }

    getAppearanceSettings() {
        return `
            <div class="settings-group">
                <h3>Appearance</h3>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Theme</span>
                        <select class="setting-select" name="theme">
                            <option value="light">Light</option>
                            <option value="dark">Dark</option>
                            <option value="auto">Auto (System)</option>
                            <option value="consumer">Consumer</option>
                            <option value="professional">Professional</option>
                            <option value="marine">Marine</option>
                            <option value="gaming">Gaming</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Layout</span>
                        <select class="setting-select" name="layout">
                            <option value="sidebar">Sidebar</option>
                            <option value="default">Default</option>
                            <option value="compact">Compact</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Font Size</span>
                        <select class="setting-select" name="fontSize">
                            <option value="small">Small</option>
                            <option value="medium">Medium</option>
                            <option value="large">Large</option>
                            <option value="extra-large">Extra Large</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="animations" />
                        <span class="checkbox-text">Enable animations</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="compactMode" />
                        <span class="checkbox-text">Compact mode</span>
                    </label>
                </div>
            </div>
        `;
    }

    getPrivacySettings() {
        return `
            <div class="settings-group">
                <h3>Privacy & Security</h3>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Data Visibility</span>
                        <select class="setting-select" name="dataVisibility">
                            <option value="private">Private</option>
                            <option value="friends">Friends Only</option>
                            <option value="public">Public</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="trackingOptOut" />
                        <span class="checkbox-text">Opt out of analytics tracking</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="twoFactorAuth" />
                        <span class="checkbox-text">Enable two-factor authentication</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="sessionTimeout" />
                        <span class="checkbox-text">Auto-logout after inactivity</span>
                    </label>
                </div>
            </div>
            
            <div class="settings-group">
                <h3>Data Management</h3>
                
                <div class="setting-item">
                    <button class="btn-secondary" data-action="exportData">Export My Data</button>
                    <p class="setting-description">Download a copy of your data</p>
                </div>
                
                <div class="setting-item">
                    <button class="btn-danger" data-action="deleteAccount">Delete Account</button>
                    <p class="setting-description">Permanently delete your account and all data</p>
                </div>
            </div>
        `;
    }

    getNotificationSettings() {
        return `
            <div class="settings-group">
                <h3>Notification Preferences</h3>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="pushNotifications" />
                        <span class="checkbox-text">Push notifications</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="emailNotifications" />
                        <span class="checkbox-text">Email notifications</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="dailyDigest" />
                        <span class="checkbox-text">Daily digest</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="weeklyReport" />
                        <span class="checkbox-text">Weekly report</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Notification Sound</span>
                        <select class="setting-select" name="notificationSound">
                            <option value="default">Default</option>
                            <option value="chime">Chime</option>
                            <option value="bell">Bell</option>
                            <option value="none">None</option>
                        </select>
                    </label>
                </div>
            </div>
        `;
    }

    getDataSettings() {
        return `
            <div class="settings-group">
                <h3>Data & Synchronization</h3>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="cloudSync" />
                        <span class="checkbox-text">Enable cloud synchronization</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="offlineMode" />
                        <span class="checkbox-text">Enable offline mode</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Sync Frequency</span>
                        <select class="setting-select" name="syncFrequency">
                            <option value="realtime">Real-time</option>
                            <option value="hourly">Hourly</option>
                            <option value="daily">Daily</option>
                            <option value="manual">Manual</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <button class="btn-secondary" data-action="syncNow">Sync Now</button>
                    <p class="setting-description">Force synchronization of all data</p>
                </div>
                
                <div class="setting-item">
                    <button class="btn-secondary" data-action="clearCache">Clear Cache</button>
                    <p class="setting-description">Clear local cache and temporary files</p>
                </div>
            </div>
        `;
    }

    getAdvancedSettings() {
        return `
            <div class="settings-group">
                <h3>Advanced Settings</h3>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="developerMode" />
                        <span class="checkbox-text">Enable developer mode</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-checkbox">
                        <input type="checkbox" name="experimentalFeatures" />
                        <span class="checkbox-text">Enable experimental features</span>
                    </label>
                </div>
                
                <div class="setting-item">
                    <label class="setting-label">
                        <span class="label-text">Log Level</span>
                        <select class="setting-select" name="logLevel">
                            <option value="error">Error</option>
                            <option value="warn">Warning</option>
                            <option value="info">Info</option>
                            <option value="debug">Debug</option>
                        </select>
                    </label>
                </div>
                
                <div class="setting-item">
                    <button class="btn-secondary" data-action="downloadLogs">Download Logs</button>
                    <p class="setting-description">Download application logs for debugging</p>
                </div>
                
                <div class="setting-item">
                    <button class="btn-danger" data-action="resetSettings">Reset All Settings</button>
                    <p class="setting-description">Reset all settings to factory defaults</p>
                </div>
            </div>
        `;
    }

    async bindEvents() {
        await super.bindEvents();
        
        const navItems = this.container.querySelectorAll('.settings-nav-item');
        const inputs = this.container.querySelectorAll('input, select');
        
        navItems.forEach(item => {
            item.addEventListener('click', this.handleSectionChange.bind(this));
        });
        
        inputs.forEach(input => {
            input.addEventListener('change', this.handleSettingChange.bind(this));
        });
    }

    handleSectionChange(event) {
        event.preventDefault();
        
        const section = event.target.closest('.settings-nav-item').dataset.section;
        this.switchSection(section);
    }

    switchSection(sectionName) {
        const navItems = this.container.querySelectorAll('.settings-nav-item');
        const sections = this.container.querySelectorAll('.settings-section');
        
        navItems.forEach(item => {
            item.classList.toggle('active', item.dataset.section === sectionName);
        });
        
        sections.forEach(section => {
            section.classList.toggle('active', section.dataset.section === sectionName);
        });
        
        this.activeSection = sectionName;
    }

    handleSettingChange(event) {
        const input = event.target;
        const name = input.name;
        const value = input.type === 'checkbox' ? input.checked : input.value;
        
        this.updateSetting(name, value);
    }

    updateSetting(name, value) {
        this.settings.set(name, value);
        this.unsavedChanges = true;
        
        const saveButton = this.container.querySelector('[data-action="save"]');
        if (saveButton) {
            saveButton.disabled = false;
        }
        
        if (name === 'theme') {
            this.previewTheme(value);
        }
    }

    previewTheme(themeName) {
        document.dispatchEvent(new CustomEvent('theme:preview', {
            detail: { theme: themeName }
        }));
    }

    handleSave() {
        this.saveSettings();
    }

    handleReset() {
        if (confirm('Reset all settings to defaults? This cannot be undone.')) {
            this.resetSettings();
        }
    }

    handleExport() {
        this.exportSettings();
    }

    handleExportData() {
        document.dispatchEvent(new CustomEvent('app:data:export'));
    }

    handleDeleteAccount() {
        if (confirm('Are you sure you want to delete your account? This cannot be undone.')) {
            document.dispatchEvent(new CustomEvent('auth:account:delete'));
        }
    }

    handleSyncNow() {
        document.dispatchEvent(new CustomEvent('sync:force'));
    }

    handleClearCache() {
        document.dispatchEvent(new CustomEvent('app:cache:clear'));
    }

    handleDownloadLogs() {
        document.dispatchEvent(new CustomEvent('app:logs:download'));
    }

    handleResetSettings() {
        if (confirm('Reset all settings to factory defaults? This cannot be undone.')) {
            this.resetAllSettings();
        }
    }

    async saveSettings() {
        try {
            const settingsObject = Object.fromEntries(this.settings);
            
            document.dispatchEvent(new CustomEvent('settings:save', {
                detail: { settings: settingsObject }
            }));
            
            this.unsavedChanges = false;
            
            const saveButton = this.container.querySelector('[data-action="save"]');
            if (saveButton) {
                saveButton.disabled = true;
            }
            
            this.showSaveSuccess();
            
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showSaveError(error);
        }
    }

    resetSettings() {
        const inputs = this.container.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = input.getAttribute('data-default') || '';
            }
        });
        
        this.settings.clear();
        this.unsavedChanges = true;
    }

    resetAllSettings() {
        localStorage.removeItem(`settings_${this.config.name}`);
        location.reload();
    }

    exportSettings() {
        const settingsObject = Object.fromEntries(this.settings);
        const dataStr = JSON.stringify(settingsObject, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `${this.config.name || 'app'}-settings.json`;
        link.click();
    }

    showSaveSuccess() {
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.textContent = 'Settings saved successfully';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    showSaveError(error) {
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = `Failed to save settings: ${error.message}`;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    async loadData() {
        try {
            const saved = localStorage.getItem(`settings_${this.config.name}`);
            if (saved) {
                const settings = JSON.parse(saved);
                this.applySettings(settings);
            }
        } catch (error) {
            console.warn('Failed to load settings:', error);
        }
    }

    applySettings(settings) {
        for (const [name, value] of Object.entries(settings)) {
            const input = this.container.querySelector(`[name="${name}"]`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = value;
                } else {
                    input.value = value;
                }
            }
            this.settings.set(name, value);
        }
    }
}