from chemcards.database.core import MoleculeEntry, MoleculeDB
from chemcards.gui.molecules import MoleculeViz, MoleculeWindow
from chemcards.database.services.chembl import open_chembl_molecule_link
import pytest

@pytest.fixture
def molecule():
    from chemcards.database.core import MoleculeEntry
    return MoleculeEntry(name="benzene",
                         smiles="CCCCCC")

def test_main_window_settings(molecule):
    from chemcards.gui.core import WindowOptions
    wo = WindowOptions.from_screen()

@pytest.mark.skip(reason="Not sure how to test window creation")
def test_chembl_link(molecule):
    assert open_chembl_molecule_link(molecule=molecule)

@pytest.mark.skip(reason="Not sure how to test window creation")
def test_molecule_window(molecule):
    molwindow = MoleculeWindow(molecule=molecule)
