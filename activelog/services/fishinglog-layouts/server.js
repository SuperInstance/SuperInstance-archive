#!/usr/bin/env node
/**
 * Professional Marine Navigation Layout Manager
 * Provides specialized UI layouts for different operational modes
 */

const express = require('express');
const cors = require('cors');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 8368;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));
app.use('/build', express.static('build'));

// Layout definitions
const layouts = {
  helm: {
    id: 'helm',
    name: 'Helm Station',
    description: 'Essential navigation controls for active helming',
    components: ['chart', 'instruments', 'radar'],
    priority: 'navigation',
    layout: [
      { i: 'chart', x: 0, y: 0, w: 8, h: 8, minW: 6, minH: 6 },
      { i: 'instruments', x: 8, y: 0, w: 4, h: 4, minW: 3, minH: 3 },
      { i: 'radar', x: 8, y: 4, w: 4, h: 4, minW: 3, minH: 3 }
    ]
  },
  navigation: {
    id: 'navigation',
    name: 'Navigation Planning',
    description: 'Route planning and weather analysis',
    components: ['chart', 'route', 'weather'],
    priority: 'planning',
    layout: [
      { i: 'chart', x: 0, y: 0, w: 6, h: 8, minW: 4, minH: 6 },
      { i: 'route', x: 6, y: 0, w: 6, h: 4, minW: 4, minH: 3 },
      { i: 'weather', x: 6, y: 4, w: 6, h: 4, minW: 4, minH: 3 }
    ]
  },
  fishing: {
    id: 'fishing',
    name: 'Fishing Operations',
    description: 'Fish finding and catch management',
    components: ['chart', 'fishfinder', 'catchlog'],
    priority: 'fishing',
    layout: [
      { i: 'chart', x: 0, y: 0, w: 6, h: 6, minW: 4, minH: 4 },
      { i: 'fishfinder', x: 6, y: 0, w: 6, h: 6, minW: 4, minH: 4 },
      { i: 'catchlog', x: 0, y: 6, w: 12, h: 2, minW: 8, minH: 2 }
    ]
  },
  docking: {
    id: 'docking',
    name: 'Docking Assistance',
    description: 'Close-quarters maneuvering aids',
    components: ['chart', 'cameras', 'wind'],
    priority: 'maneuvering',
    layout: [
      { i: 'chart', x: 0, y: 0, w: 4, h: 6, minW: 3, minH: 4 },
      { i: 'cameras', x: 4, y: 0, w: 8, h: 6, minW: 6, minH: 4 },
      { i: 'wind', x: 0, y: 6, w: 12, h: 2, minW: 8, minH: 2 }
    ]
  },
  passage: {
    id: 'passage',
    name: 'Passage Making',
    description: 'Long-distance cruising layout',
    components: ['chart', 'weather', 'watchkeeping'],
    priority: 'cruising',
    layout: [
      { i: 'chart', x: 0, y: 0, w: 8, h: 6, minW: 6, minH: 4 },
      { i: 'weather', x: 8, y: 0, w: 4, h: 6, minW: 3, minH: 4 },
      { i: 'watchkeeping', x: 0, y: 6, w: 12, h: 2, minW: 8, minH: 2 }
    ]
  },
  emergency: {
    id: 'emergency',
    name: 'Emergency Response',
    description: 'Critical situation management',
    components: ['chart', 'ais', 'communications'],
    priority: 'emergency',
    layout: [
      { i: 'chart', x: 0, y: 0, w: 6, h: 6, minW: 4, minH: 4 },
      { i: 'ais', x: 6, y: 0, w: 6, h: 3, minW: 4, minH: 2 },
      { i: 'communications', x: 6, y: 3, w: 6, h: 5, minW: 4, minH: 3 }
    ]
  }
};

// Component definitions
const components = {
  chart: {
    id: 'chart',
    name: 'Electronic Chart',
    type: 'navigation',
    description: 'Interactive marine chart display',
    dataEndpoint: '/api/chart',
    refreshRate: 1000
  },
  instruments: {
    id: 'instruments',
    name: 'Navigation Instruments',
    type: 'instruments',
    description: 'Speed, depth, heading, GPS data',
    dataEndpoint: '/api/instruments',
    refreshRate: 500
  },
  radar: {
    id: 'radar',
    name: 'Radar Display',
    type: 'radar',
    description: 'Marine radar overlay and targets',
    dataEndpoint: '/api/radar',
    refreshRate: 2000
  },
  route: {
    id: 'route',
    name: 'Route Planning',
    type: 'navigation',
    description: 'Waypoint and route management',
    dataEndpoint: '/api/route',
    refreshRate: 5000
  },
  weather: {
    id: 'weather',
    name: 'Weather Display',
    type: 'weather',
    description: 'Weather conditions and forecasts',
    dataEndpoint: '/api/weather',
    refreshRate: 10000
  },
  fishfinder: {
    id: 'fishfinder',
    name: 'Fish Finder',
    type: 'fishing',
    description: 'Sonar depth and fish detection',
    dataEndpoint: '/api/fishfinder',
    refreshRate: 1000
  },
  catchlog: {
    id: 'catchlog',
    name: 'Catch Log',
    type: 'fishing',
    description: 'Fish catch recording and statistics',
    dataEndpoint: '/api/catchlog',
    refreshRate: 30000
  },
  cameras: {
    id: 'cameras',
    name: 'Camera Views',
    type: 'visual',
    description: 'Onboard camera feeds',
    dataEndpoint: '/api/cameras',
    refreshRate: 100
  },
  wind: {
    id: 'wind',
    name: 'Wind Instruments',
    type: 'instruments',
    description: 'Wind speed and direction',
    dataEndpoint: '/api/wind',
    refreshRate: 1000
  },
  watchkeeping: {
    id: 'watchkeeping',
    name: 'Watch Management',
    type: 'operational',
    description: 'Crew watch schedules and logs',
    dataEndpoint: '/api/watchkeeping',
    refreshRate: 60000
  },
  ais: {
    id: 'ais',
    name: 'AIS Traffic',
    type: 'navigation',
    description: 'Automatic Identification System',
    dataEndpoint: '/api/ais',
    refreshRate: 2000
  },
  communications: {
    id: 'communications',
    name: 'Communications',
    type: 'communications',
    description: 'VHF radio and emergency comms',
    dataEndpoint: '/api/communications',
    refreshRate: 5000
  }
};

