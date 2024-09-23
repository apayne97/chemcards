from pydantic import Field

from chemcards.database.core import MoleculeEntry
from chemcards.flashcards.core import FlashCardBase, FlashCardGeneratorBase
import random
from abc import abstractmethod


class MultipleChoice(FlashCardBase):
    question: str
    display: MoleculeEntry = Field(None, description="Molecule to display if required")
    choices: list
    answer: int


class MultipleChoiceGeneratorBase(FlashCardGeneratorBase):

    @abstractmethod
    def next(self) -> MultipleChoice:
        pass


class MultipleChoiceMoleculeToTargetGenerator(MultipleChoiceGeneratorBase):

    name = "Multiple Choice - Molecule to Target"

    def next(self) -> MultipleChoice:
        example_molecules = random.sample(self.molecule_db.molecules, 4)
        correct = random.randint(0, 3)
        return MultipleChoice(
            question="What is the target of this molecule?",
            display=example_molecules[correct],
            choices=[mol.target for mol in example_molecules],
            answer=correct,
        )


class MultipleChoiceMoleculeToNameGenerator(FlashCardGeneratorBase):

    name = "Multiple Choice - Molecule to Name"

    def next(self) -> MultipleChoice:
        example_molecules = random.sample(self.molecule_db.molecules, 4)
        correct = random.randint(0, 3)
        return MultipleChoice(
            question="What is the name of this molecule?",
            display=example_molecules[correct],
            choices=[mol.name for mol in example_molecules],
            answer=correct,
    )