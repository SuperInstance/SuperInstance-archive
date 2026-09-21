// Marine Navigation Common JavaScript
// Base functionality for all marine navigation layouts

class MarineInterface {
    constructor() {
        this.currentLayout = document.body.className.match(/(\w+)-layout/)?.[1] || 'unknown';
        this.position = { lat: 41.24123, lon: -71.51456 };
        this.vessel = {
            heading: 45,
            speed: 8.2,
            course: 45
        };
        this.weather = {
            wind: { speed: 12, direction: 'NE' },
            waves: { height: 2.3, direction: 'NE' },
            visibility: 10,
            barometer: 30.15
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startDataUpdates();
        this.setupModals();
        this.initializeChartControls();
        
        console.log(`Marine Interface initialized for ${this.currentLayout} layout`);
    }

    // Event Listeners
    setupEventListeners() {
        // Chart controls
        document.getElementById('zoomIn')?.addEventListener('click', () => this.zoomChart(1.2));
        document.getElementById('zoomOut')?.addEventListener('click', () => this.zoomChart(0.8));
        document.getElementById('centerVessel')?.addEventListener('click', () => this.centerOnVessel());
        
        // Chart type changes
        document.getElementById('chartType')?.addEventListener('change', (e) => this.changeChartType(e.target.value));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        // Window resize
        window.addEventListener('resize', () => this.handleResize());
        
        // Context menus
        document.addEventListener('contextmenu', (e) => this.handleContextMenu(e));
    }

    // Chart Management
    initializeChartControls() {
        const chartCanvas = document.getElementById('chartCanvas');
        if (chartCanvas) {
            chartCanvas.addEventListener('click', (e) => this.handleChartClick(e));
            chartCanvas.addEventListener('mousemove', (e) => this.handleChartMouseMove(e));
        }
    }

    zoomChart(factor) {
        // Implement chart zoom functionality
        console.log(`Zooming chart by factor: ${factor}`);
        
        // Update zoom level display if it exists
        const zoomDisplay = document.querySelector('.zoom-level');
        if (zoomDisplay) {
            const currentZoom = parseFloat(zoomDisplay.textContent) || 1.0;
            const newZoom = (currentZoom * factor).toFixed(1);
            zoomDisplay.textContent = `${newZoom}x`;
        }
    }

    centerOnVessel() {
        console.log('Centering chart on vessel position');
        
        // Update vessel position indicator
        const vesselIcon = document.querySelector('.vessel-position');
        if (vesselIcon) {
            vesselIcon.style.transform = 'translate(-50%, -50%)';
            vesselIcon.style.animation = 'pulse 1s ease-out';
            setTimeout(() => {
                vesselIcon.style.animation = 'pulse 2s infinite';
            }, 1000);
        }
    }

    changeChartType(type) {
        console.log(`Changing chart type to: ${type}`);
        
        const chartCanvas = document.getElementById('chartCanvas');
        if (chartCanvas) {
            chartCanvas.classList.remove('nautical', 'satellite', 'weather', 'fishing', 'bathymetric');
            chartCanvas.classList.add(type);
        }
    }

    handleChartClick(e) {
        const rect = e.target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        console.log(`Chart clicked at: ${x}, ${y}`);
        
        // Convert screen coordinates to lat/lon (simplified)
        const lat = this.position.lat + (y - rect.height/2) * 0.001;
        const lon = this.position.lon + (x - rect.width/2) * 0.001;
        
        this.updateCoordinatesDisplay(lat, lon);
    }

    handleChartMouseMove(e) {
        const rect = e.target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Convert to coordinates and update cursor display
        const lat = this.position.lat + (y - rect.height/2) * 0.001;
        const lon = this.position.lon + (x - rect.width/2) * 0.001;
        
        this.updateMouseCoordinates(lat, lon);
    }

    // Data Updates
    startDataUpdates() {
        // Update position and vessel data every second
        setInterval(() => {
            this.updateVesselData();
            this.updateWeatherData();
            this.updateNavigationData();
        }, 1000);

        // Update coordinates display every 100ms
        setInterval(() => {
            this.updateCoordinatesDisplay();
        }, 100);
    }

    updateVesselData() {
        // Simulate vessel movement
        this.vessel.heading += (Math.random() - 0.5) * 2;
        this.vessel.speed += (Math.random() - 0.5) * 0.1;
        this.vessel.course = this.vessel.heading + (Math.random() - 0.5) * 5;
        
        // Keep values in valid ranges
        this.vessel.heading = (this.vessel.heading + 360) % 360;
        this.vessel.speed = Math.max(0, Math.min(15, this.vessel.speed));
        this.vessel.course = (this.vessel.course + 360) % 360;
    }

    updateWeatherData() {
        // Simulate weather changes
        this.weather.wind.speed += (Math.random() - 0.5) * 0.5;
        this.weather.waves.height += (Math.random() - 0.5) * 0.1;
        this.weather.barometer += (Math.random() - 0.5) * 0.01;
        
        // Keep values in realistic ranges
        this.weather.wind.speed = Math.max(0, Math.min(50, this.weather.wind.speed));
        this.weather.waves.height = Math.max(0, Math.min(20, this.weather.waves.height));
        this.weather.barometer = Math.max(28, Math.min(32, this.weather.barometer));
    }

    updateNavigationData() {
        // Simulate position updates based on course and speed
        const speedKnots = this.vessel.speed;
        const courseRad = this.vessel.course * Math.PI / 180;
        
        // Convert speed to degrees per second (very approximate)
        const deltaLat = Math.cos(courseRad) * speedKnots * 0.0000048;
        const deltaLon = Math.sin(courseRad) * speedKnots * 0.0000048;
        
        this.position.lat += deltaLat;
        this.position.lon += deltaLon;
    }

    // Display Updates
    updateCoordinatesDisplay(lat = null, lon = null) {
        const currentLat = lat || this.position.lat;
        const currentLon = lon || this.position.lon;
        
        const coordinatesElement = document.querySelector('.coordinates');
        if (coordinatesElement) {
            const latStr = this.formatCoordinate(currentLat, 'lat');
            const lonStr = this.formatCoordinate(currentLon, 'lon');
            coordinatesElement.textContent = `LAT: ${latStr} LON: ${lonStr}`;
        }
    }

    updateMouseCoordinates(lat, lon) {
        const mouseCoords = document.querySelector('.mouse-coordinates');
        if (mouseCoords) {
            const latStr = this.formatCoordinate(lat, 'lat');
            const lonStr = this.formatCoordinate(lon, 'lon');
            mouseCoords.textContent = `${latStr} ${lonStr}`;
        }
    }

    formatCoordinate(decimal, type) {
        const isNegative = decimal < 0;
        const absDecimal = Math.abs(decimal);
        const degrees = Math.floor(absDecimal);
        const minutes = (absDecimal - degrees) * 60;
        
        const direction = type === 'lat' 
            ? (isNegative ? 'S' : 'N')
            : (isNegative ? 'W' : 'E');
            
        return `${degrees}°${minutes.toFixed(3)}'${direction}`;
    }

    // Modal Management
    setupModals() {
        // Close modals on outside click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });

        // Close modals on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });

        // Setup modal buttons
        document.querySelectorAll('[data-modal]').forEach(button => {
            button.addEventListener('click', (e) => {
                const modalId = e.target.getAttribute('data-modal');
                this.openModal(modalId);
            });
        });

        document.querySelectorAll('.modal .btn-secondary').forEach(button => {
            if (button.textContent.includes('Cancel')) {
                button.addEventListener('click', (e) => {
                    const modal = e.target.closest('.modal');
                    this.closeModal(modal);
                });
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('fade-in');
        }
    }

    closeModal(modal) {
        if (typeof modal === 'string') {
            modal = document.getElementById(modal);
        }
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('fade-in');
        }
    }

    closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            this.closeModal(modal);
        });
    }

    // Keyboard Shortcuts
    handleKeyboard(e) {
        // Prevent default for our shortcuts
        const shortcuts = {
            'Equal': () => this.zoomChart(1.2),           // + key
            'Minus': () => this.zoomChart(0.8),           // - key
            'KeyC': () => this.centerOnVessel(),          // C key
            'Escape': () => this.closeAllModals(),        // ESC key
            'F11': (e) => { e.preventDefault(); this.toggleFullscreen(); }
        };

        if (shortcuts[e.code]) {
            if (e.code !== 'F11') e.preventDefault();
            shortcuts[e.code](e);
        }
    }

    // Window Management
    handleResize() {
        // Adjust layout for new window size
        console.log('Window resized, adjusting layout');
        
        // Update chart display if needed
        const chartCanvas = document.getElementById('chartCanvas');
        if (chartCanvas) {
            // Trigger any responsive chart adjustments
            this.adjustChartSize();
        }
    }

    adjustChartSize() {
        // Implement chart size adjustment logic
        console.log('Adjusting chart size for current viewport');
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    // Context Menu
    handleContextMenu(e) {
        // Custom context menu for chart area
        if (e.target.closest('.chart-display')) {
            e.preventDefault();
            this.showContextMenu(e.clientX, e.clientY);
        }
    }

    showContextMenu(x, y) {
        // Remove existing context menu
        const existingMenu = document.querySelector('.context-menu');
        if (existingMenu) {
            existingMenu.remove();
        }

        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.style.position = 'fixed';
        menu.style.top = `${y}px`;
        menu.style.left = `${x}px`;
        menu.style.zIndex = '9999';
        menu.style.background = 'var(--marine-panel-bg)';
        menu.style.border = '1px solid var(--marine-border)';
        menu.style.borderRadius = 'var(--radius-md)';
        menu.style.padding = 'var(--spacing-sm)';
        menu.style.boxShadow = 'var(--shadow-lg)';

        const menuItems = [
            { text: 'Drop Waypoint', action: () => this.dropWaypoint() },
            { text: 'Measure Distance', action: () => this.startMeasure() },
            { text: 'Set Course', action: () => this.setCourse() },
            { text: 'Mark Position', action: () => this.markPosition() }
        ];

        menuItems.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.textContent = item.text;
            menuItem.style.padding = 'var(--spacing-xs) var(--spacing-sm)';
            menuItem.style.cursor = 'pointer';
            menuItem.style.borderRadius = 'var(--radius-sm)';
            menuItem.style.fontSize = 'var(--font-size-small)';
            menuItem.style.color = 'var(--marine-text)';
            
            menuItem.addEventListener('mouseover', () => {
                menuItem.style.background = 'var(--marine-accent)';
            });
            menuItem.addEventListener('mouseout', () => {
                menuItem.style.background = 'transparent';
            });
            menuItem.addEventListener('click', () => {
                item.action();
                menu.remove();
            });
            
            menu.appendChild(menuItem);
        });

        document.body.appendChild(menu);

        // Remove menu on next click
        setTimeout(() => {
            document.addEventListener('click', () => menu.remove(), { once: true });
        }, 100);
    }

    // Chart Actions
    dropWaypoint() {
        console.log('Dropping waypoint at current mouse position');
        // Implement waypoint dropping logic
    }

    startMeasure() {
        console.log('Starting distance measurement tool');
        // Implement measurement tool
    }

    setCourse() {
        console.log('Setting course to clicked position');
        // Implement course setting
    }

    markPosition() {
        console.log('Marking current position');
        // Implement position marking
    }

    // Utility Functions
    formatTime(date = new Date()) {
        return date.toLocaleTimeString('en-US', { 
            hour12: false,
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatDate(date = new Date()) {
        return date.toLocaleDateString('en-US', {
            month: '2-digit',
            day: '2-digit',
            year: 'numeric'
        });
    }

    formatDistance(nauticalMiles) {
        if (nauticalMiles < 0.1) {
            return `${Math.round(nauticalMiles * 6076)} ft`;
        } else {
            return `${nauticalMiles.toFixed(1)} nm`;
        }
    }

    formatBearing(degrees) {
        const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                           'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
        const index = Math.round(degrees / 22.5) % 16;
        return `${Math.round(degrees)}° ${directions[index]}`;
    }

    // Animation helpers
    animateValue(element, start, end, duration, suffix = '') {
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const current = start + (end - start) * this.easeOutCubic(progress);
            element.textContent = Math.round(current * 10) / 10 + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    // Error handling
    handleError(error, context = 'Marine Interface') {
        console.error(`${context} Error:`, error);
        
        // Show user-friendly error message
        this.showToast(`Error in ${context}: ${error.message}`, 'error');
    }

    // Toast notifications
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: 'var(--spacing-md)',
            background: type === 'error' ? 'var(--marine-danger)' : 'var(--marine-accent)',
            color: 'white',
            borderRadius: 'var(--radius-md)',
            zIndex: '10000',
            fontSize: 'var(--font-size-small)',
            maxWidth: '300px',
            boxShadow: 'var(--shadow-lg)'
        });
        
        document.body.appendChild(toast);
        
        // Animate in
        toast.style.transform = 'translateX(100%)';
        toast.style.opacity = '0';
        
        requestAnimationFrame(() => {
            toast.style.transition = 'all 0.3s ease';
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });
        
        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// Initialize when DOM is loaded
let marineInterface;

document.addEventListener('DOMContentLoaded', () => {
    try {
        marineInterface = new MarineInterface();
    } catch (error) {
        console.error('Failed to initialize Marine Interface:', error);
    }
});

// Export for use by specific layouts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MarineInterface;
}