"""Pharmadle — Wordle-style drug identification game.

The player is shown a mystery molecule and must identify it by guessing drug
names.  Each guess is matched to the closest drug in the database; the four
ATC classification levels (organ system → therapeutic area → pharmacological
class → chemical subgroup) are shown as green / grey tiles, giving
progressively specific hints about where the mystery drug sits in the
hierarchy.
"""
import difflib
import json
import random
import streamlit as st
from collections import Counter

from chemcards.database.core import MoleculeDB, MoleculeEntry
from chemcards.database.resources import CHEMBL_ATC_DOWNLOAD
from utils import load_db, load_atc_lookup, render_smiles

MAX_GUESSES = 6
P = "pharmadle_"

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

# ATC prefix lengths for each level
LEVEL_CHARS = [1, 3, 4, 5]
LEVEL_NAMES = ["Organ System", "Therapeutic Area", "Pharmacological Class", "Chemical Subgroup"]


def _k(key):
    return P + key


def _norm(s: str) -> str:
    return "".join(s.lower().split()).replace("-", "").replace(",", "")


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
@st.cache_data
def compute_l3_data() -> tuple[list[str], dict[str, str], dict[str, int], int]:
    atc_lookup = load_atc_lookup()
    db = load_db()
    code_counts: Counter = Counter()
    no_atc = 0
    for m in db.molecules:
        if m.atc_classifications:
            seen: set = set()
            for code in m.atc_classifications:
                if len(code) >= 4:
                    l3 = code[:4]
                    if l3 not in seen:
                        code_counts[l3] += 1
                        seen.add(l3)
        else:
            no_atc += 1
    label_to_code: dict[str, str] = {}
    label_to_count: dict[str, int] = {}
    for code, count in code_counts.items():
        if count >= 4:
            label = atc_lookup.get(code)
            if label:
                label_to_code[label] = code
                label_to_count[label] = count
    sorted_labels = sorted(label_to_count, key=lambda l: -label_to_count[l])
    return sorted_labels, label_to_code, label_to_count, no_atc


def build_filtered_db() -> MoleculeDB:
    db = load_db()
    _, label_to_code, _, _ = compute_l3_data()
    selected_labels: list[str] = st.session_state.get(_k("l3_select"), [])
    include_none: bool = st.session_state.get(_k("atc_none"), True)
    if not selected_labels:
        if include_none:
            return db
        return MoleculeDB(molecules=[m for m in db.molecules if m.atc_classifications])
    selected_codes = {label_to_code[l] for l in selected_labels if l in label_to_code}
    mols = []
    for m in db.molecules:
        if m.atc_classifications:
            if any(len(c) >= 4 and c[:4] in selected_codes for c in m.atc_classifications if c):
                mols.append(m)
        elif include_none:
            mols.append(m)
    return MoleculeDB(molecules=mols)


def playable_pool(db: MoleculeDB) -> list[MoleculeEntry]:
    """Molecules that have a full 5-char ATC code — needed for 4 tile levels."""
    return [m for m in db.molecules if any(len(c) >= 5 for c in m.atc_classifications)]


def best_atc(mol: MoleculeEntry) -> str | None:
    """Primary ATC code (5+ chars) for a molecule."""
    codes = [c for c in mol.atc_classifications if len(c) >= 5]
    return codes[0] if codes else None


def find_molecule(query: str, db: MoleculeDB) -> MoleculeEntry | None:
    """Fuzzy-match a typed name to the closest molecule in the full DB."""
    q_norm = _norm(query)
    best_ratio, best_mol = 0.0, None
    for m in db.molecules:
        ratio = difflib.SequenceMatcher(None, q_norm, _norm(m.name)).ratio()
        if ratio > best_ratio:
            best_ratio, best_mol = ratio, m
    return best_mol if best_ratio >= 0.5 else None


def compare_atc(guess_mol: MoleculeEntry, target_mol: MoleculeEntry,
                atc_lookup: dict) -> list[dict]:
    target_code = best_atc(target_mol)
    guess_code = best_atc(guess_mol)
    results = []
    for n_chars, name in zip(LEVEL_CHARS, LEVEL_NAMES):
        t_prefix = target_code[:n_chars] if target_code and len(target_code) >= n_chars else None
        g_prefix = guess_code[:n_chars] if guess_code and len(guess_code) >= n_chars else None
        match = t_prefix is not None and g_prefix is not None and t_prefix == g_prefix
        # Label: show the guess's label (informative when it doesn't match)
        if g_prefix:
            label = atc_lookup.get(g_prefix) or ATC_L1.get(g_prefix) or g_prefix
        else:
            label = "No ATC code"
        results.append({"level": name, "match": match, "label": label,
                         "g_prefix": g_prefix, "t_prefix": t_prefix})
    return results


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    for key, val in {
        "target": None,
        "guesses": [],   # list of {input, mol, comparison, won}
        "game_status": "idle",  # idle | playing | won | lost
    }.items():
        st.session_state.setdefault(_k(key), val)
    st.session_state.setdefault(_k("atc_none"), True)


