const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// وەڵامدانەوەی لاپەڕەی سەرەکی
app.get('/', (req, res) => {
    res.status(200).send('Server is Running! 🚀');
});

// ئەم بەشە وەڵامی هەموو جۆرە داواکارییەک دەداتەوە (دروستکردنی بۆت)
app.all('/create-bot', async (req, res) => {
    // ئەگەر بەرنامەکە زانیاری ناردبوو
    const data = req.body || {};
    const token = data.token;

    if (!token) {
        return res.status(400).json({ ok: false, error: "Token required" });
    }

    try {
        const response = await axios.get(`https://api.telegram.org/bot${token}/getMe`);
        if (response.data.ok) {
            return res.status(200).json({ 
                ok: true, 
                bot_id: response.data.result.id,
                username: response.data.result.username 
            });
        }
        res.status(400).json({ ok: false, error: "Invalid Token" });
    } catch (e) {
        res.status(500).json({ ok: false, error: "Telegram API Error" });
    }
});

// بۆ ئەوەی ئیرۆری 404 نەدات لە هیچ لینکێکدا
app.use((req, res) => {
    res.status(200).json({ ok: true, message: "Server is alive" });
});

module.exports = app;
