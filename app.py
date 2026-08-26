import streamlit as st
from pathlib import Path
from PIL import Image

_icon_path = Path("assets/chemcards-logo.png")
_icon = Image.open(_icon_path)

st.set_page_config(page_title="ChemCards", page_icon=_icon, layout="centered")
st.logo("assets/chemcards-logo.png")
pg = st.navigation({
    "": [
        st.Page("pages/stats.py", title="Home", icon="🏠", default=True),
    ],
    "Build Your Own": [
        st.Page("pages/drug_quiz.py", title="Drug Quiz", icon="💊"),
        st.Page("pages/fg_quiz.py", title="Functional Group Quiz", icon="⚗️"),
        st.Page("pages/cbb_quiz.py", title="Chemical Building Blocks Quiz", icon="🧱"),
    ],
    "Inspired by Wordle": [
        st.Page("pages/drugle.py", title="Drugle", icon="💊"),
        st.Page("pages/orgle.py", title="Orgle", icon="⚗️"),
        st.Page("pages/medchemble.py", title="MedChemble", icon="🧱"),
    ],
    "Glossary": [
        st.Page("pages/drug_glossary.py", title="Drug Glossary", icon="📖"),
        st.Page("pages/fg_glossary.py", title="Functional Group Glossary", icon="📖"),
        st.Page("pages/cbb_glossary.py", title="Chemical Building Blocks", icon="🧱"),
        st.Page("pages/feedback.py", title="Feedback", icon="📬"),
    ],
})
pg.run()
