from typing import Optional
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from docling_core.types.doc.base import ImageRefMode
from langchain_docling.loader import ExportType


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
    model_name: str = ""
    temperature: float = 0.7
    timeout: int = 60


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


class MilvusDBSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="MILVUS__",
        case_sensitive=False,
    )
    uri: str = ""
    database_name: str = ""
    collection_name: str = ""
    namespace: str = ""
    api_key: str = ""


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
    export_type: ExportType = ExportType.DOC_CHUNKS

    picture_prompt: str = "Describe this image in sentences in a single paragraph."
    image_scale: int = 2

    tokenizer_model_id: str = "jinaai/jina-embeddings-v3"
    max_tokens: int = 1000
    image_mode: ImageRefMode = ImageRefMode.PLACEHOLDER
    image_placeholder: str = ""
    mark_annotation: bool = True
    include_annotation: bool = True


class JinaEmbeddingClient(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="JINA__",
        case_sensitive=False,
    )
    embedding_url: str = ""
    jina_api_key: str = ""
    model_name: str = ""

class LangfuseClient(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="LANGFUSE__",
        case_sensitive=False,
    )
    public_key: str = ''
    secret_key: str = ''
    base_url: str = ''

class Settings(BaseConfigSettings):
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    mongo_db: MongoDBSettings = Field(default_factory=MongoDBSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    milvus: MilvusDBSettings = Field(default_factory=MilvusDBSettings)

    parser: ParserSettings = Field(default_factory=ParserSettings)
    jina: JinaEmbeddingClient = Field(default_factory=JinaEmbeddingClient)
    langfuse: LangfuseClient = Field(default_factory=LangfuseClient)
    api_server: str = "http://localhost:8000"
