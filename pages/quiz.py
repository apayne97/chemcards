import streamlit as st

from chemcards.database.core import MoleculeEntry
from chemcards.database.cheminformatics import FunctionalGroup
from chemcards.flashcards.multiplechoice import (
    MultipleChoiceMoleculeToTargetGenerator,
    MultipleChoiceMoleculeToNameGenerator,
    MultipleChoiceNameToMoleculeGenerator,
    MultipleChoiceMoleculeToFunctionalGroupNameGenerator,
)
from utils import load_db, load_filtered_db, render_smiles, render_smarts


QUIZZES = {
    "Molecule → Target": (MultipleChoiceMoleculeToTargetGenerator, True),
    "Molecule → Name": (MultipleChoiceMoleculeToNameGenerator, True),
    "Name → Molecule": (MultipleChoiceNameToMoleculeGenerator, True),
    "Functional Group → Name": (MultipleChoiceMoleculeToFunctionalGroupNameGenerator, False),
}


def init_state() -> None:
    defaults: dict = {
        "mode": "menu",
        "generator": None,
        "quiz_name": "",
        "current_question": None,
        "score": 0,
        "total": 0,
        "answered": False,
        "correct_last": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def show_menu() -> None:
    st.title("🧪 ChemCards")
    st.markdown("Test your chemistry knowledge. Choose a quiz to get started.")
    st.divider()

    raw_db = load_db()
    filtered_db = load_filtered_db()

    for quiz_name, (GeneratorClass, apply_filters) in QUIZZES.items():
        if st.button(quiz_name, use_container_width=True):
            db = filtered_db if apply_filters else raw_db
            generator = GeneratorClass(molecule_db=db)
            st.session_state.generator = generator
            st.session_state.quiz_name = quiz_name
            st.session_state.current_question = generator.next()
            st.session_state.score = 0
            st.session_state.total = 0
            st.session_state.answered = False
            st.session_state.correct_last = None
            st.session_state.mode = "quiz"
            st.rerun()


def show_quiz() -> None:
    q = st.session_state.current_question

    col_title, col_score, col_end = st.columns([4, 1, 1])
    with col_title:
        st.subheader(st.session_state.quiz_name)
    with col_score:
        st.metric("Score", f"{st.session_state.score}/{st.session_state.total}")
    with col_end:
        if st.button("End Quiz"):
            st.session_state.mode = "result"
            st.rerun()

    st.divider()

    choices_are_molecules = q.choices and isinstance(q.choices[0], MoleculeEntry)
    radio_key = f"answer_radio_{st.session_state.total}"

    if choices_are_molecules:
        st.subheader(q.question)

        labels = ["A", "B", "C", "D"]
        top_cols = st.columns(2)
        bot_cols = st.columns(2)
        grid = [top_cols[0], top_cols[1], bot_cols[0], bot_cols[1]]
        for mol_entry, col, label in zip(q.choices, grid, labels):
            with col:
                img = render_smiles(mol_entry.smiles, size=250)
                if img:
                    st.image(img, caption=label)

        radio_value = st.radio(
            "Your answer:",
            labels,
            index=None,
            key=radio_key,
            disabled=st.session_state.answered,
        )
        selected_idx = labels.index(radio_value) if radio_value else None

    else:
        if q.display is not None:
            if isinstance(q.display, FunctionalGroup):
                img = render_smarts(q.display.smarts)
            else:
                img = render_smiles(q.display.smiles)
            if img:
                col_img, _ = st.columns([1, 2])
                with col_img:
                    st.image(img)

        st.subheader(q.question)
        radio_value = st.radio(
            "Your answer:",
            q.choices,
            index=None,
            key=radio_key,
            disabled=st.session_state.answered,
        )
        selected_idx = q.choices.index(radio_value) if radio_value else None

    st.divider()

    if not st.session_state.answered:
        if st.button("Check Answer", disabled=(radio_value is None), type="primary"):
            st.session_state.answered = True
            st.session_state.total += 1
            st.session_state.correct_last = selected_idx == q.answer_index
            if st.session_state.correct_last:
                st.session_state.score += 1
            st.rerun()
    else:
        if st.session_state.correct_last:
            st.success("Correct!")
        else:
            correct = q.choices[q.answer_index]
            if isinstance(correct, MoleculeEntry):
                correct = correct.name
            st.error(f"Incorrect. The answer was: **{correct}**")

        if q.answer_molecule:
            with st.expander("View molecule details"):
                m = q.answer_molecule
                st.markdown(f"**Name:** {m.name}")
                st.markdown(f"**Target:** {m.target}")
                st.markdown(f"**Mechanism:** {m.mechanism_of_action}")
                st.markdown(f"**Indication:** {m.indication}")
                if m.molecule_chembl_id != "unknown":
                    st.link_button(
                        "View on ChEMBL",
                        f"https://www.ebi.ac.uk/chembl/compound_report_card/{m.molecule_chembl_id}/",
                    )

        if st.button("Next Question", type="primary"):
            st.session_state.current_question = st.session_state.generator.next()
            st.session_state.answered = False
            st.session_state.correct_last = None
            st.rerun()


def show_result() -> None:
    st.title("Quiz Complete!")
    score = st.session_state.score
    total = st.session_state.total
    pct = round(100 * score / total) if total > 0 else 0
    st.metric("Final Score", f"{score}/{total}", f"{pct}%")

    if pct >= 80:
        st.success("Great job!")
    elif pct >= 50:
        st.info("Good effort! Keep practicing.")
    else:
        st.warning("Keep studying — you'll get there!")

    if st.button("Back to Menu", type="primary"):
        st.session_state.mode = "menu"
        st.session_state.generator = None
        st.session_state.current_question = None
        st.session_state.score = 0
        st.session_state.total = 0
        st.session_state.answered = False
        st.session_state.correct_last = None
        st.rerun()


init_state()

if st.session_state.mode == "menu":
    show_menu()
elif st.session_state.mode == "quiz":
    show_quiz()
elif st.session_state.mode == "result":
    show_result()
