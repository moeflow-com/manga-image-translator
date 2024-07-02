import logging
import streamlit as st

logging.basicConfig()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

st.set_page_config(
        page_title = "manga_image_translator in streamlit"
        )

logger.info("streamlit_main")

