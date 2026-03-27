"""
Cayu Exception Reporter Middleware

Catches unhandled Django exceptions and reports them to the Cayu platform
for monitoring and auto-fix capabilities. Zero impact on user app — all
errors in reporting are silently caught and logged.
"""
import traceback

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404

from .reporter import send_report, generate_fingerprint, MAX_TRACEBACK_LENGTH, MAX_MESSAGE_LENGTH

SENSITIVE_HEADERS = {'authorization', 'cookie', 'x-api-key', 'x-csrf-token'}
IGNORED_EXCEPTIONS = (Http404, PermissionDenied, SuspiciousOperation)


class CayuExceptionReporterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.reporting_url = getattr(settings, 'CAYU_ERROR_REPORTING_URL', '')
        self.reporting_token = getattr(settings, 'CAYU_ERROR_REPORTING_TOKEN', '')

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not self.reporting_url:
            return None

        if isinstance(exception, IGNORED_EXCEPTIONS):
            return None

        try:
            self._report_exception(request, exception)
        except Exception:
            pass  # send_report already logs warnings internally

        return None

    def _report_exception(self, request, exception):
        tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
        tb_str = ''.join(tb)

        exception_class = type(exception).__qualname__
        message = str(exception)

        file_path, line_number, function_name = self._find_user_frame(exception)
        fingerprint = generate_fingerprint(exception_class, file_path or 'unknown', line_number or 0)
        request_context = self._extract_request_context(request)

        payload = {
            'fingerprint': fingerprint,
            'exception_class': exception_class,
            'message': message[:MAX_MESSAGE_LENGTH],
            'file_path': file_path,
            'line_number': line_number,
            'function_name': function_name,
            'traceback': tb_str[:MAX_TRACEBACK_LENGTH],
            'request_context': request_context,
        }

        send_report(self.reporting_url, self.reporting_token, payload)

    def _find_user_frame(self, exception):
        """Find the first stack frame in user code (apps/ or backend/ directory)."""
        tb = exception.__traceback__
        file_path = None
        line_number = None
        function_name = None

        while tb is not None:
            frame = tb.tb_frame
            filename = frame.f_code.co_filename

            if '/apps/' in filename or '/backend/' in filename:
                if '/backend/' in filename:
                    idx = filename.index('/backend/')
                    file_path = filename[idx + 1:]
                elif '/apps/' in filename:
                    idx = filename.index('/apps/')
                    file_path = filename[idx + 1:]
                line_number = tb.tb_lineno
                function_name = frame.f_code.co_name

            tb = tb.tb_next

        return file_path, line_number, function_name

    def _extract_request_context(self, request):
        """Extract safe request context, stripping sensitive headers."""
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].lower().replace('_', '-')
                if header_name not in SENSITIVE_HEADERS:
                    headers[header_name] = value[:200]

        return {
            'method': request.method,
            'path': request.path,
            'query_string': request.META.get('QUERY_STRING', '')[:500],
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'remote_addr': request.META.get('REMOTE_ADDR', ''),
            'headers': headers,
        }
