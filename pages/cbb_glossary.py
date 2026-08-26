import streamlit as st
from rdkit.Chem import MolFromSmiles, MolFromSmarts
from chemcards.database.cheminformatics import CHEMICAL_BUILDING_BLOCKS, FunctionalGroup
from utils import render_fg, FG_CATEGORY_LABELS


def _atom_count(fg: FunctionalGroup) -> int:
    mol = MolFromSmiles(fg.display_smiles) if fg.display_smiles else MolFromSmarts(fg.smarts)
    return mol.GetNumHeavyAtoms() if mol else 0


st.title("🧱 Chemical Building Blocks")
st.caption(
    "Heterocyclic ring scaffolds and other multi-part structures — bigger than a functional "
    "group, but not a full drug."
)

all_tags = sorted({tag for cbb in CHEMICAL_BUILDING_BLOCKS for tag in cbb.tags})

with st.sidebar:
    st.markdown("### Filter")
    search = st.text_input("Search by name", "")
    selected_tags = st.multiselect("Tags", options=all_tags, default=[], placeholder="All tags")

cbbs = CHEMICAL_BUILDING_BLOCKS
if search:
    cbbs = [cbb for cbb in cbbs if search.lower() in cbb.name.lower()]
if selected_tags:
    cbbs = [cbb for cbb in cbbs if set(cbb.tags) & set(selected_tags)]

if not cbbs:
    st.info("No chemical building blocks match your search.")
else:
    cols = st.columns(3)
    for i, cbb in enumerate(sorted(cbbs, key=_atom_count)):
        with cols[i % 3]:
            img = render_fg(cbb, size=200)
            if img:
                st.image(img)
            st.caption(f"**{cbb.name}**")
            label = FG_CATEGORY_LABELS.get(cbb.category, cbb.category.replace("_", " ").title()) if cbb.category else "—"
            st.caption(label)
            if cbb.tags:
                for tag in cbb.tags:
                    st.badge(tag)
            with st.expander("SMARTS"):
                st.code(cbb.smarts, language=None)
