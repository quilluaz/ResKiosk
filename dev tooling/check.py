import urllib.request
import tarfile
import io

url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-2023-06-26.tar.bz2"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as r:
    with tarfile.open(fileobj=io.BytesIO(r.read()), mode='r:bz2') as t:
        for name in t.getnames():
            print(name)
