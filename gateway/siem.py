"""
SIEM integration — CEF-formatted syslog events. CHANGE-0022-C2.
Sends security, billing, and audit events to external SIEM receiver.
"""
import time, json, socket, logging
from config import settings

logger = logging.getLogger("aither.gateway.siem")

SIEM_HOST = ""
SIEM_PORT = 514
SIEM_ENABLED = False
_siem_sock = None


def init_siem():
    global SIEM_HOST, SIEM_PORT, SIEM_ENABLED, _siem_sock
    SIEM_ENABLED = settings.siem_enabled
    if not SIEM_ENABLED:
        return
    SIEM_HOST = ""
    SIEM_PORT = int(514)
    try:
        # Use environment if configured
        h = __import__("os").environ.get("SIEM_HOST", "")
        p = __import__("os").environ.get("SIEM_PORT", "514")
        if h:
            SIEM_HOST = h
            SIEM_PORT = int(p)
    except Exception:
        pass
    if SIEM_HOST:
        try:
            _siem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info("SIEM initialized: %s:%d", SIEM_HOST, SIEM_PORT)
        except Exception as e:
            logger.warning("SIEM socket error: %s", e)


def _cef_event(name: str, severity: int, extensions: dict) -> str:
    """Build CEF-formatted event string."""
    ext_str = " ".join(f"{k}={v}" for k, v in extensions.items() if v is not None)
    return (
        f"CEF:0|aither|gateway|2.0|{name}|{name}|{severity}|"
        f"src=gateway dst={SIEM_HOST or 'local'} "
        f"rt={int(time.time() * 1000)} {ext_str}"
    )


def send_event(name: str, severity: int = 5, **extensions):
    """Send SIEM event. Non-blocking, best-effort."""
    if not SIEM_ENABLED:
        return
    try:
        msg = _cef_event(name, severity, extensions)
        logger.debug("SIEM: %s", msg[:200])
        if _siem_sock:
            _siem_sock.sendto(msg.encode(), (SIEM_HOST, SIEM_PORT))
    except Exception as e:
        logger.warning("SIEM delivery failed: %s", e)


# Convenience functions for common event types
def auth_success(org_id: str, user_id: str = "", **kw):
    send_event("auth_success", 7, org_id=org_id, user_id=user_id, **kw)

def auth_failure(reason: str, **kw):
    send_event("auth_failure", 5, reason=reason, **kw)

def rate_limit_exceeded(org_id: str, reason: str, **kw):
    send_event("rate_limit_exceeded", 5, org_id=org_id, reason=reason, **kw)

def security_input_block(org_id: str, reason: str, **kw):
    send_event("security_input_block", 3, org_id=org_id, reason=reason, **kw)

def security_output_block(org_id: str, reason: str, **kw):
    send_event("security_output_block", 3, org_id=org_id, reason=reason, **kw)

def billing_reserve(org_id: str, ref: str, amount: int, **kw):
    send_event("billing_reserve", 7, org_id=org_id, reservation=ref, amount=str(amount), **kw)

def billing_settle(org_id: str, ref: str, amount: int, **kw):
    send_event("billing_settle", 7, org_id=org_id, reservation=ref, amount=str(amount), **kw)

def billing_refund(org_id: str, ref: str, amount: int, **kw):
    send_event("billing_refund", 5, org_id=org_id, reservation=ref, amount=str(amount), **kw)

def admin_action(org_id: str, action: str, **kw):
    send_event("admin_action", 5, org_id=org_id, action=action, **kw)

def upstream_error(model: str, error: str, **kw):
    send_event("upstream_error", 3, model=model, error=error, **kw)

def dependency_failure(component: str, error: str, **kw):
    send_event("dependency_failure", 3, component=component, error=error, **kw)

# Initialize on import
init_siem()
