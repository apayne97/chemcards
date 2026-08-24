import streamlit as st
import pandas as pd
from utils import load_db, load_atc_lookup, render_smiles

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
LEVEL_NAMES = ["Organ System", "Therapeutic Area", "Pharmacological Class", "Chemical Class"]

st.title("💊 Drug Glossary")

db = load_db()
atc_lookup = load_atc_lookup()

with st.sidebar:
    st.markdown("### Filter")
    search = st.text_input("Search by name", "")
    all_targets = sorted({m.target for m in db.molecules if m.target and m.target != "unknown"})
    selected_targets = st.multiselect("Biological target", all_targets, placeholder="All targets")

    all_l3: dict[str, str] = {}
    all_l4: dict[str, str] = {}
    for m in db.molecules:
        for code in m.atc_classifications:
            if len(code) >= 4:
                label = atc_lookup.get(code[:4])
                if label:
                    all_l3[label] = code[:4]
            if len(code) >= 5:
                label = atc_lookup.get(code[:5])
                if label:
                    all_l4[label] = code[:5]
    selected_l3 = st.multiselect("Pharmacological class (ATC L3)", sorted(all_l3), placeholder="All classes")
    selected_l4 = st.multiselect("Chemical class (ATC L4)", sorted(all_l4), placeholder="All classes")

mols = db.molecules
if search:
    mols = [m for m in mols if search.lower() in m.name.lower()]
if selected_targets:
    mols = [m for m in mols if m.target in selected_targets]
if selected_l3:
    selected_codes = {all_l3[l] for l in selected_l3}
    mols = [
        m for m in mols
        if any(len(c) >= 4 and c[:4] in selected_codes for c in m.atc_classifications)
    ]
if selected_l4:
    selected_codes = {all_l4[l] for l in selected_l4}
    mols = [
        m for m in mols
        if any(len(c) >= 5 and c[:5] in selected_codes for c in m.atc_classifications)
    ]

mol_list = sorted(mols, key=lambda x: x.name)
st.caption(f"{len(mol_list):,} drugs · click a row to see the structure")

def _atc_levels(m) -> dict[str, str]:
    codes = [c for c in m.atc_classifications if c]
    if not codes:
        return {}
    primary = max(codes, key=len)
    levels = {}
    for n_chars, name in zip(LEVEL_CHARS, LEVEL_NAMES):
        if len(primary) >= n_chars:
            prefix = primary[:n_chars]
            levels[name] = atc_lookup.get(prefix) or ATC_L1.get(prefix, prefix)
    return levels

rows = []
for m in mol_list:
    lvl = _atc_levels(m)
    rows.append({
        "Name": m.name,
        "Biological Target": m.target if m.target != "unknown" else "",
        "Drug Family (USAN)": m.usan_stem_definition if m.usan_stem_definition != "unknown" else "",
        "Organ System": lvl.get("Organ System", ""),
        "Therapeutic Area": lvl.get("Therapeutic Area", ""),
        "Pharmacological Class": lvl.get("Pharmacological Class", ""),
        "Chemical Class": lvl.get("Chemical Class", ""),
        "Mechanism": m.mechanism_of_action if m.mechanism_of_action != "unknown" else "",
    })

if not rows:
    st.info("No drugs match your filters.")
else:
    df = pd.DataFrame(rows)
    event = st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows
    if selected_rows:
        m = mol_list[selected_rows[0]]
        lvl = _atc_levels(m)

        st.divider()
        col_img, col_info = st.columns([1, 2])

        with col_img:
            img = render_smiles(m.smiles, size=280)
            if img:
                st.image(img)

        with col_info:
            st.markdown(f"### {m.name}")
            if m.target and m.target != "unknown":
                st.markdown(f"**Biological target:** {m.target}")
            if m.usan_stem_definition and m.usan_stem_definition != "unknown":
                st.markdown(f"**Drug family (USAN):** {m.usan_stem_definition}")
            if m.mechanism_of_action and m.mechanism_of_action != "unknown":
                st.markdown(f"**Mechanism:** {m.mechanism_of_action}")
            if lvl:
                st.markdown("**ATC classification:**")
                for name in LEVEL_NAMES:
                    if name in lvl:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{name}: {lvl[name]}")
            if m.molecule_chembl_id and m.molecule_chembl_id != "unknown":
                st.link_button(
                    "View on ChEMBL",
                    f"https://www.ebi.ac.uk/chembl/compound_report_card/{m.molecule_chembl_id}/",
                )
