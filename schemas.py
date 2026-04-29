from pydantic import BaseModel

class CaseInput(BaseModel):
    text: str

class CardNewsInput(BaseModel):
    text: str

class BlogSaveInput(BaseModel):
    title: str
    content: str

class ThumbnailInput(BaseModel):
    text: str