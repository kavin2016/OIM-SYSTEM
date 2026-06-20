from pydantic import BaseModel


class CaptchaResponse(BaseModel):
    captcha_token: str
    captcha_image: str
    expires_in: int
