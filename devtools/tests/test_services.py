import pytest
from chemcards.database.services.chembl import ChemblDB, CHEMBL_DOWNLOAD, CHEMBL_MECHANISM_DOWNLOAD, ChemblMoleculeEntry, ChemblMechanismEntry
from chemcards.database.core import MoleculeEntry
import json


class TestChemblDB:
    @pytest.fixture
    def chembl_molecule_entry_dict(self):
        with open(CHEMBL_DOWNLOAD, "r") as f:
            molecule_list = json.load(f)
        return molecule_list[0]

    @pytest.fixture
    def chembl_mechanism_entry_dict(self):
        with open(CHEMBL_MECHANISM_DOWNLOAD, "r") as f:
            molecule_list = json.load(f)
        return molecule_list[0]

    def test_chembl_molecule_entry(self, chembl_molecule_entry_dict):
        molecule = ChemblMoleculeEntry.from_download(chembl_molecule_entry_dict)
        assert isinstance(molecule, ChemblMoleculeEntry)
        assert molecule.molecule_chembl_id == "CHEMBL2"

    def test_chembl_mechanism_entry(self, chembl_mechanism_entry_dict):
        molecule = ChemblMechanismEntry.from_download(chembl_mechanism_entry_dict)
        assert isinstance(molecule, ChemblMechanismEntry)
        assert molecule.molecule_chembl_id == "CHEMBL19"


