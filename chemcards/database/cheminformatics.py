from chemcards.database.core import MoleculeEntry
from pydantic import BaseModel, Field
from chemcards.database.resources import FUNCTIONAL_GROUPS_DATABASE
import yaml
from rdkit import Chem


class FunctionalGroup(BaseModel):
    name: str
    category: str = Field(None)
    smarts: str
    display_smiles: str = Field(None)

    class Config:
        frozen = True

    def match(self, molecule: MoleculeEntry) -> bool:
        patt = Chem.MolFromSmarts(self.smarts)
        rmol = molecule.to_rdkit()
        return rmol.HasSubstructMatch(patt)

    def to_rdkit(self) -> Chem.Mol:
        return Chem.MolFromSmarts(self.smarts)


FUNCTIONAL_GROUPS = [
    FunctionalGroup(**fg)
    for fg in yaml.safe_load(FUNCTIONAL_GROUPS_DATABASE.read_text())
]
