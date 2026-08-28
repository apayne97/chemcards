"""MedChemble — Wordle-style chemical building block identification game.

The player is shown a mystery chemical building block (as a SMARTS pattern)
and must name it.  Each guess is matched to the closest building block in the
database; seven structural properties (one per canonical tag) are shown as
green / grey tiles.
"""
import datetime
import difflib
import random
import streamlit as st

from chemcards.database.cheminformatics import CHEMICAL_BUILDING_BLOCKS, FunctionalGroup
from utils import (
    render_fg, norm_name, tile_html, tag_label,
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
TILE_TAGS = ["heterocycle", "hydrocarbon", "oxygen", "nitrogen", "halogen", "sulfur", "carbonyl"]


def _k(key):
    return P + key


def _date_seed() -> int:
    return int(datetime.date.today().strftime("%Y%m%d"))


def build_filtered_cbbs() -> list[FunctionalGroup]:
    return build_filtered_by_tags(CHEMICAL_BUILDING_BLOCKS, P)


def find_cbb(query: str, pool: list[FunctionalGroup]) -> FunctionalGroup | None:
    q_norm = norm_name(query)
    best_ratio, best_cbb = 0.0, None
    for cbb in pool:
        ratio = difflib.SequenceMatcher(None, q_norm, norm_name(cbb.name)).ratio()
        if ratio > best_ratio:
            best_ratio, best_cbb = ratio, cbb
    return best_cbb if best_ratio >= 0.5 else None


def compare_cbb(guess_cbb: FunctionalGroup, target_cbb: FunctionalGroup) -> list[dict]:
    results = []
    for tag in TILE_TAGS:
        g_val = tag in guess_cbb.tags
        t_val = tag in target_cbb.tags
        match = g_val == t_val
        display = "Yes" if g_val else "No"
        results.append({"level": tag_label(tag), "match": match, "label": display})
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
    for tag in all_tags(CHEMICAL_BUILDING_BLOCKS):
        st.session_state.setdefault(_k(f"tag_{tag}"), True)


def daily_game():
    full_pool = [cbb for cbb in CHEMICAL_BUILDING_BLOCKS if cbb.tags]
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
def show_sidebar():
    tags = all_tags(CHEMICAL_BUILDING_BLOCKS)
    counts = counts_by_tag(CHEMICAL_BUILDING_BLOCKS)
    with st.sidebar:
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


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("🧱 MedChemble")
    st.markdown(
        "A Wordle-style chemical building block identification game. A mystery SMARTS pattern "
        "is shown — guess the building block name. Each guess shows seven structural properties "
        "as green (match) or grey (no match) tiles: " +
        ", ".join(f"**{tag_label(t)}**" for t in TILE_TAGS) + "."
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.button("📅 Today's Building Block", type="primary", use_container_width=True, on_click=daily_game)
    with col2:
        st.button("🎲 Random Building Block", use_container_width=True, on_click=new_game)


def show_game():
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
