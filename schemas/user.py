from pydantic import BaseModel, Field


class ApiKeySaveRequest(BaseModel):
    gemini_api_key: str = ""
    openai_api_key: str = ""

class TitleGenerateRequest(BaseModel):
    case: str = ""
    subInput: str = ""
    subInput2: str = ""
    provider: str = "gemini"
    model: str | None = None

class GenerateRequest(BaseModel):
    category: str = ""
    url: str = ""
    keywords: str = ""
    subInput: str = ""
    subTitle: str = ""
    length: str = "1200"
    provider: str = "gemini"
    model: str | None = None


class BlogPublishRequest(BaseModel):
    title: str = ""
    content: str = ""
    publisher_profile_key: str = ""
    blog_id: str = ""
    publish_mode: str = "now"
    scheduled_at: str = ""
    include_random_image: bool = False
    vpn_activation_code: str = ""
    middle_image_count: int = Field(default=1, ge=0, le=10)
    bottom_image_count: int = Field(default=1, ge=0, le=10)
    bottom_image_link: str = ""
    bottom_first_image_link: str = ""
    typing_delay_min: int = Field(default=30, ge=0, le=500)
    typing_delay_max: int = Field(default=85, ge=0, le=500)
    conclusion_paragraph_count: int = Field(default=1, ge=0, le=10)
    body_font_size: str = "15"
    subtitle_font_size: str = "24"
    subtitle_quote_style: int = Field(default=1, ge=1, le=6)
