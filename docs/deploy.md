# Deploy Telegram Digest Bot

Этот проект удобно деплоить на один VPS через Docker Compose и GitHub Actions по SSH.

Схема простая:

- GitHub Actions прогоняет тесты на каждом push в `main`.
- Если тесты прошли, workflow заходит на сервер по SSH.
- На сервере выполняется `git pull`.
- Docker Compose пересобирает и перезапускает контейнеры `bot` и `db`.
- Секреты лежат только в `.env` на сервере и в GitHub Secrets.

## 1. Что будет на сервере

Рекомендуемый путь приложения:

```bash
/opt/topic_digests
```

Внутри:

```text
/opt/topic_digests
  .env
  docker-compose.yml
  Dockerfile
  logs/
  backups/
```

Контейнеры:

- `bot` - Python-приложение с aiogram polling.
- `db` - PostgreSQL 16.

Важно: не запускайте один и тот же Telegram bot token одновременно локально и на сервере. Для polling должен быть один активный процесс.

## 2. Подготовить VPS

Пример для Ubuntu 22.04/24.04. Лучше ставить Docker из официального Docker apt repository: в стандартных репозиториях Ubuntu пакет `docker-compose-plugin` может отсутствовать.

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

После `usermod` перелогиньтесь в SSH-сессию, чтобы группа `docker` применилась.

Проверьте:

```bash
docker --version
docker compose version
```

Если у вас Debian, замените URL `linux/ubuntu` на `linux/debian` в командах выше.

## 3. Создать пользователя для деплоя

Можно деплоить от обычного пользователя, например `deploy`.

```bash
sudo adduser deploy
sudo usermod -aG docker deploy
sudo mkdir -p /opt/topic_digests
sudo chown -R deploy:deploy /opt/topic_digests
```

Дальше зайдите под ним:

```bash
su - deploy
```

## 4. Настроить SSH-ключ для GitHub Actions

На локальной машине или на сервере создайте отдельный ключ только для деплоя:

```bash
ssh-keygen -t ed25519 -C "github-actions-topic-digests" -f topic_digests_deploy_key
```

Публичный ключ добавьте на сервер пользователю `deploy`:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat topic_digests_deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Приватный ключ `topic_digests_deploy_key` понадобится добавить в GitHub Secrets.

## 5. Склонировать репозиторий на сервер

```bash
cd /opt/topic_digests
git clone <YOUR_REPO_SSH_OR_HTTPS_URL> .
git checkout main
```

Если репозиторий приватный, удобнее использовать deploy key GitHub для чтения репозитория или HTTPS clone с токеном. Самый чистый вариант: добавить отдельный read-only deploy key в настройках репозитория GitHub.

## 6. Создать production `.env`

На сервере:

```bash
cd /opt/topic_digests
cp .env.production.example .env
nano .env
```

Пример:

```env
TG_TOKEN=123456:telegram-token
ADMIN_IDS=701151229,203601147
OPENROUTER_API_KEY=sk-or-v1-...

POSTGRES_DB=topic_digests
POSTGRES_USER=topic_digests
POSTGRES_PASSWORD=long-random-password
DATABASE_URL=postgresql+asyncpg://topic_digests:long-random-password@db:5432/topic_digests

PROXY=
```

`POSTGRES_PASSWORD` и пароль внутри `DATABASE_URL` должны совпадать.

Права:

```bash
chmod 600 .env
mkdir -p logs backups
sudo chown -R 10001:10001 logs
```

Почему `10001`: контейнер бота запускается от non-root пользователя `app` с UID `10001`, ему нужна запись в `logs/`.

## 7. Первый запуск вручную

Перед подключением CI/CD лучше один раз проверить руками:

```bash
cd /opt/topic_digests
docker compose up -d --build
docker compose ps
docker compose logs -f bot
```

Если нужно создать таблицы без удаления данных, достаточно запуска бота: `main.py` вызывает `init_db()`.

Если нужно полностью сбросить БД под новую схему:

```bash
docker compose run --rm bot python scripts/reset_db.py
```

Осторожно: `reset_db.py` удаляет таблицы и данные.

## 8. GitHub Secrets

В GitHub:

`Repository -> Settings -> Secrets and variables -> Actions -> New repository secret`

Добавьте:

```text
SERVER_HOST
SERVER_USER
SERVER_SSH_KEY
APP_DIR
SERVER_PORT
```

