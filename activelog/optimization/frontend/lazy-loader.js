class LazyLoader {
  constructor(options = {}) {
    this.options = {
      // Intersection Observer options
      rootMargin: options.rootMargin || '50px',
      threshold: options.threshold || 0.1,
      
      // Loading options
      loadingClass: options.loadingClass || 'lazy-loading',
      loadedClass: options.loadedClass || 'lazy-loaded',
      errorClass: options.errorClass || 'lazy-error',
      
      // Performance options
      debounceDelay: options.debounceDelay || 100,
      retryAttempts: options.retryAttempts || 3,
      retryDelay: options.retryDelay || 1000,
      
      // Advanced options
      enablePlaceholder: options.enablePlaceholder ?? true,
      enableFadeIn: options.enableFadeIn ?? true,
      fadeInDuration: options.fadeInDuration || 300,
      preloadOffset: options.preloadOffset || 200,
      
      ...options
    };

    this.observer = null;
    this.loadQueue = new Set();
    this.loadedElements = new WeakMap();
    this.retryCount = new WeakMap();
    this.stats = {
      totalElements: 0,
      loadedElements: 0,
      errorElements: 0,
      avgLoadTime: 0,
      totalLoadTime: 0
    };

    this.init();
  }

  // Initialize lazy loader
  init() {
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported, falling back to immediate loading');
      this.fallbackToImmediate = true;
      return;
    }

    this.observer = new IntersectionObserver(
      this.debounce(this.handleIntersection.bind(this), this.options.debounceDelay),
      {
        rootMargin: this.options.rootMargin,
        threshold: this.options.threshold
      }
    );

    this.setupCSS();
    this.observeExistingElements();
  }

  // Setup CSS for animations and placeholders
  setupCSS() {
    if (document.getElementById('lazy-loader-styles')) return;

    const style = document.createElement('style');
    style.id = 'lazy-loader-styles';
    style.textContent = `
      .lazy-loading {
        opacity: 0;
        transition: opacity ${this.options.fadeInDuration}ms ease-in-out;
      }
      
      .lazy-loaded {
        opacity: 1;
      }
      
      .lazy-error {
        opacity: 0.5;
        filter: grayscale(100%);
      }
      
      .lazy-placeholder {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: lazy-shimmer 1.5s infinite;
      }
      
      @keyframes lazy-shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
      }
      
      .lazy-fade-in {
        animation: lazy-fade-in ${this.options.fadeInDuration}ms ease-in-out;
      }
      
      @keyframes lazy-fade-in {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    
    document.head.appendChild(style);
  }

  // Observe existing elements on page
  observeExistingElements() {
    const elements = document.querySelectorAll('[data-lazy]');
    elements.forEach(element => this.observe(element));
  }

  // Observe an element for lazy loading
  observe(element) {
    if (this.fallbackToImmediate) {
      this.loadElement(element);
      return;
    }

    if (this.loadedElements.has(element)) {
      return;
    }

    this.stats.totalElements++;
    
    // Setup placeholder if enabled
    if (this.options.enablePlaceholder) {
      this.setupPlaceholder(element);
    }

    this.observer.observe(element);
  }

  // Setup placeholder for element
  setupPlaceholder(element) {
    const type = element.dataset.lazy;
    
    if (type === 'image' && element.tagName === 'IMG') {
      // Create placeholder for images
      const width = element.dataset.width || element.offsetWidth || 300;
      const height = element.dataset.height || element.offsetHeight || 200;
      
      element.style.width = width + 'px';
      element.style.height = height + 'px';
      element.classList.add('lazy-placeholder');
      
      // Set placeholder image
      if (!element.src || element.src === '') {
        element.src = this.generatePlaceholderImage(width, height);
      }
    } else if (type === 'background') {
      // Placeholder for background images
      element.classList.add('lazy-placeholder');
    }
  }

  // Generate placeholder image
  generatePlaceholderImage(width, height) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, width, height);
    
    // Add loading text
    ctx.fillStyle = '#999';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Loading...', width / 2, height / 2);
    
    return canvas.toDataURL();
  }

  // Handle intersection observer callback
  handleIntersection(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        this.observer.unobserve(entry.target);
        this.loadElement(entry.target);
      }
    });
  }

  // Load an element based on its type
  async loadElement(element) {
    if (this.loadedElements.has(element)) {
      return;
    }

    const startTime = performance.now();
    const type = element.dataset.lazy;
    
    element.classList.add(this.options.loadingClass);
    this.loadQueue.add(element);

    try {
      switch (type) {
        case 'image':
          await this.loadImage(element);
          break;
        case 'background':
          await this.loadBackgroundImage(element);
          break;
        case 'iframe':
          await this.loadIframe(element);
          break;
        case 'video':
          await this.loadVideo(element);
          break;
        case 'script':
          await this.loadScript(element);
          break;
        case 'component':
          await this.loadComponent(element);
          break;
        default:
          await this.loadGeneric(element);
      }

      this.onLoadSuccess(element, performance.now() - startTime);
      
    } catch (error) {
      this.onLoadError(element, error);
    }
  }

  // Load image element
  loadImage(element) {
    return new Promise((resolve, reject) => {
      const img = element.tagName === 'IMG' ? element : new Image();
      const src = element.dataset.src || element.dataset.lazySrc;
      
      if (!src) {
        reject(new Error('No src specified for image'));
        return;
      }

      img.onload = () => {
        if (element.tagName === 'IMG') {
          element.src = src;
        } else {
          element.style.backgroundImage = `url(${src})`;
        }
        resolve();
      };

      img.onerror = () => {
        reject(new Error(`Failed to load image: ${src}`));
      };

      // Start loading
      img.src = src;
      
      // Handle srcset if provided
      if (element.dataset.srcset) {
        img.srcset = element.dataset.srcset;
        if (element.tagName === 'IMG') {
          element.srcset = element.dataset.srcset;
        }
      }
    });
  }

  // Load background image
  loadBackgroundImage(element) {
    return new Promise((resolve, reject) => {
      const src = element.dataset.bg || element.dataset.backgroundSrc;
      
      if (!src) {
        reject(new Error('No background src specified'));
        return;
      }

      const img = new Image();
      
      img.onload = () => {
        element.style.backgroundImage = `url(${src})`;
        resolve();
      };

      img.onerror = () => {
        reject(new Error(`Failed to load background image: ${src}`));
      };

      img.src = src;
    });
  }

  // Load iframe
  loadIframe(element) {
    return new Promise((resolve, reject) => {
      const src = element.dataset.src || element.dataset.lazySrc;
      
      if (!src) {
        reject(new Error('No src specified for iframe'));
        return;
      }

      element.onload = () => resolve();
      element.onerror = () => reject(new Error(`Failed to load iframe: ${src}`));
      
      element.src = src;
    });
  }

  // Load video element
  loadVideo(element) {
    return new Promise((resolve, reject) => {
      const src = element.dataset.src || element.dataset.lazySrc;
      
      if (!src) {
        reject(new Error('No src specified for video'));
        return;
      }

      element.addEventListener('canplaythrough', () => resolve(), { once: true });
      element.addEventListener('error', () => reject(new Error(`Failed to load video: ${src}`)), { once: true });
      
      element.src = src;
      element.load();
    });
  }

  // Load script dynamically
  loadScript(element) {
    return new Promise((resolve, reject) => {
      const src = element.dataset.src || element.dataset.lazySrc;
      
      if (!src) {
        reject(new Error('No src specified for script'));
        return;
      }

      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      
      document.head.appendChild(script);
    });
  }

  // Load component dynamically
  async loadComponent(element) {
    const componentPath = element.dataset.component;
    const componentProps = element.dataset.props ? JSON.parse(element.dataset.props) : {};
    
    if (!componentPath) {
      throw new Error('No component path specified');
    }

    try {
      // Dynamic import of component
      const module = await import(componentPath);
      const Component = module.default || module[Object.keys(module)[0]];
      
      if (typeof Component === 'function') {
        // Render component
        if (typeof React !== 'undefined' && typeof ReactDOM !== 'undefined') {
          ReactDOM.render(React.createElement(Component, componentProps), element);
        } else {
          // Custom component rendering
          const componentInstance = new Component(componentProps);
          element.innerHTML = componentInstance.render();
        }
      }
    } catch (error) {
      throw new Error(`Failed to load component: ${componentPath}`);
    }
  }

  // Load generic content
  loadGeneric(element) {
    return new Promise((resolve, reject) => {
      const content = element.dataset.content;
      const url = element.dataset.url;
      
      if (content) {
        element.innerHTML = content;
        resolve();
      } else if (url) {
        fetch(url)
          .then(response => response.text())
          .then(html => {
            element.innerHTML = html;
            resolve();
          })
          .catch(reject);
      } else {
        reject(new Error('No content or URL specified'));
      }
    });
  }

  // Handle successful load
  onLoadSuccess(element, loadTime) {
    element.classList.remove(this.options.loadingClass, 'lazy-placeholder');
    element.classList.add(this.options.loadedClass);
    
    if (this.options.enableFadeIn) {
      element.classList.add('lazy-fade-in');
    }
    
    this.loadQueue.delete(element);
    this.loadedElements.set(element, { loaded: true, loadTime });
    
    this.stats.loadedElements++;
    this.stats.totalLoadTime += loadTime;
    this.stats.avgLoadTime = this.stats.totalLoadTime / this.stats.loadedElements;
    
    // Dispatch custom event
    element.dispatchEvent(new CustomEvent('lazyloaded', {
      detail: { loadTime }
    }));
  }

  // Handle load error
  async onLoadError(element, error) {
    element.classList.remove(this.options.loadingClass);
    element.classList.add(this.options.errorClass);
    
    this.loadQueue.delete(element);
    this.stats.errorElements++;
    
    // Retry logic
    const currentRetries = this.retryCount.get(element) || 0;
    
    if (currentRetries < this.options.retryAttempts) {
      this.retryCount.set(element, currentRetries + 1);
      
      setTimeout(() => {
        element.classList.remove(this.options.errorClass);
        this.loadElement(element);
      }, this.options.retryDelay * (currentRetries + 1));
      
      return;
    }
    
    // Dispatch error event
    element.dispatchEvent(new CustomEvent('lazyerror', {
      detail: { error }
    }));
    
    console.warn('Lazy loading failed for element:', element, error);
  }

  // Preload elements that are close to viewport
  preloadNearbyElements() {
    if (!this.observer) return;

    const elements = document.querySelectorAll('[data-lazy]:not(.lazy-loaded)');
    
    elements.forEach(element => {
      const rect = element.getBoundingClientRect();
      const isNearViewport = rect.top <= window.innerHeight + this.options.preloadOffset;
      
      if (isNearViewport && !this.loadQueue.has(element)) {
        this.loadElement(element);
      }
    });
  }

  // Utility: Debounce function
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Get loading statistics
  getStats() {
    return {
      ...this.stats,
      loadingElements: this.loadQueue.size,
      successRate: this.stats.totalElements > 0 
        ? ((this.stats.loadedElements / this.stats.totalElements) * 100).toFixed(1) + '%'
        : '0%'
    };
  }

  // Refresh observer for dynamically added elements
  refresh() {
    this.observeExistingElements();
  }

  // Cleanup resources
  destroy() {
    if (this.observer) {
      this.observer.disconnect();
    }
    
    this.loadQueue.clear();
    this.loadedElements = new WeakMap();
    this.retryCount = new WeakMap();
  }
}

// Image lazy loading utilities
class LazyImageLoader extends LazyLoader {
  constructor(options = {}) {
    super({
      ...options,
      // Image-specific defaults
      enablePlaceholder: options.enablePlaceholder ?? true,
      enableProgressiveLoading: options.enableProgressiveLoading ?? true,
      enableWebPDetection: options.enableWebPDetection ?? true,
      supportedFormats: options.supportedFormats || ['webp', 'jpeg', 'png']
    });
    
    this.webpSupport = null;
    this.checkWebPSupport();
  }

  // Check WebP support
  async checkWebPSupport() {
    return new Promise(resolve => {
      const webP = new Image();
      webP.onload = webP.onerror = () => {
        this.webpSupport = (webP.height === 2);
        resolve(this.webpSupport);
      };
      webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
    });
  }

  // Enhanced image loading with format detection
  async loadImage(element) {
    let src = element.dataset.src || element.dataset.lazySrc;
    
    // Choose best format based on support
    if (this.options.enableWebPDetection && this.webpSupport) {
      const webpSrc = element.dataset.webp;
      if (webpSrc) {
        src = webpSrc;
      }
    }

    return super.loadImage({ ...element, dataset: { ...element.dataset, src } });
  }
}

// Component lazy loading utilities
class LazyComponentLoader extends LazyLoader {
  constructor(options = {}) {
    super(options);
    this.componentCache = new Map();
  }

  // Enhanced component loading with caching
  async loadComponent(element) {
    const componentPath = element.dataset.component;
    
    // Check cache first
    if (this.componentCache.has(componentPath)) {
      const Component = this.componentCache.get(componentPath);
      this.renderComponent(element, Component);
      return;
    }

    // Load and cache component
    try {
      const module = await import(componentPath);
      const Component = module.default || module[Object.keys(module)[0]];
      
      this.componentCache.set(componentPath, Component);
      this.renderComponent(element, Component);
    } catch (error) {
      throw new Error(`Failed to load component: ${componentPath}`);
    }
  }

  // Render component
  renderComponent(element, Component) {
    const props = element.dataset.props ? JSON.parse(element.dataset.props) : {};
    
    if (typeof Component === 'function') {
      if (typeof React !== 'undefined' && typeof ReactDOM !== 'undefined') {
        ReactDOM.render(React.createElement(Component, props), element);
      } else {
        const instance = new Component(props);
        element.innerHTML = instance.render();
      }
    }
  }
}

// Auto-initialize on DOM ready
if (typeof window !== 'undefined') {
  let globalLoader = null;
  
  function initializeLazyLoader() {
    if (!globalLoader) {
      globalLoader = new LazyLoader();
      window.lazyLoader = globalLoader;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLazyLoader);
  } else {
    initializeLazyLoader();
  }

  // Auto-refresh on dynamic content changes
  if ('MutationObserver' in window) {
    const observer = new MutationObserver(() => {
      if (globalLoader) {
        globalLoader.refresh();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    LazyLoader,
    LazyImageLoader,
    LazyComponentLoader
  };
}