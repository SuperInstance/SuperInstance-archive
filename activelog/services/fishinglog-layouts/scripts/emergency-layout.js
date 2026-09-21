// Emergency Layout Specific JavaScript
// Extends the base Marine Interface for emergency response functionality

class EmergencyLayout extends MarineInterface {
    constructor() {
        super();
        this.emergencyState = {
            active: true,
            type: 'MAYDAY',
            startTime: new Date(),
            position: { ...this.position },
            procedures: []
        };
        
        this.aisVessels = [];
        this.rescueAssets = [];
        this.communications = {
            channels: [16, 9, 22, 70, 156.8],
            activeChannel: 16,
            dscEnabled: true,
            epirb: { status: 'armed', lastTest: new Date(Date.now() - 86400000) }
        };
        
        this.equipment = {
            vhf: 'operational',
            gps: 'operational',
            radar: 'operational',
            ais: 'operational',
            epirb: 'operational',
            liferaft: 'operational'
        };
        
        this.initEmergencyFeatures();
    }

    initEmergencyFeatures() {
        this.setupEmergencyAlert();
        this.setupAISTracking();
        this.setupCommunications();
        this.setupEmergencyProcedures();
        this.setupDistressSignals();
        this.generateRescueAssets();
        this.startEmergencyUpdates();
        
        console.log('Emergency layout initialized - MAYDAY ACTIVE');
        this.broadcastMayday();
    }

    // Emergency Alert Functions
    setupEmergencyAlert() {
        // Emergency action buttons
        document.getElementById('maydayBtn')?.addEventListener('click', () => {
            this.declareMayday();
        });
        
        document.getElementById('panpanBtn')?.addEventListener('click', () => {
            this.declarePanPan();
        });
        
        document.getElementById('securiteBtn')?.addEventListener('click', () => {
            this.declareSecurite();
        });
        
        document.getElementById('cancelEmergencyBtn')?.addEventListener('click', () => {
            this.cancelEmergency();
        });
    }

    declareMayday() {
        this.emergencyState.type = 'MAYDAY';
        this.emergencyState.active = true;
        this.emergencyState.startTime = new Date();
        
        this.updateEmergencyDisplay();
        this.broadcastMayday();
        this.showToast('MAYDAY MAYDAY MAYDAY - Distress signal transmitted', 'error', 8000);
        
        // Trigger all emergency systems
        this.activateAllEmergencySystems();
    }

    declarePanPan() {
        this.emergencyState.type = 'PAN-PAN';
        this.emergencyState.active = true;
        this.emergencyState.startTime = new Date();
        
        this.updateEmergencyDisplay();
        this.broadcastPanPan();
        this.showToast('PAN-PAN PAN-PAN PAN-PAN - Urgency signal transmitted', 'warning', 6000);
    }

    declareSecurite() {
        this.emergencyState.type = 'SÉCURITÉ';
        this.emergencyState.active = true;
        this.emergencyState.startTime = new Date();
        
        this.updateEmergencyDisplay();
        this.broadcastSecurite();
        this.showToast('SÉCURITÉ SÉCURITÉ SÉCURITÉ - Safety signal transmitted', 'info', 4000);
    }

    cancelEmergency() {
        this.emergencyState.active = false;
        this.broadcastCancel();
        this.updateEmergencyDisplay();
        this.showToast('Emergency cancelled - All stations notified', 'info');
    }

