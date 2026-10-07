import urllib.request
import zipfile
import sys
import os

url = "https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/artifacts/11269820365/zip"

try:
    req = urllib.request.Request(url)
    # GitHub requires authorization to download artifacts via API
    # Since I don't have a token, this will probably fail with 401 Unauthorized
    with urllib.request.urlopen(req) as response:
        with open('pytest-results.zip', 'wb') as out_file:
            out_file.write(response.read())
            
    with zipfile.ZipFile('pytest-results.zip', 'r') as zip_ref:
        zip_ref.extractall('artifact_dir')
        
    print("Downloaded and extracted successfully.")
except Exception as e:
    print(f"Failed to download/extract: {e}")
