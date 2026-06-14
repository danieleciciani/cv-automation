from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    jsearch_api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = "eu-west-1"
    generated_cvs_dir: str = "generated_cvs"
    base_cv_path: str = "cv_data/base_cv.txt"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
