# server_local.py
# Variante simple del servidor que registra IPs y controla con ventana deslizante

from flask import Flask, request, jsonify
import time
from collections import defaultdict

app = Flask(__name__)

WINDOW = 10
LIMIT = 50
hits = defaultdict(list)

def prune_and_count(ip):
    now = time.time()
    window_start = now - WINDOW
    lst = hits[ip]
    while lst and lst[0] < window_start:
        lst.pop(0)
    return len(lst)

@app.route('/')
def index():
    ip = request.remote_addr
    now = time.time()
    count = prune_and_count(ip)
    if count >= LIMIT:
        return jsonify({"error":"rate limit exceeded"}), 429
    hits[ip].append(now)
    return jsonify({"ok":True, "your_ip": ip, "requests_in_window": count+1})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
