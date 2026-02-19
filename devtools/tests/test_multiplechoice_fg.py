from chemcards.flashcards.multiplechoice import MultipleChoiceMoleculeToFunctionalGroupNameGenerator
from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup


def test_functional_group_generator_returns_fg_display():
    # Use the molecule DB load path but don't require molecules for this generator
    gen = MultipleChoiceMoleculeToFunctionalGroupNameGenerator(molecule_db=None)
    q = gen.next()
    # display should be a FunctionalGroup
    assert isinstance(q.display, FunctionalGroup)
    # choices should be strings (names)
    assert all(isinstance(c, str) for c in q.choices)
    # answer_index should be within range
    assert 0 <= q.answer_index < len(q.choices)
    # the answer should equal the choice at answer_index
    assert q.answer == q.choices[q.answer_index]
