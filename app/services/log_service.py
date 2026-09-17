import threading
import time
from collections import defaultdict

logs: dict[str, list[str]] = defaultdict(list)
_logs_lock = threading.Lock()

def add_logs(request_id: str, message: str) -> None:
    entry = f"{time.strftime('%H:%M:%S')} - {message}"
    with _logs_lock:
        logs[request_id].append(entry)

def remove_logs(request_id: str) -> None:
    with _logs_lock:
        logs.pop(request_id, None)

def get_logs(request_id: str):
    with _logs_lock:
        return list(logs.get(request_id, []))




