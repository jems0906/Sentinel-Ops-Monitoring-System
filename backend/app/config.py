from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sentinel Ops Monitoring System"
    database_url: str = "sqlite:///./data/sentinel_ops.db"
    monitor_interval_seconds: int = 10
    incident_cooldown_seconds: int = 60
    disable_monitor: bool = False
    auto_ack_repeat_threshold: int = 0
    auto_ack_severities: str = "warning,info"
    smtp_host: str | None = None
    smtp_port: int = 25
    smtp_username: str | None = None
    smtp_password: str | None = None
    alert_from_email: str = "sentinel-ops@example.com"
    alert_to_email: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTINEL_")


settings = Settings()
