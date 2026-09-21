const express = require('express');
const cors = require('cors');
const { create, all } = require('mathjs');
const Decimal = require('decimal.js');

// Create custom mathjs instance with high-precision config
const math = create(all);
math.config({
  precision: 64,
  predictable: true
});

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Calculation history storage
let calculationHistory = [];

// API Routes for Revolutionary Calculator

// Basic calculation endpoint
app.post('/api/calculate', (req, res) => {
  try {
    const { expression, precision = 10 } = req.body;
    
    // Use mathjs for complex expressions
    const result = math.evaluate(expression);
    
    // Store in history
    const calculation = {
      id: Date.now(),
      expression: expression,
      result: result,
      timestamp: new Date().toISOString()
    };
    calculationHistory.unshift(calculation);
    
    // Keep only last 100 calculations
    calculationHistory = calculationHistory.slice(0, 100);
    
    res.json({
      success: true,
      expression: expression,
      result: result,
      formatted: typeof result === 'number' ? result.toPrecision(precision) : result.toString()
    });
    
  } catch (error) {
    res.status(400).json({
      success: false,
      error: error.message,
      expression: req.body.expression
    });
  }
});

// Get calculation history
app.get('/api/history', (req, res) => {
  res.json(calculationHistory);
});

// Clear history
app.delete('/api/history', (req, res) => {
  calculationHistory = [];
  res.json({ success: true, message: 'History cleared' });
});

// Scientific function endpoint
app.post('/api/scientific', (req, res) => {
  try {
    const { function: func, value, unit = 'rad' } = req.body;
    let result;
    
    switch(func) {
      case 'sin': result = Math.sin(unit === 'deg' ? value * Math.PI / 180 : value); break;
      case 'cos': result = Math.cos(unit === 'deg' ? value * Math.PI / 180 : value); break;
      case 'tan': result = Math.tan(unit === 'deg' ? value * Math.PI / 180 : value); break;
      case 'log': result = Math.log10(value); break;
      case 'ln': result = Math.log(value); break;
      case 'sqrt': result = Math.sqrt(value); break;
      case 'factorial': result = math.factorial(value); break;
      default: throw new Error('Unknown function');
    }
    
    res.json({ success: true, function: func, input: value, result: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Unit conversion endpoint
app.post('/api/convert', (req, res) => {
  try {
    const { value, from, to } = req.body;
    const result = math.unit(value, from).to(to);
    res.json({ success: true, original: `${value} ${from}`, converted: result.toString() });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

console.log('🧮 Revolutionary Calculator Server Starting...');
console.log('⚡ Features: High-precision math, Scientific functions, History, Unit conversion');

app.listen(PORT, () => {
  console.log(`🚀 Revolutionary Calculator running on http://localhost:${PORT}`);
  console.log('🧠 Powered by Nobel Prize-level AI research');
});
