// Marine Navigation JavaScript

class NavigationSystem {
    constructor() {
        this.socket = io();
        this.chart = null;
        this.aisTargets = [];
        this.radarTargets = [];
        this.currentPosition = {lat: 0, lon: 0, heading: 0, speed: 0};
        
        this.init();
    }
    
    init() {
        this.setupSocketListeners();
        this.setupChart();
        this.setupControls();
    }
    
    setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to navigation server');
        });
        
        this.socket.on('position_update', (data) => {
            this.updatePosition(data);
        });
        
        this.socket.on('ais_update', (data) => {
            this.updateAISTargets(data);
        });
        
        this.socket.on('radar_update', (data) => {
            this.updateRadar(data);
        });
        
        this.socket.on('mob_alert', (data) => {
            this.handleMOBAlert(data);
        });
        
        this.socket.on('night_mode_changed', (data) => {
            this.setNightMode(data.enabled);
        });
    }
    
    setupChart() {
        const canvas = document.getElementById('chart-canvas');
        if (!canvas) return;
        
        this.chart = canvas.getContext('2d');
        this.chart.fillStyle = '#001122';
        this.chart.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw compass rose
        this.drawCompassRose(canvas.width/2, canvas.height/2);
    }
    
    setupControls() {
        // Setup control panel interactions
        const mobButton = document.getElementById('mob-button');
        if (mobButton) {
            mobButton.addEventListener('click', () => this.markMOB());
        }
    }
    
    updatePosition(position) {
        this.currentPosition = position;
        
        // Update position display
        const latDisplay = document.getElementById('lat-display');
        const lonDisplay = document.getElementById('lon-display');
        
        if (latDisplay) {
            latDisplay.textContent = this.formatLatitude(position.lat);
        }
        if (lonDisplay) {
            lonDisplay.textContent = this.formatLongitude(position.lon);
        }
        
        this.redrawChart();
    }
    
    updateAISTargets(data) {
        this.aisTargets = data.targets || [];
        
        // Update AIS display
        const aisList = document.getElementById('ais-list');
        if (aisList) {
            aisList.innerHTML = '';
            
            this.aisTargets.forEach(target => {
                const div = document.createElement('div');
                div.className = `ais-target ${target.collision_risk}`;
                div.innerHTML = `
                    <strong>${target.vessel_name || target.mmsi}</strong><br>
                    ${target.collision_risk.toUpperCase()}<br>
                    CPA: ${target.cpa_distance?.toFixed(2) || 'N/A'}nm<br>
                    TCPA: ${target.tcpa_time?.toFixed(1) || 'N/A'}min
                `;
                aisList.appendChild(div);
            });
        }
        
        this.redrawChart();
    }
    
    updateRadar(data) {
        this.radarTargets = data.targets || [];
        this.redrawChart();
    }
    
    redrawChart() {
        if (!this.chart) return;
        
        const canvas = this.chart.canvas;
        
        // Clear canvas
        this.chart.fillStyle = '#001122';
        this.chart.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw compass rose
        this.drawCompassRose(canvas.width/2, canvas.height/2);
        
        // Draw own vessel
        this.drawOwnVessel(canvas.width/2, canvas.height/2);
        
        // Draw AIS targets
        this.aisTargets.forEach(target => {
            this.drawAISTarget(target);
        });
        
        // Draw radar targets
        this.radarTargets.forEach(target => {
            this.drawRadarTarget(target);
        });
    }
    
    drawCompassRose(centerX, centerY) {
        const radius = 100;
        
        this.chart.strokeStyle = '#00FFFF';
        this.chart.lineWidth = 2;
        
        // Draw circle
        this.chart.beginPath();
        this.chart.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        this.chart.stroke();
        
        // Draw cardinal directions
        this.chart.font = '16px Arial';
        this.chart.fillStyle = '#00FFFF';
        this.chart.textAlign = 'center';
        
        this.chart.fillText('N', centerX, centerY - radius - 10);
        this.chart.fillText('S', centerX, centerY + radius + 20);
        this.chart.fillText('E', centerX + radius + 15, centerY + 5);
        this.chart.fillText('W', centerX - radius - 15, centerY + 5);
    }
    
    drawOwnVessel(centerX, centerY) {
        this.chart.fillStyle = '#FFFF00';
        this.chart.beginPath();
        this.chart.arc(centerX, centerY, 8, 0, 2 * Math.PI);
        this.chart.fill();
        
        // Draw heading line
        const headingRad = (this.currentPosition.heading - 90) * Math.PI / 180;
        this.chart.strokeStyle = '#FFFF00';
        this.chart.lineWidth = 3;
        this.chart.beginPath();
        this.chart.moveTo(centerX, centerY);
        this.chart.lineTo(
            centerX + Math.cos(headingRad) * 30,
            centerY + Math.sin(headingRad) * 30
        );
        this.chart.stroke();
    }
    
    drawAISTarget(target) {
        // Convert lat/lon to screen coordinates (simplified)
        const x = 400 + (target.lon - this.currentPosition.lon) * 1000;
        const y = 400 + (this.currentPosition.lat - target.lat) * 1000;
        
        // Color based on risk
        const colors = {
            safe: '#00FF00',
            caution: '#FFFF00', 
            warning: '#FF8800',
            danger: '#FF0000'
        };
        
        this.chart.fillStyle = colors[target.collision_risk] || '#FFFFFF';
        this.chart.beginPath();
        this.chart.arc(x, y, 6, 0, 2 * Math.PI);
        this.chart.fill();
        
        // Draw vessel name
        this.chart.font = '10px Arial';
        this.chart.fillText(target.vessel_name || target.mmsi, x + 10, y - 10);
    }
    
    drawRadarTarget(target) {
        // Convert polar to Cartesian coordinates
        const range = target.range * 20; // Scale factor
        const bearingRad = (target.bearing - 90) * Math.PI / 180;
        
        const centerX = this.chart.canvas.width / 2;
        const centerY = this.chart.canvas.height / 2;
        
        const x = centerX + Math.cos(bearingRad) * range;
        const y = centerY + Math.sin(bearingRad) * range;
        
        this.chart.fillStyle = '#FF00FF';
        this.chart.beginPath();
        this.chart.arc(x, y, 4, 0, 2 * Math.PI);
        this.chart.fill();
    }
    
    formatLatitude(lat) {
        const deg = Math.floor(Math.abs(lat));
        const min = (Math.abs(lat) - deg) * 60;
        const dir = lat >= 0 ? 'N' : 'S';
        return `${deg}°${min.toFixed(3)}'${dir}`;
    }
    
    formatLongitude(lon) {
        const deg = Math.floor(Math.abs(lon));
        const min = (Math.abs(lon) - deg) * 60;
        const dir = lon >= 0 ? 'E' : 'W';
        return `${deg}°${min.toFixed(3)}'${dir}`;
    }
    
    markMOB() {
        fetch('/api/mob/mark', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.handleMOBAlert(data.mob_data);
            }
        });
    }
    
    handleMOBAlert(mobData) {
        // Flash screen red
        document.body.style.backgroundColor = '#FF0000';
        setTimeout(() => {
            document.body.style.backgroundColor = '#001122';
        }, 1000);
        
        // Show alert
        alert(`MOB MARKED!\nPosition: ${mobData.position.lat}, ${mobData.position.lon}\nTime: ${new Date(mobData.timestamp).toLocaleTimeString()}`);
    }
    
    setNightMode(enabled) {
        if (enabled) {
            document.body.classList.add('night-mode');
        } else {
            document.body.classList.remove('night-mode');
        }
    }
}

function setRadarRange(range) {
    nav.socket.emit('radar_control', {
        command: 'set_range',
        params: {range: range}
    });
}

// Initialize navigation system
const nav = new NavigationSystem();