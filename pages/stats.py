import streamlit as st
import plotly.express as px
import pandas as pd
from collections import Counter

from utils import load_db

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
    mols = db.molecules
    targets = Counter(m.target for m in mols if m.target != "unknown")
    mechanisms = Counter(m.mechanism_of_action for m in mols if m.mechanism_of_action != "unknown")
    action_types = Counter(m.action_type for m in mols if m.action_type != "unknown")

    drug_classes: Counter = Counter()
    for m in mols:
        seen: set = set()
        for code in m.atc_classifications:
            label = ATC_L1.get(code[0]) if code else None
            if label and label not in seen:
                drug_classes[label] += 1
                seen.add(label)

    return {
        "total": len(mols),
        "n_targets": len(targets),
        "n_action_types": len(action_types),
        "n_mechanisms": len(mechanisms),
        "targets": targets,
        "mechanisms": mechanisms,
        "action_types": action_types,
        "drug_classes": drug_classes,
    }


GROUPINGS = {
    "Drug Class (ATC)": ("drug_classes", None),
    "Target (USAN)": ("targets", 20),
    "Mechanism of Action": ("mechanisms", 20),
    "Action Type": ("action_types", None),
}

stats = compute_stats()

col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image("assets/chemcards-logo.png", use_container_width=True)
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
st.plotly_chart(fig, use_container_width=True)
