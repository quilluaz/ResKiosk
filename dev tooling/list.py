import os
import subprocess

out = subprocess.check_output(["adb", "shell", "ls", "-la", "/data/user/0/com.reskiosk/files/sherpa-models/sherpa-onnx-streaming-zipformer-en-2023-06-26"])
print(out.decode('utf-8'))
