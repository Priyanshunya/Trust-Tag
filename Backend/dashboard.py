import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template_string
import threading
import time
import os

app = Flask(__name__)

# --- CONFIGURATION ---
CRED_PATH = "key.json" 
COLLECTION_NAME = "shipments" # The collection we listen to

# --- FIRESTORE CONNECTION ---
db = None
try:
    if os.path.exists(CRED_PATH):
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print(f"✅ Connected to Google Firestore: {COLLECTION_NAME}")
    else:
        print("❌ ERROR: 'key.json' not found. Please download Service Account Key from GCP.")
except Exception as e:
    print(f"⚠️ Connection Error: {e}")

# --- LOCAL CACHE (The Live View) ---
# Structure: { "PACK_001": { "status": "SECURE", "res": 10500, "history": [...] } }
local_db = {}
system_status = "CONNECTING..."

# --- REAL-TIME LISTENER ---
def on_snapshot(col_snapshot, changes, read_time):
    global local_db, system_status
    system_status = "ONLINE (LIVE SYNC)"
    
    for change in changes:
        doc = change.document
        data = doc.to_dict()
        pid = doc.id # The Document ID
        
        # Update our local view with latest cloud data
        if change.type.name in ['ADDED', 'MODIFIED']:
            local_db[pid] = {
                "id": pid,
                "origin": data.get("origin_res", 0),
                "res": data.get("current_res", 0),
                "status": data.get("status", "UNKNOWN"),
                "history": data.get("logs", [])
            }
            print(f"🔥 Cloud Update: {pid} is now {data.get('status')}")

# Background Thread to keep listener alive
def start_cloud_listener():
    if db:
        doc_ref = db.collection(COLLECTION_NAME).document("INIT_CHECK")
        doc_ref.set({"status": "SYSTEM_READY"})
        
        # Attach the listener
        col_ref = db.collection(COLLECTION_NAME)
        col_ref.on_snapshot(on_snapshot)
        
        while True:
            time.sleep(1)

if db:
    t = threading.Thread(target=start_cloud_listener)
    t.daemon = True
    t.start()

# --- DASHBOARD UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Trust-Tag Integrity Cloud</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: 'Segoe UI', monospace; margin: 0; padding: 20px; }
        .nav { display: flex; justify-content: space-between; border-bottom: 2px solid #334155; padding-bottom: 15px; margin-bottom: 30px; }
        .brand { font-size: 24px; font-weight: bold; color: #3b82f6; }
        .stat { font-size: 14px; background: #1e293b; padding: 5px 15px; border-radius: 4px; border: 1px solid #334155; color: #94a3b8; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        
        .head { display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
        .pid { font-size: 24px; font-weight: bold; color: #fff; }
        .meta { font-size: 12px; color: #64748b; }
        
        .badge { padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 14px; }
        .REGISTERED { background: #1d4ed8; color: #bfdbfe; }
        .SECURE { background: #15803d; color: #bbf7d0; border: 1px solid #15803d; }
        .TAMPERED { background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; animation: blink 1s infinite; }
        
        @keyframes blink { 50% { opacity: 0.5; } }

        table { width: 100%; font-size: 13px; border-collapse: collapse; margin-top: 10px; }
        th { text-align: left; color: #64748b; border-bottom: 1px solid #334155; padding-bottom: 5px; }
        td { padding: 6px 0; border-bottom: 1px solid #334155; }
        
        .empty { text-align: center; color: #64748b; margin-top: 50px; }
    </style>
</head>
<body>
    <div class="nav">
        <div class="brand">🛡️ TRUST-TAG CLOUD (GCP)</div>
        <div class="stat">NODE: ASIA-SOUTH1 | {{ sys_status }}</div>
    </div>

    {% if not db %}
        <div class="empty">
            <h2>Waiting for Cloud Stream...</h2>
            <p>Ensure 'key.json' is loaded and Cloud Function is Active.</p>
        </div>
    {% endif %}

    <div class="grid">
        {% for pid, data in db.items() %}
            {% if pid != "INIT_CHECK" %}
            <div class="card">
                <div class="head">
                    <div>
                        <div class="pid">{{ pid }}</div>
                        <div class="meta">ORIGIN: {{ data.origin }} Ω</div>
                    </div>
                    <div class="badge {{ data.status }}">{{ data.status }}</div>
                </div>
                <table>
                    <thead><tr><th>TIME</th><th>SIG</th><th>EVENT</th></tr></thead>
                    <tbody>
                        {% for log in data.history[:5] %}
                        <tr>
                            <td>{{ log.time }}</td>
                            <td>{{ log.res }} Ω</td>
                            <td>{{ log.event }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, db=local_db, sys_status=system_status)

if __name__ == '__main__':
    print("🚀 GCP DASHBOARD ACTIVE: http://localhost:5000")
    app.run(port=5000)
