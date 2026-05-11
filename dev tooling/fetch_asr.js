const fs = require('fs');
const https = require('https');

https.get('https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models', { headers: { 'User-Agent': 'node' } }, (res) => {
    let raw = '';
    res.on('data', chunk => raw += chunk);
    res.on('end', () => {
        const data = JSON.parse(raw);
        const multi = data.assets.filter(a => a.name.includes("multi") || a.name.includes("bi")).map(a => a.name);
        fs.writeFileSync('c:/Users/Keith/Documents/ResKiosk/reskiosk/found_asr.txt', JSON.stringify(multi, null, 2));
    });
});
