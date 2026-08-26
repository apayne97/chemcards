from chemcards.database.core import MoleculeEntry
from pydantic import BaseModel, Field
from chemcards.database.resources import FUNCTIONAL_GROUPS_DATABASE
import yaml
from rdkit import Chem


class FunctionalGroup(BaseModel):
    name: str
    kind: str = Field("functional_group")
    tags: list[str] = Field(default_factory=list)
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


# Closed vocabulary for FunctionalGroup.tags — validated by devtools/tests/test_functional_groups.py
# rather than a Pydantic Literal, since the chemical building blocks list is expected to keep
# growing with new tags (amino_acid, nucleotide, metabolite, etc.) as content is added.
CANONICAL_TAGS = {"heterocycle", "nitrogen", "oxygen", "sulfur", "carbonyl", "halogen", "hydrocarbon"}

_ALL_FUNCTIONAL_GROUPS = [
    FunctionalGroup(**fg)
    for fg in yaml.safe_load(FUNCTIONAL_GROUPS_DATABASE.read_text())
]

# "Functional group" is reserved for the small, classic reactive moieties. Heterocyclic ring
# scaffolds and other multi-part structures (amino acids, nucleotides, etc.) are tagged
# kind="chemical_building_block" in functional_groups.yaml instead — they're building blocks in
# their own right, not substituent groups.
FUNCTIONAL_GROUPS = [fg for fg in _ALL_FUNCTIONAL_GROUPS if fg.kind == "functional_group"]
CHEMICAL_BUILDING_BLOCKS = [fg for fg in _ALL_FUNCTIONAL_GROUPS if fg.kind == "chemical_building_block"]
