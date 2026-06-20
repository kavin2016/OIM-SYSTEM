# Server Setup

Use this guide for a single Ubuntu server deployment.

## 1. Prepare the Server

SSH into the server and run:

```bash
sudo sh deploy/server-setup-ubuntu.sh
```

This installs Docker, Docker Compose, starts Docker, and opens ports `22`, `80`, and `443`.

## 2. Configure Production Variables

Create a root `.env` from the example:

```bash
cp .env.example .env
```

Edit `.env` and replace all passwords:

```env
MYSQL_ROOT_PASSWORD=replace_with_strong_mysql_root_password
MYSQL_DATABASE=OMIS
MYSQL_USER=oim
MYSQL_PASSWORD=replace_with_strong_database_password
WEB_PORT=80
VITE_API_BASE_URL=/api
TZ=Asia/Hong_Kong
```

Then edit `backend/docker.env`:

```bash
nano backend/docker.env
```

Change at least:

```env
JWT_SECRET_KEY=replace_with_a_long_random_secret
INITIAL_ADMIN_PASSWORD=replace_with_strong_admin_password
```

If you use a domain, also set:

```env
CORS_ALLOW_ORIGINS=["https://your-domain.example.com"]
```

## 3. Start the System

```bash
docker compose up -d --build
```

Check containers:

```bash
docker compose ps
docker compose logs -f backend
```

Open:

```text
http://your-server-ip/
```

## 4. Validate

API health:

```bash
curl http://127.0.0.1/ping
```

Database health:

```bash
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/db').read().decode())"
```

## 5. Operations

Restart:

```bash
docker compose restart
```

Update after code changes:

```bash
docker compose up -d --build
```

Backup database:

```bash
docker compose exec mysql mysqldump -uroot -p OMIS > oim-backup.sql
```
