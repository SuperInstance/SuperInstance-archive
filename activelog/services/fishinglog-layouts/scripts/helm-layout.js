// Helm Layout Specific JavaScript
// Extends the base Marine Interface for helm control functionality

class HelmLayout extends MarineInterface {
    constructor() {
        super();
        this.instruments = {
            compass: { value: 45, target: 45 },
            speedometer: { value: 8.2, max: 25 },
            depthSounder: { value: 45.2, alarm: 10 },
            windIndicator: { speed: 12, direction: 45 },
            rudderAngle: { value: 0, max: 35 },
            engineRPM: { port: 1800, starboard: 1800, max: 3000 }
        };
        
        this.autopilot = {
            active: false,
            mode: 'compass',
            compassHeading: 45,
            windAngle: 0,
            routes: []
        };
        
        this.radar = {
            range: 6, // nautical miles
            targets: [],
            sweep: 0
        };
        
        this.initHelmFeatures();
    }

    initHelmFeatures() {
        this.setupInstruments();
        this.setupAutopilot();
        this.setupRadar();
        this.setupHelmControls();
        this.startInstrumentUpdates();
        this.startRadarSweep();
        
        console.log('Helm layout initialized');
    }

    // Instrument Panel Functions
    setupInstruments() {
        // Initialize instrument displays
        this.updateAllInstruments();
        
        // Setup instrument interactions
        document.querySelectorAll('.instrument').forEach(instrument => {
            instrument.addEventListener('click', (e) => {
                const instrumentType = e.currentTarget.dataset.instrument;
                this.showInstrumentDetail(instrumentType);
            });
        });
    }

    startInstrumentUpdates() {
        setInterval(() => {
            this.updateInstrumentData();
            this.updateInstrumentDisplays();
            this.updateEngineStatus();
        }, 100); // Update instruments frequently for smooth animation
    }

    updateInstrumentData() {
        // Compass - simulate small variations
        this.instruments.compass.value += (Math.random() - 0.5) * 2;
        this.instruments.compass.value = (this.instruments.compass.value + 360) % 360;
        
        // Speed - simulate engine response
        const targetSpeed = this.autopilot.active ? 8.0 : this.vessel.speed;
        this.instruments.speedometer.value += (targetSpeed - this.instruments.speedometer.value) * 0.1;
        
        // Depth - simulate depth changes
        this.instruments.depthSounder.value += (Math.random() - 0.5) * 0.5;
        this.instruments.depthSounder.value = Math.max(5, Math.min(200, this.instruments.depthSounder.value));
        
        // Wind
        this.instruments.windIndicator.speed = this.weather.wind.speed;
        this.instruments.windIndicator.direction += (Math.random() - 0.5) * 5;
        
        // Rudder angle - follows compass changes
        if (!this.autopilot.active) {
            this.instruments.rudderAngle.value += (Math.random() - 0.5) * 3;
            this.instruments.rudderAngle.value = Math.max(-35, Math.min(35, this.instruments.rudderAngle.value));
        }
        
        // Engine RPM
        const baseRPM = this.instruments.speedometer.value * 200;
        this.instruments.engineRPM.port = baseRPM + (Math.random() - 0.5) * 100;
        this.instruments.engineRPM.starboard = baseRPM + (Math.random() - 0.5) * 100;
    }

    updateInstrumentDisplays() {
        // Update compass
        this.updateCompass();
        
        // Update speedometer
        this.updateSpeedometer();
        
        // Update depth sounder
        this.updateDepthSounder();
        
        // Update wind indicator
        this.updateWindIndicator();
        
        // Update rudder angle
        this.updateRudderIndicator();
    }

    updateCompass() {
        const needle = document.querySelector('[data-instrument=\"compass\"] .instrument-needle');
        const value = document.querySelector('[data-instrument=\"compass\"] .instrument-value');
        
        if (needle) {
            needle.style.transform = `translate(-50%, -100%) rotate(${this.instruments.compass.value}deg)`;
        }
        if (value) {
            value.textContent = Math.round(this.instruments.compass.value);
        }
    }

