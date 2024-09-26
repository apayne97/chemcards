from chemcards.database.core import MoleculeEntry, MoleculeDB
from chemcards.gui.molecules import MoleculeViz, MoleculeWindow
from chemcards.database.services.chembl import open_chembl_molecule_link
import pytest

@pytest.fixture
def mdb():
    return MoleculeDB.load()


@pytest.fixture
def molecule(mdb):
    return mdb.molecules[0]

def test_chembl_link(molecule):
    assert open_chembl_molecule_link(molecule=molecule)


def test_molecule_window(molecule):
    molwindow = MoleculeWindow(molecule=molecule)