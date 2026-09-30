import json
import logging
import time

logger = logging.getLogger("desk.request")


class RequestLogMiddleware:
    """One JSON line per request: method, path, status, duration, user id."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        user = getattr(request, "user", None)
        user_id = user.pk if getattr(user, "is_authenticated", False) else None
        logger.info(
            json.dumps(
                {
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "user_id": user_id,
                }
            )
        )
        return response