    updateSpeedometer() {
        const needle = document.querySelector('[data-instrument=\"speed\"] .instrument-needle');
        const value = document.querySelector('[data-instrument=\"speed\"] .instrument-value');
        
        if (needle) {
            const angle = (this.instruments.speedometer.value / this.instruments.speedometer.max) * 270 - 135;
            needle.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
        }
        if (value) {
            value.textContent = this.instruments.speedometer.value.toFixed(1);
        }
    }

    updateDepthSounder() {
        const value = document.querySelector('[data-instrument=\"depth\"] .instrument-value');
        const statusValue = document.querySelector('.status-item:nth-child(2) .status-value');
        
        const depth = this.instruments.depthSounder.value;
        
        if (value) {
            value.textContent = depth.toFixed(1);
        }
        if (statusValue) {
            statusValue.textContent = `${depth.toFixed(1)} ft`;
            
            // Color code based on depth alarm
            if (depth < this.instruments.depthSounder.alarm) {
                statusValue.className = 'status-value danger';
            } else if (depth < this.instruments.depthSounder.alarm * 2) {
                statusValue.className = 'status-value warning';
            } else {
                statusValue.className = 'status-value';
            }
        }
    }

    updateWindIndicator() {
        const needle = document.querySelector('[data-instrument=\"wind\"] .instrument-needle');
        const speedValue = document.querySelector('[data-instrument=\"wind\"] .instrument-value');
        
        if (needle) {
            needle.style.transform = `translate(-50%, -100%) rotate(${this.instruments.windIndicator.direction}deg)`;
        }
        if (speedValue) {
            speedValue.textContent = Math.round(this.instruments.windIndicator.speed);
        }
    }

    updateRudderIndicator() {
        const needle = document.querySelector('[data-instrument=\"rudder\"] .instrument-needle');
        const value = document.querySelector('[data-instrument=\"rudder\"] .instrument-value');
        
        if (needle) {
            const angle = (this.instruments.rudderAngle.value / this.instruments.rudderAngle.max) * 45;
            needle.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
        }
        if (value) {
            const direction = this.instruments.rudderAngle.value > 0 ? 'STBD' : 'PORT';
            value.textContent = `${Math.abs(this.instruments.rudderAngle.value).toFixed(0)}° ${direction}`;
        }
    }

    updateEngineStatus() {
        const portRPM = document.querySelector('.engine-indicator:nth-child(1) .engine-value');
        const stbdRPM = document.querySelector('.engine-indicator:nth-child(2) .engine-value');
        const portTemp = document.querySelector('.engine-indicator:nth-child(3) .engine-value');
        const stbdTemp = document.querySelector('.engine-indicator:nth-child(4) .engine-value');
        const oilPressure = document.querySelector('.engine-indicator:nth-child(5) .engine-value');
        const fuelLevel = document.querySelector('.engine-indicator:nth-child(6) .engine-value');
        
        if (portRPM) {
            portRPM.textContent = `${Math.round(this.instruments.engineRPM.port)} RPM`;
            this.setEngineStatusColor(portRPM, this.instruments.engineRPM.port, 2500);
        }
        
        if (stbdRPM) {
            stbdRPM.textContent = `${Math.round(this.instruments.engineRPM.starboard)} RPM`;
            this.setEngineStatusColor(stbdRPM, this.instruments.engineRPM.starboard, 2500);
        }
        
        if (portTemp) {
            const temp = 180 + (this.instruments.engineRPM.port / 3000) * 40;
            portTemp.textContent = `${Math.round(temp)}°F`;
            this.setEngineStatusColor(portTemp, temp, 200);
        }
        
        if (stbdTemp) {
            const temp = 180 + (this.instruments.engineRPM.starboard / 3000) * 40;
            stbdTemp.textContent = `${Math.round(temp)}°F`;
            this.setEngineStatusColor(stbdTemp, temp, 200);
        }
        
        if (oilPressure) {
            const pressure = 45 + (Math.random() * 10);
            oilPressure.textContent = `${Math.round(pressure)} PSI`;
            this.setEngineStatusColor(oilPressure, pressure, 30, true); // Lower is worse for oil pressure
        }
        
        if (fuelLevel) {
            // Simulate fuel consumption
            const currentLevel = parseFloat(fuelLevel.textContent) || 75;
            const newLevel = Math.max(0, currentLevel - 0.001);
            fuelLevel.textContent = `${newLevel.toFixed(1)}%`;
            this.setEngineStatusColor(fuelLevel, newLevel, 20, true);
        }
    }

