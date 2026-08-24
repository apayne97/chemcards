import streamlit as st
import plotly.express as px
import pandas as pd
from collections import Counter

from utils import load_db, load_atc_lookup

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


@st.cache_data
def compute_stats() -> dict:
    db = load_db()
    atc_lookup = load_atc_lookup()
    mols = db.molecules
    targets = Counter(m.target for m in mols if m.target != "unknown")
    usan_stems = Counter(m.usan_stem_definition for m in mols if m.usan_stem_definition != "unknown")
    action_types = Counter(m.action_type for m in mols if m.action_type != "unknown")

    drug_classes: Counter = Counter()
    pharm_classes: Counter = Counter()
    for m in mols:
        seen_l1: set = set()
        seen_l3: set = set()
        for code in m.atc_classifications:
            if not code:
                continue
            # Level 1 (1 char): organ system
            l1 = ATC_L1.get(code[0])
            if l1 and l1 not in seen_l1:
                drug_classes[l1] += 1
                seen_l1.add(l1)
            # Level 3 (4 chars): pharmacological class
            if len(code) >= 4:
                l3_label = atc_lookup.get(code[:4])
                if l3_label and l3_label not in seen_l3:
                    pharm_classes[l3_label] += 1
                    seen_l3.add(l3_label)

    return {
        "total": len(mols),
        "n_targets": len(targets),
        "n_action_types": len(action_types),
        "targets": targets,
        "usan_stems": usan_stems,
        "action_types": action_types,
        "drug_classes": drug_classes,
        "pharm_classes": pharm_classes,
    }


GROUPINGS = {
    "Pharmacological Class (ATC)": ("pharm_classes", 25),
    "Organ System (ATC)": ("drug_classes", None),
    "Drug Family (USAN stem)": ("usan_stems", 20),
    "Biological Target": ("targets", 20),
    "Action Type": ("action_types", None),
}

stats = compute_stats()

col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image("assets/chemcards-logo.png", width="stretch")
with col_title:
    st.title("ChemCards")
    st.markdown(
        "An interactive flashcard app for learning FDA-approved drugs and functional groups. "
        "Use the sidebar to start a quiz."
    )

st.divider()

# --- Summary metrics ---
c1, c2, c3 = st.columns(3)
c1.metric("Molecules", f"{stats['total']:,}")
c2.metric("Unique Targets", f"{stats['n_targets']:,}")
c3.metric("Action Types", f"{stats['n_action_types']:,}")

last_updated = load_db().last_updated
st.caption(
    f"Data sourced from ChEMBL · Last updated: {last_updated}"
    if last_updated else
    "Data sourced from ChEMBL · Last updated: unknown"
)

st.divider()

# --- Grouped bar chart with dropdown ---
grouping = st.selectbox("Group molecules by", list(GROUPINGS.keys()))
field_key, top_n = GROUPINGS[grouping]
counter = stats[field_key]

entries = counter.most_common(top_n)
df = pd.DataFrame(entries, columns=[grouping, "Count"]).sort_values("Count")

fig = px.bar(
    df,
    x="Count",
    y=grouping,
    orientation="h",
    color="Count",
    color_continuous_scale="teal",
)
fig.update_layout(
    coloraxis_showscale=False,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title=None,
    xaxis_title="Number of molecules",
    height=max(300, len(df) * 22),
)
st.plotly_chart(fig, width="stretch")

st.divider()

# --- Meet the author ---
st.markdown("#### Meet the author")
st.markdown(
    "ChemCards was built by **Alex Payne**, a computational chemist at the Chodera Lab. "
    "Learn more at [apayne.org](https://apayne.org/)."
)
