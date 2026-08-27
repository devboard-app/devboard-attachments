from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    S3_ENDPOINT_URL: str
    S3_BUCKET: str
    MAX_FILE_SIZE_MB: int
    PRESIGNED_URL_TTL_SECONDS: int
    JWT_SECRET: str
    INTERNAL_API_KEY: str
    DATABASE_URL: str

settings = Settings() #type: ignore