import difflib
import random
import streamlit as st
from collections import Counter

from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, FunctionalGroup
from chemcards.flashcards.multiplechoice import MultipleChoice
from utils import render_smarts

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

P = "medchemble_"


def _k(key):
    return P + key


def _norm(s: str) -> str:
    return "".join(s.lower().split()).replace("-", "").replace(",", "")


def _all_categories() -> list[str]:
    return sorted({fg.category for fg in FUNCTIONAL_GROUPS if fg.category})


def _counts_by_category() -> dict[str, int]:
    return Counter(fg.category for fg in FUNCTIONAL_GROUPS if fg.category)


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
    for cat in _all_categories():
        st.session_state.setdefault(_k(f"cat_{cat}"), True)


def build_filtered_fgs() -> list[FunctionalGroup]:
    return [
        fg for fg in FUNCTIONAL_GROUPS
        if fg.category and st.session_state.get(_k(f"cat_{fg.category}"), True)
    ]


def next_question(filtered_fgs: list[FunctionalGroup]) -> MultipleChoice:
    sample_count = min(4, len(filtered_fgs))
    examples = random.sample(filtered_fgs, sample_count)
    correct = random.randrange(sample_count)
    return MultipleChoice(
        question="What is the name of this functional group?",
        display=examples[correct],
        choices=[fg.name for fg in examples],
        answer_index=correct,
        answer_molecule=None,
    )


def start_quiz():
    filtered = build_filtered_fgs()
    if len(filtered) < 4:
        st.error("Need at least 4 functional groups — select more categories.")
        return
    q = next_question(filtered)
    st.session_state[_k("current_question")] = q
    st.session_state[_k("filtered_fgs")] = filtered
    st.session_state[_k("score")] = 0
    st.session_state[_k("total")] = 0
    st.session_state[_k("answered")] = False
    st.session_state[_k("correct_last")] = None
    st.session_state[_k("mode")] = "quiz"


def reset_to_menu():
    for key in ("current_question", "filtered_fgs"):
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
    cats = _all_categories()
    counts = _counts_by_category()
    mode = st.session_state[_k("mode")]

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

        st.radio("Answer mode", ["Multiple choice", "Type answer"], key=_k("answer_mode"))
        st.divider()

        pool_size = len(build_filtered_fgs())
        st.caption(f"{pool_size} functional groups selected")

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
    st.title("⚗️ Functional Group Quiz")
    st.markdown(
        "Test your knowledge of medicinal chemistry functional groups. "
        "Use the sidebar to filter by category, then hit **Start Quiz**."
    )
    st.divider()
    st.markdown(
        "You'll be shown a SMARTS pattern and asked to identify the functional group by name."
    )


# ---------------------------------------------------------------------------
# Main area: quiz
# ---------------------------------------------------------------------------
def show_quiz():
    q: MultipleChoice = st.session_state[_k("current_question")]
    filtered_fgs: list[FunctionalGroup] = st.session_state[_k("filtered_fgs")]
    score = st.session_state[_k("score")]
    total = st.session_state[_k("total")]
    answered = st.session_state[_k("answered")]

    col_title, col_score, col_end = st.columns([4, 1, 1])
    with col_title:
        st.subheader("Functional Group → Name")
    with col_score:
        st.metric("Score", f"{score}/{total}")
    with col_end:
        if st.button("End"):
            st.session_state[_k("mode")] = "result"
            st.rerun()

    st.divider()

    if isinstance(q.display, FunctionalGroup):
        img = render_smarts(q.display.smarts, size=300)
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
            guess = st.text_input("Type the functional group name:", disabled=answered)
            submitted = st.form_submit_button("Check", type="primary",
                                              use_container_width=True, disabled=answered)
        if submitted and guess.strip() and not answered:
            ratio = difflib.SequenceMatcher(None, _norm(guess), _norm(correct_name)).ratio()
            if _norm(guess) == _norm(correct_name):
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
            with st.expander("Functional group details"):
                fg = q.display
                label = CATEGORY_LABELS.get(fg.category, fg.category.replace("_", " ").title()) if fg.category else "—"
                st.markdown(f"**Name:** {fg.name}")
                st.markdown(f"**Category:** {label}")
                st.code(fg.smarts, language=None)

        if st.button("Next Question", type="primary"):
            st.session_state[_k("current_question")] = next_question(filtered_fgs)
            st.session_state[_k("answered")] = False
            st.session_state[_k("correct_last")] = None
            st.rerun()


# ---------------------------------------------------------------------------
# Main area: result
# ---------------------------------------------------------------------------
def show_result():
    st.title("Quiz Complete!")
    score = st.session_state[_k("score")]
    total = st.session_state[_k("total")]
    pct = round(100 * score / total) if total > 0 else 0
    st.metric("Final Score", f"{score}/{total}", f"{pct}%")

    if pct >= 80:
        st.success("Great job!")
    elif pct >= 50:
        st.info("Good effort — keep practicing.")
    else:
        st.warning("Keep studying — you'll get there!")

    if st.button("Back to Menu", type="primary"):
        reset_to_menu()


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
