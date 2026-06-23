from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    cors_allow_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    mysql_user: str = "root"
    mysql_password: str = "OMIS#¥@22"
    mysql_host: str = "47.238.233.206"
    mysql_port: int = 3317
    mysql_db: str = "OMIS"
    mysql_pool_recycle_seconds: int = 3600
    jwt_secret_key: str = "CHANGE_ME_SUPER_SECRET"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    openvpn_event_secret: Optional[str] = None
    openvpn_client_config_root: str = "./storage/openvpn-clients"
    openvpn_ssh_key_dir: str = "/data/oim/ssh"
    openvpn_default_ssh_key_path: Optional[str] = None
    openvpn_default_easy_rsa_dir: str = "/etc/openvpn/easy-rsa"
    openvpn_default_tls_crypt_key_path: str = "/etc/openvpn/tls-crypt.key"
    initial_admin_username: Optional[str] = "admin"
    initial_admin_email: Optional[str] = "admin@example.com"
    initial_admin_password: Optional[str] = "admin"
    auto_create_tables: bool = True

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()


def get_database_url() -> str:
    user = quote_plus(settings.mysql_user)
    password = quote_plus(settings.mysql_password)
    database = quote_plus(settings.mysql_db)
    return (
        f"mysql+pymysql://{user}:{password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{database}?charset=utf8mb4"
    )
