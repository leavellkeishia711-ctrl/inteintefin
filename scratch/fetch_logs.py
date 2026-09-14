import urllib.request
import json
import sys
import zipfile
import io

repo = "leavellkeishia711-ctrl/inteintefin"
run_id = "31215961766"

url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs"
req = urllib.request.Request(url)
# No auth token needed for public repo logs usually, but let's see if it redirects
try:
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            for filename in z.namelist():
                if "test/5_Install dependencies.txt" in filename:
                    print(f"--- {filename} ---")
                    print(z.read(filename).decode('utf-8')[-2000:])
                    break
except Exception as e:
    print(e)
