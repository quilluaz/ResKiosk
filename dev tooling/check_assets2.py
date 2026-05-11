import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models", headers={'User-Agent': 'Mozilla/5.0'})
try:
    r = urllib.request.urlopen(req, context=ctx)
    data = json.loads(r.read())
    for a in data["assets"]:
        if "multilingual" in a["name"]:
            print("ASR: " + a["name"])
except Exception as e:
    print("ASR error", e)

req2 = urllib.request.Request("https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/tts-models", headers={'User-Agent': 'Mozilla/5.0'})
try:
    r2 = urllib.request.urlopen(req2, context=ctx)
    data2 = json.loads(r2.read())
    for a in data2["assets"]:
        if "lessac" in a["name"]:
            print("TTS: " + a["name"])
except Exception as e:
    print("TTS error", e)
