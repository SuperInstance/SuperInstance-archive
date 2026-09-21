const express = require('express');
const path = require('path');
const net = require('net');

const app = express();

// Function to find available port
function findAvailablePort(startPort = 3000, maxPort = 3100) {
  return new Promise((resolve, reject) => {
    function tryPort(port) {
      if (port > maxPort) {
        reject(new Error('No available ports found'));
        return;
      }
      
      const server = net.createServer();
      
      server.listen(port, () => {
        server.once('close', () => resolve(port));
        server.close();
      });
      
      server.on('error', () => {
        tryPort(port + 1);
      });
    }
    
    tryPort(startPort);
  });
}

app.use(express.static('public'));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server with automatic port detection
async function startServer() {
  try {
    const PORT = process.env.PORT || await findAvailablePort(3000);
    
    app.listen(PORT, () => {
      console.log(`🚀 AI-Built App running on http://localhost:${PORT}`);
      console.log(`💡 Automatically found available port: ${PORT}`);
    });
  } catch (error) {
    console.error('❌ Could not find available port:', error.message);
    process.exit(1);
  }
}

startServer();
