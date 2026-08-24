import random
import streamlit as st
from collections import Counter

from chemcards.database.core import MoleculeDB, MoleculeEntry
from chemcards.flashcards.multiplechoice import (
    MultipleChoiceMoleculeToTargetGenerator,
    MultipleChoiceMoleculeToNameGenerator,
    MultipleChoiceNameToMoleculeGenerator,
    MultipleChoice,
)
from utils import load_db, load_atc_lookup, render_smiles

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

QUIZ_TYPES = {
    "Molecule → Name": MultipleChoiceMoleculeToNameGenerator,
    "Name → Molecule": MultipleChoiceNameToMoleculeGenerator,
    "Molecule → Target": MultipleChoiceMoleculeToTargetGenerator,
}

P = "drugle_"


def _k(key):
    return P + key


def init_state():
    for key, val in {
        "mode": "menu",
        "generator": None,
        "current_question": None,
        "score": 0,
        "total": 0,
        "answered": False,
        "correct_last": None,
    }.items():
        st.session_state.setdefault(_k(key), val)
    for code in ATC_L1:
        st.session_state.setdefault(_k(f"atc_{code}"), True)
    st.session_state.setdefault(_k("atc_none"), True)


@st.cache_data
def compute_atc_counts() -> tuple[dict, int]:
    db = load_db()
    counts: Counter = Counter()
    no_atc = 0
    for m in db.molecules:
        if m.atc_classifications:
            seen: set = set()
            for code in m.atc_classifications:
                if code and code[0] not in seen:
                    counts[code[0]] += 1
                    seen.add(code[0])
        else:
            no_atc += 1
    return dict(counts), no_atc


def build_filtered_db() -> MoleculeDB:
    db = load_db()
    selected = {c for c in ATC_L1 if st.session_state.get(_k(f"atc_{c}"), True)}
    include_none = st.session_state.get(_k("atc_none"), True)
    mols = []
    for m in db.molecules:
        if m.atc_classifications:
            if any(code[0] in selected for code in m.atc_classifications if code):
                mols.append(m)
        elif include_none:
            mols.append(m)
    return MoleculeDB(molecules=mols)


def start_quiz(quiz_type: str):
    filtered = build_filtered_db()
    if len(filtered.molecules) < 4:
        st.error("Need at least 4 molecules — select more drug classes.")
        return
    gen = QUIZ_TYPES[quiz_type](molecule_db=filtered)
    st.session_state[_k("generator")] = gen
    st.session_state[_k("current_question")] = gen.next()
    st.session_state[_k("score")] = 0
    st.session_state[_k("total")] = 0
    st.session_state[_k("answered")] = False
    st.session_state[_k("correct_last")] = None
    st.session_state[_k("mode")] = "quiz"
    st.rerun()


def reset_to_menu():
    for key in ("generator", "current_question"):
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
    atc_counts, no_atc_count = compute_atc_counts()
    mode = st.session_state[_k("mode")]

    with st.sidebar:
        st.markdown("### 🧬 Drug Class (ATC)")
        c1, c2 = st.columns(2)
        if c1.button("All", key=_k("btn_all"), use_container_width=True):
            for code in ATC_L1:
                st.session_state[_k(f"atc_{code}")] = True
            st.session_state[_k("atc_none")] = True
            st.rerun()
        if c2.button("None", key=_k("btn_none"), use_container_width=True):
            for code in ATC_L1:
                st.session_state[_k(f"atc_{code}")] = False
            st.session_state[_k("atc_none")] = False
            st.rerun()

        for code, label in ATC_L1.items():
            count = atc_counts.get(code, 0)
            st.checkbox(f"{label} ({count})", key=_k(f"atc_{code}"))
        st.checkbox(f"Unclassified ({no_atc_count})", key=_k("atc_none"))

        st.divider()
        quiz_type = st.radio("Quiz type", list(QUIZ_TYPES.keys()), key=_k("quiz_type_radio"))
        st.divider()

        pool_size = len(build_filtered_db().molecules)
        st.caption(f"{pool_size:,} molecules selected")

        if mode == "menu":
            st.button(
                "▶ Start Quiz",
                type="primary",
                use_container_width=True,
                disabled=pool_size < 4,
                on_click=start_quiz,
                args=(quiz_type,),
            )
        else:
            if st.button("⏹ New Quiz", use_container_width=True):
                reset_to_menu()


