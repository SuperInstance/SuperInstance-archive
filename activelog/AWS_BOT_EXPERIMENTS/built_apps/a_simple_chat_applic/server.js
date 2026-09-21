const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static('public'));
let messages = [{user:'AI',text:'Welcome to your AI-built chat app!',time:new Date().toISOString()}];

app.use(express.json());
app.get('/api/messages',(req,res)=>res.json(messages));
app.post('/api/messages',(req,res)=>{
const msg={...req.body,time:new Date().toISOString()};messages.push(msg);res.json(msg);});

app.listen(PORT,()=>console.log(`💬 Chat app running on http://localhost:${PORT}`));
