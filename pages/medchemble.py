"""MedChemble — Wordle-style chemical building block identification game.

Two modes:
- "Write the name": a mystery structure is shown, guess its name.
- "Draw the Structure": a mystery *name* is shown, draw the matching structure using an
  embedded molecule editor (streamlit-ketcher / Ketcher) until it's an exact match.

Either way, each guess is compared against the target on eight structural properties (one
per canonical tag) shown as green / grey tiles.
"""
import datetime
import difflib
import random
import streamlit as st
from rdkit import Chem
from streamlit_ketcher import st_ketcher

from chemcards.database.cheminformatics import CHEMICAL_BUILDING_BLOCKS, FunctionalGroup, compute_tags
from utils import (
    render_fg, render_mol, mcs_highlight_atoms, norm_name, tile_html, tag_label,
    all_tags, counts_by_tag,
    build_filtered_by_tags,
)

MAX_GUESSES = 6
P = "cbbwordle_"

# One tile per canonical tag (see cheminformatics.CANONICAL_TAGS). Reading tags directly
# instead of recomputing from SMARTS avoids a real bug the old RDKit-based computation had:
# Chem.MolFromSmarts on a recursive SMARTS pattern like "[$(n1ncnc1),$(n1nncc1)]" (triazole,
# oxazole, thiazole, dioxane) produces a single query atom with no materialized ring bonds, so
# ring-perception calls like GetSSSR wrongly report 0 rings for those entries.
TILE_TAGS = ["heterocycle", "hydrocarbon", "oxygen", "nitrogen", "halogen", "sulfur", "carbonyl", "aromatic"]


def _k(key):
    return P + key


def _date_seed() -> int:
    return int(datetime.date.today().strftime("%Y%m%d"))


def _is_drawable(cbb: FunctionalGroup) -> bool:
    """A target is only fair for "Draw the Structure" if a player could actually draw an
    exact match — excludes entries whose display_smiles has an unfilled R-group wildcard
    (just acylimidazole, currently)."""
    return bool(cbb.display_smiles) and "*" not in cbb.display_smiles


def _is_draw_mode() -> bool:
    return st.session_state.get(_k("answer_mode"), "Write the name") == "Draw the Structure"


def build_filtered_cbbs() -> list[FunctionalGroup]:
    pool = build_filtered_by_tags(CHEMICAL_BUILDING_BLOCKS, P)
    if _is_draw_mode():
        pool = [cbb for cbb in pool if _is_drawable(cbb)]
    return pool


def find_cbb(query: str, pool: list[FunctionalGroup]) -> FunctionalGroup | None:
    q_norm = norm_name(query)
    best_ratio, best_cbb = 0.0, None
    for cbb in pool:
        ratio = difflib.SequenceMatcher(None, q_norm, norm_name(cbb.name)).ratio()
        if ratio > best_ratio:
            best_ratio, best_cbb = ratio, cbb
    return best_cbb if best_ratio >= 0.5 else None


def _compare_tags(guess_tags: set[str], target_tags: set[str]) -> list[dict]:
    results = []
    for tag in TILE_TAGS:
        g_val = tag in guess_tags
        t_val = tag in target_tags
        match = g_val == t_val
        display = "Yes" if g_val else "No"
        results.append({"level": tag_label(tag), "match": match, "label": display})
    return results


def compare_cbb(guess_cbb: FunctionalGroup, target_cbb: FunctionalGroup) -> list[dict]:
    return _compare_tags(set(guess_cbb.tags), set(target_cbb.tags))


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    for key, val in {
        "target": None,
        "guesses": [],
        "game_status": "idle",
        "is_daily": False,
        "answer_mode": "Write the name",
    }.items():
        st.session_state.setdefault(_k(key), val)
    for tag in all_tags(CHEMICAL_BUILDING_BLOCKS):
        st.session_state.setdefault(_k(f"tag_{tag}"), True)


