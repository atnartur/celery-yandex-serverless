import base64
import importlib
import json
import logging
import os

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

_secret_key_slug = "CELERY_YANDEX_SERVERLESS_KEY"
_secret_key = getattr(settings, _secret_key_slug, os.environ.get(_secret_key_slug))
if _secret_key is None:
    logger.error("Define CELERY_YANDEX_SERVERLESS_KEY settings with secret key for serverless worker")


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

        try:
            data = json.loads(request.body)
            messages = data['messages']
        except KeyError:
            logger.error("incorrect data structure")
            logger.debug(request.body)
            return JsonResponse({"status": "error", "message": "incorrect data structure"}, status=500)

        for message in messages:
            # enable force saving task results
            celery_app.conf.task_store_eager_result = True
            store_result_original_value = celery_app.conf.task_store_eager_result

            try:
                # decode message
                data_json = base64.b64decode(message['details']['message']['body']).decode()
                data = celery_app.backend.decode(data_json)

                # search for target function
                module_path = data['headers']['task'].split('.')
                package_path = ".".join(module_path[:-1])
                function_name = module_path[-1]
                module = importlib.import_module(package_path)
                function = getattr(module, function_name)

                # get task arguments
                args, kwargs, options = json.loads(base64.b64decode(data['body']))
            except KeyError:
                logger.error("incorrect data structure")
                logger.debug(request.body)
                return JsonResponse({"status": "error", "message": "incorrect data structure"}, status=500)

            logger.info("task %s received", function_name)

            try:
                # start celery task
                result = function.apply(
                    args=args,
                    kwargs=kwargs,
                    task_id=data['headers']['id'],
                    **options
                )
                logger.info("task %s processed", function_name)

                if not result.successful():
                    logging.error(result.info)
                    return JsonResponse({"status": "task_error", "info": str(result.info)})
            except Exception:
                raise
            finally:
                # return settings to default state
                celery_app.conf.task_store_eager_result = store_result_original_value

        return JsonResponse({"status": "ok"})
    return _worker_view
