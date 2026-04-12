const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// Main endpoint
app.get('/', (req, res) => {
    res.status(200).send('Creator Bot Server is running 🚀');
});

// Endpoint that Sketchware is ACTUALLY calling
app.post('/api/register_bot', async (req, res) => {
    const { token } = req.body;

    if (!token) {
        return res.status(400).json({ ok: false, error: "توکێن نەنێردراوە" });
    }

    try {
        const response = await axios.get(`https://api.telegram.org/bot${token}/getMe`);
        
        if (response.data.ok) {
            const botInfo = response.data.result;
            return res.status(200).json({ 
                ok: true, 
                bot_id: botInfo.id
            });
        } else {
            return res.status(400).json({ ok: false, error: "توکێنەکە لەلایەن تیلیگرامەوە ڕەتکرایەوە" });
        }
    } catch (e) {
        return res.status(500).json({ ok: false, error: "ناتوانرێت پەیوەندی بە سێرڤەری تیلیگرامەوە بکرێت" });
    }
});

// Dummy endpoints to prevent errors
app.post('/api/delete_bot', (req, res) => res.json({ ok: true }));
app.post('/api/update_setting', (req, res) => res.json({ ok: true }));
app.post('/api/broadcast', (req, res) => res.json({ ok: true }));
app.get('/api/stats', (req, res) => res.json({ ok: true, users: 0, bots: 0 }));

module.exports = app;
