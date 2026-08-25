import json
import streamlit as st
from collections import Counter
from rdkit import Chem
from rdkit.Chem import MolFromSmiles, MolFromSmarts, AllChem
from rdkit.Chem import rdRGroupDecomposition
from rdkit.Chem.Draw import rdMolDraw2D

from chemcards.database.core import MoleculeDB
from chemcards.database.resources import CHEMBL_ATC_DOWNLOAD
from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS

# ---------------------------------------------------------------------------
# ATC constants
# ---------------------------------------------------------------------------
ATC_L1 = {
    "A": "Alimentary tract & metabolism",
    "B": "Blood & blood-forming organs",
    "C": "Cardiovascular system",
    "D": "Dermatologicals",
    "G": "Genito-urinary system & sex hormones",
    "H": "Systemic hormonal preparations",
    "J": "Antiinfectives (systemic)",
    "L": "Antineoplastic & immunomodulating",
    "M": "Musculoskeletal system",
    "N": "Nervous system",
    "P": "Antiparasitic products",
    "R": "Respiratory system",
    "S": "Sensory organs",
    "V": "Various",
}

LEVEL_CHARS = [1, 3, 4, 5]
ATC_LEVEL_NAMES = ["Organ System", "Therapeutic Area", "Pharmacological Class", "Chemical Class"]

# ---------------------------------------------------------------------------
# Functional group constants
# ---------------------------------------------------------------------------
FG_CATEGORY_LABELS = {
    "amide_derivatives": "Amide derivatives",
    "carbonyl_derivatives": "Carbonyl derivatives",
    "halogenated": "Halogenated",
    "hydrocarbon": "Hydrocarbon",
    "multiple_heteroatom_acyclic": "Multi-heteroatom acyclic",
    "multiple_heteroatom_heterocycles": "Multi-heteroatom heterocycles",
    "nitrogen_functionalities": "Nitrogen functionalities",
    "nitrogen_heterocycles": "Nitrogen heterocycles",
    "oxygen_functionalities": "Oxygen functionalities",
    "oxygen_heterocycles": "Oxygen heterocycles",
    "sulfur_functionalities": "Sulfur functionalities",
    "sulfur_heterocycles": "Sulfur heterocycles",
}


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------
def norm_name(s: str) -> str:
    return "".join(s.lower().split()).replace("-", "").replace(",", "")


def tile_html(label: str, match: bool, level: str) -> str:
    bg = "#538d4e" if match else "#3a3a3c"
    return (
        f"<div style='background:{bg};color:white;border-radius:6px;padding:8px 6px;"
        f"text-align:center;margin:2px;min-height:60px;display:flex;"
        f"flex-direction:column;justify-content:center;'>"
        f"<div style='font-size:0.65em;opacity:0.75;margin-bottom:2px;'>{level}</div>"
        f"<div style='font-size:0.8em;font-weight:600;line-height:1.2;'>{label}</div>"
        f"</div>"
    )


def show_quiz_result(score: int, total: int, on_back) -> None:
    st.title("Quiz Complete!")
    pct = round(100 * score / total) if total > 0 else 0
    st.metric("Final Score", f"{score}/{total}", f"{pct}%")
    if pct >= 80:
        st.success("Great job!")
    elif pct >= 50:
        st.info("Good effort — keep practicing.")
    else:
        st.warning("Keep studying — you'll get there!")
    if st.button("Back to Menu", type="primary"):
        on_back()


# ---------------------------------------------------------------------------
# Functional group helpers
# ---------------------------------------------------------------------------
def fg_all_categories() -> list[str]:
    return sorted({fg.category for fg in FUNCTIONAL_GROUPS if fg.category})


def fg_counts_by_category() -> dict[str, int]:
    return Counter(fg.category for fg in FUNCTIONAL_GROUPS if fg.category)


def build_filtered_fgs(prefix: str) -> list:
    return [
        fg for fg in FUNCTIONAL_GROUPS
        if fg.category and st.session_state.get(f"{prefix}cat_{fg.category}", True)
    ]


# ---------------------------------------------------------------------------
# Drug DB helpers
# ---------------------------------------------------------------------------
@st.cache_resource
def load_db() -> MoleculeDB:
    return MoleculeDB.load()


@st.cache_resource
def load_atc_lookup() -> dict[str, str]:
    if not CHEMBL_ATC_DOWNLOAD.exists():
        return {}
    with open(CHEMBL_ATC_DOWNLOAD) as f:
        return json.load(f)


@st.cache_data
def compute_l3_data() -> tuple[list[str], dict[str, str], dict[str, int], int]:
    atc_lookup = load_atc_lookup()
    db = load_db()
    code_counts: Counter = Counter()
    no_atc = 0
    for m in db.molecules:
        if m.atc_classifications:
            seen: set = set()
            for code in m.atc_classifications:
                if len(code) >= 4:
                    l3 = code[:4]
                    if l3 not in seen:
                        code_counts[l3] += 1
                        seen.add(l3)
        else:
            no_atc += 1
    label_to_code: dict[str, str] = {}
    label_to_count: dict[str, int] = {}
    for code, count in code_counts.items():
        if count >= 4:
            label = atc_lookup.get(code)
            if label:
                label_to_code[label] = code
                label_to_count[label] = count
    sorted_labels = sorted(label_to_count, key=lambda l: -label_to_count[l])
    return sorted_labels, label_to_code, label_to_count, no_atc


def build_filtered_drug_db(prefix: str) -> MoleculeDB:
    db = load_db()
    _, label_to_code, _, _ = compute_l3_data()
    selected_labels: list[str] = st.session_state.get(f"{prefix}l3_select", [])
    include_none: bool = st.session_state.get(f"{prefix}atc_none", True)
    if not selected_labels:
        if include_none:
            return db
        return db.subset([m for m in db.molecules if m.atc_classifications])
    selected_codes = {label_to_code[l] for l in selected_labels if l in label_to_code}
    mols = []
    for m in db.molecules:
        if m.atc_classifications:
            if any(len(c) >= 4 and c[:4] in selected_codes for c in m.atc_classifications if c):
                mols.append(m)
        elif include_none:
            mols.append(m)
    return db.subset(mols)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _draw_mol(mol, size: int) -> bytes | None:
    if mol is None:
        return None
    d = rdMolDraw2D.MolDraw2DCairo(size, size)
    rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
    d.FinishDrawing()
    return d.GetDrawingText()


def render_smiles(smiles: str, size: int = 300) -> bytes | None:
    return _draw_mol(MolFromSmiles(smiles), size)


def render_smarts(smarts: str, size: int = 300) -> bytes | None:
    return _draw_mol(MolFromSmarts(smarts), size)


def _add_polar_hs(mol: Chem.Mol) -> Chem.Mol:
    mol = Chem.AddHs(mol)
    rw = Chem.RWMol(mol)
    to_remove = sorted(
        [a.GetIdx() for a in rw.GetAtoms()
         if a.GetAtomicNum() == 1
         and all(n.GetAtomicNum() == 6 for n in a.GetNeighbors())],
        reverse=True,
    )
    for idx in to_remove:
        rw.RemoveAtom(idx)
    Chem.SanitizeMol(rw)
    return rw.GetMol()


def render_fg(fg, size: int = 300) -> bytes | None:
    if fg.display_smiles:
        mol = MolFromSmiles(fg.display_smiles)
        if mol:
            rdRGroupDecomposition.RelabelMappedDummies(mol)
            mol = _add_polar_hs(mol)
            AllChem.Compute2DCoords(mol)
            return _draw_mol(mol, size)
    return render_smarts(fg.smarts, size)
