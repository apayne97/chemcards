import streamlit as st
from rdkit.Chem import MolFromSmiles, MolFromSmarts
from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup
from utils import render_fg, all_tags


def _atom_count(fg: FunctionalGroup) -> int:
    mol = MolFromSmiles(fg.display_smiles) if fg.display_smiles else MolFromSmarts(fg.smarts)
    return mol.GetNumHeavyAtoms() if mol else 0


st.title("⚗️ Functional Group Glossary")

available_tags = all_tags(FUNCTIONAL_GROUPS)

with st.sidebar:
    st.markdown("### Filter")
    search = st.text_input("Search by name", "")
    selected_tags = st.multiselect("Tags", options=available_tags, default=[], placeholder="All tags")

fgs = FUNCTIONAL_GROUPS
if search:
    fgs = [fg for fg in fgs if search.lower() in fg.name.lower()]
if selected_tags:
    fgs = [fg for fg in fgs if set(fg.tags) & set(selected_tags)]

if not fgs:
    st.info("No functional groups match your search.")
else:
    cols = st.columns(3)
    for i, fg in enumerate(sorted(fgs, key=_atom_count)):
        with cols[i % 3]:
            img = render_fg(fg, size=200)
            if img:
                st.image(img)
            st.caption(f"**{fg.name}**")
            if fg.tags:
                for tag in fg.tags:
                    st.badge(tag)
            with st.expander("SMARTS"):
                st.code(fg.smarts, language=None)
