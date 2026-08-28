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

    def subset(self, molecules: list["MoleculeEntry"]) -> "MoleculeDB":
        return MoleculeDB.model_construct(molecules=molecules)

    def update(self, other: "MoleculeDB") -> "MoleculeDB":
        # Start with other (existing DB), then overwrite with self (new data).
        # self wins on conflicts so schema changes and fresh ChEMBL data always take effect.
        # Molecules only in other (e.g. manually added, or entries from a schema version
        # predating the all_targets/mechanism-join pipeline — e.g. peptide drugs ChEMBL's
        # current molecule_type="Small molecule" filter excludes) are preserved as-is.
        merged = {molecule.name: molecule for molecule in other.molecules}
        merged.update({molecule.name: molecule for molecule in self.molecules})

        # A preserved legacy entry can have a real `target` but an empty `all_targets` list
        # (that field didn't exist yet when it was written). Backfill so `all_targets` is never
        # spuriously empty when we already know at least one real target — cheap, always
        # correct (all_targets built by the current pipeline is never inconsistent with target
        # this way already), and self-heals for any future stale-preserved entry too.
        for name, molecule in merged.items():
            if not molecule.all_targets and molecule.target and molecule.target != "unknown":
                merged[name] = molecule.model_copy(update={"all_targets": [molecule.target]})

        return MoleculeDB.model_construct(molecules=list(merged.values()), last_updated=self.last_updated)

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
