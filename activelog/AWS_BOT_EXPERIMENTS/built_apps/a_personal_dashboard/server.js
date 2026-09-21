const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static('public'));
app.get('/api/stats',(req,res)=>res.json({
users:Math.floor(Math.random()*1000)+500,
revenue:Math.floor(Math.random()*50000)+10000,
orders:Math.floor(Math.random()*200)+50,
growth:Math.floor(Math.random()*30)+5
}));

app.listen(PORT,()=>console.log(`📊 Dashboard running on http://localhost:${PORT}`));
