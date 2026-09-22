import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass
class LogMessage:
    timestamp: str
    level: str
    message: str

@dataclass
class Log:
    successful: bool = False
    logs: list[LogMessage] = field(default_factory=list)

    def add_log(self, log_message: LogMessage) -> None:
        self.logs.append(log_message)

    def mark_successful(self) -> None:
        self.successful = True

_logs: dict[str, Log] = {}
_logs_lock = threading.Lock()

def _current_timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def add_logs(request_id: str, level: str, message: str) -> None:
    log_message = LogMessage(_current_timestamp(), level, message)
    with (_logs_lock):
        _logs.setdefault(request_id, Log()).add_log(log_message)

def add_info_log(request_id: str, message: str) -> None:
    add_logs(request_id, "INFO", message)

def add_error_log(request_id: str, message: str) -> None:
    add_logs(request_id, "ERROR", message)

def mark_successful(request_id: str) -> None:
    with _logs_lock:
        entry = _logs.get(request_id, None)
        if entry is not None:
            entry.mark_successful()

def remove_logs(request_id: str) -> None:
    with _logs_lock:
        _logs.pop(request_id, None)

def get_logs(request_id: str):
    with _logs_lock:
        entry = _logs.get(request_id, None)
        if entry is None:
            return None
        return {"id": request_id, "successful": entry.successful, "logs": list(entry.logs) }