Пример:

```text
SERVER_HOST=1.2.3.4
SERVER_USER=deploy
SERVER_SSH_KEY=<private key topic_digests_deploy_key>
APP_DIR=/opt/topic_digests
SERVER_PORT=22
```

`APP_DIR` и `SERVER_PORT` можно не задавать: workflow использует `/opt/topic_digests` и `22` по умолчанию.

## 9. Как работает CI/CD

Файл workflow:

```text
.github/workflows/deploy.yml
```

На push в `main`:

1. GitHub Actions ставит Python 3.12.
2. Устанавливает зависимости из `requirements.txt`.
3. Запускает:

```bash
python -m unittest discover -s tests
```

4. Если тесты прошли, заходит на сервер по SSH.
5. Выполняет:

```bash
cd /opt/topic_digests
git fetch origin main
git checkout main
git pull --ff-only origin main
mkdir -p logs backups
docker compose up -d --build --remove-orphans
docker image prune -f
docker compose ps
```

## 10. Ручной деплой

Если GitHub Actions не нужен или временно сломан:

```bash
cd /opt/topic_digests
git pull --ff-only origin main
docker compose up -d --build --remove-orphans
docker compose ps
```

## 11. Логи

Логи контейнера:

```bash
docker compose logs -f bot
```

Последние 200 строк:

```bash
docker compose logs --tail=200 bot
```

Файл приложения:

```bash
tail -f logs/app.log
```

Логи PostgreSQL:

```bash
docker compose logs -f db
```

## 12. Бэкапы PostgreSQL

Ручной backup:

```bash
cd /opt/topic_digests
docker compose exec -T db pg_dump -U topic_digests topic_digests > backups/topic_digests_$(date +%Y%m%d_%H%M%S).sql
```

Восстановление:

```bash
cat backups/topic_digests_YYYYMMDD_HHMMSS.sql | docker compose exec -T db psql -U topic_digests topic_digests
```

Простой cron backup каждый день в 03:00:

```bash
crontab -e
```

Добавить:

```cron
0 3 * * * cd /opt/topic_digests && docker compose exec -T db pg_dump -U topic_digests topic_digests > backups/topic_digests_$(date +\%Y\%m\%d_\%H\%M\%S).sql
```

## 13. Откат

Посмотреть коммиты:

```bash
cd /opt/topic_digests
git log --oneline -10
```

Откатиться к конкретному коммиту:

```bash
git checkout <commit_sha>
docker compose up -d --build --remove-orphans
```

Вернуться на `main`:

```bash
git checkout main
git pull --ff-only origin main
docker compose up -d --build --remove-orphans
```

## 14. Обновление `.env`

После изменения `.env`:

```bash
docker compose up -d
```

Если поменяли только переменные окружения, пересборка образа не нужна.

## 15. Частые проблемы

### Conflict: terminated by other getUpdates request

Запущено два экземпляра бота с одним токеном. Остановите локальный запуск или старый контейнер:

```bash
docker compose ps
docker compose stop bot
```

### Бот не видит базу

Проверьте, что `DATABASE_URL` указывает на host `db`, не `localhost`:

```env
DATABASE_URL=postgresql+asyncpg://topic_digests:password@db:5432/topic_digests
```

Внутри Docker Compose `localhost` означает сам контейнер бота, а не контейнер PostgreSQL.

### Нет прав на logs/app.log

```bash
cd /opt/topic_digests
sudo chown -R 10001:10001 logs
docker compose restart bot
```

### GitHub Actions не может зайти по SSH

Проверьте:

```bash
ssh -i topic_digests_deploy_key deploy@SERVER_HOST
```

Если локально не заходит, GitHub Actions тоже не зайдет.

## 16. Минимальный production checklist

- `.env` создан на сервере и не закоммичен.
- `DATABASE_URL` использует host `db`.
- `POSTGRES_PASSWORD` длинный и совпадает с паролем в `DATABASE_URL`.
- `ADMIN_IDS` заполнен.
- `OPENROUTER_API_KEY` заполнен.
- `docker compose up -d --build` успешно стартует.
- `docker compose logs -f bot` показывает polling.
- GitHub Secrets добавлены.
- Push в `main` проходит test и deploy jobs.
- Бэкап PostgreSQL настроен.
