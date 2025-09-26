"""
client_test_safe.py
Cliente de prueba SEGURO para pruebas controladas en tu infraestructura.

Uso ejemplo:
python client_test_safe.py https://midominio.private --concurrency 20 --duration 90 --path / --ramp-up 10 --delay 0 --out results.csv --confirm-own
"""
import requests
import threading
import time
import argparse
import csv
import sys
from queue import Queue
from datetime import datetime
from threading import Lock

# Parámetros máximos razonables por seguridad (ajusta con precaución)
MAX_CONCURRENCY_SAFE = 200

parser = argparse.ArgumentParser(description="Cliente de prueba controlada (SEGURO)")
parser.add_argument("baseurl", help="URL objetivo (debe ser tuya). Ej: https://midominio.private")
parser.add_argument("--concurrency", type=int, default=10, help="Hilos concurrentes (default 10)")
parser.add_argument("--duration", type=int, default=90, help="Duración total en segundos (default 90)")
parser.add_argument("--path", default="/", help="Ruta a solicitar (default /)")
parser.add_argument("--timeout", type=float, default=5.0, help="Timeout por request (s)")
parser.add_argument("--ramp-up", type=int, default=0, help="Segundos para aumentar hilos gradualmente desde 1 hasta concurrency (default 0)")
parser.add_argument("--delay", type=float, default=0.0, help="Delay (s) entre requests por hilo (default 0.0). Usa para reducir intensidad.")
parser.add_argument("--out", default=None, help="Archivo CSV de salida para registros (opcional)")
parser.add_argument("--confirm-own", action="store_true", help="Confirmas que eres propietario/administrador del objetivo (OBLIGATORIO para ejecutar)")

args = parser.parse_args()

# Seguridad básica: requerir confirmación explícita
if not args.confirm_own:
    print("ERROR: Debes pasar la opción --confirm-own para confirmar que el objetivo es tuyo.")
    print("Ejemplo:\n  python client_test_safe.py https://midominio.private --confirm-own")
    sys.exit(1)

base = args.baseurl.rstrip("/")
url = base + args.path
duration = args.duration
concurrency = max(1, args.concurrency)
timeout = args.timeout
ramp_up = max(0, args.ramp_up)
delay_between_requests = max(0.0, args.delay)
out_csv = args.out

# Límite máximo para evitar abusos accidentales
if concurrency > MAX_CONCURRENCY_SAFE:
    print(f"Advertencia: concurrency solicitado ({concurrency}) excede el máximo seguro ({MAX_CONCURRENCY_SAFE}).")
    print("Modifica concurrency con precaución o ajusta MAX_CONCURRENCY_SAFE en el script si entiendes los riesgos.")
    sys.exit(1)

print("="*60)
print("CLIENTE DE PRUEBA SEGURO")
print(f"Objetivo: {url}")
print(f"Duración (s): {duration}")
print(f"Hilos solicitados: {concurrency}")
print(f"Timeout por request (s): {timeout}")
print(f"Ramp-up (s): {ramp_up}")
print(f"Delay por petición (s): {delay_between_requests}")
if out_csv:
    print(f"Salida CSV: {out_csv}")
print("CONFIRMACIÓN: Ejecutando contra infraestructura propia. No usar contra terceros.")
print("="*60)

stop_time = time.time() + duration
q = Queue()
stats_lock = Lock()
stats = {
    "sent": 0,
    "success": 0,
    "errors": 0,
    "codes": {},
    "records": []
}

def make_request(thread_id):
    global stats
    while time.time() < stop_time:
        ts = datetime.utcnow().isoformat() + "Z"
        try:
            r = requests.get(url, timeout=timeout)
            status = r.status_code
            with stats_lock:
                stats["sent"] += 1
                stats["codes"].setdefault(status, 0)
                stats["codes"][status] += 1
                if status < 400:
                    stats["success"] += 1
                if out_csv:
                    stats["records"].append((ts, thread_id, status, len(r.content)))
        except Exception as e:
            with stats_lock:
                stats["sent"] += 1
                stats["errors"] += 1
                if out_csv:
                    stats["records"].append((ts, thread_id, "ERR", str(e)))
        if delay_between_requests > 0:
            time.sleep(delay_between_requests)
    q.put(True)

threads = []
# ramp-up: incrementar hilos gradualmente
if ramp_up > 0 and concurrency > 1:
    interval = ramp_up / max(1, concurrency-1)
else:
    interval = 0

for i in range(concurrency):
    t = threading.Thread(target=make_request, args=(i,), daemon=True)
    threads.append(t)
    t.start()
    if interval > 0:
        time.sleep(interval)

# esperar a que todos terminen
for _ in threads:
    q.get()

# Informe final
print("\n=== INFORME FINAL ===")
print(f"URL objetivo: {url}")
print(f"Duración real (s): {duration}")
print(f"Peticiones enviadas: {stats['sent']}")
print(f"Respuestas exitosas (<400): {stats['success']}")
print(f"Errores/Timeouts: {stats['errors']}")
print("Códigos HTTP recibidos:")
for code, n in sorted(stats["codes"].items()):
    print(f"  {code}: {n}")

if out_csv:
    try:
        with open(out_csv, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_utc","thread_id","status_or_error","bytes_or_error"])
            for rec in stats["records"]:
                writer.writerow(rec)
        print(f"Registros guardados en {out_csv}")
    except Exception as e:
        print("No se pudo escribir CSV:", e)

print("FIN.")
