/**
 * Modern UI Components Library
 */

export class ModernButton {
    constructor(options = {}) {
        this.options = {
            text: options.text || 'Button',
            variant: options.variant || 'primary', // primary, secondary, success, warning, error
            size: options.size || 'medium', // small, medium, large
            icon: options.icon || null,
            loading: options.loading || false,
            disabled: options.disabled || false,
            onClick: options.onClick || (() => {}),
            ...options
        };
    }

    render() {
        const button = document.createElement('button');
        button.className = `modern-btn modern-btn--${this.options.variant} modern-btn--${this.options.size}`;
        
        if (this.options.disabled) button.disabled = true;
        if (this.options.loading) button.classList.add('modern-btn--loading');

        const content = document.createElement('span');
        content.className = 'modern-btn__content';

        if (this.options.icon && !this.options.loading) {
            const icon = document.createElement('span');
            icon.className = 'modern-btn__icon';
            icon.textContent = this.options.icon;
            content.appendChild(icon);
        }

        if (this.options.loading) {
            const spinner = document.createElement('span');
            spinner.className = 'modern-btn__spinner';
            content.appendChild(spinner);
        }

        const text = document.createElement('span');
        text.textContent = this.options.text;
        content.appendChild(text);

        button.appendChild(content);
        button.addEventListener('click', this.options.onClick);

        return button;
    }
}

export class ModernCard {
    constructor(options = {}) {
        this.options = {
            title: options.title || '',
            subtitle: options.subtitle || '',
            content: options.content || '',
            actions: options.actions || [],
            hover: options.hover !== false,
            elevation: options.elevation || 1, // 1-5
            ...options
        };
    }

    render() {
        const card = document.createElement('div');
        card.className = `modern-card modern-card--elevation-${this.options.elevation}`;
        
        if (this.options.hover) {
            card.classList.add('modern-card--hover');
        }

        if (this.options.title || this.options.subtitle) {
            const header = document.createElement('div');
            header.className = 'modern-card__header';

            if (this.options.title) {
                const title = document.createElement('h3');
                title.className = 'modern-card__title';
                title.textContent = this.options.title;
                header.appendChild(title);
            }

            if (this.options.subtitle) {
                const subtitle = document.createElement('p');
                subtitle.className = 'modern-card__subtitle';
                subtitle.textContent = this.options.subtitle;
                header.appendChild(subtitle);
            }

            card.appendChild(header);
        }

        if (this.options.content) {
            const content = document.createElement('div');
            content.className = 'modern-card__content';
            
            if (typeof this.options.content === 'string') {
                content.innerHTML = this.options.content;
            } else {
                content.appendChild(this.options.content);
            }
            
            card.appendChild(content);
        }

        if (this.options.actions.length > 0) {
            const actions = document.createElement('div');
            actions.className = 'modern-card__actions';
            
            this.options.actions.forEach(action => {
                if (action instanceof ModernButton) {
                    actions.appendChild(action.render());
                } else {
                    actions.appendChild(action);
                }
            });
            
            card.appendChild(actions);
        }

        return card;
    }
}

export class ModernModal {
    constructor(options = {}) {
        this.options = {
            title: options.title || '',
            content: options.content || '',
            actions: options.actions || [],
            size: options.size || 'medium', // small, medium, large, fullscreen
            closeable: options.closeable !== false,
            backdrop: options.backdrop !== false,
            onClose: options.onClose || (() => {}),
            ...options
        };
        this.isOpen = false;
        this.element = null;
    }

