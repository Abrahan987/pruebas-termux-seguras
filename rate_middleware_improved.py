"""
rate_middleware_improved.py
Middleware Flask mejorado para pruebas locales.
Registra accesos y aplica limitación simple en memoria.
"""

from time import time
from collections import defaultdict
from flask import Flask, request, jsonify
import csv
from datetime import datetime
import threading
import os

WINDOW = int(os.getenv("LIMIT_WINDOW", "10"))   # segundos
LIMIT = int(os.getenv("LIMIT_COUNT", "50"))     # peticiones por ventana
LOG_FILE = "access_log.csv"

app = Flask(__name__)
hits = defaultdict(list)
lock = threading.Lock()

# inicializar archivo de log si no existe
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc","remote_addr","path","status"])

def prune_and_count(ip):
    now = time()
    start = now - WINDOW
    lst = hits[ip]
    # eliminar antiguos
    while lst and lst[0] < start:
        lst.pop(0)
    return len(lst)

def log_access(ip, path, status):
    ts = datetime.utcnow().isoformat() + "Z"
    line = f"{ts} {ip} {path} {status}"
    print(line)
    try:
        with lock:
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([ts, ip, path, status])
    except Exception as e:
        print("Error escribiendo log:", e)

@app.before_request
def check_rate():
    ip = request.remote_addr or "unknown"
    count = prune_and_count(ip)
    if count >= LIMIT:
        log_access(ip, request.path, 429)
        return jsonify({"error":"too many requests","requests_in_window":count}), 429
    hits[ip].append(time())
    # allow request to continue

@app.route("/")
def index():
    ip = request.remote_addr or "unknown"
    log_access(ip, "/", 200)
    return jsonify({"ok": True, "your_ip": ip})

@app.route("/health")
def health():
    return jsonify({"status":"ok","time_window":WINDOW,"limit":LIMIT})

@app.route("/metrics")
def metrics():
    unique_ips = len(hits)
    return jsonify({
        "unique_ips_tracked": unique_ips,
        "window_seconds": WINDOW,
        "limit": LIMIT
    })

if __name__ == "__main__":
    print("Servidor de pruebas iniciando en http://0.0.0.0:8000")
    print(f"Window={WINDOW}s Limit={LIMIT} req/window")
    app.run(host="0.0.0.0", port=8000)
