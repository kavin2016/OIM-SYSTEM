# OIM Backend

FastAPI backend with MySQL, JWT auth, user table migration, and dynamic captcha.

## Start

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /ping`
- `GET /health/db`
- `GET /auth/captcha`
- `POST /auth/token`
- `POST /auth/register`
- `GET /auth/me`
- `GET /users/me`
- `PUT /users/me`
- `GET /users`
- `POST /users`
- `GET /users/{user_id}`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`
- `GET /departments`
- `POST /departments`
- `GET /departments/{department_id}`
- `PUT /departments/{department_id}`
- `DELETE /departments/{department_id}`
- `GET /roles`
- `POST /roles`
- `GET /roles/{role_id}`
- `PUT /roles/{role_id}`
- `DELETE /roles/{role_id}`
- `GET /permissions`
- `POST /permissions`
- `GET /permissions/{permission_id}`
- `PUT /permissions/{permission_id}`
- `DELETE /permissions/{permission_id}`