    setEngineStatusColor(element, value, warningThreshold, lowerIsBad = false) {
        element.className = 'engine-value';
        
        if (lowerIsBad) {
            if (value < warningThreshold * 0.5) {
                element.classList.add('danger');
            } else if (value < warningThreshold) {
                element.classList.add('warning');
            } else {
                element.classList.add('normal');
            }
        } else {
            if (value > warningThreshold * 1.2) {
                element.classList.add('danger');
            } else if (value > warningThreshold) {
                element.classList.add('warning');
            } else {
                element.classList.add('normal');
            }
        }
    }

    showInstrumentDetail(instrumentType) {
        let detail = '';
        
        switch (instrumentType) {
            case 'compass':
                detail = `Heading: ${Math.round(this.instruments.compass.value)}°\\nVariation: 14°W\\nDeviation: 2°E`;
                break;
            case 'speed':
                detail = `Speed: ${this.instruments.speedometer.value.toFixed(1)} kts\\nMax Speed: ${this.instruments.speedometer.max} kts\\nAverage: 7.8 kts`;
                break;
            case 'depth':
                detail = `Depth: ${this.instruments.depthSounder.value.toFixed(1)} ft\\nAlarm: ${this.instruments.depthSounder.alarm} ft\\nMax Today: 85.2 ft`;
                break;
            case 'wind':
                detail = `Wind Speed: ${Math.round(this.instruments.windIndicator.speed)} kts\\nDirection: ${Math.round(this.instruments.windIndicator.direction)}°\\nApparent Wind`;
                break;
        }
        
        if (detail) {
            this.showToast(detail, 'info', 4000);
        }
    }

