from pydantic import Field

from chemcards.database.core import MoleculeEntry
from chemcards.flashcards.core import FlashCardBase, FlashCardGeneratorBase
import random


class MultipleChoice(FlashCardBase):
    question: str
    display: MoleculeEntry = Field(None, description="Molecule to display if required")
    choices: list
    answer: int


class MultipleChoiceGenerator(FlashCardGeneratorBase):

    def next(self) -> MultipleChoice:
        example_molecules = random.sample(self.molecule_db.molecules, 4)
        correct = random.randint(0, 3)
        return MultipleChoice(
            question="What is the target of this molecule?",
            display=example_molecules[correct],
            choices=[mol.target for mol in example_molecules],
            answer=correct,
        )
