from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    prompt: str