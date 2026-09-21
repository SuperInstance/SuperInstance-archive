// Fishing Layout Specific JavaScript
// Extends the base Marine Interface for fishing-specific functionality

class FishingLayout extends MarineInterface {
    constructor() {
        super();
        this.sonarData = [];
        this.fishTargets = [];
        this.catches = [];
        this.fishingSpots = [
            { id: 1, name: 'Rocky Bottom', species: ['Striped Bass', 'Tautog'], active: true },
            { id: 2, name: 'Wreck Site', species: ['Cod', 'Fluke'], active: false }
        ];
        this.sonarRange = 50; // feet
        this.fishingMode = true;
        
        this.initFishingFeatures();
    }

    initFishingFeatures() {
        this.setupSonarDisplay();
        this.setupCatchLog();
        this.setupFishingTools();
        this.startSonarUpdates();
        this.setupSpeciesGuide();
        
        console.log('Fishing layout initialized');
    }

    // Sonar/Fish Finder Functions
    setupSonarDisplay() {
        const canvas = document.getElementById('sonarCanvas');
        if (canvas) {
            this.sonarContext = canvas.getContext('2d');
            this.sonarWidth = canvas.width;
            this.sonarHeight = canvas.height;
            this.initializeSonarCanvas();
        }

        // Sonar controls
        document.getElementById('sonarRange')?.addEventListener('change', (e) => {
            this.sonarRange = parseInt(e.target.value);
            this.updateSonarDisplay();
        });

        document.getElementById('sonarGain')?.addEventListener('click', () => {
            this.adjustSonarGain();
        });

        document.getElementById('fishAlarm')?.addEventListener('click', () => {
            this.toggleFishAlarm();
        });
    }

    initializeSonarCanvas() {
        if (!this.sonarContext) return;
        
        // Set up sonar background
        this.sonarContext.fillStyle = '#001122';
        this.sonarContext.fillRect(0, 0, this.sonarWidth, this.sonarHeight);
        
        // Initialize sonar data array
        this.sonarData = new Array(this.sonarWidth).fill(0).map(() => 
            new Array(this.sonarHeight).fill(0)
        );
    }

    startSonarUpdates() {
        setInterval(() => {
            this.updateSonarData();
            this.updateSonarDisplay();
            this.updateFishTargets();
        }, 200); // Update every 200ms for realistic sonar refresh
    }

    updateSonarData() {
        if (!this.sonarContext) return;

        // Shift sonar data to the left
        this.sonarData.shift();
        
        // Generate new column of sonar data
        const newColumn = [];
        const depth = 45.2; // Current depth in feet
        const bottomDepth = Math.floor((depth / this.sonarRange) * this.sonarHeight);
        
        for (let y = 0; y < this.sonarHeight; y++) {
            let intensity = 0;
            
            // Bottom return
            if (y >= bottomDepth - 2 && y <= bottomDepth + 2) {
                intensity = 0.8 + Math.random() * 0.2;
            }
            // Fish targets
            else if (Math.random() < 0.02) { // 2% chance of fish
                intensity = 0.3 + Math.random() * 0.4;
                this.addFishTarget(y);
            }
            // Noise
            else {
                intensity = Math.random() * 0.1;
            }
            
            newColumn.push(intensity);
        }
        
        this.sonarData.push(newColumn);
    }

    updateSonarDisplay() {
        if (!this.sonarContext) return;

        // Clear canvas
        this.sonarContext.fillStyle = '#001122';
        this.sonarContext.fillRect(0, 0, this.sonarWidth, this.sonarHeight);
        
        // Draw sonar data
        for (let x = 0; x < this.sonarData.length; x++) {
            for (let y = 0; y < this.sonarData[x].length; y++) {
                const intensity = this.sonarData[x][y];
                if (intensity > 0.1) {
                    const alpha = Math.min(intensity, 1);
                    const color = this.getSonarColor(intensity, y);
                    this.sonarContext.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
                    this.sonarContext.fillRect(x, y, 1, 1);
                }
            }
        }
    }

