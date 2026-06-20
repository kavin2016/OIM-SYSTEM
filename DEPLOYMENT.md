# OIM Docker Deployment

This setup runs the system on one server with three containers:

- `mysql`: MySQL 8.0 database with persistent volume
- `backend`: FastAPI API service
- `web`: Nginx static frontend and reverse proxy

## Requirements

- Linux server with Docker and Docker Compose
- Open port `80` on the server firewall
- Domain and HTTPS certificate are recommended for production

## First-Time Setup

1. Review `backend/docker.env` and replace the default passwords and `JWT_SECRET_KEY`.
2. Optional: create a root `.env` file to override compose-level values:

```env
MYSQL_ROOT_PASSWORD=replace_with_strong_root_password
MYSQL_DATABASE=OMIS
MYSQL_USER=oim
MYSQL_PASSWORD=oim_password
WEB_PORT=80
VITE_API_BASE_URL=/api
TZ=Asia/Hong_Kong
```

3. Build and start the stack:

```bash
docker compose up -d --build
```

4. Check status:

```bash
docker compose ps
docker compose logs -f backend
```

5. Open the system:

```text
http://your-server-ip/
```

The default admin account comes from `backend/docker.env`.

## Common Commands

Stop the system:

```bash
docker compose down
```

Restart after code or env changes:

```bash
docker compose up -d --build
```

Run database migrations manually:

```bash
docker compose exec backend alembic upgrade head
```

Backup MySQL:

```bash
docker compose exec mysql mysqldump -uroot -p OMIS > oim-backup.sql
```

## Production Notes

- Change all default passwords before exposing the server.
- Use a real domain with HTTPS in front of the `web` service.
- Keep `mysql_data` backed up.
- Keep `AUTO_CREATE_TABLES=false`; migrations are run automatically when the backend container starts.
