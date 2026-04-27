const fs = require('fs');
const https = require('https');

https.get('https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models', { headers: { 'User-Agent': 'node' } }, (res) => {
    let raw = '';
    res.on('data', chunk => raw += chunk);
    res.on('end', () => {
        const data = JSON.parse(raw);
        console.log("ASR MULTI models:");
        data.assets.filter(a => a.name.includes("multilingual")).forEach(a => console.log(a.name));
    });
});

https.get('https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/tts-models', { headers: { 'User-Agent': 'node' } }, (res) => {
    let raw = '';
    res.on('data', chunk => raw += chunk);
    res.on('end', () => {
        const data = JSON.parse(raw);
        console.log("TTS LESSAC models:");
        data.assets.filter(a => a.name.includes("lessac")).forEach(a => console.log(a.name));
    });
});
