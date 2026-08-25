import yaml
import streamlit as st
from rdkit.Chem import MolFromSmiles, MolFromSmarts
from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup
from chemcards.database.resources import DATABASE
from utils import render_fg, FG_CATEGORY_LABELS

_yaml_order = yaml.safe_load((DATABASE / "functional_group_categories.yaml").read_text())
CATEGORY_ORDER = [c.replace(" ", "_") for c in _yaml_order]


def _atom_count(fg: FunctionalGroup) -> int:
    mol = MolFromSmiles(fg.display_smiles) if fg.display_smiles else MolFromSmarts(fg.smarts)
    return mol.GetNumHeavyAtoms() if mol else 0

st.title("⚗️ Functional Group Glossary")

all_cats = [c for c in CATEGORY_ORDER if any(fg.category == c for fg in FUNCTIONAL_GROUPS)]

with st.sidebar:
    st.markdown("### Filter")
    search = st.text_input("Search by name", "")
    selected_cats = st.multiselect(
        "Category",
        options=all_cats,
        format_func=lambda c: FG_CATEGORY_LABELS.get(c, c.replace("_", " ").title()),
        default=[],
        placeholder="All categories",
    )

fgs = FUNCTIONAL_GROUPS
if search:
    fgs = [fg for fg in fgs if search.lower() in fg.name.lower()]
if selected_cats:
    fgs = [fg for fg in fgs if fg.category in selected_cats]

by_cat: dict = {}
for fg in fgs:
    by_cat.setdefault(fg.category or "uncategorized", []).append(fg)

if not by_cat:
    st.info("No functional groups match your search.")
else:
    for cat in [c for c in CATEGORY_ORDER if c in by_cat]:
        label = FG_CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        st.subheader(label)
        cols = st.columns(3)
        for i, fg in enumerate(sorted(by_cat[cat], key=_atom_count)):
            with cols[i % 3]:
                img = render_fg(fg, size=200)
                if img:
                    st.image(img)
                st.caption(f"**{fg.name}**")
                with st.expander("SMARTS"):
                    st.code(fg.smarts, language=None)
