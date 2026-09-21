console.log('Starting server debug...');

try {
  console.log('1. Loading express...');
  const express = require('express');
  
  console.log('2. Loading logger...');
  const logger = require('./src/utils/logger');
  
  console.log('3. Loading basic modules...');
  const cors = require('cors');
  const helmet = require('helmet');
  
  console.log('4. Creating express app...');
  const app = express();
  
  console.log('5. Loading routes...');
  const worldRoutes = require('./src/routes/world');
  const storyRoutes = require('./src/routes/story');
  
  console.log('6. Setting up basic middleware...');
  app.use(cors());
  app.use(express.json());
  
  console.log('7. Adding health route...');
  app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
  });
  
  console.log('8. Starting server...');
  const PORT = 8407;
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
  
} catch (error) {
  console.error('Error during startup:', error);
  console.error('Stack:', error.stack);
}