// API Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/api/layouts', (req, res) => {
  res.json({ layouts: Object.values(layouts) });
});

app.get('/api/layouts/:id', (req, res) => {
  const layout = layouts[req.params.id];
  if (!layout) {
    return res.status(404).json({ error: 'Layout not found' });
  }
  res.json({ layout });
});

app.get('/api/components', (req, res) => {
  res.json({ components: Object.values(components) });
});

app.get('/api/components/:id', (req, res) => {
  const component = components[req.params.id];
  if (!component) {
    return res.status(404).json({ error: 'Component not found' });
  }
  res.json({ component });
});

// Layout management
app.post('/api/layouts/:id/save', (req, res) => {
  const layoutId = req.params.id;
  const { layout: newLayout } = req.body;
  
  if (layouts[layoutId]) {
    layouts[layoutId].layout = newLayout;
    
    // Broadcast layout change to all connected clients
    io.emit('layoutUpdated', {
      layoutId,
      layout: layouts[layoutId]
    });
    
    res.json({ success: true, layout: layouts[layoutId] });
  } else {
    res.status(404).json({ error: 'Layout not found' });
  }
});

// Mock data endpoints for components
app.get('/api/chart', (req, res) => {
  res.json({
    position: { lat: 40.7589, lng: -73.9851 },
    zoom: 12,
    heading: 045,
    tracks: [
      { lat: 40.7589, lng: -73.9851, timestamp: Date.now() - 60000 },
      { lat: 40.7599, lng: -73.9841, timestamp: Date.now() - 30000 },
      { lat: 40.7609, lng: -73.9831, timestamp: Date.now() }
    ]
  });
});

app.get('/api/instruments', (req, res) => {
  res.json({
    speed: 12.5,
    heading: 045,
    depth: 18.3,
    gps: { lat: 40.7589, lng: -73.9851 },
    timestamp: Date.now()
  });
});

app.get('/api/radar', (req, res) => {
  res.json({
    range: 6,
    targets: [
      { bearing: 030, range: 2.1, cpa: 0.5, tcpa: 8 },
      { bearing: 120, range: 4.8, cpa: 1.2, tcpa: 15 }
    ],
    timestamp: Date.now()
  });
});

app.get('/api/weather', (req, res) => {
  res.json({
    current: {
      windSpeed: 15,
      windDirection: 230,
      temperature: 22,
      pressure: 1013,
      humidity: 65
    },
    forecast: [
      { time: '12:00', windSpeed: 18, windDirection: 240, conditions: 'Partly cloudy' },
      { time: '18:00', windSpeed: 22, windDirection: 250, conditions: 'Cloudy' }
    ]
  });
});

app.get('/api/fishfinder', (req, res) => {
  res.json({
    depth: 45.2,
    waterTemp: 18.5,
    fishArches: [
      { depth: 25.3, strength: 0.8, size: 'medium' },
      { depth: 38.1, strength: 0.6, size: 'small' }
    ],
    bottomType: 'rocky'
  });
});

// Socket.IO for real-time updates
io.on('connection', (socket) => {
  console.log('Layout client connected:', socket.id);
  
  socket.on('selectLayout', (layoutId) => {
    socket.join(`layout-${layoutId}`);
    console.log(`Client ${socket.id} joined layout: ${layoutId}`);
  });
  
  socket.on('updateLayout', (data) => {
    const { layoutId, layout } = data;
    if (layouts[layoutId]) {
      layouts[layoutId].layout = layout;
      socket.to(`layout-${layoutId}`).emit('layoutChanged', { layoutId, layout });
    }
  });
  
  socket.on('disconnect', () => {
    console.log('Layout client disconnected:', socket.id);
  });
});

// Start server
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Marine Layout Manager running on http://localhost:${PORT}`);
  console.log('Available layouts:', Object.keys(layouts).join(', '));
  console.log('Features: Grid Layouts, Real-time Updates, Component Management');
});