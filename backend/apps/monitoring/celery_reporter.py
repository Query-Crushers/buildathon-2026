"""
Cayu Celery Exception Reporter

Connects to Celery's task_failure signal to report worker exceptions
to the Cayu platform. Same payload format as the middleware but uses
task_name and task_id instead of request context.
"""
import re

from celery.signals import task_failure
from django.conf import settings

from .reporter import send_report, generate_fingerprint, MAX_TRACEBACK_LENGTH, MAX_MESSAGE_LENGTH


@task_failure.connect
def report_task_failure(sender=None, task_id=None, exception=None,
                        traceback=None, einfo=None, **kwargs):
    """Report Celery task failures to the Cayu platform."""
    reporting_url = getattr(settings, 'CAYU_ERROR_REPORTING_URL', '')
    reporting_token = getattr(settings, 'CAYU_ERROR_REPORTING_TOKEN', '')

    if not reporting_url:
        return

    exception_class = type(exception).__qualname__
    message = str(exception)
    task_name = sender.name if sender else 'unknown'

    file_path, line_number, function_name = _parse_user_frame(einfo)
    fingerprint = generate_fingerprint(exception_class, task_name, file_path or '', line_number or 0)

    tb_str = str(einfo)[:MAX_TRACEBACK_LENGTH] if einfo else ''

    payload = {
        'fingerprint': fingerprint,
        'exception_class': exception_class,
        'message': message[:MAX_MESSAGE_LENGTH],
        'file_path': file_path,
        'line_number': line_number,
        'function_name': function_name,
        'traceback': tb_str,
        'celery_context': {
            'task_name': task_name,
            'task_id': str(task_id) if task_id else None,
        },
    }

    send_report(reporting_url, reporting_token, payload)


# Matches: File "path/to/file.py", line 42, in function_name
_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+), in (\w+)')


def _parse_user_frame(einfo):
    """Extract the last user-code frame from einfo traceback string."""
    if not einfo:
        return None, None, None

    tb_str = str(einfo)
    file_path = None
    line_number = None
    function_name = None

    for match in _FRAME_RE.finditer(tb_str):
        filename = match.group(1)
        if '/apps/' in filename or '/backend/' in filename:
            if '/backend/' in filename:
                idx = filename.index('/backend/')
                file_path = filename[idx + 1:]
            elif '/apps/' in filename:
                idx = filename.index('/apps/')
                file_path = filename[idx + 1:]
            line_number = int(match.group(2))
            function_name = match.group(3)

    return file_path, line_number, function_name