def new_game():
    db = build_filtered_db()
    pool = playable_pool(db)
    if not pool:
        st.error("No molecules with full ATC codes in the current selection.")
        return
    target = random.choice(pool)
    st.session_state[_k("target")] = target
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def show_sidebar():
    sorted_labels, _, label_to_count, no_atc = compute_l3_data()
    with st.sidebar:
        st.markdown("### 🧬 Pharmacological Class")
        st.multiselect(
            "Filter pool",
            options=sorted_labels,
            default=[],
            key=_k("l3_select"),
            format_func=lambda l: f"{l} ({label_to_count[l]})",
            placeholder="All classes — type to search",
            label_visibility="collapsed",
        )
        st.checkbox(f"Include unclassified ({no_atc:,})", key=_k("atc_none"))
        st.divider()
        pool_size = len(playable_pool(build_filtered_db()))
        st.caption(f"{pool_size:,} drugs in pool")
        st.button("🎲 New Game", type="primary", use_container_width=True,
                  on_click=new_game)


# ---------------------------------------------------------------------------
# Tile rendering
# ---------------------------------------------------------------------------
def _tile_html(label: str, match: bool, level: str) -> str:
    bg = "#538d4e" if match else "#3a3a3c"
    return (
        f"<div style='background:{bg};color:white;border-radius:6px;padding:8px 6px;"
        f"text-align:center;margin:2px;min-height:60px;display:flex;"
        f"flex-direction:column;justify-content:center;'>"
        f"<div style='font-size:0.65em;opacity:0.75;margin-bottom:2px;'>{level}</div>"
        f"<div style='font-size:0.75em;font-weight:600;line-height:1.2;'>{label}</div>"
        f"</div>"
    )


def render_guess_row(guess_dict: dict):
    mol: MoleculeEntry = guess_dict["mol"]
    comparison: list[dict] = guess_dict["comparison"]
    exact: bool = guess_dict["exact"]

    label = f"**{mol.name}**" + (" ✓" if exact else "")
    st.markdown(label)
    cols = st.columns(4)
    for col, result in zip(cols, comparison):
        tile = _tile_html(result["label"], result["match"], result["level"])
        col.markdown(tile, unsafe_allow_html=True)
    st.markdown("")  # spacer


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("💊 Pharmadle")
    st.markdown(
        "A Wordle-style drug identification game. A mystery drug structure is shown — "
        "guess the drug name. Each guess is matched to the closest drug in the database "
        "and shows how its ATC classification compares to the target across four levels."
    )
    st.divider()
    st.markdown("Use the sidebar to filter the drug pool, then hit **New Game** to start.")


def show_game():
    atc_lookup = load_atc_lookup()
    target: MoleculeEntry = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    n_guesses = len(guesses)
    full_db = load_db()

    st.title("💊 Pharmadle")
    st.caption(f"Guess {n_guesses}/{MAX_GUESSES} · Identify the mystery drug")
    st.divider()

    # Mystery molecule
    img = render_smiles(target.smiles, size=350)
    col_mol, col_game = st.columns([1, 1])
    with col_mol:
        if img:
            st.image(img)

    with col_game:
        # Guess history
        for g in guesses:
            render_guess_row(g)

        # Input / outcome
        if status == "playing":
            with st.form(key=_k(f"guess_form_{n_guesses}"), clear_on_submit=True):
                guess_input = st.text_input("Drug name:", placeholder="e.g. imatinib")
                submitted = st.form_submit_button("Guess", type="primary",
                                                  use_container_width=True)

            if submitted and guess_input.strip():
                matched = find_molecule(guess_input.strip(), full_db)
                if matched is None:
                    st.warning("No matching drug found — try a different spelling.")
                else:
                    comparison = compare_atc(matched, target, atc_lookup)
                    exact = _norm(matched.name) == _norm(target.name)
                    guesses.append({"input": guess_input, "mol": matched,
                                    "comparison": comparison, "exact": exact})
                    if exact:
                        st.session_state[_k("game_status")] = "won"
                    elif len(guesses) >= MAX_GUESSES:
                        st.session_state[_k("game_status")] = "lost"
                    st.rerun()

            if st.button("Give Up", use_container_width=True):
                st.session_state[_k("game_status")] = "lost"
                st.rerun()

        elif status == "won":
            st.success(f"🎉 Correct! The drug was **{target.name}**.")
            _show_answer_details(target, atc_lookup)
            st.button("🎲 New Game", type="primary", use_container_width=True, on_click=new_game)

        elif status == "lost":
            st.error(f"The drug was **{target.name}**.")
            _show_answer_details(target, atc_lookup)
            st.button("🎲 New Game", type="primary", use_container_width=True, on_click=new_game)


def _show_answer_details(mol: MoleculeEntry, atc_lookup: dict):
    with st.expander("Drug details"):
        st.markdown(f"**Biological target:** {mol.target}")
        if mol.usan_stem_definition != "unknown":
            st.markdown(f"**Drug family (USAN):** {mol.usan_stem_definition}")
        code = best_atc(mol)
        if code:
            levels = [atc_lookup.get(code[:n], code[:n]) for n in LEVEL_CHARS]
            st.markdown("**ATC classification:** " + " → ".join(levels))
        if mol.molecule_chembl_id != "unknown":
            st.link_button(
                "View on ChEMBL",
                f"https://www.ebi.ac.uk/chembl/compound_report_card/{mol.molecule_chembl_id}/",
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
init_state()
show_sidebar()

status = st.session_state[_k("game_status")]
if status == "idle":
    show_idle()
else:
    show_game()
