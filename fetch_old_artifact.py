import urllib.request
import json
import zipfile
import io

url = 'https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs/37111089844/artifacts'
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        for a in data.get('artifacts', []):
            print(f"Found artifact: {a['name']} ({a['id']})")
            if a['name'] == 'pytest-results':
                dl_url = a['archive_download_url']
                print(f"Downloading {dl_url}...")
                req_dl = urllib.request.Request(dl_url)
                with urllib.request.urlopen(req_dl) as res_dl:
                    with zipfile.ZipFile(io.BytesIO(res_dl.read())) as z:
                        z.extractall('artifact_old')
                        print('Extracted old artifact')
except Exception as e:
    print('Error:', e)