    updateEmergencyDisplay() {
        const alertStatus = document.querySelector('.alert-status');
        const alertTime = document.querySelector('.alert-time');
        const alertPosition = document.querySelector('.alert-position');
        
        if (alertStatus) {
            alertStatus.innerHTML = `🚨 ${this.emergencyState.type} ACTIVE`;
        }
        
        if (alertTime) {
            const elapsed = Math.floor((Date.now() - this.emergencyState.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            alertTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        
        if (alertPosition) {
            alertPosition.textContent = `${this.formatCoordinate(this.emergencyState.position.lat, 'lat')} ${this.formatCoordinate(this.emergencyState.position.lon, 'lon')}`;
        }
    }

    broadcastMayday() {
        const mayDay = {
            type: 'MAYDAY',
            vessel: 'M/V ACTIVE LOG',
            position: this.emergencyState.position,
            souls: 4,
            nature: 'Taking on water',
            assistance: 'Immediate assistance required'
        };
        
        console.log('Broadcasting MAYDAY:', mayDay);
        this.logCommunication('MAYDAY', 'Ch 16', 'BROADCAST', mayDay);
    }

    broadcastPanPan() {
        const panPan = {
            type: 'PAN-PAN',
            vessel: 'M/V ACTIVE LOG',
            position: this.emergencyState.position,
            nature: 'Engine failure',
            assistance: 'Require tow assistance'
        };
        
        console.log('Broadcasting PAN-PAN:', panPan);
        this.logCommunication('PAN-PAN', 'Ch 16', 'BROADCAST', panPan);
    }

    broadcastSecurite() {
        const securite = {
            type: 'SÉCURITÉ',
            vessel: 'M/V ACTIVE LOG',
            position: this.emergencyState.position,
            message: 'Navigation equipment malfunction - maintaining position'
        };
        
        console.log('Broadcasting SÉCURITÉ:', securite);
        this.logCommunication('SÉCURITÉ', 'Ch 16', 'BROADCAST', securite);
    }

    broadcastCancel() {
        const cancel = {
            type: 'CANCEL',
            vessel: 'M/V ACTIVE LOG',
            originalType: this.emergencyState.type,
            message: 'Emergency situation resolved - cancel assistance'
        };
        
        console.log('Broadcasting CANCEL:', cancel);
        this.logCommunication('CANCEL', 'Ch 16', 'BROADCAST', cancel);
    }

    activateAllEmergencySystems() {
        // Activate EPIRB
        this.activateEPIRB();
        
        // Set emergency channel
        this.setEmergencyChannel(16);
        
        // Start emergency beacon
        this.startEmergencyBeacon();
        
        // Notify nearby vessels
        this.notifyNearbyVessels();
    }

    // AIS Tracking Functions
    setupAISTracking() {
        this.generateAISVessels();
        
        // AIS vessel click handlers
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('ais-vessel')) {
                const vesselId = e.target.dataset.vesselId;
                this.showVesselDetail(vesselId);
            }
        });
    }

    generateAISVessels() {
        this.aisVessels = [
            {
                id: 'USCG_001',
                name: 'USCG CUTTER SENECA',
                type: 'Coast Guard',
                mmsi: '366123456',
                position: { lat: this.position.lat + 0.05, lon: this.position.lon + 0.02 },
                course: 135,
                speed: 18,
                distance: 2.8,
                bearing: 045,
                emergency: false,
                capability: 'SAR'
            },
            {
                id: 'HELO_001',
                name: 'USCG 6501',
                type: 'Rescue Helicopter',
                mmsi: '366123457',
                position: { lat: this.position.lat + 0.03, lon: this.position.lon + 0.04 },
                course: 225,
                speed: 120,
                distance: 4.2,
                bearing: 065,
                emergency: false,
                capability: 'AIR_SAR'
            },
            {
                id: 'VES_001',
                name: 'F/V BOSTON LADY',
                type: 'Fishing Vessel',
                mmsi: '366789012',
                position: { lat: this.position.lat - 0.02, lon: this.position.lon + 0.03 },
                course: 180,
                speed: 8,
                distance: 1.8,
                bearing: 285,
                emergency: false,
                capability: 'ASSIST'
            },
            {
                id: 'VES_002',
                name: 'M/Y FREEDOM',
                type: 'Motor Yacht',
                mmsi: '366555123',
                position: { lat: this.position.lat + 0.01, lon: this.position.lon - 0.02 },
                course: 090,
                speed: 12,
                distance: 1.2,
                bearing: 315,
                emergency: false,
                capability: 'ASSIST'
            }
        ];
        
        this.updateAISDisplay();
    }

