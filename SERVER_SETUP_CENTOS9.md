# CentOS Stream 9 Server Deployment

This server already has Docker and an existing MySQL database.

Use this compose file:

```bash
docker compose -f docker-compose.server.yml up -d --build
```

It starts only:

- `oim-backend`
- `oim-web`

It does not create a new MySQL container.

## Server Values

The backend runtime config is in:

```text
backend/docker.env
```

For this server, the database connection should be:

```env
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3317
MYSQL_DB=OMIS
MYSQL_USER=omis_app
```

The compose stack uses the external Docker network `oim-shared`.
Connect the existing MySQL container to that network once:

```bash
docker network create oim-shared
docker network connect oim-shared mysql8
```

Then the backend can reach MySQL by container name:

```env
MYSQL_HOST=mysql8
MYSQL_PORT=3306
```

## Firewall

Open HTTP and HTTPS if needed:

```bash
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

If `firewalld` is not running, check the cloud provider security group and allow:

```text
80/tcp
443/tcp
```

The database port `3317` does not need to be opened publicly for the web system if the app and database are on the same server.

## Deploy

From the project root on the server:

```bash
docker compose -f docker-compose.server.yml up -d --build
```

Check status:

```bash
docker compose -f docker-compose.server.yml ps
docker compose -f docker-compose.server.yml logs -f backend
```

Open:

```text
http://47.238.233.206/
```

## Validate

Frontend/API proxy:

```bash
curl http://127.0.0.1/ping
```

Backend database connection:

```bash
docker compose -f docker-compose.server.yml exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/db').read().decode())"
```

## Update

After code changes:

```bash
docker compose -f docker-compose.server.yml up -d --build
```
