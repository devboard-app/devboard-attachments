from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    S3_ENDPOINT_URL: str
    S3_PUBLIC_ENDPOINT_URL: str
    S3_BUCKET: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    MAX_FILE_SIZE_MB: int
    PRESIGNED_URL_TTL_SECONDS: int
    JWT_SECRET: str
    INTERNAL_API_KEY: str
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

settings = Settings() #type: ignore