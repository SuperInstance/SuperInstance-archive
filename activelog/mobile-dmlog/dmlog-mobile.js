/**
 * DMLog Mobile App JavaScript
 * Offline-first RPG companion with sync capabilities
 */

class DMLogMobile {
    constructor() {
        this.isOnline = navigator.onLine;
        this.rollHistory = [];
        this.character = {};
        this.combatants = [];
        this.currentTurn = 0;
        this.round = 1;
        this.spells = [];
        this.notes = '';
        
        this.init();
    }

    init() {
        this.loadFromStorage();
        this.setupEventListeners();
        this.updateConnectionStatus();
        this.loadSpellDatabase();
        this.setupServiceWorker();
        
        // Sync every 30 seconds if online
        setInterval(() => {
            if (this.isOnline) {
                this.syncData();
            }
        }, 30000);
    }

    setupEventListeners() {
        // Network status
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateConnectionStatus();
            this.syncData();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateConnectionStatus();
        });

        // Notes auto-save
        document.getElementById('notesArea').addEventListener('input', (e) => {
            this.notes = e.target.value;
            this.saveToStorage();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.rollDice(20);
                        break;
                    case 's':
                        e.preventDefault();
                        this.saveNotes();
                        break;
                }
            }
        });
    }

    updateConnectionStatus() {
        const indicator = document.getElementById('connectionStatus');
        const offlineIndicator = document.getElementById('offlineIndicator');
        
        if (this.isOnline) {
            indicator.classList.remove('offline');
            offlineIndicator.classList.remove('show');
        } else {
            indicator.classList.add('offline');
            offlineIndicator.classList.add('show');
        }
    }

    // Tab Management
    showTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // Show selected tab
        document.getElementById(tabName).classList.add('active');
        event.target.classList.add('active');

        // Load tab-specific data
        if (tabName === 'character') {
            this.loadCharacterData();
        } else if (tabName === 'spells') {
            this.loadSpells();
        } else if (tabName === 'notes') {
            this.loadNotes();
        }
    }

    // Dice Rolling
    rollDice(sides, count = 1, modifier = 0) {
        const rolls = [];
        for (let i = 0; i < count; i++) {
            rolls.push(Math.floor(Math.random() * sides) + 1);
        }
        
        const total = rolls.reduce((sum, roll) => sum + roll, 0) + modifier;
        const result = {
            dice: `${count}d${sides}${modifier !== 0 ? (modifier > 0 ? `+${modifier}` : `${modifier}`) : ''}`,
            rolls: rolls,
            modifier: modifier,
            total: total,
            timestamp: new Date().toLocaleTimeString()
        };

        this.rollHistory.unshift(result);
        if (this.rollHistory.length > 10) {
            this.rollHistory.pop();
        }

        this.displayDiceResult(result);
        this.saveToStorage();

        // Haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    }

    rollCustomDice() {
        const count = parseInt(document.getElementById('customDice').value) || 1;
        const sides = parseInt(document.getElementById('customSides').value) || 20;
        const modifier = parseInt(document.getElementById('modifier').value) || 0;
        
        this.rollDice(sides, count, modifier);
    }

    displayDiceResult(result) {
        const resultDiv = document.getElementById('diceResult');
        const historyDiv = document.getElementById('rollHistory');
        
        // Animate result
        resultDiv.style.animation = 'none';
        setTimeout(() => {
            resultDiv.textContent = `${result.total}`;
            resultDiv.style.animation = 'rollIn 0.5s ease';
        }, 10);

        // Update history
        historyDiv.innerHTML = this.rollHistory.map(roll => 
            `<div style="margin-bottom: 5px; padding: 5px; background: rgba(255,255,255,0.05); border-radius: 4px;">
                <strong>${roll.dice}</strong>: [${roll.rolls.join(', ')}] = <strong>${roll.total}</strong>
                <small style="float: right;">${roll.timestamp}</small>
            </div>`
        ).join('');
    }

    // Character Management
    updateStat(stat) {
        const score = parseInt(document.getElementById(`${stat}Score`).value);
        const modifier = Math.floor((score - 10) / 2);
        
        document.getElementById(`${stat}Value`).textContent = score;
        document.getElementById(`${stat}Mod`).textContent = modifier >= 0 ? `+${modifier}` : `${modifier}`;
        
        this.character[stat] = score;
        this.saveCharacter();
    }

    rollStats() {
        const stats = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
        stats.forEach(stat => {
            // Roll 4d6, drop lowest
            const rolls = [1,2,3,4].map(() => Math.floor(Math.random() * 6) + 1);
            rolls.sort((a, b) => b - a);
            const total = rolls[0] + rolls[1] + rolls[2];
            
            document.getElementById(`${stat}Score`).value = total;
            this.updateStat(stat);
        });
    }

    saveCharacter() {
        this.character = {
            name: document.getElementById('characterName').value,
            class: document.getElementById('characterClass').value,
            level: parseInt(document.getElementById('characterLevel').value),
            str: parseInt(document.getElementById('strScore').value),
            dex: parseInt(document.getElementById('dexScore').value),
            con: parseInt(document.getElementById('conScore').value),
            int: parseInt(document.getElementById('intScore').value),
            wis: parseInt(document.getElementById('wisScore').value),
            cha: parseInt(document.getElementById('chaScore').value)
        };
        
        this.saveToStorage();
    }

    loadCharacterData() {
        if (this.character.name) {
            document.getElementById('characterName').value = this.character.name || '';
            document.getElementById('characterClass').value = this.character.class || '';
            document.getElementById('characterLevel').value = this.character.level || 1;
            
            const stats = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
            stats.forEach(stat => {
                if (this.character[stat]) {
                    document.getElementById(`${stat}Score`).value = this.character[stat];
                    this.updateStat(stat);
                }
            });
        }
    }

    syncCharacter() {
        if (!this.isOnline) {
            alert('Cannot sync while offline');
            return;
        }

        const syncIndicator = document.getElementById('syncIndicator');
        syncIndicator.style.display = 'inline-block';

        // Simulate API call
        setTimeout(() => {
            syncIndicator.style.display = 'none';
            
            // Show success feedback
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ Synced';
            btn.style.background = 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)';
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)';
            }, 2000);
        }, 1500);
    }

    // Combat Management
    addCombatant() {
        const name = document.getElementById('combatantName').value;
        const initiative = parseInt(document.getElementById('combatantInit').value);
        
        if (name && initiative) {
            this.combatants.push({
                id: Date.now(),
                name: name,
                initiative: initiative,
                hp: 100 // Default HP
            });
            
            this.combatants.sort((a, b) => b.initiative - a.initiative);
            this.updateInitiativeDisplay();
            
            document.getElementById('combatantName').value = '';
            document.getElementById('combatantInit').value = '';
            
            this.saveToStorage();
        }
    }

    updateInitiativeDisplay() {
        const list = document.getElementById('initiativeList');
        
        if (this.combatants.length === 0) {
            list.innerHTML = '<li style="text-align: center; color: #888; padding: 20px;">No combatants added</li>';
            return;
        }
        
        list.innerHTML = this.combatants.map((combatant, index) => 
            `<li class="initiative-item ${index === this.currentTurn ? 'current' : ''}">
                <div>
                    <strong>${combatant.name}</strong><br>
                    <small>Initiative: ${combatant.initiative}</small>
                </div>
                <div style="text-align: right;">
                    <div>HP: ${combatant.hp}</div>
                    <button onclick="dmlog.removeCombatant(${combatant.id})" style="background: #f44336; border: none; color: white; padding: 5px; border-radius: 4px; font-size: 12px;">Remove</button>
                </div>
            </li>`
        ).join('');
    }

    nextTurn() {
        if (this.combatants.length === 0) return;
        
        this.currentTurn++;
        if (this.currentTurn >= this.combatants.length) {
            this.currentTurn = 0;
            this.round++;
            document.getElementById('roundCounter').textContent = this.round;
        }
        
        this.updateInitiativeDisplay();
        this.saveToStorage();
    }

    removeCombatant(id) {
        this.combatants = this.combatants.filter(c => c.id !== id);
        if (this.currentTurn >= this.combatants.length) {
            this.currentTurn = 0;
        }
        this.updateInitiativeDisplay();
        this.saveToStorage();
    }

    clearCombat() {
        this.combatants = [];
        this.currentTurn = 0;
        this.round = 1;
        document.getElementById('roundCounter').textContent = '1';
        this.updateInitiativeDisplay();
        this.saveToStorage();
    }

    // Spells and Abilities
    loadSpellDatabase() {
        // Sample spell database - in real app would be loaded from API/file
        this.spells = [
            {
                name: 'Magic Missile',
                level: 1,
                school: 'Evocation',
                castingTime: '1 action',
                range: '120 feet',
                duration: 'Instantaneous',
                description: '3 darts of magical force, each dealing 1d4+1 force damage'
            },
            {
                name: 'Fireball',
                level: 3,
                school: 'Evocation',
                castingTime: '1 action',
                range: '150 feet',
                duration: 'Instantaneous',
                description: '20-foot radius sphere, 8d6 fire damage, Dex save for half'
            },
            {
                name: 'Healing Word',
                level: 1,
                school: 'Evocation',
                castingTime: '1 bonus action',
                range: '60 feet',
                duration: 'Instantaneous',
                description: 'Heal a creature for 1d4 + spellcasting modifier HP'
            },
            {
                name: 'Shield',
                level: 1,
                school: 'Abjuration',
                castingTime: '1 reaction',
                range: 'Self',
                duration: '1 round',
                description: '+5 bonus to AC until start of next turn'
            },
            {
                name: 'Counterspell',
                level: 3,
                school: 'Abjuration',
                castingTime: '1 reaction',
                range: '60 feet',
                duration: 'Instantaneous',
                description: 'Attempt to interrupt a creature casting a spell'
            }
        ];
    }

    loadSpells() {
        const spellList = document.getElementById('spellList');
        spellList.innerHTML = this.spells.map(spell => 
            `<div class="spell-item" onclick="dmlog.showSpellDetails('${spell.name}')">
                <div class="spell-name">${spell.name}</div>
                <div class="spell-details">Level ${spell.level} ${spell.school} • ${spell.castingTime}</div>
            </div>`
        ).join('');
    }

    filterSpells() {
        const search = document.getElementById('spellSearch').value.toLowerCase();
        const filtered = this.spells.filter(spell => 
            spell.name.toLowerCase().includes(search) ||
            spell.school.toLowerCase().includes(search) ||
            spell.description.toLowerCase().includes(search)
        );
        
        const spellList = document.getElementById('spellList');
        spellList.innerHTML = filtered.map(spell => 
            `<div class="spell-item" onclick="dmlog.showSpellDetails('${spell.name}')">
                <div class="spell-name">${spell.name}</div>
                <div class="spell-details">Level ${spell.level} ${spell.school} • ${spell.castingTime}</div>
            </div>`
        ).join('');
    }

    showSpellDetails(spellName) {
        const spell = this.spells.find(s => s.name === spellName);
        if (spell) {
            alert(`${spell.name}\n\nLevel: ${spell.level}\nSchool: ${spell.school}\nCasting Time: ${spell.castingTime}\nRange: ${spell.range}\nDuration: ${spell.duration}\n\n${spell.description}`);
        }
    }

    // Notes Management
    loadNotes() {
        document.getElementById('notesArea').value = this.notes;
    }

    saveNotes() {
        this.notes = document.getElementById('notesArea').value;
        this.saveToStorage();
        
        // Show save confirmation
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✅ Saved';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 1500);
    }

    exportNotes() {
        const notes = this.notes;
        const timestamp = new Date().toISOString().split('T')[0];
        const filename = `dmlog-notes-${timestamp}.txt`;
        
        const blob = new Blob([notes], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        
        URL.revokeObjectURL(url);
    }

    // Data Persistence
    saveToStorage() {
        const data = {
            character: this.character,
            rollHistory: this.rollHistory,
            combatants: this.combatants,
            currentTurn: this.currentTurn,
            round: this.round,
            notes: this.notes,
            lastSaved: new Date().toISOString()
        };
        
        localStorage.setItem('dmlog-mobile', JSON.stringify(data));
    }

    loadFromStorage() {
        const stored = localStorage.getItem('dmlog-mobile');
        if (stored) {
            const data = JSON.parse(stored);
            this.character = data.character || {};
            this.rollHistory = data.rollHistory || [];
            this.combatants = data.combatants || [];
            this.currentTurn = data.currentTurn || 0;
            this.round = data.round || 1;
            this.notes = data.notes || '';
            
            // Update UI
            document.getElementById('roundCounter').textContent = this.round;
            this.updateInitiativeDisplay();
        }
    }

    // Cloud Sync
    async syncData() {
        if (!this.isOnline) return;
        
        try {
            // In a real implementation, this would sync with DMLog backend
            const response = await fetch('http://localhost:8400/api/mobile-sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    character: this.character,
                    notes: this.notes,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                console.log('Data synced successfully');
            }
        } catch (error) {
            console.log('Sync failed, will retry later:', error);
        }
    }

    // Service Worker Setup
    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/dmlog-sw.js');
                console.log('ServiceWorker registered');
            } catch (error) {
                console.log('ServiceWorker registration failed:', error);
            }
        }
    }

    // Voice Commands (if browser supports it)
    setupVoiceCommands() {
        if ('webkitSpeechRecognition' in window) {
            const recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = (event) => {
                const command = event.results[0][0].transcript.toLowerCase();
                this.processVoiceCommand(command);
            };
            
            // Add voice button to UI if supported
            const voiceBtn = document.createElement('button');
            voiceBtn.textContent = '🎤';
            voiceBtn.onclick = () => recognition.start();
            voiceBtn.style.position = 'fixed';
            voiceBtn.style.bottom = '20px';
            voiceBtn.style.right = '20px';
            voiceBtn.style.borderRadius = '50%';
            voiceBtn.style.width = '50px';
            voiceBtn.style.height = '50px';
            document.body.appendChild(voiceBtn);
        }
    }

    processVoiceCommand(command) {
        if (command.includes('roll d20')) {
            this.rollDice(20);
        } else if (command.includes('roll d6')) {
            this.rollDice(6);
        } else if (command.includes('next turn')) {
            this.nextTurn();
        }
        // Add more voice commands as needed
    }
}

