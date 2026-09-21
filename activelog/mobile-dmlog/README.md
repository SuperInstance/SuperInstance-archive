# DMLog Mobile - RPG Companion App

A Progressive Web App (PWA) companion for the DMLog tabletop RPG management system. Works offline and syncs with the main DMLog services.

## Features

### 🎲 Dice Roller
- Quick roll buttons for standard dice (d4, d6, d8, d10, d12, d20)
- Custom dice combinations with modifiers
- Roll history with timestamps
- Haptic feedback on supported devices

### 👤 Character Sheet Companion
- Basic character information (name, class, level)
- Ability scores with automatic modifier calculation
- 4d6 drop lowest stat rolling
- Sync with main DMLog Core service

### ⚔️ Initiative Tracker
- Add combatants with initiative scores
- Automatic sorting by initiative
- Turn tracking with round counter
- Combat participant management

### ✨ Spell & Ability Reference
- Searchable spell database
- Quick reference for common spells
- Level, school, and casting information
- Expandable with custom content

### 📝 Session Notes
- Auto-saving note taking
- Export notes to text files
- Offline note storage
- Sync with session manager

## Technical Features

### 📱 Progressive Web App
- Installable on mobile devices
- Offline-first architecture
- Service worker caching
- Native app-like experience

### 🔄 Sync Capabilities  
- Background sync when online
- Conflict resolution
- Data persistence in localStorage
- Real-time sync with DMLog backend

### 🎨 Mobile-Optimized UI
- Touch-friendly interface
- Responsive design
- Dark theme optimized for gaming
- Smooth animations and transitions

## Installation

### As a Web App
1. Open in mobile browser: `http://localhost:8080`
2. Tap "Add to Home Screen" or install prompt
3. Launch from home screen like native app

### Development Server
```bash
cd ~/activelog/mobile-dmlog
python server.py
```

### Integration with DMLog
The mobile app syncs with DMLog services:
- Character data → DMLog Core (port 8400)
- Session notes → Session Manager (port 8404)
- Combat data → Battle System (port 8403)

## Usage

### First Launch
1. Create or load character
2. Configure sync settings
3. Test dice rolling and features
4. Take session notes

### During Play
- Use dice roller for quick rolls
- Track initiative in combat
- Reference spells and abilities
- Take session notes
- All data saves automatically

### Offline Mode
- All features work offline
- Data stored locally
- Sync when connection restored
- Visual indicators for connection status

## Browser Support

### Recommended
- Chrome/Chromium (Android/Desktop)
- Safari (iOS/macOS)
- Firefox (Android/Desktop)
- Edge (Windows/Android)

### PWA Features
- Service Worker: ✅ All modern browsers
- Web App Manifest: ✅ Chrome, Safari, Edge
- Add to Home Screen: ✅ All mobile browsers
- Background Sync: ✅ Chrome, Edge
- Push Notifications: 🔄 Future feature

## API Endpoints

### Sync Endpoints
- `POST /api/mobile-sync` - Sync app data
- `GET /api/health` - Health check

### DMLog Integration
- Connects to DMLog Core API
- Syncs with Session Manager
- Updates Battle System data
- Character import/export

## Development

### File Structure
```
mobile-dmlog/
├── index.html          # Main app HTML
├── dmlog-mobile.js     # App JavaScript
├── dmlog-sw.js         # Service Worker
├── manifest.json       # PWA Manifest
├── server.py           # Development server
└── README.md          # This file
```

### Adding Features
1. Update UI in `index.html`
2. Add functionality in `dmlog-mobile.js`
3. Update service worker cache if needed
4. Add sync endpoints as required

### Testing
- Test offline functionality
- Verify PWA installation
- Check sync with DMLog services
- Test on multiple devices/browsers

## Future Enhancements

### Planned Features
- [ ] Voice commands for dice rolling
- [ ] Camera integration for dice recognition
- [ ] Push notifications for turn reminders
- [ ] Multi-character support
- [ ] Campaign sharing
- [ ] Custom spell/ability database
- [ ] Integration with D&D Beyond
- [ ] Miniature photo tracking
- [ ] Audio note recording

### Technical Improvements
- [ ] IndexedDB for larger data storage
- [ ] WebRTC for peer-to-peer sync
- [ ] WebGL dice animations
- [ ] Background refresh
- [ ] Keyboard shortcuts
- [ ] Accessibility improvements

## License

Part of the DMLog RPG Management System. For personal and educational use.