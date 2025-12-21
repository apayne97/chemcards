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


from pydantic import BaseModel, computed_field


class WindowOptions(BaseModel):
    window_height: int = 1200
    window_width: int = 1600
    frame_padding: int = 20
    edge: int = 40
    between: int = 20

    @computed_field
    @property
    def window_size(self) -> str:
        return f"{self.window_width}x{self.window_height}"

    @computed_field
    @property
    def frame_height(self) -> int:
        return self.window_height - self.frame_padding

    @computed_field
    @property
    def frame_width(self) -> int:
        return self.window_width - self.frame_padding

    @computed_field
    @property
    def frame_size(self) -> str:
        return f"{self.frame_width}x{self.frame_height}"
