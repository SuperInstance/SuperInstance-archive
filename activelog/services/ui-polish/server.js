#!/usr/bin/env node
/**
 * Professional UI Polish Server
 * Serves polished UI components and animations
 */

const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8367;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));
app.use('/dist', express.static('dist'));

// Serve main application
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API Routes for demo data
app.get('/api/demo/cards', (req, res) => {
    res.json({
        cards: [
            { id: 1, title: 'Micro-interactions', description: 'Smooth button animations and feedback' },
            { id: 2, title: 'Loading States', description: 'Skeleton screens and progress indicators' },
            { id: 3, title: 'Gesture Support', description: 'Swipe and touch interactions' },
            { id: 4, title: 'Accessibility', description: 'Keyboard navigation and focus indicators' }
        ]
    });
});

app.get('/api/demo/images', (req, res) => {
    // Simulate progressive image loading
    setTimeout(() => {
        res.json({
            images: [
                { id: 1, url: 'https://picsum.photos/400/300?random=1', alt: 'Sample 1' },
                { id: 2, url: 'https://picsum.photos/400/300?random=2', alt: 'Sample 2' },
                { id: 3, url: 'https://picsum.photos/400/300?random=3', alt: 'Sample 3' }
            ]
        });
    }, req.query.delay || 1000);
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`UI Polish Server running on http://localhost:${PORT}`);
    console.log('Features: Micro-interactions, Animations, Gestures, Accessibility');
});