    render() {
        if (this.element) return this.element;

        const overlay = document.createElement('div');
        overlay.className = 'modern-modal-overlay';
        
        if (this.options.backdrop) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) this.close();
            });
        }

        const modal = document.createElement('div');
        modal.className = `modern-modal modern-modal--${this.options.size}`;

        if (this.options.title || this.options.closeable) {
            const header = document.createElement('div');
            header.className = 'modern-modal__header';

            if (this.options.title) {
                const title = document.createElement('h2');
                title.className = 'modern-modal__title';
                title.textContent = this.options.title;
                header.appendChild(title);
            }

            if (this.options.closeable) {
                const closeBtn = document.createElement('button');
                closeBtn.className = 'modern-modal__close';
                closeBtn.innerHTML = '×';
                closeBtn.addEventListener('click', () => this.close());
                header.appendChild(closeBtn);
            }

            modal.appendChild(header);
        }

        if (this.options.content) {
            const content = document.createElement('div');
            content.className = 'modern-modal__content';
            
            if (typeof this.options.content === 'string') {
                content.innerHTML = this.options.content;
            } else {
                content.appendChild(this.options.content);
            }
            
            modal.appendChild(content);
        }

        if (this.options.actions.length > 0) {
            const actions = document.createElement('div');
            actions.className = 'modern-modal__actions';
            
            this.options.actions.forEach(action => {
                if (action instanceof ModernButton) {
                    actions.appendChild(action.render());
                } else {
                    actions.appendChild(action);
                }
            });
            
            modal.appendChild(actions);
        }

        overlay.appendChild(modal);
        this.element = overlay;
        return overlay;
    }

    open() {
        if (this.isOpen) return;

        const modal = this.render();
        document.body.appendChild(modal);
        document.body.classList.add('modern-modal-open');
        
        // Trigger animation
        requestAnimationFrame(() => {
            modal.classList.add('modern-modal-overlay--open');
        });

        this.isOpen = true;

        // Escape key handler
        this.escapeHandler = (e) => {
            if (e.key === 'Escape' && this.options.closeable) {
                this.close();
            }
        };
        document.addEventListener('keydown', this.escapeHandler);
    }

    close() {
        if (!this.isOpen || !this.element) return;

        this.element.classList.remove('modern-modal-overlay--open');
        
        setTimeout(() => {
            if (this.element.parentNode) {
                this.element.parentNode.removeChild(this.element);
            }
            document.body.classList.remove('modern-modal-open');
        }, 200);

        this.isOpen = false;
        
        if (this.escapeHandler) {
            document.removeEventListener('keydown', this.escapeHandler);
        }

        this.options.onClose();
    }
}

export class ModernToast {
    static toasts = [];
    static container = null;

    static init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'modern-toast-container';
            document.body.appendChild(this.container);
        }
    }

    static show(options = {}) {
        this.init();

        const toast = document.createElement('div');
        toast.className = `modern-toast modern-toast--${options.type || 'info'}`;
        
        if (options.icon) {
            const icon = document.createElement('span');
            icon.className = 'modern-toast__icon';
            icon.textContent = options.icon;
            toast.appendChild(icon);
        }

        const content = document.createElement('div');
        content.className = 'modern-toast__content';
        
        if (options.title) {
            const title = document.createElement('div');
            title.className = 'modern-toast__title';
            title.textContent = options.title;
            content.appendChild(title);
        }

        if (options.message) {
            const message = document.createElement('div');
            message.className = 'modern-toast__message';
            message.textContent = options.message;
            content.appendChild(message);
        }

        toast.appendChild(content);

        if (options.closeable !== false) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'modern-toast__close';
            closeBtn.innerHTML = '×';
            closeBtn.addEventListener('click', () => this.remove(toast));
            toast.appendChild(closeBtn);
        }

        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('modern-toast--show');
        });

        // Auto remove
        if (options.duration !== 0) {
            const duration = options.duration || 5000;
            setTimeout(() => this.remove(toast), duration);
        }

        return toast;
    }

    static remove(toast) {
        toast.classList.remove('modern-toast--show');
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 200);
    }

    static success(message, options = {}) {
        return this.show({
            ...options,
            type: 'success',
            icon: options.icon || '✓',
            message
        });
    }

    static error(message, options = {}) {
        return this.show({
            ...options,
            type: 'error',
            icon: options.icon || '⚠',
            message
        });
    }

    static warning(message, options = {}) {
        return this.show({
            ...options,
            type: 'warning',
            icon: options.icon || '⚠',
            message
        });
    }

    static info(message, options = {}) {
        return this.show({
            ...options,
            type: 'info',
            icon: options.icon || 'ℹ',
            message
        });
    }
}