# ---------------------------------------------------------------------------
# Main area: menu
# ---------------------------------------------------------------------------
def show_menu():
    st.title("💊 Drugle")
    st.markdown(
        "Test your knowledge of FDA-approved drugs. "
        "Use the sidebar to filter by drug class and choose a quiz type, then hit **Start Quiz**."
    )
    st.divider()
    st.markdown("**Quiz types**")
    st.markdown("- **Molecule → Name** — see the structure, pick the drug name")
    st.markdown("- **Name → Molecule** — see the name, pick the correct structure")
    st.markdown("- **Molecule → Target** — see the structure, pick the biological target")


# ---------------------------------------------------------------------------
# Main area: quiz
# ---------------------------------------------------------------------------
def show_quiz():
    q: MultipleChoice = st.session_state[_k("current_question")]
    score = st.session_state[_k("score")]
    total = st.session_state[_k("total")]
    answered = st.session_state[_k("answered")]

    col_title, col_score, col_end = st.columns([4, 1, 1])
    with col_title:
        quiz_type = st.session_state.get(_k("quiz_type_radio"), "Quiz")
        st.subheader(quiz_type)
    with col_score:
        st.metric("Score", f"{score}/{total}")
    with col_end:
        if st.button("End"):
            st.session_state[_k("mode")] = "result"
            st.rerun()

    st.divider()

    radio_key = _k(f"radio_{total}")
    choices_are_molecules = q.choices and isinstance(q.choices[0], MoleculeEntry)

    if choices_are_molecules:
        st.subheader(q.question)
        labels = ["A", "B", "C", "D"]
        top, bot = st.columns(2), st.columns(2)
        grid = [top[0], top[1], bot[0], bot[1]]
        for entry, col, label in zip(q.choices, grid, labels):
            with col:
                img = render_smiles(entry.smiles, size=250)
                if img:
                    st.image(img, caption=label)
        radio_val = st.radio("Your answer:", labels, index=None, key=radio_key, disabled=answered)
        selected_idx = labels.index(radio_val) if radio_val else None

    else:
        if q.display is not None:
            img = render_smiles(q.display.smiles, size=300)
            if img:
                col_img, _ = st.columns([1, 2])
                with col_img:
                    st.image(img)
        st.subheader(q.question)
        radio_val = st.radio("Your answer:", q.choices, index=None, key=radio_key, disabled=answered)
        selected_idx = q.choices.index(radio_val) if radio_val else None

    st.divider()

    if not answered:
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
            ans = q.choices[q.answer_index]
            if isinstance(ans, MoleculeEntry):
                ans = ans.name
            st.error(f"The answer was: **{ans}**")

        if q.answer_molecule:
            atc_lookup = load_atc_lookup()
            with st.expander("Molecule details"):
                m = q.answer_molecule
                st.markdown(f"**Name:** {m.name}")
                st.markdown(f"**Biological target:** {m.target}")
                if m.usan_stem_definition != "unknown":
                    st.markdown(f"**Drug family (USAN):** {m.usan_stem_definition}")
                if m.atc_classifications:
                    l3_labels = []
                    for code in m.atc_classifications:
                        if len(code) >= 4:
                            label = atc_lookup.get(code[:4])
                            if label:
                                l3_labels.append(label)
                    if l3_labels:
                        st.markdown(f"**Pharmacological class:** {', '.join(set(l3_labels))}")
                st.markdown(f"**Mechanism:** {m.mechanism_of_action}")
                if m.molecule_chembl_id != "unknown":
                    st.link_button(
                        "View on ChEMBL",
                        f"https://www.ebi.ac.uk/chembl/compound_report_card/{m.molecule_chembl_id}/",
                    )

        if st.button("Next Question", type="primary"):
            st.session_state[_k("current_question")] = st.session_state[_k("generator")].next()
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
