"""MedChemble — Wordle-style chemical building block identification game.

Covers both functional groups and chemical building blocks (the former Orgle game) as one
combined pool, presented under the "Chemical Building Block" umbrella — `kind` is kept only
as an internal filter facet (see the sidebar), not a separate game.

Two modes:
- "Write the name": a mystery structure is shown, guess its name.
- "Draw the Structure": a mystery *name* is shown, draw the matching structure using an
  embedded molecule editor (streamlit-ketcher / Ketcher) until it's an exact match.

Either way, each guess is compared against the target on two rows of tiles:
- Elements (O, N, S, F, Cl): green if the count matches exactly, yellow if it's present on
  both sides but the wrong amount, like Wordle's "right letter, wrong spot". Br/I are real
  but rare enough in this dataset that they aren't tracked as their own tile.
- Ring / Carbonyl / Aromatic: plain green/grey presence-or-absence tiles. "Ring" means any
  ring at all, carbocyclic or heterocyclic — a heterocycle is just a subset of it.
Hydrocarbon isn't shown as its own tile — it's just "none of the above elements present".
"""
import datetime
import difflib
import random
import streamlit as st
from rdkit import Chem
from streamlit_ketcher import st_ketcher

from chemcards.database.cheminformatics import (
    ALL_BUILDING_BLOCKS, FunctionalGroup, compute_tags, count_elements,
)
from utils import (
    render_fg, render_mol, mcs_highlight_atoms, norm_name, tile_html, tile_html_tristate, tag_label,
    all_tags, counts_by_tag,
    build_filtered_pool, init_kind_filter_state, show_kind_filter,
)

MAX_GUESSES = 6
P = "cbbwordle_"

# Plain presence/absence tiles (see cheminformatics.CANONICAL_TAGS). Reading tags directly
# instead of recomputing from SMARTS avoids a real bug the old RDKit-based computation had:
# Chem.MolFromSmarts on a recursive SMARTS pattern like "[$(n1ncnc1),$(n1nncc1)]" (triazole,
# oxazole, thiazole, dioxane) produces a single query atom with no materialized ring bonds, so
# ring-perception calls like GetSSSR wrongly report 0 rings for those entries.
TILE_TAGS = ["ring", "carbonyl", "aromatic"]
# Count-based tiles — see count_elements(). Order matches cheminformatics.ELEMENT_ATOMIC_NUMS.
ELEMENT_TILES = ["O", "N", "S", "F", "Cl"]


def _k(key):
    return P + key


def _date_seed() -> int:
    return int(datetime.date.today().strftime("%Y%m%d"))


def _is_drawable(entry: FunctionalGroup) -> bool:
    """A target is only fair for "Draw the Structure" if a player could actually draw an
    exact match — excludes entries whose display_smiles is a substituent fragment with an
    unfilled R-group wildcard (most plain functional groups; the ring-containing ones and all
    chemical building blocks are complete molecules and pass)."""
    return bool(entry.display_smiles) and "*" not in entry.display_smiles


def _is_draw_mode() -> bool:
    return st.session_state.get(_k("answer_mode"), "Write the name") == "Draw the Structure"


def build_filtered_bbs() -> list[FunctionalGroup]:
    pool = build_filtered_pool(ALL_BUILDING_BLOCKS, P)
    if _is_draw_mode():
        pool = [entry for entry in pool if _is_drawable(entry)]
    return pool


def find_entry(query: str, pool: list[FunctionalGroup]) -> FunctionalGroup | None:
    q_norm = norm_name(query)
    best_ratio, best_entry = 0.0, None
    for entry in pool:
        ratio = difflib.SequenceMatcher(None, q_norm, norm_name(entry.name)).ratio()
        if ratio > best_ratio:
            best_ratio, best_entry = ratio, entry
    return best_entry if best_ratio >= 0.5 else None


def _compare_tags(guess_tags: set[str], target_tags: set[str]) -> list[dict]:
    results = []
    for tag in TILE_TAGS:
        g_val = tag in guess_tags
        t_val = tag in target_tags
        match = g_val == t_val
        display = "Yes" if g_val else "No"
        results.append({"level": tag_label(tag), "match": match, "label": display})
    return results