    getSonarColor(intensity, depth) {
        // Different colors for different returns
        if (intensity > 0.7) {
            // Strong bottom return - red
            return { r: 255, g: 50, b: 50 };
        } else if (intensity > 0.4) {
            // Medium return (fish) - yellow
            return { r: 255, g: 255, b: 100 };
        } else {
            // Weak return - green
            return { r: 100, g: 255, b: 100 };
        }
    }

    addFishTarget(depth) {
        const target = {
            id: Date.now() + Math.random(),
            depth: depth,
            size: Math.random() > 0.7 ? 'large' : Math.random() > 0.4 ? 'medium' : 'small',
            timestamp: Date.now()
        };
        
        this.fishTargets.push(target);
        
        // Remove old targets
        this.fishTargets = this.fishTargets.filter(t => 
            Date.now() - t.timestamp < 10000
        );
        
        this.updateFishCount();
    }

    updateFishTargets() {
        // Update fish arch displays
        const fishArches = document.querySelectorAll('.fish-arch');
        fishArches.forEach((arch, index) => {
            if (this.fishTargets[index]) {
                const target = this.fishTargets[index];
                const age = Date.now() - target.timestamp;
                const opacity = Math.max(0, 1 - (age / 10000));
                arch.style.opacity = opacity;
                
                // Move fish arch across screen
                const position = (age / 4000) * 100;
                arch.style.right = `${position}%`;
            }
        });
    }

    updateFishCount() {
        const fishCountElement = document.querySelector('.fish-count');
        if (fishCountElement) {
            const recentFish = this.fishTargets.filter(t => 
                Date.now() - t.timestamp < 5000
            );
            fishCountElement.textContent = `${recentFish.length} targets`;
        }
    }

    adjustSonarGain() {
        // Cycle through gain settings
        const gainLevels = ['Low', 'Med', 'High', 'Auto'];
        const currentGain = document.getElementById('sonarGain')?.textContent || 'Auto';
        const currentIndex = gainLevels.indexOf(currentGain);
        const nextIndex = (currentIndex + 1) % gainLevels.length;
        
        if (document.getElementById('sonarGain')) {
            document.getElementById('sonarGain').textContent = gainLevels[nextIndex];
        }
        
        console.log(`Sonar gain set to: ${gainLevels[nextIndex]}`);
    }

    toggleFishAlarm() {
        const alarmBtn = document.getElementById('fishAlarm');
        const statusValue = document.querySelector('.status-bar .status-value');
        
        if (alarmBtn && statusValue) {
            const isActive = statusValue.classList.contains('active');
            if (isActive) {
                statusValue.classList.remove('active');
                statusValue.textContent = 'OFF';
                alarmBtn.style.background = 'var(--marine-panel-bg)';
            } else {
                statusValue.classList.add('active');
                statusValue.textContent = 'ON';
                alarmBtn.style.background = 'var(--marine-accent)';
            }
        }
    }

    // Catch Log Functions
    setupCatchLog() {
        document.getElementById('newCatchBtn')?.addEventListener('click', () => {
            this.openCatchModal();
        });

        document.getElementById('saveCatch')?.addEventListener('click', () => {
            this.saveCatch();
        });

        document.getElementById('cancelCatch')?.addEventListener('click', () => {
            this.closeModal('catchModal');
        });

        document.getElementById('exportLog')?.addEventListener('click', () => {
            this.exportCatchLog();
        });
    }

    openCatchModal() {
        // Pre-fill with current conditions
        document.getElementById('catchPosition').textContent = 
            `${this.formatCoordinate(this.position.lat, 'lat')} ${this.formatCoordinate(this.position.lon, 'lon')}`;
        document.getElementById('catchDepth').textContent = '45.2 ft';
        document.getElementById('catchTide').textContent = 'Rising +2.1ft';
        document.getElementById('catchWind').textContent = `${this.weather.wind.direction} ${this.weather.wind.speed} kts`;
        
        this.openModal('catchModal');
    }

