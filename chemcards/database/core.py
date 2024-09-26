from pydantic import BaseModel, Field
from chemcards.database.resources import MOLECULE_DATABASE
import json
from abc import abstractmethod
from rdkit.Chem import Mol, MolFromSmiles


class MoleculeEntry(BaseModel):
    name: str
    smiles: str
    target: str = Field("unknown")
    indication: str = Field("unknown")
    mechanism_of_action: str = Field("unknown")
    action_type: str = Field("unknown")
    molecule_chembl_id: str = Field("unknown")
    target_chembl_id: str = Field("unknown")

    def to_rdkit(self) -> Mol:
        return MolFromSmiles(self.smiles)


class MoleculeDB(BaseModel):
    molecules: list[MoleculeEntry]

    def update(self, other: "MoleculeDB") -> "MoleculeDB":

        self_molecules = {molecule.name: molecule for molecule in self.molecules}
        other_molecules = {molecule.name: molecule for molecule in other.molecules}
        self_molecules.update(other_molecules)

        return MoleculeDB(molecules=list(self_molecules.values()))

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
