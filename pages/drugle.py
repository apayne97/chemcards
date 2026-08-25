"""Drugle — Wordle-style drug identification game.

The player is shown a mystery molecule and must identify it by guessing drug
names.  Each guess is matched to the closest drug in the database; the four
ATC classification levels (organ system → therapeutic area → pharmacological
class → chemical subgroup) are shown as green / grey tiles, giving
progressively specific hints about where the mystery drug sits in the
hierarchy.
"""
import datetime
import difflib
import random
import streamlit as st

from chemcards.database.core import MoleculeDB, MoleculeEntry
from utils import (
    load_db, load_atc_lookup, render_smiles,
    ATC_L1, LEVEL_CHARS, ATC_LEVEL_NAMES,
    norm_name, tile_html, compute_l3_data, build_filtered_drug_db,
)

MAX_GUESSES = 6
P = "drugle_"


def _k(key):
    return P + key


def _date_seed() -> int:
    return int(datetime.date.today().strftime("%Y%m%d"))


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def build_filtered_db() -> MoleculeDB:
    return build_filtered_drug_db(P)


def playable_pool(db: MoleculeDB) -> list[MoleculeEntry]:
    """Molecules that have a full 5-char ATC code — needed for 4 tile levels."""
    return [m for m in db.molecules if any(len(c) >= 5 for c in m.atc_classifications)]


def best_atc(mol: MoleculeEntry) -> str | None:
    """Primary ATC code (5+ chars) for a molecule."""
    codes = [c for c in mol.atc_classifications if len(c) >= 5]
    return codes[0] if codes else None


def find_molecule(query: str, db: MoleculeDB) -> MoleculeEntry | None:
    """Fuzzy-match a typed name to the closest molecule in the full DB."""
    q_norm = norm_name(query)
    best_ratio, best_mol = 0.0, None
    for m in db.molecules:
        ratio = difflib.SequenceMatcher(None, q_norm, norm_name(m.name)).ratio()
        if ratio > best_ratio:
            best_ratio, best_mol = ratio, m
    return best_mol if best_ratio >= 0.5 else None


def compare_atc(guess_mol: MoleculeEntry, target_mol: MoleculeEntry,
                atc_lookup: dict) -> list[dict]:
    target_code = best_atc(target_mol)
    guess_code = best_atc(guess_mol)
    results = []
    for n_chars, name in zip(LEVEL_CHARS, ATC_LEVEL_NAMES):
        t_prefix = target_code[:n_chars] if target_code and len(target_code) >= n_chars else None
        g_prefix = guess_code[:n_chars] if guess_code and len(guess_code) >= n_chars else None
        match = t_prefix is not None and g_prefix is not None and t_prefix == g_prefix
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
        "guesses": [],
        "game_status": "idle",
        "is_daily": False,
    }.items():
        st.session_state.setdefault(_k(key), val)
    st.session_state.setdefault(_k("atc_none"), True)


def daily_game():
    full_pool = playable_pool(load_db())
    if not full_pool:
        st.error("No molecules with full ATC codes in the database.")
        return
    target = random.Random(_date_seed()).choice(full_pool)
    st.session_state[_k("target")] = target
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = True


def new_game():
    pool = playable_pool(build_filtered_db())
    if not pool:
        st.error("No molecules with full ATC codes in the current selection.")
        return
    target = random.choice(pool)
    st.session_state[_k("target")] = target
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def show_sidebar():
    sorted_labels, _, label_to_count, no_atc = compute_l3_data()
    with st.sidebar:
        st.button("📅 Today's Drug", type="primary", use_container_width=True, on_click=daily_game)
        st.button("🎲 Random Drug", use_container_width=True, on_click=new_game)
        st.divider()
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
        st.caption(f"{pool_size:,} drugs in random pool")


# ---------------------------------------------------------------------------
# Tile rendering
# ---------------------------------------------------------------------------
def render_guess_row(guess_dict: dict):
    mol: MoleculeEntry = guess_dict["mol"]
    comparison: list[dict] = guess_dict["comparison"]
    exact: bool = guess_dict["exact"]

    label = f"**{mol.name}**" + (" ✓" if exact else "")
    st.markdown(label)
    cols = st.columns(4)
    for col, result in zip(cols, comparison):
        col.markdown(tile_html(result["label"], result["match"], result["level"]),
                     unsafe_allow_html=True)
    st.markdown("")


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("💊 Drugle")
    st.markdown(
        "A Wordle-style drug identification game. A mystery drug structure is shown — "
        "guess the drug name. Each guess is matched to the closest drug in the database "
        "and shows how its ATC classification compares to the target across four levels."
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.button("📅 Today's Drug", type="primary", use_container_width=True, on_click=daily_game)
    with col2:
        st.button("🎲 Random Drug", use_container_width=True, on_click=new_game)


def show_game():
    atc_lookup = load_atc_lookup()
    target: MoleculeEntry = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    is_daily: bool = st.session_state.get(_k("is_daily"), False)
    n_guesses = len(guesses)
    full_db = load_db()

    title_suffix = " · 📅 Daily" if is_daily else ""
    st.title(f"💊 Drugle{title_suffix}")
    st.caption(f"Guess {n_guesses}/{MAX_GUESSES} · Identify the mystery drug")
    st.divider()

    img = render_smiles(target.smiles, size=350)
    col_mol, col_game = st.columns([1, 1])
    with col_mol:
        if img:
            st.image(img)

    with col_game:
        for g in guesses:
            render_guess_row(g)

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
                    exact = norm_name(matched.name) == norm_name(target.name)
                    guesses.append({"input": guess_input, "mol": matched,
                                    "comparison": comparison, "exact": exact})
                    st.session_state[_k("guesses")] = guesses
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
            st.button("🎲 New Random Drug", type="primary", use_container_width=True, on_click=new_game)

        elif status == "lost":
            st.error(f"The drug was **{target.name}**.")
            _show_answer_details(target, atc_lookup)
            st.button("🎲 New Random Drug", type="primary", use_container_width=True, on_click=new_game)


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