export class ModernProgress {
    constructor(options = {}) {
        this.options = {
            value: options.value || 0,
            max: options.max || 100,
            size: options.size || 'medium', // small, medium, large
            variant: options.variant || 'primary',
            showLabel: options.showLabel !== false,
            animated: options.animated !== false,
            ...options
        };
    }

    render() {
        const container = document.createElement('div');
        container.className = `modern-progress modern-progress--${this.options.size}`;

        if (this.options.showLabel) {
            const label = document.createElement('div');
            label.className = 'modern-progress__label';
            label.textContent = `${Math.round((this.options.value / this.options.max) * 100)}%`;
            container.appendChild(label);
        }

        const track = document.createElement('div');
        track.className = 'modern-progress__track';

        const bar = document.createElement('div');
        bar.className = `modern-progress__bar modern-progress__bar--${this.options.variant}`;
        
        if (this.options.animated) {
            bar.classList.add('modern-progress__bar--animated');
        }
        
        bar.style.width = `${(this.options.value / this.options.max) * 100}%`;

        track.appendChild(bar);
        container.appendChild(track);

        return container;
    }

    update(value) {
        this.options.value = Math.min(Math.max(value, 0), this.options.max);
        const container = this.element;
        if (container) {
            const bar = container.querySelector('.modern-progress__bar');
            const label = container.querySelector('.modern-progress__label');
            
            if (bar) {
                bar.style.width = `${(this.options.value / this.options.max) * 100}%`;
            }
            
            if (label && this.options.showLabel) {
                label.textContent = `${Math.round((this.options.value / this.options.max) * 100)}%`;
            }
        }
    }
}

