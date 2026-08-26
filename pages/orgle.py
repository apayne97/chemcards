"""Orgle — Wordle-style functional group identification game.

The player is shown a mystery functional group (as a SMARTS pattern) and must
name it.  Each guess is matched to the closest functional group in the
database; five structural properties are shown as green / grey tiles:
ring membership, aromaticity, and presence of N / O / S.
"""
import datetime
import difflib
import random
import streamlit as st
from rdkit import Chem

from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup
from utils import (
    render_fg, norm_name, tile_html, tag_label,
    all_tags, counts_by_tag,
    build_filtered_by_tags,
)

MAX_GUESSES = 6
P = "orgle_"

TILE_DEFS = [
    ("is_ring", "Ring"),
    ("is_aromatic", "Aromatic"),
    ("has_nitrogen", "Nitrogen"),
    ("has_oxygen", "Oxygen"),
    ("has_sulfur", "Sulfur"),
]


def _k(key):
    return P + key


def _date_seed() -> int:
    return int(datetime.date.today().strftime("%Y%m%d"))


def build_filtered_fgs() -> list[FunctionalGroup]:
    return build_filtered_by_tags(FUNCTIONAL_GROUPS, P)


def fg_properties(fg: FunctionalGroup) -> dict:
    mol = Chem.MolFromSmarts(fg.smarts)
    atoms = [a.GetAtomicNum() for a in mol.GetAtoms() if a.GetAtomicNum() > 0] if mol else []
    aromatic = any(a.GetIsAromatic() for a in mol.GetAtoms()) if mol else False
    is_ring = len(Chem.GetSSSR(mol)) > 0 if mol else False
    return {
        "is_ring": is_ring,
        "is_aromatic": aromatic,
        "has_nitrogen": 7 in atoms,
        "has_oxygen": 8 in atoms,
        "has_sulfur": 16 in atoms,
    }


def find_fg(query: str, pool: list[FunctionalGroup]) -> FunctionalGroup | None:
    q_norm = norm_name(query)
    best_ratio, best_fg = 0.0, None
    for fg in pool:
        ratio = difflib.SequenceMatcher(None, q_norm, norm_name(fg.name)).ratio()
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
        "is_daily": False,
    }.items():
        st.session_state.setdefault(_k(key), val)
    for tag in all_tags(FUNCTIONAL_GROUPS):
        st.session_state.setdefault(_k(f"tag_{tag}"), True)


def daily_game():
    full_pool = [fg for fg in FUNCTIONAL_GROUPS if fg.tags]
    if not full_pool:
        st.error("No functional groups available.")
        return
    target = random.Random(_date_seed()).choice(full_pool)
    st.session_state[_k("target")] = target
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = True


def new_game():
    pool = build_filtered_fgs()
    if len(pool) < 2:
        st.error("Need at least 2 functional groups — select more tags.")
        return
    st.session_state[_k("target")] = random.choice(pool)
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def show_sidebar():
    tags = all_tags(FUNCTIONAL_GROUPS)
    counts = counts_by_tag(FUNCTIONAL_GROUPS)
    with st.sidebar:
        st.button("📅 Today's Functional Group", type="primary", use_container_width=True, on_click=daily_game)
        st.button("🎲 Random Functional Group", use_container_width=True, on_click=new_game)
        st.divider()
        st.markdown("### ⚗️ Functional Group Tags")
        c1, c2 = st.columns(2)
        if c1.button("All", key=_k("btn_all"), use_container_width=True):
            for tag in tags:
                st.session_state[_k(f"tag_{tag}")] = True
            st.rerun()
        if c2.button("None", key=_k("btn_none"), use_container_width=True):
            for tag in tags:
                st.session_state[_k(f"tag_{tag}")] = False
            st.rerun()
        for tag in tags:
            st.checkbox(f"{tag_label(tag)} ({counts[tag]})", key=_k(f"tag_{tag}"))
        st.divider()
        pool_size = len(build_filtered_fgs())
        st.caption(f"{pool_size} functional groups in random pool")


# ---------------------------------------------------------------------------
# Tile rendering
# ---------------------------------------------------------------------------
def render_guess_row(guess_dict: dict):
    fg: FunctionalGroup = guess_dict["fg"]
    comparison: list[dict] = guess_dict["comparison"]
    exact: bool = guess_dict["exact"]
    label = f"**{fg.name}**" + (" ✓" if exact else "")
    st.markdown(label)
    cols = st.columns(5)
    for col, result in zip(cols, comparison):
        col.markdown(tile_html(result["label"], result["match"], result["level"]),
                     unsafe_allow_html=True)
    st.markdown("")


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("⚗️ Orgle")
    st.markdown(
        "A Wordle-style organic chemistry game. A mystery SMARTS pattern is shown — "
        "guess the functional group name. Each guess shows five structural properties as "
        "green (match) or grey (no match) tiles: **Ring**, **Aromatic**, **N**, **O**, **S**."
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.button("📅 Today's Functional Group", type="primary", use_container_width=True, on_click=daily_game)
    with col2:
        st.button("🎲 Random Functional Group", use_container_width=True, on_click=new_game)


def show_game():
    target: FunctionalGroup = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    is_daily: bool = st.session_state.get(_k("is_daily"), False)
    n_guesses = len(guesses)
    all_fgs = FUNCTIONAL_GROUPS

    title_suffix = " · 📅 Daily" if is_daily else ""
    st.title(f"⚗️ Orgle{title_suffix}")
    st.caption(f"Guess {n_guesses}/{MAX_GUESSES} · Identify the functional group")
    st.divider()

    img = render_fg(target, size=300)
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
                                            placeholder="e.g. amide")
                submitted = st.form_submit_button("Guess", type="primary",
                                                  use_container_width=True)
            if submitted and guess_input.strip():
                matched = find_fg(guess_input.strip(), all_fgs)
                if matched is None:
                    st.warning("No matching functional group found.")
                else:
                    comparison = compare_fg(matched, target)
                    exact = norm_name(matched.name) == norm_name(target.name)
                    guesses.append({"input": guess_input, "fg": matched,
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
            st.success(f"🎉 Correct! The functional group was **{target.name}**.")
            _show_answer_details(target)
            st.button("🎲 New Random Functional Group", type="primary", use_container_width=True, on_click=new_game)

        elif status == "lost":
            st.error(f"The functional group was **{target.name}**.")
            _show_answer_details(target)
            st.button("🎲 New Random Functional Group", type="primary", use_container_width=True, on_click=new_game)


def _show_answer_details(fg: FunctionalGroup):
    with st.expander("Details"):
        if fg.tags:
            st.markdown(f"**Tags:** {', '.join(tag_label(t) for t in fg.tags)}")
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
