from chemcards.database.core import MoleculeDB, MoleculeEntry
import pytest


class TestMoleculeEntry:
    def test_from_chembl_approved_drugs(self):
        pass


class TestMoleculeDB:
    def test_load(self):
        moleculedb = MoleculeDB.load()
        assert len(moleculedb.molecules) >= 4

    @pytest.mark.skip(reason="requires ChEMBL network access")
    def test_from_chembl_approved_drugs(self):
        from chemcards.database.services.chembl import ChemblDB
        moleculedb = ChemblDB.from_mechanism()
        moleculedb.load()
        assert len(moleculedb.molecules) >= 4

    def test_update_backfills_all_targets_for_preserved_legacy_entries(self):
        """A molecule only present in `other` (e.g. a legacy entry predating the
        all_targets/mechanism-join pipeline) can have a real `target` but an empty
        `all_targets`. update() should backfill all_targets=[target] for it."""
        legacy = MoleculeEntry(name="LEGACY", smiles="C", target="Some Receptor", all_targets=[])
        other = MoleculeDB(molecules=[legacy])
        fresh = MoleculeDB(molecules=[])

        merged = fresh.update(other)

        result = next(m for m in merged.molecules if m.name == "LEGACY")
        assert result.all_targets == ["Some Receptor"]

    def test_update_does_not_touch_unknown_target(self):
        """A molecule with no known target at all should stay untouched — nothing to backfill."""
        legacy = MoleculeEntry(name="LEGACY", smiles="C", target="unknown", all_targets=[])
        other = MoleculeDB(molecules=[legacy])
        fresh = MoleculeDB(molecules=[])

        merged = fresh.update(other)

        result = next(m for m in merged.molecules if m.name == "LEGACY")
        assert result.all_targets == []

    def test_update_does_not_touch_fresh_entries(self):
        """A fresh-build entry that already has all_targets set should be left alone —
        fresh entries always win on conflict regardless."""
        fresh_entry = MoleculeEntry(name="FRESH", smiles="C", target="A", all_targets=["A", "B"])
        fresh = MoleculeDB(molecules=[fresh_entry])
        other = MoleculeDB(molecules=[])

        merged = fresh.update(other)

        result = next(m for m in merged.molecules if m.name == "FRESH")
        assert result.all_targets == ["A", "B"]
