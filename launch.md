# AI Prompt Hub - Инструкция по запуску

## 1. Клонирование репозитория

```bash
git clone <repository-url>
cd ai_prompt_manager
```

## 2. Настройка окружения

Создайте файл `.env.prod` на основе примера:

```bash
cp .env.prod.example .env.prod
```

Отредактируйте `.env.prod` и укажите свои API ключи:

```dotenv
# AI Provider
AI_PROVIDER=qwen

# QWEN API Key (обязательно)
QWEN_API_KEY=your-api-key-here
QWEN_API_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max

# Database (оставьте как есть для Docker)
DB_HOST=db
DB_PORT=5432
DB_NAME=prompthub
DB_USER=postgres
DB_PASSWORD=prompthub_secret
```

## 3. Запуск приложения

### Первый запуск (или после очистки)

```bash
docker compose up --build -d
```

При первом запуске PostgreSQL автоматически создаёт все таблицы и дефолтную группу `General` через `init.sql`.

### Повторный запуск (без пересборки)

```bash
docker compose up -d
```

### Пересборка после изменений в коде

```bash
docker compose up --build -d
```

### Перезапуск только приложения (без пересборки)

```bash
docker compose restart app
```

### Перезапуск только базы данных

```bash
docker compose restart db
```

## 4. Проверка статуса

```bash
docker compose ps
docker logs prompthub-app
```

## 5. Доступ к приложению

Откройте браузер: http://localhost:8000

## Остановка

```bash
docker compose down
```

## Полная очистка (с удалением данных БД)

```bash
docker compose down -v
```

## Просмотр логов

```bash
# Все контейнеры
docker compose logs -f

# Только приложение
docker logs prompthub-app -f

# Только база данных
docker logs prompthub-db -f
```

## Подключение к БД внутри контейнера

```bash
docker exec -it prompthub-db psql -U postgres -d prompthub
```
