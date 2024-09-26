from pydantic import BaseModel
from enum import StrEnum

class FontWeight(StrEnum):
    normal = "normal"
    bold = "bold"
    italic = "italic"
    bold_italic = "bold italic"


class TKFontStyle(BaseModel):
    font: str
    size: int
    weight: FontWeight

    def __call__(self) -> tuple:
        return self.font, self.size, self.weight

class FontDefaults:
    title = TKFontStyle(font="MS Serif", size=48, weight=FontWeight.bold)
    subtitle = TKFontStyle(font="MS Serif", size=36, weight=FontWeight.bold)
    text = TKFontStyle(font="Helvetica", size=18, weight=FontWeight.bold)

class PaddingAndSize:
    window_height = 1200
    window_width = 1600
    frame_padding = 20
    edge = 40
    between = 20

    @classmethod
    @property
    def window_size(cls) -> str:
        return f"{cls.window_width}x{cls.window_height}"

    @classmethod
    @property
    def frame_height(cls):
        return cls.window_height - cls.frame_padding

    @classmethod
    @property
    def frame_width(cls):
        return cls.window_width - cls.frame_padding

    @classmethod
    @property
    def frame_size(cls):
        return f"{cls.frame_width}x{cls.frame_height}"
