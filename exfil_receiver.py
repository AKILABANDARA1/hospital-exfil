import os
import time
import json
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from threading import Lock

app = FastAPI()

UPLOAD_DIR = "/data/uploads"
LOG_FILE = "/data/received_files.jsonl"

os.makedirs(UPLOAD_DIR, exist_ok=True)

received_files = {}
total_bytes = 0
lock = Lock()

def load_logs():
    global total_bytes
    if not os.path.exists(LOG_FILE):
        return
    with open(LOG_FILE, "r") as f:
        for line in f:
            entry = json.loads(line)
            filename = entry["filename"]
            received_files[filename] = {
                "size": entry["size"],
                "timestamp": entry["timestamp"]
            }
            total_bytes += entry["size"]

def append_log(entry):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

@app.on_event("startup")
def startup_event():
    load_logs()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global total_bytes
    filename = file.filename
    content = await file.read()

    filepath = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as e:
        return {"detail": f"Failed to save file: {str(e)}"}

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"filename": filename, "size": len(content), "timestamp": timestamp}

    with lock:
        received_files[filename] = {"size": len(content), "timestamp": timestamp}
        total_bytes += len(content)
        append_log(entry)

    return {"status": "file received", "filename": filename, "size": len(content)}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    with lock:
        files_info = "".join(
            f"<tr><td>{fname}</td><td>{data['size']} bytes</td><td>{data['timestamp']}</td></tr>"
            for fname, data in received_files.items()
        )
        last_upload = max((data["timestamp"] for data in received_files.values()), default="N/A")
        total_files = len(received_files)
        total_data_mb = total_bytes / (1024 * 1024)

    html = f"""
    <html>
    <head>
      <title>Exfiltration Receiver Dashboard</title>
      <meta http-equiv="refresh" content="10" />
      <style>
        body {{
          background: #101a3a;
          color: #a0c8ff;
          font-family: 'Roboto Mono', monospace;
          margin: 2rem auto;
          max-width: 700px;
          padding: 1rem 2rem;
          border-radius: 10px;
          box-shadow: 0 0 15px #3a5aff;
        }}
        h1 {{
          color: #4a7eff;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          margin-top: 1rem;
        }}
        th, td {{
          padding: 0.5rem 0.75rem;
          border-bottom: 1px solid #3a5aff88;
          text-align: left;
        }}
        th {{
          background: #27408b;
        }}
        caption {{
          caption-side: bottom;
          padding-top: 0.5rem;
          font-size: 0.9rem;
          color: #789fff;
        }}
      </style>
    </head>
    <body>
      <h1>Exfiltration Receiver Dashboard</h1>
      <p>Total files received: <strong>{total_files}</strong></p>
      <p>Total data received: <strong>{total_data_mb:.2f} MB</strong></p>
      <p>Last file uploaded at: <strong>{last_upload}</strong></p>
      <table>
        <thead><tr><th>Filename</th><th>Size</th><th>Timestamp</th></tr></thead>
        <tbody>
          {files_info}
        </tbody>
      </table>
      <p>Page auto-refreshes every 10 seconds.</p>
    </body>
    </html>
    """
    return html