    // Autopilot Functions
    setupAutopilot() {
        // Mode selection
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setAutopilotMode(e.target.dataset.mode);
            });
        });
        
        // Adjustment controls
        document.querySelectorAll('.adjust-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const direction = e.target.textContent.includes('+') ? 1 : -1;
                const setting = e.target.closest('.autopilot-setting').dataset.setting;
                this.adjustAutopilotSetting(setting, direction);
            });
        });
        
        // Standby button
        document.getElementById('autopilotStandby')?.addEventListener('click', () => {
            this.toggleAutopilot();
        });
    }

    setAutopilotMode(mode) {
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        document.querySelector(`[data-mode=\"${mode}\"]`).classList.add('active');
        this.autopilot.mode = mode;
        
        console.log(`Autopilot mode set to: ${mode}`);
        this.showToast(`Autopilot: ${mode.toUpperCase()} mode`, 'info');
    }

    adjustAutopilotSetting(setting, direction) {
        const increment = direction * (setting === 'heading' ? 1 : 0.1);
        
        switch (setting) {
            case 'heading':
                this.autopilot.compassHeading += increment;
                this.autopilot.compassHeading = (this.autopilot.compassHeading + 360) % 360;
                break;
            case 'wind':
                this.autopilot.windAngle += increment;
                this.autopilot.windAngle = Math.max(-180, Math.min(180, this.autopilot.windAngle));
                break;
        }
        
        this.updateAutopilotDisplay();
    }

    updateAutopilotDisplay() {
        const headingValue = document.querySelector('[data-setting=\"heading\"] .setting-value');
        const windValue = document.querySelector('[data-setting=\"wind\"] .setting-value');
        
        if (headingValue) {
            headingValue.textContent = `${Math.round(this.autopilot.compassHeading)}°`;
        }
        if (windValue) {
            windValue.textContent = `${this.autopilot.windAngle > 0 ? '+' : ''}${this.autopilot.windAngle.toFixed(1)}°`;
        }
    }

    toggleAutopilot() {
        this.autopilot.active = !this.autopilot.active;
        
        const standbyBtn = document.getElementById('autopilotStandby');
        if (standbyBtn) {
            if (this.autopilot.active) {
                standbyBtn.textContent = 'STANDBY';
                standbyBtn.style.background = 'var(--marine-success)';
            } else {
                standbyBtn.textContent = 'ENGAGE';
                standbyBtn.style.background = 'var(--marine-panel-bg)';
            }
        }
        
        const status = this.autopilot.active ? 'ENGAGED' : 'STANDBY';
        this.showToast(`Autopilot: ${status}`, 'info');
        
        if (this.autopilot.active) {
            this.startAutopilotControl();
        }
    }

    startAutopilotControl() {
        if (!this.autopilot.active) return;
        
        // Simulate autopilot control
        const targetHeading = this.autopilot.compassHeading;
        const currentHeading = this.instruments.compass.value;
        const headingError = this.calculateHeadingError(currentHeading, targetHeading);
        
        // Apply rudder correction (simplified)
        if (Math.abs(headingError) > 2) {
            this.instruments.rudderAngle.value = Math.max(-10, Math.min(10, headingError * 0.3));
        } else {
            this.instruments.rudderAngle.value *= 0.9; // Return to center
        }
        
        // Continue autopilot control
        setTimeout(() => this.startAutopilotControl(), 500);
    }

    calculateHeadingError(current, target) {
        let error = target - current;
        if (error > 180) error -= 360;
        if (error < -180) error += 360;
        return error;
    }

    // Radar Functions
    setupRadar() {
        // Radar controls
        document.getElementById('radarRange')?.addEventListener('change', (e) => {
            this.radar.range = parseFloat(e.target.value);
            this.updateRadarDisplay();
        });
        
        document.getElementById('radarGain')?.addEventListener('click', () => {
            this.adjustRadarGain();
        });
        
        document.getElementById('radarStandby')?.addEventListener('click', () => {
            this.toggleRadarStandby();
        });
        
        // Initialize radar targets
        this.generateRadarTargets();
    }

    startRadarSweep() {
        setInterval(() => {
            this.radar.sweep = (this.radar.sweep + 6) % 360; // 6 degrees per update
            this.updateRadarSweep();
            this.updateRadarTargets();
        }, 100);
    }

    updateRadarSweep() {
        const sweepElement = document.querySelector('.radar-sweep');
        if (sweepElement) {
            sweepElement.style.transform = `translate(-50%, -50%) rotate(${this.radar.sweep}deg)`;
        }
    }

    generateRadarTargets() {
        // Generate some random radar targets
        this.radar.targets = [];
        
        for (let i = 0; i < 5; i++) {
            const range = Math.random() * this.radar.range * 0.8 + 0.5;
            const bearing = Math.random() * 360;
            const size = Math.random() > 0.7 ? 'large' : 'normal';
            
            this.radar.targets.push({
                id: i,
                range: range,
                bearing: bearing,
                size: size,
                type: size === 'large' ? 'vessel' : 'small_craft'
            });
        }
    }

    updateRadarTargets() {
        // Move targets slightly for realism
        this.radar.targets.forEach(target => {
            target.bearing += (Math.random() - 0.5) * 2;
            target.range += (Math.random() - 0.5) * 0.1;
            target.range = Math.max(0.2, Math.min(this.radar.range, target.range));
        });
        
        this.displayRadarTargets();
    }

    displayRadarTargets() {
        // Remove existing targets
        document.querySelectorAll('.radar-target').forEach(target => target.remove());
        
        const radarDisplay = document.querySelector('.radar-display');
        if (!radarDisplay) return;
        
        const centerX = radarDisplay.offsetWidth / 2;
        const centerY = radarDisplay.offsetHeight / 2;
        const maxRadius = Math.min(centerX, centerY) * 0.9;
        
        this.radar.targets.forEach(target => {
            const radius = (target.range / this.radar.range) * maxRadius;
            const angle = (target.bearing - 90) * Math.PI / 180; // Convert to radians, adjust for display
            
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            
            const targetElement = document.createElement('div');
            targetElement.className = `radar-target ${target.size}`;
            targetElement.style.left = `${x}px`;
            targetElement.style.top = `${y}px`;
            targetElement.title = `${target.type.replace('_', ' ')} - ${target.range.toFixed(1)}nm @ ${Math.round(target.bearing)}°`;
            
            radarDisplay.appendChild(targetElement);
        });
    }

    updateRadarDisplay() {
        // Update radar info display
        const rangeDisplay = document.querySelector('[data-radar-info=\"range\"] span');
        const targetsDisplay = document.querySelector('[data-radar-info=\"targets\"] span');
        
        if (rangeDisplay) {
            rangeDisplay.textContent = `${this.radar.range} nm`;
        }
        if (targetsDisplay) {
            targetsDisplay.textContent = this.radar.targets.length;
        }
    }

    adjustRadarGain() {
        const gainBtn = document.getElementById('radarGain');
        const gains = ['Low', 'Med', 'High', 'Auto'];
        const current = gainBtn?.textContent || 'Auto';
        const nextIndex = (gains.indexOf(current) + 1) % gains.length;
        
        if (gainBtn) {
            gainBtn.textContent = gains[nextIndex];
        }
        
        this.showToast(`Radar gain: ${gains[nextIndex]}`, 'info');
    }

    toggleRadarStandby() {
        const standbyBtn = document.getElementById('radarStandby');
        const isStandby = standbyBtn?.textContent === 'STBY';
        
        if (standbyBtn) {
            if (isStandby) {
                standbyBtn.textContent = 'ON';
                standbyBtn.style.background = 'var(--marine-success)';
                this.generateRadarTargets();
            } else {
                standbyBtn.textContent = 'STBY';
                standbyBtn.style.background = 'var(--marine-panel-bg)';
                this.radar.targets = [];
                this.displayRadarTargets();
            }
        }
    }

    // Helm Controls
    setupHelmControls() {
        document.querySelectorAll('.helm-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.executeHelmAction(action);
            });
        });
    }

    executeHelmAction(action) {
        switch (action) {
            case 'center_rudder':
                this.centerRudder();
                break;
            case 'follow_gps':
                this.followGPSTrack();
                break;
            case 'man_overboard':
                this.manOverboard();
                break;
            case 'anchor':
                this.dropAnchor();
                break;
        }
    }

    centerRudder() {
        this.instruments.rudderAngle.value = 0;
        this.showToast('Rudder amidships', 'info');
    }

    followGPSTrack() {
        if (!this.autopilot.active) {
            this.autopilot.active = true;
            this.autopilot.mode = 'gps';
            this.showToast('Following GPS track', 'info');
        } else {
            this.showToast('Autopilot already active', 'warning');
        }
    }

    manOverboard() {
        // Emergency procedure
        this.showToast('MAN OVERBOARD! Executing emergency turn', 'error');
        
        // Quick turn to port
        this.instruments.rudderAngle.value = -35;
        
        // Drop MOB marker
        const mobMarker = {
            position: { ...this.position },
            type: 'MOB',
            timestamp: new Date()
        };
        
        // Add MOB waypoint to chart
        this.addMOBMarker(mobMarker);
    }

    dropAnchor() {
        this.showToast('Preparing to anchor - reducing speed', 'info');
        
        // Reduce speed
        this.vessel.speed = Math.max(0, this.vessel.speed - 2);
        
        // Add anchor marker
        const anchorMarker = {
            position: { ...this.position },
            type: 'anchor',
            timestamp: new Date()
        };
        
        this.addAnchorMarker(anchorMarker);
    }

    addMOBMarker(marker) {
        // Add MOB marker to chart with high visibility
        console.log('MOB marker added at:', marker.position);
        // Implementation would add visual marker to chart
    }

    addAnchorMarker(marker) {
        // Add anchor marker to chart
        console.log('Anchor marker added at:', marker.position);
        // Implementation would add visual marker to chart
    }
}

// Initialize helm layout when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('helm-layout')) {
        try {
            window.helmLayout = new HelmLayout();
        } catch (error) {
            console.error('Failed to initialize Helm Layout:', error);
        }
    }
});