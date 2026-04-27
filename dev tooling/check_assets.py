import urllib.request
import json
try:
    r = urllib.request.urlopen("https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models")
    data = json.loads(r.read())
    for a in data["assets"]:
        if "multilingual" in a["name"]:
            print("ASR: " + a["name"])
except Exception as e:
    print("ASR error", e)

try:
    r2 = urllib.request.urlopen("https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/tts-models")
    data2 = json.loads(r2.read())
    for a in data2["assets"]:
        if "lessac" in a["name"]:
            print("TTS: " + a["name"])
except Exception as e:
    print("TTS error", e)