def daily_game():
    full_pool = [cbb for cbb in CHEMICAL_BUILDING_BLOCKS if cbb.tags]
    if _is_draw_mode():
        full_pool = [cbb for cbb in full_pool if _is_drawable(cbb)]
    if not full_pool:
        st.error("No chemical building blocks available.")
        return
    target = random.Random(_date_seed()).choice(full_pool)
    st.session_state[_k("target")] = target
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = True


def new_game():
    pool = build_filtered_cbbs()
    if len(pool) < 2:
        st.error("Need at least 2 chemical building blocks — select more tags.")
        return
    st.session_state[_k("target")] = random.choice(pool)
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def _reset_round_on_mode_change():
    """Switching mode mid-round would let a player see the structure in "Write the name"
    mode, then flip to "Draw the Structure" and just copy what they already saw — force a
    fresh round instead."""
    st.session_state[_k("target")] = None
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "idle"
    st.session_state[_k("is_daily")] = False


def show_sidebar():
    tags = all_tags(CHEMICAL_BUILDING_BLOCKS)
    counts = counts_by_tag(CHEMICAL_BUILDING_BLOCKS)
    with st.sidebar:
        is_playing = st.session_state[_k("game_status")] == "playing"
        help_text = '"Draw the Structure" shows the name and asks you to draw a matching structure.'
        if is_playing:
            help_text = (
                "Locked until you finish or give up the current round — otherwise you could "
                "see the structure in one mode and just copy it in the other.\n\n" + help_text
            )
        st.radio(
            "How do you want to answer?",
            ["Write the name", "Draw the Structure"],
            key=_k("answer_mode"),
            on_change=_reset_round_on_mode_change,
            disabled=is_playing,
            help=help_text,
        )
        st.button("📅 Today's Building Block", type="primary", use_container_width=True, on_click=daily_game)
        st.button("🎲 Random Building Block", use_container_width=True, on_click=new_game)
        st.divider()
        st.markdown("### 🧱 Building Block Tags")
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
        pool_size = len(build_filtered_cbbs())
        st.caption(f"{pool_size} chemical building blocks in random pool")


# ---------------------------------------------------------------------------
# Tile rendering
# ---------------------------------------------------------------------------
def render_guess_row(guess_dict: dict):
    cbb: FunctionalGroup = guess_dict["cbb"]
    comparison: list[dict] = guess_dict["comparison"]
    exact: bool = guess_dict["exact"]
    label = f"**{cbb.name}**" + (" ✓" if exact else "")
    st.markdown(label)
    cols = st.columns(len(TILE_TAGS))
    for col, result in zip(cols, comparison):
        col.markdown(tile_html(result["label"], result["match"], result["level"]),
                     unsafe_allow_html=True)
    st.markdown("")