def _compare_elements(guess_mol, target_mol) -> list[dict]:
    guess_counts = count_elements(guess_mol)
    target_counts = count_elements(target_mol)
    results = []
    for elem in ELEMENT_TILES:
        g, t = guess_counts[elem], target_counts[elem]
        state = "green" if g == t else "yellow"
        results.append({"level": elem, "state": state, "label": str(g)})
    return results


def compare_entries(guess_entry: FunctionalGroup, target_entry: FunctionalGroup) -> tuple[list[dict], list[dict]]:
    guess_mol = Chem.MolFromSmiles(guess_entry.display_smiles) if guess_entry.display_smiles else None
    target_mol = Chem.MolFromSmiles(target_entry.display_smiles) if target_entry.display_smiles else None
    comparison = _compare_tags(set(guess_entry.tags), set(target_entry.tags))
    element_comparison = _compare_elements(guess_mol, target_mol)
    return comparison, element_comparison


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
    for tag in all_tags(ALL_BUILDING_BLOCKS):
        st.session_state.setdefault(_k(f"tag_{tag}"), True)
    init_kind_filter_state(P)


def daily_game():
    full_pool = [entry for entry in ALL_BUILDING_BLOCKS if entry.tags]
    if _is_draw_mode():
        full_pool = [entry for entry in full_pool if _is_drawable(entry)]
    if not full_pool:
        st.error("No chemical building blocks available.")
        return
    target = random.Random(_date_seed()).choice(full_pool)
    st.session_state[_k("target")] = target
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = True


def new_game():
    pool = build_filtered_bbs()
    if len(pool) < 2:
        st.error("Need at least 2 chemical building blocks — select more tags.")
        return
    st.session_state[_k("target")] = random.choice(pool)
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "playing"
    st.session_state[_k("is_daily")] = False


# ---------------------------------------------------------------------------
# Answer-mode selector — main content area only (idle screen + end-of-round screens),
# never while a round is "playing". A player could otherwise see the structure in "Write
# the name" mode, switch to "Draw the Structure", and just copy what they already saw —
# keeping this out of the sidebar (rendered every rerun regardless of game state) and only
# calling it from non-playing branches makes that structurally impossible, not just disabled.
# ---------------------------------------------------------------------------
def _reset_round_on_mode_change():
    st.session_state[_k("target")] = None
    st.session_state[_k("guesses")] = []
    st.session_state[_k("game_status")] = "idle"
    st.session_state[_k("is_daily")] = False


