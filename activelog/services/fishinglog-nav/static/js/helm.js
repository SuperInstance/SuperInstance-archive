// Helm Station JavaScript

class HelmStation {
    constructor() {
        this.socket = io();
        this.init();
    }
    
    init() {
        this.socket.on('connect', () => {
            this.socket.emit('join_station', {station_type: 'helm'});
        });
        
        this.socket.on('position_update', (data) => {
            this.updateCompass(data.heading);
            this.updateSpeed(data.speed);
        });
    }
    
    updateCompass(heading) {
        const compass = document.getElementById('compass-display');
        if (compass) {
            compass.textContent = `${heading.toFixed(0)}°`;
        }
    }
    
    updateSpeed(speed) {
        const speedDisplay = document.getElementById('speed-display');
        if (speedDisplay) {
            speedDisplay.textContent = `${speed.toFixed(1)} kts`;
        }
    }
}

function markMOB() {
    fetch('/api/mob/mark', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('MOB MARKED!');
            }
        });
}

const helm = new HelmStation();