def render_drawn_guess_row(guess_dict: dict, n: int):
    """A guess row for "Draw the Structure" mode: the player's own drawn structure, with
    whatever part of it already matches the target (their maximum common substructure)
    highlighted — without revealing the rest of the target."""
    comparison: list[dict] = guess_dict["comparison"]
    exact: bool = guess_dict["exact"]
    col_img, col_tiles = st.columns([1, 2])
    with col_img:
        img = render_mol(guess_dict["mol"], size=200, highlight_atoms=guess_dict["highlight_atoms"])
        if img:
            st.image(img)
        else:
            st.caption("Couldn't parse guess #%d" % n)
    with col_tiles:
        if exact:
            st.markdown("✓ Exact match!")
        cols = st.columns(len(TILE_TAGS))
        for col, result in zip(cols, comparison):
            col.markdown(tile_html(result["label"], result["match"], result["level"]),
                         unsafe_allow_html=True)
    st.markdown("")


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("🧱 MedChemble")
    st.markdown(
        "A Wordle-style chemical building block identification game. Choose a mode in the "
        "sidebar: **Write the name** shows a mystery structure for you to name, or "
        "**Draw the Structure** gives you the name and asks you to draw a matching structure. "
        "Each guess shows eight structural properties as green (match) or grey (no match) "
        "tiles: " + ", ".join(f"**{tag_label(t)}**" for t in TILE_TAGS) + "."
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.button("📅 Today's Building Block", type="primary", use_container_width=True, on_click=daily_game)
    with col2:
        st.button("🎲 Random Building Block", use_container_width=True, on_click=new_game)


def show_game():
    if _is_draw_mode():
        show_draw_game()
    else:
        show_name_game()


def show_name_game():
    target: FunctionalGroup = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    is_daily: bool = st.session_state.get(_k("is_daily"), False)
    n_guesses = len(guesses)
    all_cbbs = CHEMICAL_BUILDING_BLOCKS

    title_suffix = " · 📅 Daily" if is_daily else ""
    st.title(f"🧱 MedChemble{title_suffix}")
    st.caption(f"Guess {n_guesses}/{MAX_GUESSES} · Identify the chemical building block")
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
                guess_input = st.text_input("Building block name:",
                                            placeholder="e.g. indole")
                submitted = st.form_submit_button("Guess", type="primary",
                                                  use_container_width=True)
            if submitted and guess_input.strip():
                matched = find_cbb(guess_input.strip(), all_cbbs)
                if matched is None:
                    st.warning("No matching chemical building block found.")
                else:
                    comparison = compare_cbb(matched, target)
                    exact = norm_name(matched.name) == norm_name(target.name)
                    guesses.append({"input": guess_input, "cbb": matched,
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
            st.success(f"🎉 Correct! The chemical building block was **{target.name}**.")
            _show_answer_details(target)
            st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)

        elif status == "lost":
            st.error(f"The chemical building block was **{target.name}**.")
            _show_answer_details(target)
            st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)


def show_draw_game():
    target: FunctionalGroup = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    is_daily: bool = st.session_state.get(_k("is_daily"), False)
    n_guesses = len(guesses)
    target_mol = Chem.MolFromSmiles(target.display_smiles)

    title_suffix = " · 📅 Daily" if is_daily else ""
    st.title(f"🧱 MedChemble{title_suffix}")
    st.caption(f"Guess {n_guesses}/{MAX_GUESSES} · Draw the structure")
    st.divider()

    st.markdown(f"### Draw: **{target.name}**")

    for g in guesses:
        render_drawn_guess_row(g, guesses.index(g) + 1)

    if status == "playing":
        drawn_smiles = st_ketcher("", key=_k(f"ketcher_{n_guesses}"))
        submitted = st.button("Check Guess", type="primary", use_container_width=True)
        if submitted:
            guess_mol = Chem.MolFromSmiles(drawn_smiles) if drawn_smiles else None
            if guess_mol is None:
                st.warning("That doesn't parse as a valid structure — try again.")
            else:
                guess_tags = compute_tags(guess_mol)
                comparison = _compare_tags(guess_tags, set(target.tags))
                exact = Chem.MolToSmiles(guess_mol) == Chem.MolToSmiles(target_mol)
                highlight_guess, _ = mcs_highlight_atoms(guess_mol, target_mol)
                guesses.append({
                    "mol": guess_mol, "comparison": comparison, "exact": exact,
                    "highlight_atoms": highlight_guess,
                })
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
        st.success(f"🎉 Exact match! That was **{target.name}**.")
        _show_draw_answer(target, target_mol)
        st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)

    elif status == "lost":
        st.error(f"The target structure was **{target.name}**.")
        _show_draw_answer(target, target_mol)
        st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)


def _show_draw_answer(cbb: FunctionalGroup, target_mol):
    img = render_mol(target_mol, size=300)
    if img:
        st.image(img)
    _show_answer_details(cbb)


def _show_answer_details(cbb: FunctionalGroup):
    with st.expander("Details"):
        if cbb.tags:
            st.markdown(f"**Tags:** {', '.join(tag_label(t) for t in cbb.tags)}")
        st.code(cbb.smarts, language=None)


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
