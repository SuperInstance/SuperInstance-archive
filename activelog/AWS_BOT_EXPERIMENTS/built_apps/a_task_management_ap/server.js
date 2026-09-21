const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// In-memory storage for demo
let tasks = [
  { id: 1, title: 'Welcome to your task manager', completed: false, priority: 'medium' },
  { id: 2, title: 'Add your first real task', completed: false, priority: 'high' }
];
let nextId = 3;

// API Routes
app.get('/api/tasks', (req, res) => {
  res.json(tasks);
});

app.post('/api/tasks', (req, res) => {
  const task = {
    id: nextId++,
    title: req.body.title,
    completed: false,
    priority: req.body.priority || 'medium'
  };
  tasks.push(task);
  res.json(task);
});

app.put('/api/tasks/:id', (req, res) => {
  const task = tasks.find(t => t.id === parseInt(req.params.id));
  if (task) {
    Object.assign(task, req.body);
    res.json(task);
  } else {
    res.status(404).json({ error: 'Task not found' });
  }
});

app.delete('/api/tasks/:id', (req, res) => {
  tasks = tasks.filter(t => t.id !== parseInt(req.params.id));
  res.json({ success: true });
});

app.listen(PORT, () => {
  console.log(`🚀 Task Manager running on http://localhost:${PORT}`);
});
