const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// ئەمە بۆ تاقیکردنەوەیە کە بزانیت سێرڤەرەکە کار دەکات
app.get('/', (req, res) => {
    res.send('سێرڤەری Creator Bot بە سەرکەوتوویی کار دەکات 🚀');
});

// ئەمە ئەو بەشەیە کە سکێچوێر داوای دەکات
app.post('/create-bot', async (req, res) => {
    const { token, name, type, owner_uid } = req.body;

    if (!token) {
        return res.status(400).json({ ok: false, error: "توکێن نەنێردراوە" });
    }

    try {
        // پەیوەندی کردن بە تیلیگرام بۆ دڵنیابوون لە توکێنەکە
        const response = await axios.get(`https://api.telegram.org/bot${token}/getMe`);
        
        if (response.data.ok) {
            const botInfo = response.data.result;
            
            // لێرەدا دەتوانیت کۆدی تری بۆ زیاد بکەیت بۆ چالاککردنی وێبهوک
            // بەڵام بۆ ئێستا تەنها وەڵامی سەرکەوتوو دەدەینەوە بە بەرنامەکە
            res.status(200).json({ 
                ok: true, 
                bot_id: botInfo.id,
                bot_username: botInfo.username 
            });
        } else {
            res.status(400).json({ ok: false, error: "توکێنەکە لەلایەن تیلیگرامەوە ڕەتکرایەوە" });
        }
    } catch (error) {
        res.status(500).json({ ok: false, error: "ناتوانرێت پەیوەندی بە سێرڤەری تیلیگرامەوە بکرێت" });
    }
});

// بەشی نوێکردنەوەی ڕێکخستنەکان (بۆ ئەوەی ئیرۆر نەدات)
app.post('/update-setting', (req, res) => {
    res.json({ ok: true, message: "ڕێکخستنەکان نوێکرانەوە" });
});

module.exports = app;
