import re
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
    "ring", "ring_5", "ring_6", "nitrogen", "oxygen", "sulfur", "carbonyl", "halogen",
    "hydrocarbon", "aromatic",
}

# Plain-language description of what each tag actually means — shown in the glossary so the
# tags on every card (and MedChemble's naming-segment tiles, which check a guess's implied
# chemistry against these same tags) aren't just unexplained words.
TAG_DESCRIPTIONS: dict[str, str] = {
    "ring": "Contains at least one ring, carbocyclic or heterocyclic.",
    "ring_5": "Contains a 5-membered ring (e.g. furan, pyrrole, thiazole).",
    "ring_6": "Contains a 6-membered ring (e.g. pyridine, morpholine).",
    "nitrogen": "Contains at least one nitrogen atom.",
    "oxygen": "Contains an oxygen atom that isn't a carbonyl's own =O.",
    "sulfur": "Contains at least one sulfur atom.",
    "carbonyl": "Contains a C=O group.",
    "halogen": "Contains fluorine, chlorine, bromine, or iodine.",
    "hydrocarbon": "Made of only carbon and hydrogen — no heteroatoms at all.",
    "aromatic": "Contains an aromatic ring system.",
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

    # "ring" means any ring at all — carbocyclic (benzene, para-quinone) or heterocyclic
    # (pyridine, furan). A heterocycle is just a subset of this, not a separate tag. "ring_5"/
    # "ring_6" narrow that down by ring *size* — added specifically so naming-segment tiles
    # like "-ole" (a real 5-ring suffix) don't light up green against a 6-ring target just
    # because both happen to be "ring, aromatic" (caught via oxazole/pyridazine mix-ups in
    # MedChemble's naming-Wordle mode). A fused system can carry both (indole has one 5-ring
    # and one 6-ring); either size present is enough for its tag, independent of the other.
    ring_sizes = {len(ring) for ring in mol.GetRingInfo().AtomRings()}
    if ring_sizes:
        tags.add("ring")
    if 5 in ring_sizes:
        tags.add("ring_5")
    if 6 in ring_sizes:
        tags.add("ring_6")

    return tags


# Tracked individually as their own Wordle-style element tiles. Br and I are real but rare in
# this dataset, so they aren't broken out separately — see count_elements().
ELEMENT_ATOMIC_NUMS = {"O": 8, "N": 7, "S": 16, "F": 9, "Cl": 17}


def count_elements(mol: "Chem.Mol") -> dict[str, int]:
    """Count O/N/S/F/Cl atoms in a molecule — for Wordle-style "Elements" tiles (exact count =
    green, present but the wrong count = yellow) rather than plain presence/absence. Br/I are
    real halogens but rare enough in this dataset that they aren't tracked as their own tile.
    """
    counts = {name: 0 for name in ELEMENT_ATOMIC_NUMS}
    if mol is None:
        return counts
    z_to_name = {z: name for name, z in ELEMENT_ATOMIC_NUMS.items()}
    for atom in mol.GetAtoms():
        name = z_to_name.get(atom.GetAtomicNum())
        if name:
            counts[name] += 1
    return counts


# ---------------------------------------------------------------------------
# Naming segments — for MedChemble's "Write the name" mode. A small library of recognizable
# IUPAC-ish prefixes/suffixes (from linear functional-group nomenclature, plus a few safe
# Hantzsch-Widman-style heteroatom/ring-size roots for the curated ring systems) mapped to the
# CANONICAL_TAGS chemistry each one implies. parse_naming_segments() scans arbitrary guess text
# for these, longest match first, so a guess doesn't need to *be* the target's name to earn
# credit — typing "propanol" against a target that has a hydroxyl group anywhere should still
# light up the "-ol" tile, because the underlying chemistry is genuinely shared. Each entry is
# (match_pattern, display_label, implied_tags) — the pattern is what's searched for (lowercase,
# no spaces/hyphens); the label is what the player sees on the tile.
#
# Deliberately conservative: every pattern here is checked (in
# devtools/tests/test_functional_groups.py) to never imply a tag that isn't actually true for
# the curated entry whose name it's drawn from — no pattern is registered "for" one entry only,
# since matching is a flat scan over whatever text is typed, checked against whatever the real
# target's tags are, not against which entry a pattern was first written for. Two documented
# exceptions where the implied chemistry can legitimately fall short (checked as such, not
# excluded — see the test): "anhydride" against "beta-keto anhydride" (misnamed — it's actually
# a 1,3-diketone, no O-bridge) and "amide" against "sulfonamide" (S-based, not C=O-based; it
# also gets its own "sulfon-" prefix so the real chemistry still lands somewhere). A few other
# things to know before touching this list:
#   - "az"/"ole": oxazole's/imidazole's "-azo-" is NOT the azo (N=N) functional group — it's
#     the elided Hantzsch-Widman "aza-" (nitrogen-in-ring) root running into the "-ole" (5-ring,
#     unsaturated) suffix, spelled with only one "a" once elided (neither word contains "aza"
#     as a literal substring). Split into these two so a guess like "imidazole" against target
#     "oxazole" correctly credits nitrogen + ring/aromatic without implying an azo linkage.
#   - "ox" (not "oxa"): in "oxazole", "oxa-" and "az-" overlap on the shared middle letter
#     (ox-A-zole) — a non-overlapping scanner can only claim one interpretation of that letter,
#     so if "oxa" (3 letters) claims it, "az" can no longer match right after. Shortening to
#     "ox" (2 letters) leaves that shared letter for "az" to pick up, so oxazole correctly
#     yields oxygen + nitrogen + ring/aromatic instead of losing the nitrogen tile.
#   - "thio"/"thia": same sulfur root, two spellings depending on what follows (thiophene vs.
#     thiazole) — both registered.
#   - Retained/non-compositional names (morpholine, furan, pyrrole, indole's own base name,
#     pyridine/pyrimidine, the tetrahydro-* saturated rings) intentionally have few or no
#     segments — they lean on the letter-Wordle layer (wordle_letter_diff in utils.py) instead.
NAMING_SEGMENTS: list[tuple[str, str, frozenset[str]]] = [
    ("sulfon", "sulfon-", frozenset({"sulfur", "oxygen"})),
    ("sulfoxide", "sulfoxide", frozenset({"sulfur", "oxygen"})),
    ("sulfone", "sulfone", frozenset({"sulfur", "oxygen"})),
    ("sulfide", "sulfide", frozenset({"sulfur"})),
    ("disulfide", "disulfide", frozenset({"sulfur"})),
    ("thiol", "-thiol", frozenset({"sulfur"})),
    ("thio", "thio-", frozenset({"sulfur"})),
    # 3 letters, not 4 ("thia"): same shared-letter overlap as oxa/az above — "thi" leaves the
    # "a" free for "az" to claim in "thiazole" (thi-A-zole), so it correctly yields both sulfur
    # and nitrogen instead of losing the nitrogen tile.
    ("thi", "thia-", frozenset({"sulfur"})),
    ("ox", "oxa-", frozenset({"oxygen"})),
    ("ether", "ether", frozenset({"oxygen"})),
    ("oicacid", "-oic acid", frozenset({"carbonyl", "oxygen"})),
    ("oate", "-oate", frozenset({"carbonyl", "oxygen"})),
    ("anhydride", "anhydride", frozenset({"carbonyl", "oxygen"})),
    ("amide", "amide", frozenset({"carbonyl", "nitrogen"})),
    ("urea", "urea", frozenset({"carbonyl", "nitrogen"})),
    ("lactam", "lactam", frozenset({"ring", "nitrogen", "carbonyl"})),
    ("keto", "keto-", frozenset({"carbonyl"})),
    ("one", "-one", frozenset({"carbonyl"})),
    ("acyl", "acyl-", frozenset({"carbonyl"})),
    ("oyl", "-oyl", frozenset({"carbonyl"})),
    ("quinone", "quinone", frozenset({"ring", "carbonyl"})),
    ("ol", "-ol", frozenset({"oxygen"})),
    ("amine", "amine", frozenset({"nitrogen"})),
    ("imine", "imine", frozenset({"nitrogen"})),
    ("nitrile", "nitrile", frozenset({"nitrogen"})),
    ("hydrazine", "hydrazine", frozenset({"nitrogen"})),
    ("nitro", "nitro-", frozenset({"nitrogen", "oxygen"})),
    ("az", "aza-", frozenset({"nitrogen"})),
    # "ring_5", not the generic "ring" — "-ole" specifically names a 5-membered ring (Hantzsch-
    # Widman), so it shouldn't light up green against a 6-membered target just because both are
    # "some kind of aromatic ring" (caught via a pyrazole guess going green against a pyridazine
    # target, which only shares nitrogen + *a* ring, not a 5-membered one).
    ("ole", "-ole", frozenset({"ring_5", "aromatic"})),
    ("phenyl", "phenyl-", frozenset({"ring", "aromatic"})),
    ("aryl", "aryl-", frozenset({"ring", "aromatic"})),
    ("halide", "halide", frozenset({"halogen"})),
    ("ane", "-ane", frozenset({"hydrocarbon"})),
    ("ene", "-ene", frozenset({"hydrocarbon"})),
    ("yne", "-yne", frozenset({"hydrocarbon"})),
    ("methyl", "methyl", frozenset({"hydrocarbon"})),
    ("ethyl", "ethyl", frozenset({"hydrocarbon"})),
]
# Longest pattern first so e.g. "sulfone" (7 letters) is tried before "sulfon" (6) at the same
# starting position, and "sulfoxide" before "sulfo"-anything shorter.
_NAMING_SEGMENTS_BY_LENGTH = sorted(NAMING_SEGMENTS, key=lambda item: -len(item[0]))

# "-ane"/"-ene"/"-yne" (hydrocarbon) are real suffixes but short enough to false-match inside
# an unrelated word ending the same way: "thiophene"/"tetrahydrothiophene" end in "...phene",
# whose last three letters spell "ene"; "dioxane" ends in "...oxane", whose last three letters
# spell "ane" (Hantzsch-Widman also reuses "-ane" for a saturated heterocycle, a different
# meaning than the plain-hydrocarbon one this game tracks). Guard against both by refusing
# these three specifically right after "h" or "x".
_HYDROCARBON_SUFFIXES = {"ane", "ene", "yne"}


def parse_naming_segments(text: str) -> list[tuple[str, frozenset[str]]]:
    """Scan `text` for known naming segments, longest match first, left to right,
    non-overlapping. Returns (display_label, implied_tags) for each segment found — the caller
    checks that chemistry against the real target, not against the guess."""
    if not text:
        return []
    lowered = re.sub(r"[^a-z]", "", text.lower())
    found: list[tuple[str, frozenset[str]]] = []
    i = 0
    while i < len(lowered):
        for pat, label, tags in _NAMING_SEGMENTS_BY_LENGTH:
            if not lowered.startswith(pat, i):
                continue
            if pat in _HYDROCARBON_SUFFIXES and i > 0 and lowered[i - 1] in "hx":
                continue
            found.append((label, tags))
            i += len(pat)
            break
        else:
            i += 1
    return found


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

# The player/browsing-facing surfaces (MedChemble, the glossary, "Build Your Own Quiz") present
# functional groups and chemical building blocks together under one "Chemical Building Block"
# umbrella, with `kind` kept only as an internal filter facet — see build_filtered_pool() in
# utils.py. This is the combined pool those pages iterate over.
ALL_BUILDING_BLOCKS = _ALL_FUNCTIONAL_GROUPS

KIND_LABELS = {"functional_group": "Functional Group", "chemical_building_block": "Building Block"}
