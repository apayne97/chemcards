from chemcards.database.core import MoleculeEntry, MoleculeDB
from pydantic import BaseModel, Field
from chemcards.database.resources import FUNCTIONAL_GROUPS_DATABASE
import yaml
from collections import defaultdict
from rdkit import Chem


class FunctionalGroup(BaseModel):
    name: str
    category: str = Field(None)
    smarts: str

    class Config:
        frozen = True

    def match(self, molecule: MoleculeEntry) -> bool:
        patt = Chem.MolFromSmarts(self.smarts)
        rmol = molecule.to_rdkit()
        return rmol.HasSubstructMatch(patt)

    def to_rdkit(self) -> Chem.Mol:
        return Chem.MolFromSmarts(self.smarts)


class AnnotatedMoleculeEntry(MoleculeEntry):
    functional_groups: list[FunctionalGroup]
    anti_functional_groups: list[FunctionalGroup]


FUNCTIONAL_GROUPS = [
    FunctionalGroup(**fg)
    for fg in yaml.safe_load(FUNCTIONAL_GROUPS_DATABASE.read_text())
]


class FunctionalGroupDatabase(BaseModel):
    functional_groups: dict[FunctionalGroup, list[MoleculeEntry]]
    anti_functional_groups: dict[FunctionalGroup, list[MoleculeEntry]]

    @classmethod
    def from_moleculedb(cls, db: MoleculeDB) -> "FunctionalGroupDatabase":
        fgs = defaultdict(list)
        afgs = defaultdict(list)
        for molecule in db.molecules:
            molecule_fgs = []
            molecule_afgs = []

            for fg in FUNCTIONAL_GROUPS:
                if fg.match(molecule):
                    molecule_fgs.append(fg)
                else:
                    molecule_afgs.append(fg)
            annotated_molecule = AnnotatedMoleculeEntry(
                **molecule.dict(),
                functional_groups=molecule_fgs,
                anti_functional_groups=molecule_afgs,
            )
            for fg in molecule_fgs:
                fgs[fg].append(annotated_molecule)
            for fg in molecule_afgs:
                afgs[fg].append(annotated_molecule)

        return FunctionalGroupDatabase(
            functional_groups=fgs,
            anti_functional_groups=afgs,
        )
