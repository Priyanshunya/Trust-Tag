import functions_framework
from google.cloud import firestore
from datetime import datetime
import json
import traceback

# This prevents memory leaks and startup crashes
try:
    db = firestore.Client()
    print("✅ Firestore Connection Established")
except Exception as e:
    print(f"❌ Firestore Init Error: {e}")
    db = None

COLLECTION = 'scan_logs'

@functions_framework.http
def ingest(request):
    """
    Handles telemetry from the ESP32 Scanner.
    Entry Point in GCP Console must be set to: ingest
    """
    try:
        # 1. Parse incoming JSON
        data = request.get_json(silent=True)
        if not data:
            print("⚠️ No JSON payload received")
            return (json.dumps({"status": "NO_PAYLOAD"}), 200, {'Content-Type': 'application/json'})
        
        # 2. Extract Data & Force Types
        # pid is the tracking ID
        pid = str(data.get('id', 'UNKNOWN'))
        
       
        try:
            res_val = data.get('res', 0)
            res = int(float(res_val)) 
        except (ValueError, TypeError):
            res = 0
            
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📥 Received from {pid}: {res} Ω")

        if db is None:
            return (json.dumps({"status": "DB_OFFLINE"}), 200, {'Content-Type': 'application/json'})

        # 3. Firestore Logic
        doc_ref = db.collection(COLLECTION).document(pid)
        doc = doc_ref.get()

        server_verdict = "UNKNOWN"

        if not doc.exists:
            # REGISTER: New package entry
            doc_ref.set({
                "pkg_id": pid,
                "origin_res": res,
                "current_res": res,
                "status": "REGISTERED",
                "last_seen": now,
                "logs": [{
                    "time": now, "res": res, "event": "REGISTERED"
                }]
            })
            server_verdict = "REGISTERED"
        else:
            # VERIFY: Check against baseline
            existing_data = doc.to_dict()
            
            try:
                # Force baseline to int to prevent abs() crash if DB has strings
                origin_val = existing_data.get('origin_res', res)
                origin = int(float(origin_val))
            except:
                origin = res
            
            diff = abs(res - origin)
            
            # Logic: Open circuit (>60k) or large change (>3k)
            if res > 60000:
                server_verdict = "TAMPERED" 
            elif diff > 3000:
                server_verdict = "TAMPERED"
            else:
                server_verdict = "SECURE"
            
            
            doc_ref.update({
                "current_res": res,
                "status": server_verdict,
                "last_seen": now,
                "logs": firestore.ArrayUnion([{
                    "time": now, "res": res, "event": server_verdict
                }])
            })

        print(f"✅ Verdict for {pid}: {server_verdict}")
        
        # 4. Return Success JSON
        response_body = json.dumps({"status": server_verdict})
        return (response_body, 200, {'Content-Type': 'application/json'})

    except Exception as e:
        
        print(f"🔥 SERVER ERROR: {str(e)}")
        print(traceback.format_exc())
        
        error_resp = json.dumps({"status": "SERVER_ERR", "msg": str(e)})
        return (error_resp, 200, {'Content-Type': 'application/json'})
