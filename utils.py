import json
import streamlit as st
from rdkit import Chem
from rdkit.Chem import MolFromSmiles, MolFromSmarts, AllChem
from rdkit.Chem import rdRGroupDecomposition
from rdkit.Chem.Draw import rdMolDraw2D

from chemcards.database.core import MoleculeDB
from chemcards.database.resources import CHEMBL_ATC_DOWNLOAD
from chemcards.flashcards.filters import FILTERS


@st.cache_resource
def load_db() -> MoleculeDB:
    return MoleculeDB.load()


@st.cache_resource
def load_atc_lookup() -> dict[str, str]:
    if not CHEMBL_ATC_DOWNLOAD.exists():
        return {}
    with open(CHEMBL_ATC_DOWNLOAD) as f:
        return json.load(f)


@st.cache_resource
def load_filtered_db() -> MoleculeDB:
    db = load_db()
    for f in FILTERS:
        db = f(db)
    return db


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
