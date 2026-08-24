import streamlit as st
from pathlib import Path
from PIL import Image

_icon_path = Path("assets/chemcards-logo.png")
_icon = Image.open(_icon_path)

st.set_page_config(page_title="ChemCards", page_icon=_icon, layout="centered")
st.logo("assets/chemcards-logo.png")
pg = st.navigation([
    st.Page("pages/stats.py", title="Home", icon="🏠", default=True),
    st.Page("pages/drugle.py", title="Drug Quiz", icon="💊"),
    st.Page("pages/pharmadle.py", title="Pharmadle", icon="🟩"),
    st.Page("pages/medchemble.py", title="FG Quiz", icon="⚗️"),
    st.Page("pages/fg_wordle.py", title="FG Wordle", icon="🟩"),
    st.Page("pages/feedback.py", title="Feedback", icon="📬"),
])
pg.run()
