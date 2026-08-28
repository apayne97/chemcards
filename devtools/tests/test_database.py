from chemcards.database.core import MoleculeDB, MoleculeEntry, DatabaseShrinkError
import chemcards.database.core as core
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

    @pytest.fixture
    def temp_db_path(self, tmp_path, monkeypatch):
        """Redirect MOLECULE_DATABASE to a scratch file so save() tests never touch the
        real database."""
        path = tmp_path / "molecule_database.json"
        monkeypatch.setattr(core, "MOLECULE_DATABASE", path)
        return path

    def _write(self, path, names):
        path.write_text(
            MoleculeDB(
                molecules=[MoleculeEntry(name=n, smiles="C") for n in names]
            ).model_dump_json()
        )

    def test_save_fully_replaces_existing_content(self, temp_db_path):
        """A molecule present in the old file but absent from the new build is dropped —
        save() no longer preserves "legacy" entries the current build doesn't reproduce.
        Same molecule count on both sides so this doesn't also trigger the shrink guard."""
        self._write(temp_db_path, [f"OLD{i}" for i in range(10)])

        fresh = MoleculeDB(molecules=[MoleculeEntry(name=f"NEW{i}", smiles="C") for i in range(10)])
        fresh.save()

        reloaded = MoleculeDB.load()
        assert [m.name for m in reloaded.molecules] == [f"NEW{i}" for i in range(10)]

    def test_save_refuses_large_shrink(self, temp_db_path):
        """A drop bigger than SHRINK_GUARD_FRACTION looks like a broken/partial build, not a
        real pruning — save() should refuse rather than silently wiping the database."""
        self._write(temp_db_path, [f"MOL{i}" for i in range(10)])

        fresh = MoleculeDB(molecules=[MoleculeEntry(name="MOL0", smiles="C")])  # 90% smaller
        with pytest.raises(DatabaseShrinkError):
            fresh.save()

        # refused — the file on disk is untouched
        assert len(MoleculeDB.load().molecules) == 10

    def test_save_force_overrides_shrink_guard(self, temp_db_path):
        self._write(temp_db_path, [f"MOL{i}" for i in range(10)])

        fresh = MoleculeDB(molecules=[MoleculeEntry(name="MOL0", smiles="C")])
        fresh.save(force=True)

        assert [m.name for m in MoleculeDB.load().molecules] == ["MOL0"]

    def test_save_allows_small_shrink(self, temp_db_path):
        """Dropping a couple of molecules out of many (e.g. a few no longer qualifying as
        Small molecule) is within SHRINK_GUARD_FRACTION and should save without force."""
        self._write(temp_db_path, [f"MOL{i}" for i in range(10)])

        fresh = MoleculeDB(molecules=[MoleculeEntry(name=f"MOL{i}", smiles="C") for i in range(9)])
        fresh.save()  # 10% smaller — right at the guard boundary, not over it

        assert len(MoleculeDB.load().molecules) == 9
