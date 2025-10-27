import streamlit as st

# Custom CSS für schmalere Sidebar und breiteren Hauptinhalt
st.markdown(
    """
    <style>
    /* Sidebar schmaler machen */
    [data-testid="stSidebar"] {
        min-width: 200px;
        max-width: 400px;
    }
    
    /* Hauptinhalt breiter machen */
    .block-container {
        max-width: 69%;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Breiteres Layout für den gesamten Content */
    .main .block-container {
        max-width: 69%;
    }
    </style>
    """,
)

# Define the pages
main_page = st.Page("pages/main_page.py", title="Main Page", icon="🎈")
page_2 = st.Page("pages/page_2.py", title="Page 2", icon="❄️")
page_3 = st.Page("pages/page_3.py", title="Page 3", icon="🎉")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3])

# Run the selected page
pg.run()