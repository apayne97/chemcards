from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup
from chemcards.flashcards.multiplechoice import (
    MultipleChoice,
    MultipleChoiceMoleculeToTargetGenerator,
    MultipleChoiceMoleculeToNameGenerator,
    MultipleChoiceNameToMoleculeGenerator,
)
from chemcards.database.core import MoleculeDB
import pytest


@pytest.fixture(scope="module")
def db():
    return MoleculeDB.load()


def test_multiple_choice_model():
    from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS
    fg = FUNCTIONAL_GROUPS[0]
    q = MultipleChoice(
        question="What is this?",
        display=fg,
        choices=["a", "b", "c", "d"],
        answer_index=0,
    )
    assert q.answer == "a"
    assert isinstance(q.display, FunctionalGroup)


def test_molecule_to_target_generator(db):
    gen = MultipleChoiceMoleculeToTargetGenerator(molecule_db=db)
    q = gen.next()
    assert isinstance(q, MultipleChoice)
    assert len(q.choices) == 4
    assert 0 <= q.answer_index < 4
    assert q.answer == q.choices[q.answer_index]
    assert len(set(q.choices)) == 4  # no duplicate targets among the answer choices


def test_molecule_to_name_generator(db):
    gen = MultipleChoiceMoleculeToNameGenerator(molecule_db=db)
    q = gen.next()
    assert isinstance(q, MultipleChoice)
    assert len(q.choices) == 4
    assert q.answer == q.choices[q.answer_index]


def test_name_to_molecule_generator(db):
    gen = MultipleChoiceNameToMoleculeGenerator(molecule_db=db)
    q = gen.next()
    assert isinstance(q, MultipleChoice)
    assert len(q.choices) == 4
    assert q.answer_index < len(q.choices)
