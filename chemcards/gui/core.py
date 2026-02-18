from enum import StrEnum
from typing import Optional
import tkinter as tk
from pydantic import BaseModel, computed_field

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


class WindowOptions(BaseModel):
    window_height: int
    window_width: int
    frame_padding: int = 20
    edge: int = 40
    between: int = 20
    percent_width: float = 0.9
    percent_height: float = 0.85
    min_width: int = 800
    min_height: int = 600

    @classmethod
    def from_screen(
        cls,
        root: Optional[tk.Tk] = None,
        percent_width: float = 0.9,
        percent_height: float = 0.85,
        min_width: int = 800,
        min_height: int = 600,
    ) -> "WindowOptions":
        """
        Create WindowOptions sized relative to the current screen.
        If `root` is not provided a temporary tk.Tk is created and destroyed.
        """
        created = False
        if root is None:
            root = tk.Tk()
            root.withdraw()
            created = True
        try:
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
        finally:
            if created:
                root.destroy()

        width = max(min_width, int(screen_w * percent_width))
        height = max(min_height, int(screen_h * percent_height))

        return cls(
            window_width=width,
            window_height=height,
            percent_width=percent_width,
            percent_height=percent_height,
            min_width=min_width,
            min_height=min_height,
        )

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

