import difflib
import random
import streamlit as st

from chemcards.database.cheminformatics import CHEMICAL_BUILDING_BLOCKS, FunctionalGroup
from chemcards.flashcards.multiplechoice import MultipleChoice
from utils import (
    render_fg, norm_name, tag_label,
    all_tags, counts_by_tag,
    build_filtered_by_tags,
    show_quiz_result,
)

P = "cbb_quiz_"


def _k(key):
    return P + key


def init_state():
    for key, val in {
        "mode": "menu",
        "current_question": None,
        "score": 0,
        "total": 0,
        "answered": False,
        "correct_last": None,
    }.items():
        st.session_state.setdefault(_k(key), val)
    for tag in all_tags(CHEMICAL_BUILDING_BLOCKS):
        st.session_state.setdefault(_k(f"tag_{tag}"), True)


def build_filtered_cbbs() -> list[FunctionalGroup]:
    return build_filtered_by_tags(CHEMICAL_BUILDING_BLOCKS, P)


def next_question(filtered_cbbs: list[FunctionalGroup]) -> MultipleChoice:
    sample_count = min(4, len(filtered_cbbs))
    examples = random.sample(filtered_cbbs, sample_count)
    correct = random.randrange(sample_count)
    return MultipleChoice(
        question="What is the name of this chemical building block?",
        display=examples[correct],
        choices=[cbb.name for cbb in examples],
        answer_index=correct,
        answer_molecule=None,
    )


def start_quiz():
    filtered = build_filtered_cbbs()
    if len(filtered) < 4:
        st.error("Need at least 4 chemical building blocks — select more tags.")
        return
    q = next_question(filtered)
    st.session_state[_k("current_question")] = q
    st.session_state[_k("filtered_cbbs")] = filtered
    st.session_state[_k("score")] = 0
    st.session_state[_k("total")] = 0
    st.session_state[_k("answered")] = False
    st.session_state[_k("correct_last")] = None
    st.session_state[_k("mode")] = "quiz"


def reset_to_menu():
    for key in ("current_question", "filtered_cbbs"):
        st.session_state[_k(key)] = None
    for key in ("score", "total"):
        st.session_state[_k(key)] = 0
    for key in ("answered", "correct_last"):
        st.session_state[_k(key)] = False
    st.session_state[_k("mode")] = "menu"
    st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def show_sidebar():
    tags = all_tags(CHEMICAL_BUILDING_BLOCKS)
    counts = counts_by_tag(CHEMICAL_BUILDING_BLOCKS)
    mode = st.session_state[_k("mode")]

    with st.sidebar:
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

        st.radio("Answer mode", ["Multiple choice", "Type answer"], key=_k("answer_mode"))
        st.divider()

        pool_size = len(build_filtered_cbbs())
        st.caption(f"{pool_size} chemical building blocks selected")

        if mode == "menu":
            st.button(
                "▶ Start Quiz",
                type="primary",
                use_container_width=True,
                disabled=pool_size < 4,
                on_click=start_quiz,
            )
        else:
            if st.button("⏹ New Quiz", use_container_width=True):
                reset_to_menu()


# ---------------------------------------------------------------------------
# Main area: menu
# ---------------------------------------------------------------------------
def show_menu():
    st.title("🧱 Chemical Building Blocks Quiz")
    st.markdown(
        "Test your knowledge of heterocyclic ring scaffolds and other chemical building blocks. "
        "Use the sidebar to filter by tag, then hit **Start Quiz**."
    )
    st.divider()
    st.markdown(
        "You'll be shown a SMARTS pattern and asked to identify the building block by name."
    )


# ---------------------------------------------------------------------------
# Main area: quiz
# ---------------------------------------------------------------------------
def show_quiz():
    q: MultipleChoice = st.session_state[_k("current_question")]
    filtered_cbbs: list[FunctionalGroup] = st.session_state[_k("filtered_cbbs")]
    score = st.session_state[_k("score")]
    total = st.session_state[_k("total")]
    answered = st.session_state[_k("answered")]

    col_title, col_score, col_end = st.columns([4, 1, 1])
    with col_title:
        st.subheader("Building Block → Name")
    with col_score:
        st.metric("Score", f"{score}/{total}")
    with col_end:
        if st.button("End"):
            st.session_state[_k("mode")] = "result"
            st.rerun()

    st.divider()

    if isinstance(q.display, FunctionalGroup):
        img = render_fg(q.display, size=300)
        if img:
            col_img, _ = st.columns([1, 2])
            with col_img:
                st.image(img)

    st.subheader(q.question)

    answer_mode = st.session_state.get(_k("answer_mode"), "Multiple choice")
    text_mode = answer_mode == "Type answer"
    correct_name = q.choices[q.answer_index]

    if text_mode:
        with st.form(key=_k(f"text_form_{total}"), clear_on_submit=False):
            guess = st.text_input("Type the building block name:", disabled=answered)
            submitted = st.form_submit_button("Check", type="primary",
                                              use_container_width=True, disabled=answered)
        if submitted and guess.strip() and not answered:
            ratio = difflib.SequenceMatcher(None, norm_name(guess), norm_name(correct_name)).ratio()
            if norm_name(guess) == norm_name(correct_name):
                st.session_state[_k("answered")] = True
                st.session_state[_k("total")] += 1
                st.session_state[_k("correct_last")] = True
                st.session_state[_k("score")] += 1
                st.rerun()
            elif ratio > 0.8:
                st.warning("So close — check your spelling and try again.")
            else:
                st.error("Not quite. Try again or reveal the answer.")
    else:
        radio_key = _k(f"radio_{total}")
        radio_val = st.radio("Your answer:", q.choices, index=None, key=radio_key, disabled=answered)
        selected_idx = q.choices.index(radio_val) if radio_val else None

    st.divider()

    if not answered:
        if text_mode:
            if st.button("Reveal answer / I don't know", use_container_width=True):
                st.session_state[_k("answered")] = True
                st.session_state[_k("total")] += 1
                st.session_state[_k("correct_last")] = False
                st.rerun()
        else:
            if st.button("Check Answer", disabled=(radio_val is None), type="primary"):
                st.session_state[_k("answered")] = True
                st.session_state[_k("total")] += 1
                correct = selected_idx == q.answer_index
                st.session_state[_k("correct_last")] = correct
                if correct:
                    st.session_state[_k("score")] += 1
                st.rerun()
    else:
        if st.session_state[_k("correct_last")]:
            st.success("Correct!")
        else:
            st.error(f"The answer was: **{correct_name}**")

        if isinstance(q.display, FunctionalGroup):
            with st.expander("Building block details"):
                cbb = q.display
                st.markdown(f"**Name:** {cbb.name}")
                if cbb.tags:
                    st.markdown(f"**Tags:** {', '.join(tag_label(t) for t in cbb.tags)}")
                st.code(cbb.smarts, language=None)

        if st.button("Next Question", type="primary"):
            st.session_state[_k("current_question")] = next_question(filtered_cbbs)
            st.session_state[_k("answered")] = False
            st.session_state[_k("correct_last")] = None
            st.rerun()


# ---------------------------------------------------------------------------
# Main area: result
# ---------------------------------------------------------------------------
def show_result():
    show_quiz_result(st.session_state[_k("score")], st.session_state[_k("total")], reset_to_menu)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
init_state()
show_sidebar()

mode = st.session_state[_k("mode")]
if mode == "menu":
    show_menu()
elif mode == "quiz":
    show_quiz()
elif mode == "result":
    show_result()
