from pydantic import BaseModel, Field
from enum import Enum
from chemcards.database.core import MoleculeEntry

class FlashcardType(Enum):
    pass

class FlashCardBase(BaseModel):
    pass

class MultipleChoice(FlashCardBase):
    question: str
    display: MoleculeEntry = Field(None, description="Molecule to display if required")
    choices: list
    answer: int
