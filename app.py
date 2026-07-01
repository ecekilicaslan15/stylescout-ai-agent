import streamlit as st

from orchestrator.fashion_orchestrator import run_fashion_agent


st.set_page_config(
    page_title="Fashion Agent",
    page_icon="👗",
    layout="centered"
)

st.title("Fashion Agent")
st.write("Describe what kind of outfit you need.")

user_input = st.text_input(
    "What are you looking for?",
    placeholder="Example: I need an elegant black dress for a wedding in summer under $300"
)

if st.button("Create Plan"):
    if user_input.strip() == "":
        st.warning("Please enter a fashion request.")
    else:
        result = run_fashion_agent(user_input)

        st.subheader("Planner Agent Output")
        st.json(result["plan"])

        st.subheader("Trend Agent Output")
        st.json(result["trends"])

        st.subheader("Stylist Agent Output")
        st.json(result["outfit"])
