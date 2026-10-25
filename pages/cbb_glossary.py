"""Chemical Building Blocks glossary — covers both functional groups and chemical building
blocks (the former separate Functional Group Glossary) as one browsable pool, with `kind`
kept only as an internal filter facet."""
import streamlit as st
from chemcards.database.cheminformatics import (
    ALL_BUILDING_BLOCKS, FunctionalGroup, KIND_LABELS, TAG_DESCRIPTIONS,
)
from chemcards.scripts.generate_catalog import _catalog_sort_key
from utils import render_fg, all_tags, tag_label


def _sort_key(entry: FunctionalGroup):
    """Same element-composition ordering as the PDF catalog (generate_catalog.py) — hydrocarbon,
    then single-heteroatom groups, then multi-heteroatom, each acyclic-before-heterocycle."""
    return _catalog_sort_key(entry.model_dump())


st.title("🧱 Chemical Building Blocks")
st.caption(
    "Functional groups, heterocyclic ring scaffolds, and other multi-part structures — "
    "bigger than a single reactive group, but not a full drug."
)

available_tags = all_tags(ALL_BUILDING_BLOCKS)

with st.expander("What do the tags mean?"):
    st.markdown(
        "Every card below is tagged with the structural features it actually has — the same "
        "tags MedChemble's naming-segment tiles check a guess's implied chemistry against."
    )
    for tag in sorted(available_tags):
        st.markdown(f"**{tag_label(tag)}** — {TAG_DESCRIPTIONS.get(tag, '')}")

with st.sidebar:
    st.markdown("### Filter")
    search = st.text_input("Search by name", "")
    selected_kinds = st.multiselect("Kind", options=list(KIND_LABELS.values()),
                                    default=list(KIND_LABELS.values()))
    selected_tags = st.multiselect("Tags", options=available_tags, default=[], placeholder="All tags")

entries = ALL_BUILDING_BLOCKS
if search:
    entries = [e for e in entries if search.lower() in e.name.lower()]
entries = [e for e in entries if KIND_LABELS[e.kind] in selected_kinds]
if selected_tags:
    entries = [e for e in entries if set(e.tags) & set(selected_tags)]

if not entries:
    st.info("No chemical building blocks match your search.")
else:
    cols = st.columns(3)
    for i, entry in enumerate(sorted(entries, key=_sort_key)):
        with cols[i % 3]:
            img = render_fg(entry, size=200)
            if img:
                st.image(img)
            st.caption(f"**{entry.name}**")
            if entry.tags:
                for tag in entry.tags:
                    st.badge(tag)
            with st.expander("SMARTS"):
                st.code(entry.smarts, language=None)
