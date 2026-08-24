import streamlit as st
from pathlib import Path
from PIL import Image

_icon_path = Path("assets/chemcards-logo.png")
_icon = Image.open(_icon_path)

st.set_page_config(page_title="ChemCards", page_icon=_icon, layout="centered")
pg = st.navigation([
    st.Page("pages/stats.py", title="Home", icon="🏠", default=True),
    st.Page("pages/drugle.py", title="Drugle", icon="💊"),
    st.Page("pages/medchemble.py", title="MedChemble", icon="⚗️"),
    st.Page("pages/feedback.py", title="Feedback", icon="📬"),
])
pg.run()
