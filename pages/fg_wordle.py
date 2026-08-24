"""FG Wordle — Wordle-style functional group identification game.

The player is shown a mystery functional group (as a SMARTS pattern) and must
name it.  Each guess is matched to the closest functional group in the
database; five structural properties are shown as green / grey tiles:
category, aromaticity, and presence of N / O / S.
"""
import difflib
import random
import streamlit as st
from rdkit import Chem

from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup
from utils import render_smarts

MAX_GUESSES = 6
P = "fgwordle_"

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

TILE_DEFS = [
    ("category", "Category"),
    ("is_aromatic", "Aromatic"),
    ("has_nitrogen", "Nitrogen"),
    ("has_oxygen", "Oxygen"),
    ("has_sulfur", "Sulfur"),
]


def _k(key):
    return P + key


def _norm(s: str) -> str:
    return "".join(s.lower().split()).replace("-", "").replace(",", "")


def _all_categories() -> list[str]:
    return sorted({fg.category for fg in FUNCTIONAL_GROUPS if fg.category})


def _counts_by_category() -> dict[str, int]:
    from collections import Counter
    return Counter(fg.category for fg in FUNCTIONAL_GROUPS if fg.category)


def build_filtered_fgs() -> list[FunctionalGroup]:
    return [
        fg for fg in FUNCTIONAL_GROUPS
        if fg.category and st.session_state.get(_k(f"cat_{fg.category}"), True)
    ]


def fg_properties(fg: FunctionalGroup) -> dict:
    mol = Chem.MolFromSmarts(fg.smarts)
    atoms = [a.GetAtomicNum() for a in mol.GetAtoms() if a.GetAtomicNum() > 0] if mol else []
    aromatic = any(a.GetIsAromatic() for a in mol.GetAtoms()) if mol else False
    return {
        "category": fg.category,
        "is_aromatic": aromatic,
        "has_nitrogen": 7 in atoms,
        "has_oxygen": 8 in atoms,
        "has_sulfur": 16 in atoms,
    }


def find_fg(query: str, pool: list[FunctionalGroup]) -> FunctionalGroup | None:
    q_norm = _norm(query)
    best_ratio, best_fg = 0.0, None
    for fg in pool:
        ratio = difflib.SequenceMatcher(None, q_norm, _norm(fg.name)).ratio()
        if ratio > best_ratio:
            best_ratio, best_fg = ratio, fg
    return best_fg if best_ratio >= 0.5 else None


def compare_fg(guess_fg: FunctionalGroup, target_fg: FunctionalGroup) -> list[dict]:
    gp = fg_properties(guess_fg)
    tp = fg_properties(target_fg)
    results = []
    for prop, label in TILE_DEFS:
        g_val = gp.get(prop)
        t_val = tp.get(prop)
        match = g_val == t_val
        if prop == "category":
            display = CATEGORY_LABELS.get(g_val, str(g_val)) if g_val else "—"
        else:
            display = "Yes" if g_val else "No"
        results.append({"level": label, "match": match, "label": display})
    return results


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    for key, val in {
        "target": None,
        "guesses": [],
        "game_status": "idle",
    }.items():
        st.session_state.setdefault(_k(key), val)
    for cat in _all_categories():
        st.session_state.setdefault(_k(f"cat_{cat}"), True)


def new_game():
    pool = build_filtered_fgs()
    if len(pool) < 2:
        st.error("Need at least 2 functional groups — select more categories.")
        return
    st.session_state[_k("target")] = random.choice(pool)
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def show_sidebar():
    cats = _all_categories()
    counts = _counts_by_category()
    with st.sidebar:
        st.markdown("### 🔬 Functional Group Categories")
        c1, c2 = st.columns(2)
        if c1.button("All", key=_k("btn_all"), use_container_width=True):
            for cat in cats:
                st.session_state[_k(f"cat_{cat}")] = True
            st.rerun()
        if c2.button("None", key=_k("btn_none"), use_container_width=True):
            for cat in cats:
                st.session_state[_k(f"cat_{cat}")] = False
            st.rerun()
        for cat in cats:
            label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
            st.checkbox(f"{label} ({counts[cat]})", key=_k(f"cat_{cat}"))
        st.divider()
        pool_size = len(build_filtered_fgs())
        st.caption(f"{pool_size} functional groups in pool")
        st.button("🎲 New Game", type="primary", use_container_width=True, on_click=new_game)


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
        f"<div style='font-size:0.8em;font-weight:600;'>{label}</div>"
        f"</div>"
    )


def render_guess_row(guess_dict: dict):
    fg: FunctionalGroup = guess_dict["fg"]
    comparison: list[dict] = guess_dict["comparison"]
    exact: bool = guess_dict["exact"]
    label = f"**{fg.name}**" + (" ✓" if exact else "")
    st.markdown(label)
    cols = st.columns(5)
    for col, result in zip(cols, comparison):
        col.markdown(_tile_html(result["label"], result["match"], result["level"]),
                     unsafe_allow_html=True)
    st.markdown("")


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("⚗️ FG Wordle")
    st.markdown(
        "A Wordle-style functional group identification game. A mystery SMARTS pattern is shown — "
        "guess the functional group name. Each guess shows five structural properties as "
        "green (match) or grey (no match) tiles: **Category**, **Aromatic**, **N**, **O**, **S**."
    )
    st.divider()
    st.markdown("Use the sidebar to filter the pool, then hit **New Game** to start.")


def show_game():
    target: FunctionalGroup = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    n_guesses = len(guesses)
    all_fgs = FUNCTIONAL_GROUPS  # match against all FGs, not just filtered pool

    st.title("⚗️ FG Wordle")
    st.caption(f"Guess {n_guesses}/{MAX_GUESSES} · Identify the functional group")
    st.divider()

    img = render_smarts(target.smarts, size=300)
    col_img, col_game = st.columns([1, 1])
    with col_img:
        if img:
            st.image(img)

    with col_game:
        for g in guesses:
            render_guess_row(g)

        if status == "playing":
            with st.form(key=_k(f"guess_form_{n_guesses}"), clear_on_submit=True):
                guess_input = st.text_input("Functional group name:",
                                            placeholder="e.g. indole")
                submitted = st.form_submit_button("Guess", type="primary",
                                                  use_container_width=True)
            if submitted and guess_input.strip():
                matched = find_fg(guess_input.strip(), all_fgs)
                if matched is None:
                    st.warning("No matching functional group found.")
                else:
                    comparison = compare_fg(matched, target)
                    exact = _norm(matched.name) == _norm(target.name)
                    guesses.append({"input": guess_input, "fg": matched,
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
            st.success(f"🎉 Correct! The functional group was **{target.name}**.")
            _show_answer_details(target)
            st.button("🎲 New Game", type="primary", use_container_width=True, on_click=new_game)

        elif status == "lost":
            st.error(f"The functional group was **{target.name}**.")
            _show_answer_details(target)
            st.button("🎲 New Game", type="primary", use_container_width=True, on_click=new_game)


def _show_answer_details(fg: FunctionalGroup):
    with st.expander("Details"):
        cat_label = CATEGORY_LABELS.get(fg.category, fg.category or "—") if fg.category else "—"
        st.markdown(f"**Category:** {cat_label}")
        st.code(fg.smarts, language=None)


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
