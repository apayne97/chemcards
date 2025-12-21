from chemcards.database.core import MoleculeDB, MoleculeEntry
import pytest

class TestMoleculeEntry:
    def test_from_chembl_approved_drugs(self):


class TestMoleculeDB:
    def test_load(self):
        moleculedb = MoleculeDB.load()
        assert len(moleculedb.molecules) >= 4

    def test_from_chembl_approved_drugs(self):
        from chemcards.database.services.chembl import ChemblDB
        moleculedb = ChemblDB.from_mechanism()
        print(moleculedb)
        moleculedb.load()
        assert len(moleculedb.molecules) >= 4

