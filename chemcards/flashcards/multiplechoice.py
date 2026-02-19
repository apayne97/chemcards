from pydantic import Field

from chemcards.database.core import MoleculeEntry
from chemcards.flashcards.core import FlashCardBase, FlashCardGeneratorBase
import random
from abc import abstractmethod
from typing import Optional, Union
from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup


class MultipleChoice(FlashCardBase):
    question: str
    display: Optional[Union[MoleculeEntry, FunctionalGroup]] = Field(
        None, description="Molecule or functional group to display if required"
    )
    choices: list
    answer_index: int
    answer_molecule: Optional[MoleculeEntry] = Field(
        None, description="Molecule to view the information of if required"
    )

    @property
    def answer(self):
        return self.choices[self.answer_index]


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
            answer_index=correct,
            answer_molecule=example_molecules[correct],
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
            answer_index=correct,
            answer_molecule=example_molecules[correct],
        )


class MultipleChoiceNameToMoleculeGenerator(FlashCardGeneratorBase):

    name = "Multiple Choice - Name to Molecule"

    def next(self) -> MultipleChoice:
        example_molecules = random.sample(self.molecule_db.molecules, 4)
        correct = random.randint(0, 3)
        return MultipleChoice(
            question=f"Which of these molecules is {example_molecules[correct].name}?",
            choices=[mol for mol in example_molecules],
            answer_index=correct,
            answer_molecule=example_molecules[correct],
        )


class MultipleChoiceMoleculeToFunctionalGroupNameGenerator(FlashCardGeneratorBase):

    name = "Multiple Choice - Functional Group (SMARTS) to Name"

    def next(self) -> MultipleChoice:
        # Sample functional groups directly from the project's functional_groups.yaml
        # Be robust if the data file has fewer than 4 entries
        sample_count = min(4, len(FUNCTIONAL_GROUPS))
        example_fgs = random.sample(FUNCTIONAL_GROUPS, sample_count)
        correct = random.randrange(sample_count)
        chosen = example_fgs[correct]
        # Ask which name corresponds to the SMARTS pattern; display the functional group as a molecule
        return MultipleChoice(
            question=f"What is the name of this functional group?",
            display=chosen,
            choices=[fg.name for fg in example_fgs],
            answer_index=correct,
            answer_molecule=None,
        )
