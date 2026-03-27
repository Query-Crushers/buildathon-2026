"""Shared exception reporting utility for the Cayu platform."""
import hashlib
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

REPORTING_TIMEOUT = 3
MAX_TRACEBACK_LENGTH = 5000
MAX_MESSAGE_LENGTH = 2000


def send_report(reporting_url, reporting_token, payload):
    """Send exception payload to the Cayu platform. Fails silently."""
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            reporting_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {reporting_token}',
            },
            method='POST',
        )
        urllib.request.urlopen(req, timeout=REPORTING_TIMEOUT)
    except Exception:
        logger.warning("Cayu exception reporting failed", exc_info=True)


def generate_fingerprint(*parts):
    """Generate stable fingerprint from parts."""
    raw = ':'.join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
