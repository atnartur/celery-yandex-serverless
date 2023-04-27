# Celery Yandex Serverless

Модуль, позволяющий запустить celery-worker внутри Yandex Cloud Serverless Container.

**Классический подход с отдельно запущенным воркером**

1. Бекенд отправляет задачу в очередь.
2. Отдельный процесс воркера забирает задачу из очереди и выполняет ее.

**Serverless-подход**

В Serverless подходе предполагается, что нет никаких запущенных постоянно процессов приложения. Эти процессы запускаются
либо по запросу пользователя, либо по различным тригерам облаком. 

Модуль `celery-yandex-serverless` помогает запустить воркер следующим образом:
1. Бекенд отправляет задачу в очередь
2. После попадания задачи в очередь срабатывает триггер, который делает http-запрос serverless-контейнеру.
3. Serverless-контейнер запускает код задачи, который ранее выполнялся в воркере.

## Использование

### Подключение Celery к Yandex Message Queue

1. Перейдите на страницу каталога в Яндекс.Облаке
2. Зайдите в раздел **Сервисные аккаунты**
3. Посмотрите название сервисного аккаунта в каталоге Яндекс.Облака
4. Сгенерируйте `ACCESS_KEY` и `SECRET_KEY` с помощью команды 
(замените `SERVICE_ACCOUNT_NAME` на название сервисного аккаунта):

```bash
yc iam access-key create --service-account-name SERVICE_ACCOUNT_NAME
```

Команда вернет следующую информацию. Сохраните ее, она пригодится в будущем.

```yml{5,6}
access_key:
  id: aje...
  service_account_id: aje...
  created_at: "2023-03-24T17:49:01.555836400Z"
  key_id: YCAJ... # <- Это access key
secret: YCPM... # <- Это secret key
```

### Настройка
Укажите переменные окружения с использованием только что полученных данных:

```
AWS_ACCESS_KEY_ID="access key, скопированный выше"
AWS_SECRET_ACCESS_KEY="secret key, скопированный выше"
AWS_DEFAULT_REGION="ru-central1"
CELERY_BROKER_URL=sqs://message-queue.api.cloud.yandex.net:443
CELERY_BROKER_IS_SECURE=True
```

В файле `settings.py` укажите:

```python
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'is_secure': os.environ.get("CELERY_BROKER_IS_SECURE", 'false').lower() == 'true'
}
```

После этого отправьте celery-задачу, чтобы в Яндекс.Облаке появилась очередь.

### Подключение модуля

1. `pip install celery-yandex-serverless` - установите модуль
2. В urls.py (`projectname` замените на название проекта):
```python
from django.urls import path
from celery_yandex_serverless.django import worker_view_factory

from projectname.celery import app

urlpatterns = [
    # другие адреса...
    path("worker/<str:key>/", worker_view_factory(app)),
]
```

3. Установите переменную окружения `CELERY_YANDEX_SERVERLESS_KEY` со случайным ключом. 
Он предотвратит нежелательные запуски воркеров по прямому обращению к URL.

### Создание триггера в Яндекс.Облаке

В консольной команде ниже сделайте замены и выполните ее:
- `YANDEX_MESSAGE_QUEUE_ARN` - ARN очереди (можно увидеть на странице очереди)
- `SERVICE_ACCOUNT_NAME` - название сервисного аккаунта
- `SERVERLESS_CONTAINER_NAME` - название serverless-контейнера
- `CELERY_YANDEX_SERVERLESS_KEY` - ключ, созданный ранее

```bash
yc serverless trigger create message-queue \
  --name celery \
  --queue YANDEX_MESSAGE_QUEUE_ARN \
  --queue-service-account-name SERVICE_ACCOUNT_NAME \
  --invoke-container-name SERVERLESS_CONTAINER_NAME \
  --invoke-container-service-account-name SERVICE_ACCOUNT_NAME \
  --invoke-container-path /worker/CELERY_YANDEX_SERVERLESS_KEY \
  --batch-size 1 \
  --batch-cutoff 10s 
```

### Включение логирования

Добавьте в `settings.py`:
```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "celery_yandex_serverless.django": {
            "level": "INFO",
        },
    },
}
```

Уровни:
- `INFO` - инфорация о начале и окончании обработки задачи
- `DEBUG` - печать содержимого аргументов celery-таска

## Статьи в Яндекс.Облаке
- [Подключение Celery](https://cloud.yandex.ru/docs/message-queue/instruments/celery)
- [Документация по созданию триггеров через yc](https://cloud.yandex.ru/docs/cli/cli-ref/managed-services/serverless/trigger/create/message-queue).
- [Подробнее про работу триггера](https://cloud.yandex.ru/docs/serverless-containers/concepts/trigger/ymq-trigger).

## Обновление

1. `poetry version ...` - обновить версию
2. закомитить изменения
3. `git tag ...` - добавить тег с версией пакета
4. `git push --tags` - запушить тег
5. `poetry publish --build` - опубликовать пакет

## Автор
[Атнагулов Артур](https://atnartur.dev)

Лицензия MIT.