def show_answer_mode_selector():
    st.radio(
        "How do you want to answer?",
        ["Write the name", "Draw the Structure"],
        key=_k("answer_mode"),
        on_change=_reset_round_on_mode_change,
        horizontal=True,
        help='"Draw the Structure" shows the name and asks you to draw a matching structure.',
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def show_sidebar():
    tags = all_tags(ALL_BUILDING_BLOCKS)
    counts = counts_by_tag(ALL_BUILDING_BLOCKS)
    with st.sidebar:
        st.button("📅 Today's Building Block", type="primary", use_container_width=True, on_click=daily_game)
        st.button("🎲 Random Building Block", use_container_width=True, on_click=new_game)
        st.divider()
        st.markdown("### ⚗️ Kind")
        show_kind_filter(P)
        st.markdown("### 🧱 Tags")
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
        pool_size = len(build_filtered_bbs())
        st.caption(f"{pool_size} chemical building blocks in random pool")


# ---------------------------------------------------------------------------
# Tile rendering
# ---------------------------------------------------------------------------
def _render_tile_rows(element_comparison: list[dict], comparison: list[dict]):
    elem_cols = st.columns(len(ELEMENT_TILES))
    for col, result in zip(elem_cols, element_comparison):
        col.markdown(tile_html_tristate(result["label"], result["state"], result["level"]),
                     unsafe_allow_html=True)
    tag_cols = st.columns(len(TILE_TAGS))
    for col, result in zip(tag_cols, comparison):
        col.markdown(tile_html(result["label"], result["match"], result["level"]),
                     unsafe_allow_html=True)


def render_guess_row(guess_dict: dict):
    entry: FunctionalGroup = guess_dict["entry"]
    exact: bool = guess_dict["exact"]
    label = f"**{entry.name}**" + (" ✓" if exact else "")
    st.markdown(label)
    _render_tile_rows(guess_dict["element_comparison"], guess_dict["comparison"])
    st.markdown("")


def render_drawn_guess_row(guess_dict: dict, n: int):
    """A guess row for "Draw the Structure" mode: the player's own drawn structure, with
    whatever part of it already matches the target (their maximum common substructure)
    highlighted — without revealing the rest of the target."""
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
        _render_tile_rows(guess_dict["element_comparison"], guess_dict["comparison"])
    st.markdown("")


# ---------------------------------------------------------------------------
# Main game area
# ---------------------------------------------------------------------------
def show_idle():
    st.title("⚗️ MedChemble")
    st.markdown(
        "A Wordle-style chemical building block identification game, covering both "
        "functional groups and chemical building blocks. **Write the name** shows a mystery "
        "structure for you to name, or **Draw the Structure** gives you the name and asks you "
        "to draw a matching structure. Each guess shows two rows of tiles: "
        "**Elements** (" + ", ".join(f"**{e}**" for e in ELEMENT_TILES) +
        ") — green if the count matches exactly, yellow if present on both sides but the "
        "wrong amount — and " + ", ".join(f"**{tag_label(t)}**" for t in TILE_TAGS) +
        " as plain green (match) or grey (no match) tiles."
    )
    show_answer_mode_selector()
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
    all_entries = ALL_BUILDING_BLOCKS

    title_suffix = " · 📅 Daily" if is_daily else ""
    st.title(f"⚗️ MedChemble{title_suffix}")
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
                matched = find_entry(guess_input.strip(), all_entries)
                if matched is None:
                    st.warning("No matching chemical building block found.")
                else:
                    comparison, element_comparison = compare_entries(matched, target)
                    exact = norm_name(matched.name) == norm_name(target.name)
                    guesses.append({"input": guess_input, "entry": matched,
                                    "comparison": comparison, "element_comparison": element_comparison,
                                    "exact": exact})
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
            show_answer_mode_selector()
            st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)

        elif status == "lost":
            st.error(f"The chemical building block was **{target.name}**.")
            _show_answer_details(target)
            show_answer_mode_selector()
            st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)


def show_draw_game():
    target: FunctionalGroup = st.session_state[_k("target")]
    guesses: list[dict] = st.session_state[_k("guesses")]
    status: str = st.session_state[_k("game_status")]
    is_daily: bool = st.session_state.get(_k("is_daily"), False)
    n_guesses = len(guesses)
    target_mol = Chem.MolFromSmiles(target.display_smiles)

    title_suffix = " · 📅 Daily" if is_daily else ""
    st.title(f"⚗️ MedChemble{title_suffix}")
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
                element_comparison = _compare_elements(guess_mol, target_mol)
                exact = Chem.MolToSmiles(guess_mol) == Chem.MolToSmiles(target_mol)
                highlight_guess, _ = mcs_highlight_atoms(guess_mol, target_mol)
                guesses.append({
                    "mol": guess_mol, "comparison": comparison, "element_comparison": element_comparison,
                    "exact": exact, "highlight_atoms": highlight_guess,
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
        show_answer_mode_selector()
        st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)

    elif status == "lost":
        st.error(f"The target structure was **{target.name}**.")
        _show_draw_answer(target, target_mol)
        show_answer_mode_selector()
        st.button("🎲 New Random Building Block", type="primary", use_container_width=True, on_click=new_game)


def _show_draw_answer(entry: FunctionalGroup, target_mol):
    img = render_mol(target_mol, size=300)
    if img:
        st.image(img)
    _show_answer_details(entry)


def _show_answer_details(entry: FunctionalGroup):
    with st.expander("Details"):
        st.markdown(f"**Kind:** {tag_label(entry.kind)}")
        if entry.tags:
            st.markdown(f"**Tags:** {', '.join(tag_label(t) for t in entry.tags)}")
        st.code(entry.smarts, language=None)


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
