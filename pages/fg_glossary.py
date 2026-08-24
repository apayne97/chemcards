import yaml
import streamlit as st
from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS
from chemcards.database.resources import DATABASE
from utils import render_smarts

CATEGORY_LABELS = {
    "amide_derivatives": "Amide derivatives",
    "carbonyl_derivatives": "Carbonyl derivatives",
    "halogenated": "Halogenated",
    "hydrocarbon": "Hydrocarbon",
    "multiple_heteroatom_heteroaromatic": "Multi-heteroatom aromatics",
    "nitrogen_functionalities": "Nitrogen functionalities",
    "nitrogen_heteroaromatic": "Nitrogen heteroaromatics",
    "oxygen_functionalities": "Oxygen functionalities",
    "oxygen_heteroaromatic": "Oxygen heteroaromatics",
    "sulfur_functionalities": "Sulfur functionalities",
    "sulfur_heteroaromatic": "Sulfur heteroaromatics",
}

_yaml_order = yaml.safe_load((DATABASE / "functional_group_categories.yaml").read_text())
CATEGORY_ORDER = [c.replace(" ", "_") for c in _yaml_order]

st.title("⚗️ Functional Group Glossary")

all_cats = [c for c in CATEGORY_ORDER if any(fg.category == c for fg in FUNCTIONAL_GROUPS)]

with st.sidebar:
    st.markdown("### Filter")
    search = st.text_input("Search by name", "")
    selected_cats = st.multiselect(
        "Category",
        options=all_cats,
        format_func=lambda c: CATEGORY_LABELS.get(c, c.replace("_", " ").title()),
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
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        st.subheader(label)
        cols = st.columns(3)
        for i, fg in enumerate(sorted(by_cat[cat], key=lambda x: x.name)):
            with cols[i % 3]:
                img = render_smarts(fg.smarts, size=200)
                if img:
                    st.image(img)
                st.caption(f"**{fg.name}**")
                with st.expander("SMARTS"):
                    st.code(fg.smarts, language=None)