    updateAISDisplay() {
        const aisTraffic = document.querySelector('.ais-traffic');
        if (!aisTraffic) return;
        
        // Update vessel list
        const vesselElements = this.aisVessels.map(vessel => {
            const cssClass = vessel.type === 'Coast Guard' ? 'coast-guard' : 
                           vessel.emergency ? 'emergency' : '';
                           
            return `
                <div class=\"ais-vessel ${cssClass}\" data-vessel-id=\"${vessel.id}\">
                    <div class=\"vessel-details\">
                        <div class=\"vessel-name\">${vessel.name}</div>
                        <div class=\"vessel-type\">${vessel.type} • MMSI: ${vessel.mmsi}</div>
                    </div>
                    <div class=\"vessel-metrics\">
                        <div class=\"vessel-distance\">${vessel.distance.toFixed(1)} nm</div>
                        <div class=\"vessel-bearing\">${Math.round(vessel.bearing).toString().padStart(3, '0')}°</div>
                    </div>
                </div>
            `;
        }).join('');
        
        aisTraffic.innerHTML = `
            <h4>AIS Traffic</h4>
            ${vesselElements}
        `;
    }

    showVesselDetail(vesselId) {
        const vessel = this.aisVessels.find(v => v.id === vesselId);
        if (!vessel) return;
        
        const details = `${vessel.name}\\nType: ${vessel.type}\\nMMSI: ${vessel.mmsi}\\nDistance: ${vessel.distance.toFixed(1)} nm\\nBearing: ${Math.round(vessel.bearing)}°\\nCourse: ${Math.round(vessel.course)}°\\nSpeed: ${vessel.speed} kts\\nCapability: ${vessel.capability}`;
        
        this.showToast(details, 'info', 6000);
    }

