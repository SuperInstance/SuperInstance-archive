const express = require('express');
const app = express();

// Intentionally broken - no port detection
app.listen(3000, () => {
  console.log('App running on port 3000');
});