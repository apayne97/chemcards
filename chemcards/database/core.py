from pydantic import BaseModel, Field
from chemcards.database.resources import MOLECULE_DATABASE
import json
import logging
from abc import abstractmethod
from rdkit.Chem import Mol, MolFromSmiles

logger = logging.getLogger(__name__)

# If a fresh build would shrink the saved database by more than this fraction, refuse to
# save — that's a sign the build ran against incomplete/failed data (e.g. a network hiccup
# partway through download_raw_data), not a real, expected pruning of unqualified molecules.
SHRINK_GUARD_FRACTION = 0.10


class MoleculeEntry(BaseModel):
    name: str
    smiles: str
    target: str = Field("unknown")
    all_targets: list[str] = Field(default_factory=list)
    usan_stem_definition: str = Field("unknown")
    indication: str = Field("unknown")
    mechanism_of_action: str = Field("unknown")
    action_type: str = Field("unknown")
    molecule_chembl_id: str = Field("unknown")
    target_chembl_id: str = Field("unknown")
    atc_classifications: list[str] = Field(default_factory=list)

    def to_rdkit(self) -> Mol:
        return MolFromSmiles(self.smiles)


class DatabaseShrinkError(RuntimeError):
    """Raised when save() would drop more molecules than SHRINK_GUARD_FRACTION allows."""


class MoleculeDB(BaseModel):
    molecules: list[MoleculeEntry]
    last_updated: str | None = None

    def subset(self, molecules: list["MoleculeEntry"]) -> "MoleculeDB":
        return MoleculeDB.model_construct(molecules=molecules)

    @classmethod
    def load(cls) -> "MoleculeDB":
        if not MOLECULE_DATABASE.exists():
            return MoleculeDB(molecules=[])
        else:
            with open(MOLECULE_DATABASE, "r") as f:
                return cls.model_validate_json(f.read())

    def save(self, force: bool = False) -> bool:
        """Persist this DB, replacing whatever was there.

        The saved file always reflects exactly the current build — a molecule ChEMBL no
        longer classifies the way we expect (e.g. dropped by molecule_type="Small molecule",
        or a duplicate salt-form entry ChEMBL later cleaned up) is removed, not preserved
        forever. If you want to keep a molecule ChEMBL's own query doesn't produce, that needs
        its own explicit step (see the unwired manually_added_molecules.yaml for a possible
        future home for that) rather than relying on "it happens to already be in the file."

        Refuses to save (raises DatabaseShrinkError) if this would shrink the existing file by
        more than SHRINK_GUARD_FRACTION — pass force=True to override once you've confirmed a
        larger drop is genuinely expected.
        """
        existing = MoleculeDB.load()
        if existing.molecules and not force:
            shrink = 1 - (len(self.molecules) / len(existing.molecules))
            if shrink > SHRINK_GUARD_FRACTION:
                raise DatabaseShrinkError(
                    f"Refusing to save: molecule count would drop from {len(existing.molecules)} "
                    f"to {len(self.molecules)} ({shrink:.0%} smaller). This usually means the "
                    f"build ran against incomplete data rather than a real pruning of "
                    f"unqualified molecules. Pass force=True if this drop is genuinely expected."
                )
        with open(MOLECULE_DATABASE, "w") as f:
            f.write(self.model_dump_json())
        return True
