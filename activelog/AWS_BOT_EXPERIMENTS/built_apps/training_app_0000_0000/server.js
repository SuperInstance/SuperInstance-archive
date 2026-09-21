const express = require('express');
const path = require('path');
const net = require('net');

const app = express();

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

async function startServer() {
  try {
    const PORT = process.env.PORT || await findAvailablePort(3000);
    app.listen(PORT, () => {
      console.log(`🎮 Tic Tac Toe Game running on http://localhost:${PORT}`);
      console.log(`💡 Port: ${PORT}`);
    });
  } catch (error) {
    console.error('❌ Could not start server:', error.message);
    process.exit(1);
  }
}

startServer();