    // Communications Functions
    setupCommunications() {
        // Radio channel buttons
        document.querySelectorAll('.channel-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const channel = e.target.dataset.channel;
                this.selectChannel(channel);
            });
        });
        
        // Emergency contacts
        document.querySelectorAll('.contact-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const contact = e.target.closest('.contact-item').dataset.contact;
                this.contactEmergencyService(contact);
            });
        });
        
        this.updateCommunicationsDisplay();
    }

    selectChannel(channel) {
        this.communications.activeChannel = parseInt(channel);
        
        // Update button states
        document.querySelectorAll('.channel-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-channel=\"${channel}\"]`)?.classList.add('active');
        
        this.showToast(`VHF Channel ${channel} selected`, 'info');
        
        // Special handling for emergency channel
        if (channel === '16') {
            this.monitorEmergencyChannel();
        }
    }

    monitorEmergencyChannel() {
        // Simulate emergency channel monitoring
        setTimeout(() => {
            const emergencyTraffic = [
                'USCG to all stations: Search and rescue in progress, area 41°24\\'N 71°51\\'W',
                'Pan Pan, Pan Pan, this is M/Y SEAHAWK, engine failure, position...',
                'Coast Guard Rescue Coordination Center to ACTIVE LOG: Acknowledge MAYDAY'
            ];
            
            if (this.communications.activeChannel === 16 && Math.random() < 0.3) {
                const message = emergencyTraffic[Math.floor(Math.random() * emergencyTraffic.length)];
                this.showToast(`Ch 16: ${message}`, 'warning', 6000);
            }
            
            if (this.communications.activeChannel === 16) {
                this.monitorEmergencyChannel();
            }
        }, 10000 + Math.random() * 20000);
    }

    contactEmergencyService(service) {
        const contacts = {
            'coast_guard': 'US Coast Guard',
            'rescue': 'Maritime Rescue',
            'police': 'Marine Police',
            'fire': 'Marine Fire'
        };
        
        const contactName = contacts[service];
        this.showToast(`Contacting ${contactName}...`, 'info');
        
        setTimeout(() => {
            this.simulateEmergencyResponse(service);
        }, 2000);
    }

    simulateEmergencyResponse(service) {
        const responses = {
            'coast_guard': 'USCG: Roger ACTIVE LOG, we have your position. Cutter SENECA responding, ETA 15 minutes.',
            'rescue': 'RESCUE: Copy your MAYDAY. Helicopter 6501 airborne, searching your area.',
            'police': 'MARINE POLICE: Acknowledged. Patrol boat dispatched to your location.',
            'fire': 'MARINE FIRE: Roger. Fire boat en route, ETA 20 minutes.'
        };
        
        const response = responses[service];
        this.showToast(response, 'info', 8000);
        this.logCommunication('RESPONSE', `${service.toUpperCase()}`, 'RECEIVED', response);
    }

    logCommunication(type, channel, direction, message) {
        const commLog = {
            timestamp: new Date(),
            type: type,
            channel: channel,
            direction: direction,
            message: typeof message === 'object' ? JSON.stringify(message) : message
        };
        
        console.log('Communication Log:', commLog);
    }

    updateCommunicationsDisplay() {
        // Update active channel display
        const activeChannelDisplay = document.querySelector('.active-channel');
        if (activeChannelDisplay) {
            activeChannelDisplay.textContent = `Channel ${this.communications.activeChannel}`;
        }
        
        // Update equipment status
        this.updateEquipmentStatus();
    }

    // Distress Signals
    setupDistressSignals() {
        document.querySelectorAll('.distress-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const signalType = e.target.dataset.signal;
                this.activateDistressSignal(signalType);
            });
        });
    }

    activateDistressSignal(signalType) {
        const signals = {
            'dsc': {
                name: 'Digital Selective Calling',
                action: 'DSC distress alert transmitted on Ch 70',
                duration: 3000
            },
            'epirb': {
                name: 'Emergency Position Radio Beacon',
                action: 'EPIRB activated - satellite distress signal broadcasting',
                duration: 5000
            },
            'flares': {
                name: 'Distress Flares',
                action: 'Red flares fired - visual distress signal active',
                duration: 4000
            },
            'horn': {
                name: 'Sound Signals',
                action: 'Continuous horn blasts - audio distress signal',
                duration: 2000
            }
        };
        
        const signal = signals[signalType];
        if (!signal) return;
        
        this.showToast(`${signal.name}: ${signal.action}`, 'error', signal.duration);
        
        // Update equipment status
        if (signalType === 'epirb') {
            this.equipment.epirb = 'transmitting';
            this.updateEquipmentStatus();
        }
        
        // Log the activation
        this.logCommunication('DISTRESS_SIGNAL', signalType.toUpperCase(), 'TRANSMITTED', signal.action);
    }

    activateEPIRB() {
        this.equipment.epirb = 'transmitting';
        this.showToast('EPIRB ACTIVATED - Satellite distress beacon transmitting', 'error', 8000);
        this.updateEquipmentStatus();
    }

    // Emergency Procedures
    setupEmergencyProcedures() {
        // Initialize emergency checklist
        this.emergencyState.procedures = [
            { id: 1, text: 'Assess immediate danger to vessel and crew', completed: false },
            { id: 2, text: 'Send MAYDAY distress signal on VHF Ch 16', completed: true },
            { id: 3, text: 'Activate EPIRB emergency beacon', completed: true },
            { id: 4, text: 'Don life jackets for all persons on board', completed: false },
            { id: 5, text: 'Prepare abandon ship bag with supplies', completed: false },
            { id: 6, text: 'Prepare life raft for deployment', completed: false },
            { id: 7, text: 'Maintain radio watch on emergency channel', completed: true },
            { id: 8, text: 'Signal rescue vessels with flares/lights', completed: false }
        ];
        
        this.updateProceduresList();
        
        // Procedure checkbox handlers
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('procedure-checkbox')) {
                const procedureId = parseInt(e.target.dataset.procedureId);
                this.toggleProcedure(procedureId);
            }
        });
    }

    updateProceduresList() {
        const proceduresList = document.querySelector('.procedure-checklist');
        if (!proceduresList) return;
        
        proceduresList.innerHTML = this.emergencyState.procedures.map(procedure => `
            <li class=\"procedure-item ${procedure.completed ? 'completed' : ''}\">
                <div class=\"procedure-checkbox ${procedure.completed ? 'completed' : ''}\" 
                     data-procedure-id=\"${procedure.id}\"></div>
                <div class=\"procedure-text\">${procedure.text}</div>
            </li>
        `).join('');
    }

    toggleProcedure(procedureId) {
        const procedure = this.emergencyState.procedures.find(p => p.id === procedureId);
        if (procedure) {
            procedure.completed = !procedure.completed;
            this.updateProceduresList();
            
            const status = procedure.completed ? 'completed' : 'unchecked';
            this.showToast(`Procedure ${status}: ${procedure.text}`, 'info', 3000);
        }
    }

    // Equipment Status
    updateEquipmentStatus() {
        const equipmentItems = document.querySelectorAll('.equipment-item');
        equipmentItems.forEach(item => {
            const equipmentName = item.querySelector('.equipment-name').textContent.toLowerCase();
            const indicator = item.querySelector('.equipment-indicator');
            
            let status = 'operational';
            if (this.equipment[equipmentName]) {
                status = this.equipment[equipmentName];
            }
            
            // Update indicator
            indicator.className = 'equipment-indicator';
            indicator.classList.add(status === 'transmitting' ? 'operational' : status);
            
            switch (status) {
                case 'operational':
                    indicator.textContent = 'OK';
                    break;
                case 'transmitting':
                    indicator.textContent = 'TX';
                    break;
                case 'warning':
                    indicator.textContent = 'WARN';
                    break;
                case 'offline':
                    indicator.textContent = 'OFF';
                    break;
            }
        });
    }

    // Rescue Assets Management
    generateRescueAssets() {
        this.rescueAssets = [
            {
                id: 'USCG_SENECA',
                type: 'coast-guard',
                name: 'USCG Cutter Seneca',
                position: { lat: this.position.lat + 0.05, lon: this.position.lon + 0.02 },
                eta: '15 min',
                capability: 'Heavy rescue, medical'
            },
            {
                id: 'USCG_6501',
                type: 'helicopter',
                name: 'USCG Helicopter 6501',
                position: { lat: this.position.lat + 0.03, lon: this.position.lon + 0.04 },
                eta: '8 min',
                capability: 'Air rescue, medical evacuation'
            },
            {
                id: 'BOSTON_LADY',
                type: 'vessel',
                name: 'F/V Boston Lady',
                position: { lat: this.position.lat - 0.02, lon: this.position.lon + 0.03 },
                eta: '12 min',
                capability: 'Towing assistance'
            }
        ];
        
        this.displayRescueAssets();
    }

    displayRescueAssets() {
        const chartCanvas = document.getElementById('chartCanvas');
        if (!chartCanvas) return;
        
        // Remove existing rescue assets
        document.querySelectorAll('.rescue-asset').forEach(asset => asset.remove());
        
        this.rescueAssets.forEach(asset => {
            const assetElement = document.createElement('div');
            assetElement.className = `rescue-asset ${asset.type}`;
            assetElement.style.position = 'absolute';
            
            // Position relative to chart (simplified positioning)
            const x = 30 + Math.random() * 40; // 30-70% from left
            const y = 20 + Math.random() * 60; // 20-80% from top
            
            assetElement.style.left = `${x}%`;
            assetElement.style.top = `${y}%`;
            
            assetElement.innerHTML = `
                <div class=\"asset-marker\">🚁</div>
                <div class=\"asset-info\">
                    ${asset.name}<br>
                    ETA: ${asset.eta}<br>
                    ${asset.capability}
                </div>
            `;
            
            chartCanvas.appendChild(assetElement);
        });
    }

    // Emergency Updates
    startEmergencyUpdates() {
        setInterval(() => {
            if (this.emergencyState.active) {
                this.updateEmergencyDisplay();
                this.updateRescuePositions();
                this.updateAISVessels();
            }
        }, 1000);
        
        // Periodic emergency announcements
        setInterval(() => {
            if (this.emergencyState.active && this.emergencyState.type === 'MAYDAY') {
                this.repeatMayday();
            }
        }, 120000); // Every 2 minutes
    }

    updateRescuePositions() {
        // Simulate rescue assets approaching
        this.rescueAssets.forEach(asset => {
            // Decrease ETA
            const currentETA = parseInt(asset.eta);
            if (currentETA > 0) {
                asset.eta = `${Math.max(0, currentETA - 1)} min`;
            } else {
                asset.eta = 'On scene';
            }
            
            // Move position slightly toward emergency
            const dx = (this.emergencyState.position.lat - asset.position.lat) * 0.01;
            const dy = (this.emergencyState.position.lon - asset.position.lon) * 0.01;
            
            asset.position.lat += dx;
            asset.position.lon += dy;
        });
    }

    updateAISVessels() {
        // Update AIS vessel positions and distances
        this.aisVessels.forEach(vessel => {
            // Simulate vessels responding to emergency
            if (vessel.capability === 'SAR' || vessel.capability === 'AIR_SAR') {
                // Move toward emergency position
                const dx = (this.emergencyState.position.lat - vessel.position.lat) * 0.005;
                const dy = (this.emergencyState.position.lon - vessel.position.lon) * 0.005;
                
                vessel.position.lat += dx;
                vessel.position.lon += dy;
                
                // Update distance and bearing
                vessel.distance = this.calculateDistance(vessel.position, this.emergencyState.position);
                vessel.bearing = this.calculateBearing(vessel.position, this.emergencyState.position);
            }
        });
        
        this.updateAISDisplay();
    }

    repeatMayday() {
        if (this.emergencyState.active && this.emergencyState.type === 'MAYDAY') {
            console.log('Repeating MAYDAY broadcast');
            this.broadcastMayday();
        }
    }

    setEmergencyChannel(channel) {
        this.selectChannel(channel.toString());
        document.querySelector(`[data-channel=\"${channel}\"]`)?.classList.add('emergency');
    }

    startEmergencyBeacon() {
        // Visual emergency beacon effect
        const emergencyAlert = document.querySelector('.emergency-alert');
        if (emergencyAlert) {
            emergencyAlert.style.animation = 'emergencyFlash 1s infinite';
        }
    }

    notifyNearbyVessels() {
        // Send emergency notification to nearby vessels
        this.aisVessels.forEach(vessel => {
            if (vessel.distance < 5) { // Within 5 nm
                console.log(`Emergency notification sent to ${vessel.name}`);
            }
        });
    }

    // Utility functions
    calculateDistance(pos1, pos2) {
        // Simplified distance calculation (haversine formula would be more accurate)
        const dx = pos2.lat - pos1.lat;
        const dy = pos2.lon - pos1.lon;
        return Math.sqrt(dx*dx + dy*dy) * 60; // Convert to nautical miles (approximately)
    }

    calculateBearing(from, to) {
        const dx = to.lon - from.lon;
        const dy = to.lat - from.lat;
        const bearing = Math.atan2(dx, dy) * 180 / Math.PI;
        return (bearing + 360) % 360;
    }
}

// Initialize emergency layout when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('emergency-layout')) {
        try {
            window.emergencyLayout = new EmergencyLayout();
        } catch (error) {
            console.error('Failed to initialize Emergency Layout:', error);
        }
    }
});