// Global functions for HTML onclick events
function showTab(tabName) {
    dmlog.showTab(tabName);
}

function rollDice(sides) {
    dmlog.rollDice(sides);
}

function rollCustomDice() {
    dmlog.rollCustomDice();
}

function updateStat(stat) {
    dmlog.updateStat(stat);
}

function rollStats() {
    dmlog.rollStats();
}

function saveCharacter() {
    dmlog.saveCharacter();
}

function syncCharacter() {
    dmlog.syncCharacter();
}

function addCombatant() {
    dmlog.addCombatant();
}

function nextTurn() {
    dmlog.nextTurn();
}

function clearCombat() {
    dmlog.clearCombat();
}

function filterSpells() {
    dmlog.filterSpells();
}

function saveNotes() {
    dmlog.saveNotes();
}

function exportNotes() {
    dmlog.exportNotes();
}

// Initialize the app
const dmlog = new DMLogMobile();

// PWA Installation
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    // Show install button
    const installBtn = document.createElement('button');
    installBtn.textContent = '📱 Install App';
    installBtn.onclick = async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                installBtn.style.display = 'none';
            }
            deferredPrompt = null;
        }
    };
    installBtn.style.position = 'fixed';
    installBtn.style.top = '10px';
    installBtn.style.right = '10px';
    installBtn.style.zIndex = '1000';
    installBtn.style.fontSize = '12px';
    installBtn.style.padding = '5px 10px';
    document.body.appendChild(installBtn);
});