    saveCatch() {
        const species = document.getElementById('catchSpecies')?.value;
        const length = parseFloat(document.getElementById('catchLength')?.value);
        const weight = parseFloat(document.getElementById('catchWeight')?.value);
        const status = document.getElementById('catchStatus')?.value;
        const bait = document.getElementById('catchBait')?.value;
        const notes = document.getElementById('catchNotes')?.value;
        
        if (!species || !length) {
            this.showToast('Please fill in required fields', 'error');
            return;
        }
        
        const catch_entry = {
            id: Date.now(),
            timestamp: new Date(),
            species: species,
            length: length,
            weight: weight || null,
            status: status,
            bait: bait,
            notes: notes,
            position: { ...this.position },
            conditions: {
                depth: 45.2,
                tide: 'Rising +2.1ft',
                wind: `${this.weather.wind.direction} ${this.weather.wind.speed} kts`,
                weather: 'Partly Cloudy'
            }
        };
        
        this.catches.unshift(catch_entry);
        this.updateCatchDisplay();
        this.updateCatchSummary();
        this.clearCatchForm();
        this.closeModal('catchModal');
        
        this.showToast(`${species} logged successfully!`, 'info');
    }

    updateCatchDisplay() {
        const catchList = document.querySelector('.catch-list');
        if (!catchList || this.catches.length === 0) return;
        
        // Show only recent catches in the display
        const recentCatches = this.catches.slice(0, 5);
        
        catchList.innerHTML = recentCatches.map(catch_entry => `
            <div class=\"catch-item\">
                <div class=\"catch-time\">${this.formatTime(catch_entry.timestamp)}</div>
                <div class=\"catch-details\">
                    <div class=\"species\">${this.getSpeciesDisplayName(catch_entry.species)}</div>
                    <div class=\"catch-specs\">${catch_entry.length}\" ${catch_entry.weight ? '• ' + catch_entry.weight + ' lbs' : ''}</div>
                    <div class=\"catch-location\">${this.formatCoordinate(catch_entry.position.lat, 'lat')} ${this.formatCoordinate(catch_entry.position.lon, 'lon')}</div>
                </div>
                <div class=\"catch-status ${catch_entry.status}\">${catch_entry.status === 'keeper' ? 'Keeper' : 'Released'}</div>
            </div>
        `).join('');
    }

    updateCatchSummary() {
        const today = new Date().toDateString();
        const todaysCatches = this.catches.filter(c => 
            c.timestamp.toDateString() === today
        );
        
        const totalCaught = todaysCatches.length;
        const keepers = todaysCatches.filter(c => c.status === 'keeper').length;
        const released = todaysCatches.filter(c => c.status === 'released').length;
        const avgWeight = todaysCatches
            .filter(c => c.weight)
            .reduce((sum, c, _, arr) => sum + c.weight / arr.length, 0);
        
        // Update display
        document.querySelector('.summary-stats .stat-item:nth-child(1) .stat-value').textContent = totalCaught;
        document.querySelector('.summary-stats .stat-item:nth-child(2) .stat-value').textContent = keepers;
        document.querySelector('.summary-stats .stat-item:nth-child(3) .stat-value').textContent = released;
        document.querySelector('.summary-stats .stat-item:nth-child(4) .stat-value').textContent = avgWeight.toFixed(1);
        
        // Update status bar
        const statusFishCount = document.querySelector('.status-bar .status-item:nth-child(5) .status-value');
        if (statusFishCount) {
            statusFishCount.textContent = `${totalCaught} fish`;
        }
    }

    clearCatchForm() {
        document.getElementById('catchSpecies').value = '';
        document.getElementById('catchLength').value = '';
        document.getElementById('catchWeight').value = '';
        document.getElementById('catchStatus').value = 'keeper';
        document.getElementById('catchBait').value = '';
        document.getElementById('catchNotes').value = '';
    }

    getSpeciesDisplayName(species) {
        const speciesMap = {
            'striped_bass': 'Striped Bass',
            'fluke': 'Fluke',
            'scup': 'Scup',
            'tautog': 'Tautog',
            'cod': 'Cod'
        };
        return speciesMap[species] || species;
    }

