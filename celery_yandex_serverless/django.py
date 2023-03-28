import logging
import os

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

_secret_key_slug = "CELERY_YANDEX_SERVERLESS_KEY"
_secret_key = getattr(settings, _secret_key_slug, os.environ.get(_secret_key_slug))
if _secret_key is None:
    logging.error("Define CELERY_YANDEX_SERVERLESS_KEY settings with secret key for serverless worker")


def worker_view_factory(celery_app):
    @csrf_exempt
    def _worker_view(request, key: str):
        if _secret_key is None:
            logging.error("Define CELERY_YANDEX_SERVERLESS_KEY settings with secret key for serverless worker")
            return JsonResponse({"status": "error", "message": "secret key is not set"}, status=500)

        if request.method != 'POST':
            return JsonResponse({"status": "error", "message": "method not allowed"}, status=405)

        if _secret_key != key:
            return JsonResponse({"status": "error", "message": "not found"}, status=404)

        return JsonResponse({"status": "ok"})
    return _worker_view
