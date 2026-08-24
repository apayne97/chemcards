import streamlit as st
import streamlit.components.v1 as components

# Replace with the Google Form embed URL once created.
# In Google Forms: Send → Embed → copy the src URL from the <iframe> tag.
FORM_EMBED_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdC7RbPRTgNMcekaQrq4Sx-2Qmco-x0dzQI_-e6mnzi5qj4mA/viewform?embedded=true"

st.title("📬 Feedback")
st.markdown(
    "We'd love to hear what you think! Your feedback helps improve ChemCards for everyone."
)
st.link_button(
    "Open a GitHub Issue",
    "https://github.com/apayne97/chemcards/issues",
    icon="🐛",
)
st.divider()

if FORM_EMBED_URL:
    components.iframe(FORM_EMBED_URL, height=600, scrolling=True)
else:
    st.info("Feedback form coming soon.")
