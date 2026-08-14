from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    public_origin: str = "https://acctbud.tail-scale.ts.net"
    user_tz: str = "America/New_York"
    morning_time: str = "08:00"
    evening_time: str = "20:00"
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:acctbud@example.com"
    db_path: str = "data/acctbud.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
