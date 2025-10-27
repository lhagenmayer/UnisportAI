import streamlit as st
from data.supabase_client import kurse_mit_angeboten

st.markdown("# Main page 🎈")
st.sidebar.markdown("# Main page 🎈")

st.title('Unisport Planner')

st.dataframe(kurse_mit_angeboten(), use_container_width=True)