// Add the CSS styles
const styles = `
/* Modern Button Styles */
.modern-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    border-radius: 8px;
    font-family: inherit;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
    user-select: none;
}

.modern-btn:before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: currentColor;
    opacity: 0;
    transition: opacity 0.2s ease;
}

.modern-btn:hover:before {
    opacity: 0.1;
}

.modern-btn:active {
    transform: scale(0.98);
}

.modern-btn--small {
    font-size: 14px;
}

.modern-btn--small .modern-btn__content {
    padding: 8px 16px;
}

.modern-btn--medium {
    font-size: 16px;
}

.modern-btn--medium .modern-btn__content {
    padding: 12px 24px;
}

.modern-btn--large {
    font-size: 18px;
}

.modern-btn--large .modern-btn__content {
    padding: 16px 32px;
}

.modern-btn__content {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 1;
}

.modern-btn__icon {
    display: flex;
    align-items: center;
}

.modern-btn__spinner {
    width: 16px;
    height: 16px;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.modern-btn--primary {
    background: #007bff;
    color: white;
}

.modern-btn--secondary {
    background: #6c757d;
    color: white;
}

.modern-btn--success {
    background: #28a745;
    color: white;
}

.modern-btn--warning {
    background: #ffc107;
    color: #212529;
}

.modern-btn--error {
    background: #dc3545;
    color: white;
}

.modern-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
}

.modern-btn--loading {
    pointer-events: none;
}

/* Modern Card Styles */
.modern-card {
    background: white;
    border-radius: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}

.modern-card--hover:hover {
    transform: translateY(-2px);
}

.modern-card--elevation-1 {
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.modern-card--elevation-2 {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modern-card--elevation-3 {
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.modern-card--elevation-4 {
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
}

.modern-card--elevation-5 {
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
}

.modern-card__header {
    padding: 24px 24px 0;
}

.modern-card__title {
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 600;
    color: #1a202c;
}

.modern-card__subtitle {
    margin: 0;
    font-size: 14px;
    color: #718096;
}

.modern-card__content {
    padding: 24px;
}

.modern-card__actions {
    padding: 0 24px 24px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}

/* Modern Modal Styles */
.modern-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    opacity: 0;
    visibility: hidden;
    transition: all 0.2s ease;
    padding: 20px;
}

.modern-modal-overlay--open {
    opacity: 1;
    visibility: visible;
}

.modern-modal {
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    transform: scale(0.95) translateY(20px);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    max-height: 90vh;
    overflow-y: auto;
}

.modern-modal-overlay--open .modern-modal {
    transform: scale(1) translateY(0);
}

.modern-modal--small {
    width: 100%;
    max-width: 400px;
}

.modern-modal--medium {
    width: 100%;
    max-width: 600px;
}

.modern-modal--large {
    width: 100%;
    max-width: 900px;
}

.modern-modal--fullscreen {
    width: calc(100% - 40px);
    height: calc(100% - 40px);
    max-width: none;
    max-height: none;
}

.modern-modal__header {
    padding: 24px 24px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.modern-modal__title {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: #1a202c;
}

.modern-modal__close {
    background: none;
    border: none;
    font-size: 28px;
    cursor: pointer;
    color: #718096;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s ease;
}

.modern-modal__close:hover {
    background: #f7fafc;
    color: #2d3748;
}

.modern-modal__content {
    padding: 24px;
}

.modern-modal__actions {
    padding: 0 24px 24px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}

.modern-modal-open {
    overflow: hidden;
}

/* Modern Toast Styles */
.modern-toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10001;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.modern-toast {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 16px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    min-width: 300px;
    max-width: 500px;
    transform: translateX(100%);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border-left: 4px solid;
}

.modern-toast--show {
    transform: translateX(0);
}

.modern-toast--success {
    border-left-color: #28a745;
}

.modern-toast--error {
    border-left-color: #dc3545;
}

.modern-toast--warning {
    border-left-color: #ffc107;
}

.modern-toast--info {
    border-left-color: #007bff;
}

.modern-toast__icon {
    font-size: 20px;
    flex-shrink: 0;
}

.modern-toast--success .modern-toast__icon {
    color: #28a745;
}

.modern-toast--error .modern-toast__icon {
    color: #dc3545;
}

.modern-toast--warning .modern-toast__icon {
    color: #ffc107;
}

.modern-toast--info .modern-toast__icon {
    color: #007bff;
}

.modern-toast__content {
    flex: 1;
}

.modern-toast__title {
    font-weight: 600;
    margin-bottom: 4px;
    color: #1a202c;
}

.modern-toast__message {
    color: #718096;
    font-size: 14px;
}

.modern-toast__close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #718096;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.modern-toast__close:hover {
    background: #f7fafc;
    color: #2d3748;
}

/* Modern Progress Styles */
.modern-progress {
    width: 100%;
}

.modern-progress__label {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 600;
    color: #4a5568;
    text-align: right;
}

.modern-progress__track {
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    overflow: hidden;
}

.modern-progress--small .modern-progress__track {
    height: 4px;
}

.modern-progress--large .modern-progress__track {
    height: 12px;
}

.modern-progress__bar {
    height: 100%;
    border-radius: inherit;
    transition: width 0.3s ease;
}

.modern-progress__bar--animated {
    background-image: linear-gradient(
        45deg,
        rgba(255, 255, 255, 0.15) 25%,
        transparent 25%,
        transparent 50%,
        rgba(255, 255, 255, 0.15) 50%,
        rgba(255, 255, 255, 0.15) 75%,
        transparent 75%,
        transparent
    );
    background-size: 20px 20px;
    animation: progress-stripes 1s linear infinite;
}

@keyframes progress-stripes {
    0% { background-position: 0 0; }
    100% { background-position: 20px 0; }
}

.modern-progress__bar--primary {
    background-color: #007bff;
}

.modern-progress__bar--success {
    background-color: #28a745;
}

.modern-progress__bar--warning {
    background-color: #ffc107;
}

.modern-progress__bar--error {
    background-color: #dc3545;
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
    .modern-toast-container {
        top: 10px;
        right: 10px;
        left: 10px;
    }
    
    .modern-toast {
        min-width: auto;
        max-width: none;
    }
    
    .modern-modal {
        margin: 0;
        border-radius: 0;
        max-height: 100vh;
    }
    
    .modern-modal--small,
    .modern-modal--medium,
    .modern-modal--large {
        width: 100%;
        max-width: none;
    }
}
`;

// Inject styles
if (!document.querySelector('#modern-components-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'modern-components-styles';
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
}