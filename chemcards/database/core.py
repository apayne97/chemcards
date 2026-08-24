from pydantic import BaseModel, Field
from chemcards.database.resources import MOLECULE_DATABASE
import json
from abc import abstractmethod
from rdkit.Chem import Mol, MolFromSmiles


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


class MoleculeDB(BaseModel):
    molecules: list[MoleculeEntry]
    last_updated: str | None = None

    def update(self, other: "MoleculeDB") -> "MoleculeDB":
        # Start with other (existing DB), then overwrite with self (new data).
        # self wins on conflicts so schema changes and fresh ChEMBL data always take effect.
        # Molecules only in other (e.g. manually added) are preserved.
        merged = {molecule.name: molecule for molecule in other.molecules}
        merged.update({molecule.name: molecule for molecule in self.molecules})
        return MoleculeDB(
            molecules=list(merged.values()),
            last_updated=self.last_updated,
        )

    @classmethod
    def load(cls) -> "MoleculeDB":
        if not MOLECULE_DATABASE.exists():
            return MoleculeDB(molecules=[])
        else:
            with open(MOLECULE_DATABASE, "r") as f:
                return cls.model_validate_json(f.read())

    def save(self) -> bool:
        existing_db = MoleculeDB.load()
        newdb = self.update(existing_db)
        with open(MOLECULE_DATABASE, "w") as f:
            f.write(newdb.model_dump_json())
