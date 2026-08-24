import json
import streamlit as st
from rdkit.Chem import MolFromSmiles, MolFromSmarts
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
