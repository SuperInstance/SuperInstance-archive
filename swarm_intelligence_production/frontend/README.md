# Swarm Intelligence Frontend

Modern, accessible, and beautiful frontend for the Swarm Intelligence Production Platform.

## Features

- **Visual Swarm Designer**: Drag-and-drop interface using React Flow for designing custom swarms
- **3D Visualization**: Real-time 3D view of swarm agents using Three.js
- **Template Library**: Browse and deploy from 100+ pre-configured swarm templates
- **One-Click Deployment**: Deploy swarms in 30 seconds with QuickDeploy interface
- **Live Metrics Dashboard**: Real-time monitoring with WebSocket updates
- **Natural Language Configuration**: Configure swarms using plain English
- **Mobile Responsive**: Fully responsive design that works on all devices
- **Accessibility**: WCAG 2.1 AA compliant with keyboard navigation and screen reader support

## Technology Stack

- **React 18** with TypeScript
- **Vite** for blazing-fast development
- **Tailwind CSS** for utility-first styling
- **React Flow** for node-based visual editor
- **Three.js** with React Three Fiber for 3D visualization
- **Recharts** for analytics and metrics
- **Framer Motion** for smooth animations
- **Zustand** for state management
- **Axios** for API communication
- **WebSocket** for real-time updates

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on http://localhost:8000 (or configure proxy in vite.config.ts)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development

The development server will start on http://localhost:3000 with:
- Hot Module Replacement (HMR)
- TypeScript type checking
- Tailwind CSS JIT compilation
- API proxy to backend

## Project Structure

```
src/
├── components/          # React components
│   ├── SwarmDesigner.tsx       # Visual flow designer
│   ├── SwarmVisualization.tsx  # 3D agent visualization
│   ├── TemplateLibrary.tsx     # Template browser
│   ├── QuickDeploy.tsx         # Deployment interface
│   ├── LiveMetrics.tsx         # Real-time dashboard
│   └── NaturalLanguageConfig.tsx # NL configuration
├── services/           # API and WebSocket services
│   ├── api.ts         # HTTP API client
│   └── websocket.ts   # WebSocket manager
├── types/             # TypeScript type definitions
│   └── index.ts
├── utils/             # Utility functions
│   ├── cn.ts          # Class name merger
│   └── format.ts      # Formatting helpers
├── styles/            # Global styles
│   └── index.css
├── App.tsx            # Main app component
└── main.tsx           # Application entry point
```

## Key Components

### SwarmDesigner
Visual drag-and-drop interface for designing custom swarms. Supports:
- Adding agents of different types
- Connecting agents to define coordination patterns
- Saving/loading configurations
- Real-time preview

### SwarmVisualization
3D visualization of live swarm activity using Three.js:
- Real-time agent positions and status
- Connection lines showing coordination
- Interactive camera controls
- Status indicators and legend

### TemplateLibrary
Browse and filter 100+ pre-configured templates:
- Search and category filtering
- Complexity-based filtering
- Sort by popularity, rating, cost, or setup time
- One-click deployment

### QuickDeploy
Streamlined deployment interface:
- Configuration in simple form
- Real-time deployment progress
- Cost estimation
- Success confirmation with dashboard link

### LiveMetrics
Real-time monitoring dashboard:
- Key performance metrics
- Performance charts
- Agent status distribution
- Live activity feed
- WebSocket-powered real-time updates

### NaturalLanguageConfig
Configure swarms using natural language:
- Plain English input
- Intent and entity extraction
- Suggested configurations
- Example queries for guidance

## Accessibility Features

This application is built with accessibility as a priority:

- **WCAG 2.1 AA Compliant**
- **Keyboard Navigation**: Full keyboard support for all interactive elements
- **Screen Reader Support**: ARIA labels and semantic HTML
- **Focus Management**: Clear focus indicators
- **Color Contrast**: Meets WCAG contrast requirements
- **Reduced Motion**: Respects prefers-reduced-motion
- **High Contrast**: Supports high contrast mode
- **Skip Links**: Skip to main content functionality

## Mobile Support

Fully responsive design with:
- Mobile-first approach
- Touch-optimized controls
- Adaptive layouts for small screens
- Mobile navigation menu
- Optimized performance for mobile devices

## Performance Optimizations

- Code splitting and lazy loading
- Optimized bundle size with tree shaking
- Image optimization
- Efficient re-rendering with React.memo
- WebSocket connection management
- Virtualized lists for large datasets

## Building for Production

```bash
npm run build
```

Creates an optimized production build in the `dist/` directory with:
- Minified and optimized code
- Source maps for debugging
- Chunked vendor libraries
- Compressed assets
- Cache-optimized file names

## Environment Variables

Create a `.env` file for environment-specific configuration:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Contributing

1. Follow the existing code style
2. Write TypeScript with proper types
3. Ensure accessibility compliance
4. Test on multiple browsers and devices
5. Update documentation as needed

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Android)

## License

Proprietary - Swarm Intelligence Platform

## Support

For issues, questions, or feature requests, please contact the development team.
