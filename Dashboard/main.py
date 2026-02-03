from flask import Flask, render_template_string, request
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime

# Initialize Firebase (GCP Default Credentials)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()
COLLECTION = 'scan_logs' 

app = Flask(__name__)

# Cyberpunk-Industrial UI Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trust-Tag Command Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="2">
    <style>
        body { font-family: 'Space Grotesk', sans-serif; background-color: #020617; color: #e2e8f0; background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #020617 70%); }
        .glass { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .mono { font-family: monospace; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .blink { animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0; } }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <header class="flex justify-between items-center mb-8">
        <div class="flex items-center gap-3">
            <div class="h-10 w-1 bg-blue-500 rounded-full"></div>
            <div>
                <h1 class="text-2xl font-bold tracking-tight text-white leading-none">TRUST<span class="text-blue-500">TAG</span></h1>
                <p class="text-[10px] text-slate-500 tracking-widest uppercase font-semibold">Logistics Integrity Protocol</p>
            </div>
        </div>
        <div class="flex items-center gap-4">
             <div class="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
                <span class="status-dot bg-green-500 blink"></span>
                <span class="text-xs font-mono text-green-500 uppercase">System Online</span>
            </div>
            <button onclick="if(confirm('Clear all logs?')) fetch('/reset', {method:'POST'}).then(()=>location.reload())" 
                    class="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 px-4 py-2 rounded-lg text-xs font-bold tracking-wide transition-all">
                RESET SYSTEM
            </button>
        </div>
    </header>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="glass p-5 rounded-xl border-t-2 border-blue-500">
            <div class="text-slate-400 text-xs font-bold uppercase mb-1">Total Packages</div>
            <div class="text-3xl font-bold text-white">{{ total }}</div>
        </div>
        <div class="glass p-5 rounded-xl border-t-2 border-green-500">
            <div class="text-slate-400 text-xs font-bold uppercase mb-1">Secure</div>
            <div class="text-3xl font-bold text-green-400">{{ secure }}</div>
        </div>
        <div class="glass p-5 rounded-xl border-t-2 border-red-500">
            <div class="text-slate-400 text-xs font-bold uppercase mb-1">Breached</div>
            <div class="text-3xl font-bold text-red-500">{{ tampered }}</div>
        </div>
        <div class="glass p-5 rounded-xl border-t-2 border-indigo-500">
             <div class="text-slate-400 text-xs font-bold uppercase mb-1">Integrity Rate</div>
             <div class="text-3xl font-bold text-indigo-400">
                {% if total > 0 %}{{ ((secure / total) * 100)|round|int }}%{% else %}100%{% endif %}
             </div>
        </div>
    </div>

    <div class="glass rounded-2xl overflow-hidden min-h-[500px]">
        <div class="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {% for pkg in logs %}
            <div class="relative bg-slate-900/50 rounded-xl p-0 border {{ 'border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.15)]' if 'TAMPERED' in pkg.status else 'border-slate-800' }} transition-all">
                <div class="p-4 border-b border-slate-800 flex justify-between items-start">
                    <div>
                        <div class="text-[10px] text-slate-500 font-bold mb-1 uppercase">TRACKING ID</div>
                        <div class="text-lg font-bold text-white mono">{{ pkg.pkg_id }}</div>
                    </div>
                    <div class="px-2 py-1 rounded text-[10px] font-bold uppercase border {{ 'bg-red-500/10 text-red-400 border-red-500/20' if 'TAMPERED' in pkg.status else 'bg-green-500/10 text-green-400 border-green-500/20' }}">
                        {{ pkg.status }}
                    </div>
                </div>
                <div class="p-4 space-y-2">
                    <div class="flex justify-between text-sm"><span class="text-slate-500">Current Res:</span><span class="mono font-bold">{{ pkg.current_res }} Ω</span></div>
                    <div class="flex justify-between text-sm"><span class="text-slate-500">Baseline:</span><span class="mono text-slate-400">{{ pkg.origin }} Ω</span></div>
                    <div class="mt-3 pt-3 border-t border-slate-800 text-[10px] text-slate-500 text-right uppercase">Last Sync: {{ pkg.last_seen }}</div>
                </div>
            </div>
            {% endfor %}
            {% if not logs %}
            <div class="col-span-full py-20 text-center text-slate-600 font-mono tracking-widest animate-pulse uppercase">Waiting for Telemetry...</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    docs = db.collection(COLLECTION).order_by('last_seen', direction=firestore.Query.DESCENDING).limit(15).stream()
    logs = []
    t_cnt, s_cnt = 0, 0
    for doc in docs:
        d = doc.to_dict()
        stat = d.get('status', 'UNKNOWN')
        if 'TAMPERED' in stat: t_cnt += 1
        elif 'SECURE' in stat: s_cnt += 1
        d['pkg_id'] = doc.id
        d['origin'] = d.get('origin_res', 0)
        logs.append(d)
    return render_template_string(HTML_TEMPLATE, logs=logs, total=len(logs), secure=s_cnt, tampered=t_cnt)

@app.route('/reset', methods=['POST'])
def reset():
    docs = db.collection(COLLECTION).stream()
    for doc in docs: doc.reference.delete()
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))