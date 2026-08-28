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
CANONICAL_TAGS = {
    "heterocycle", "nitrogen", "oxygen", "sulfur", "carbonyl", "halogen", "hydrocarbon", "aromatic",
}

_HALOGEN_ATOMIC_NUMS = {9, 17, 35, 53}
_CARBONYL_PATTERN = Chem.MolFromSmarts("[#6]=[OX1]")


def compute_tags(mol: "Chem.Mol") -> set[str]:
    """Derive which CANONICAL_TAGS apply to an arbitrary molecule, the same way the curated
    tags in functional_groups.yaml were assigned by hand.

    Used for quiz modes where the player supplies a molecule directly (e.g. draws a
    structure) instead of picking a known FUNCTIONAL_GROUPS/CHEMICAL_BUILDING_BLOCKS entry —
    those already carry curated `tags`, so this only needs to run against player input.
    """
    if mol is None:
        return set()
    Chem.GetSSSR(mol)  # ensure ring perception is computed before touching GetRingInfo()
    atoms = list(mol.GetAtoms())
    elements = {a.GetAtomicNum() for a in atoms}

    tags: set[str] = set()
    if elements <= {0, 1, 6}:  # 0 = wildcard/dummy atom (e.g. an unfilled R-group)
        tags.add("hydrocarbon")
    if 7 in elements:
        tags.add("nitrogen")
    if 16 in elements:
        tags.add("sulfur")
    if elements & _HALOGEN_ATOMIC_NUMS:
        tags.add("halogen")
    if any(a.GetIsAromatic() for a in atoms):
        tags.add("aromatic")

    # "carbonyl" is its own tag, distinct from "oxygen" — by curated convention, a carbonyl's
    # own =O doesn't also count as the generic "oxygen" tag (ketone is just ["carbonyl"]), but
    # a *second*, non-carbonyl oxygen still does (ester, C(=O)-O-C, is ["carbonyl", "oxygen"]).
    carbonyl_matches = mol.GetSubstructMatches(_CARBONYL_PATTERN)
    if carbonyl_matches:
        tags.add("carbonyl")
    carbonyl_oxygens = {
        idx for match in carbonyl_matches for idx in match
        if mol.GetAtomWithIdx(idx).GetAtomicNum() == 8
    }
    if any(a.GetAtomicNum() == 8 and a.GetIdx() not in carbonyl_oxygens for a in atoms):
        tags.add("oxygen")

    # "heterocycle" means a ring containing at least one non-carbon atom — not just "has a
    # ring" (e.g. the carbocyclic ring in para-quinone doesn't count).
    for ring in mol.GetRingInfo().AtomRings():
        if any(mol.GetAtomWithIdx(i).GetAtomicNum() != 6 for i in ring):
            tags.add("heterocycle")
            break

    return tags


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