    exportCatchLog() {
        if (this.catches.length === 0) {
            this.showToast('No catches to export', 'info');
            return;
        }
        
        // Generate CSV content
        const headers = ['Date', 'Time', 'Species', 'Length', 'Weight', 'Status', 'Latitude', 'Longitude', 'Depth', 'Bait', 'Notes'];
        const csvContent = [
            headers.join(','),
            ...this.catches.map(c => [
                this.formatDate(c.timestamp),
                this.formatTime(c.timestamp),
                this.getSpeciesDisplayName(c.species),
                c.length,
                c.weight || '',
                c.status,
                c.position.lat.toFixed(6),
                c.position.lon.toFixed(6),
                c.conditions.depth,
                c.bait || '',
                c.notes || ''
            ].join(','))
        ].join('\\n');
        
        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fishing_log_${this.formatDate().replace(/\\//g, '-')}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        this.showToast('Catch log exported successfully!', 'info');
    }

    // Fishing Tools Functions
    setupFishingTools() {
        document.getElementById('dropMarker')?.addEventListener('click', () => {
            this.dropFishingMarker();
        });

        document.getElementById('trollingSpeed')?.addEventListener('click', () => {
            this.optimizeTrollingSpeed();
        });

        document.getElementById('tideChart')?.addEventListener('click', () => {
            this.showTideChart();
        });

        document.getElementById('weatherForecast')?.addEventListener('click', () => {
            this.showFishingForecast();
        });
    }

    dropFishingMarker() {
        const marker = {
            id: Date.now(),
            position: { ...this.position },
            type: 'fishing',
            timestamp: new Date(),
            notes: `Fishing spot - ${this.formatTime()}`
        };
        
        // Add marker to chart (visual feedback)
        this.addMarkerToChart(marker);
        this.showToast('Fishing marker dropped', 'info');
    }

    optimizeTrollingSpeed() {
        const currentSpeed = this.vessel.speed;
        const optimalSpeed = 2.4; // knots
        const difference = Math.abs(currentSpeed - optimalSpeed);
        
        let status, color;
        if (difference < 0.5) {
            status = 'Optimal';
            color = 'var(--marine-success)';
        } else if (difference < 1.0) {
            status = 'Good';
            color = 'var(--marine-warning)';
        } else {
            status = 'Adjust';
            color = 'var(--marine-danger)';
        }
        
        // Update tool display
        const toolValue = document.querySelector('.tool-value');
        const toolIndicator = document.querySelector('.tool-indicator');
        
        if (toolValue) toolValue.textContent = `${currentSpeed.toFixed(1)} kts`;
        if (toolIndicator) {
            toolIndicator.textContent = status;
            toolIndicator.style.background = color;
        }
        
        if (status !== 'Optimal') {
            this.showToast(`Current: ${currentSpeed.toFixed(1)} kts | Optimal: ${optimalSpeed} kts`, 'info');
        }
    }

    showTideChart() {
        // Mock tide chart data
        const tideData = [
            { time: '06:00', height: -1.2, type: 'Low' },
            { time: '12:30', height: 3.8, type: 'High' },
            { time: '18:45', height: -0.8, type: 'Low' },
            { time: '01:15', height: 4.2, type: 'High (next day)' }
        ];
        
        let tideInfo = 'Today\\'s Tide Chart:\\n';
        tideData.forEach(tide => {
            tideInfo += `${tide.time} - ${tide.type} ${tide.height > 0 ? '+' : ''}${tide.height}ft\\n`;
        });
        
        this.showToast(tideInfo, 'info', 5000);
    }

    showFishingForecast() {
        const forecast = {
            solunar: 'Major feeding period: 14:30-16:30',
            barometer: `${this.weather.barometer.toFixed(2)}\" - Rising (Good)`,
            moonPhase: 'First Quarter (Good)',
            conditions: 'Favorable for fishing'
        };
        
        const forecastText = `Fishing Conditions:\\n${forecast.solunar}\\nBarometer: ${forecast.barometer}\\nMoon: ${forecast.moonPhase}\\nOverall: ${forecast.conditions}`;
        this.showToast(forecastText, 'info', 6000);
    }

    // Species Guide
    setupSpeciesGuide() {
        document.querySelectorAll('.species-item').forEach(item => {
            item.addEventListener('click', () => {
                const speciesName = item.querySelector('.species-name').textContent;
                this.showSpeciesInfo(speciesName);
            });
        });
    }

    showSpeciesInfo(species) {
        const speciesData = {
            'Striped Bass': {
                habitat: 'Rocky areas, structure, moving water',
                bait: 'Live eels, bunker, lures',
                techniques: 'Trolling, live bait, jigging',
                regulations: 'Min 28\", Bag limit 1',
                bestTimes: 'Dawn, dusk, moving tides'
            },
            'Fluke': {
                habitat: 'Sandy bottom, edges, structure',
                bait: 'Squid, spearing, gulp baits',
                techniques: 'Drift fishing, bouncing bottom',
                regulations: 'Min 18\", Bag limit 5',
                bestTimes: 'Moving tides, structure edges'
            },
            'Scup': {
                habitat: 'Rocky bottom, wrecks, structure',
                bait: 'Squid, clams, small pieces',
                techniques: 'Bottom fishing, light tackle',
                regulations: 'Min 10\", Bag limit 30',
                bestTimes: 'High slack tide, structure'
            }
        };
        
        const info = speciesData[species];
        if (info) {
            const infoText = `${species}:\\nHabitat: ${info.habitat}\\nBest Baits: ${info.bait}\\nTechniques: ${info.techniques}\\nRegulations: ${info.regulations}\\nBest Times: ${info.bestTimes}`;
            this.showToast(infoText, 'info', 8000);
        }
    }

    // Fishing-specific chart features
    addMarkerToChart(marker) {
        const chartCanvas = document.getElementById('chartCanvas');
        if (!chartCanvas) return;
        
        const markerElement = document.createElement('div');
        markerElement.className = 'fishing-marker';
        markerElement.style.position = 'absolute';
        markerElement.style.top = '50%';
        markerElement.style.left = '50%';
        markerElement.style.transform = 'translate(-50%, -50%)';
        markerElement.style.fontSize = 'var(--font-size-large)';
        markerElement.style.color = 'var(--marine-warning)';
        markerElement.textContent = '📍';
        markerElement.title = marker.notes;
        
        // Add with animation
        markerElement.style.opacity = '0';
        markerElement.style.transform = 'translate(-50%, -50%) scale(0)';
        chartCanvas.appendChild(markerElement);
        
        requestAnimationFrame(() => {
            markerElement.style.transition = 'all 0.3s ease';
            markerElement.style.opacity = '1';
            markerElement.style.transform = 'translate(-50%, -50%) scale(1)';
        });
        
        // Remove after 10 seconds
        setTimeout(() => {
            markerElement.style.opacity = '0';
            markerElement.style.transform = 'translate(-50%, -50%) scale(0)';
            setTimeout(() => markerElement.remove(), 300);
        }, 10000);
    }

    // Override updateNavigationData to include fishing-specific updates
    updateNavigationData() {
        super.updateNavigationData();
        
        // Update fishing-specific status
        this.updateDriftIndicator();
        this.updateBottomType();
        this.updateWaterTemp();
    }

    updateDriftIndicator() {
        const driftElement = document.querySelector('.status-item:first-child .status-value');
        if (driftElement) {
            const driftSpeed = (Math.random() * 0.5 + 0.2).toFixed(1);
            const driftDir = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.floor(Math.random() * 8)];
            driftElement.textContent = `${driftSpeed} kts ${driftDir}`;
        }
    }

    updateBottomType() {
        const bottomElement = document.querySelector('.bottom-type');
        if (bottomElement) {
            const types = ['Hard', 'Soft', 'Rocky', 'Sandy', 'Mixed'];
            // Change occasionally for realism
            if (Math.random() < 0.01) {
                bottomElement.textContent = types[Math.floor(Math.random() * types.length)];
            }
        }
    }

    updateWaterTemp() {
        const tempElement = document.querySelector('.temp-value');
        if (tempElement) {
            // Simulate gradual temperature changes
            const currentTemp = parseFloat(tempElement.textContent) || 68;
            const newTemp = currentTemp + (Math.random() - 0.5) * 0.1;
            tempElement.textContent = `${Math.round(newTemp)}°F`;
        }
    }
}

// Initialize fishing layout when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('fishing-layout')) {
        try {
            window.fishingLayout = new FishingLayout();
        } catch (error) {
            console.error('Failed to initialize Fishing Layout:', error);
        }
    }
});