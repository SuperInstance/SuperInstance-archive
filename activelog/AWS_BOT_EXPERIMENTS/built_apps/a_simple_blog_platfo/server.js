const express = require('express');
const cors = require('cors');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

let posts = [
  { id: 1, title: 'Welcome to your AI-built blog!', content: 'This blog was built automatically by AI. Start adding your own posts!', author: 'AI Builder', date: new Date().toISOString() }
];
let nextId = 2;

app.get('/api/posts', (req, res) => res.json(posts));
app.post('/api/posts', (req, res) => {
  const post = { id: nextId++, ...req.body, date: new Date().toISOString() };
  posts.unshift(post);
  res.json(post);
});

app.listen(PORT, () => console.log(`🚀 Blog running on http://localhost:${PORT}`));
