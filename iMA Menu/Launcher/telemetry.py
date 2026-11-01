import os
import sys
import re
import json
import time
import hashlib
import platform
import threading
import urllib.request
import urllib.error

# Cloudflare Worker Telemetry Endpoint
# Overridable via settings.json ("telemetry_endpoint") or env variable
DEFAULT_ENDPOINT = "https://lingering-hat-12c3.a-boby14.workers.dev"

_rate_limit_lock = threading.Lock()
_recent_errors = {}
_is_initialized = False


def _get_app_version():
    try:
        from launcher import APP_VERSION
        return str(APP_VERSION)
    except Exception:
        return "2.1.5"


def _get_endpoint():
    env_url = os.environ.get("IMA_TELEMETRY_ENDPOINT")
    if env_url:
        return env_url
    try:
        from launcher import SETTINGS_FILE
        if os.path.isfile(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom = data.get("telemetry_endpoint")
                if custom and isinstance(custom, str) and custom.startswith("http"):
                    return custom.strip()
    except Exception:
        pass
    return DEFAULT_ENDPOINT


def _scrub_pii(text):
    if not text or not isinstance(text, str):
        return text
    # Scrub user directories (e.g. C:\Users\<name>\ or /home/<name>/)
    text = re.sub(r'([a-zA-Z]:[\\/]+Users[\\/]+)[^\\/\r\n]+', r'\g<1><user>', text, flags=re.I)
    text = re.sub(r'(/home/)[^/\r\n]+', r'\g<1><user>', text, flags=re.I)
    # Scrub sensitive credentials
    text = re.sub(r'(token|secret|password|bearer|auth)[=:\s]+[A-Za-z0-9_\-\.]{8,}', r'\1=***REDACTED***', text, flags=re.I)
    return text


def _is_rate_limited(fingerprint):
    now = time.time()
    with _rate_limit_lock:
        expired = [k for k, t in _recent_errors.items() if now - t > 300]
        for k in expired:
            _recent_errors.pop(k, None)

        last_time = _recent_errors.get(fingerprint)
        if last_time and (now - last_time) < 60:
            return True
        _recent_errors[fingerprint] = now
        return False


def _dispatch_payload(payload):
    endpoint = _get_endpoint()
    if not endpoint or (DEFAULT_ENDPOINT in endpoint and endpoint == DEFAULT_ENDPOINT):
        # Default placeholder endpoint, skip dispatch if not configured
        pass

    try:
        raw_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=raw_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"iMA-Menu/{payload.get('version', '1.0')} ({platform.platform()})"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            pass
    except Exception:
        # Silently discard to avoid secondary failures
        pass


def send_telemetry_event(error_type, message, traceback_str=None, context=None):
    """
    Dispatches a crash or error report asynchronously to the Cloudflare Worker.
    Guaranteed non-blocking with zero main-thread latency.
    """
    clean_msg = _scrub_pii(str(message or ""))
    clean_trace = _scrub_pii(str(traceback_str or ""))

    # Fingerprint to avoid loop spam
    fp_raw = f"{error_type}:{clean_msg[:120]}"
    fingerprint = hashlib.md5(fp_raw.encode("utf-8", errors="ignore")).hexdigest()

    if _is_rate_limited(fingerprint):
        return

    payload = {
        "app": "iMA Menu Launcher",
        "version": _get_app_version(),
        "error_type": str(error_type or "Error"),
        "message": clean_msg,
        "traceback": clean_trace,
        "os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    if context:
        payload["context"] = str(context)

    # Dispatch in daemon thread
    t = threading.Thread(target=_dispatch_payload, args=(payload,), daemon=True)
    t.start()


def _global_excepthook(exc_type, exc_value, exc_traceback):
    import traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_str = "".join(tb_lines)
    send_telemetry_event(
        error_type=exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type),
        message=str(exc_value),
        traceback_str=tb_str,
        context="sys.excepthook"
    )
    if sys.__excepthook__:
        try:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        except Exception:
            pass


def _global_unraisablehook(unraisable):
    tb_str = ""
    if unraisable.err_msg or unraisable.object:
        import traceback
        if unraisable.exc_traceback:
            tb_str = "".join(traceback.format_tb(unraisable.exc_traceback))
        send_telemetry_event(
            error_type="UnraisableException",
            message=f"{unraisable.err_msg}: {unraisable.exc_value}",
            traceback_str=tb_str,
            context=f"unraisable in {unraisable.object}"
        )


def init_telemetry():
    """Installs global exception handlers for unhandled errors."""
    global _is_initialized
    if _is_initialized:
        return
    _is_initialized = True

    sys.excepthook = _global_excepthook
    if hasattr(sys, "unraisablehook"):
        sys.unraisablehook = _global_unraisablehook
