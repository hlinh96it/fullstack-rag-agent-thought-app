from src.config import Settings
from .parser import ParserService

settings = Settings()


def make_parser_service(settings: Settings) -> ParserService:
    return ParserService(settings if settings else Settings())
