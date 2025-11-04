from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
    )


class OpenAISettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="OPENAI__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    openai_api_key: str = ""
    model_name: str = ''
    temperature: float = 0.7
    timeout: int = 300


class MongoDBSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="MONGO__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    mongo_uri: str = ""
    mongo_database: str = ""
    mongo_collection: str = ""


class AWSSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="AWS__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )
    access_key: str = ""
    secret_key: str = ""
    region: str = ""
    bucket_name: str = ""


class ParserSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="PDF_PARSER__",
        case_sensitive=False,
    )
    max_pages: int = 30
    max_file_size_mb: int = 20
    do_orc: bool = False
    do_table_structure: bool = True


class Settings(BaseConfigSettings):
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    mongo_db: MongoDBSettings = Field(default_factory=MongoDBSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    parser: ParserSettings = Field(default_factory=ParserSettings)

    api_server: str = "http://localhost:8000"
