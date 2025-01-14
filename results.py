# results.py
import streamlit as st
import pandas as pd
from firestore_utils import get_firestore_client, get_squadron_data

def results_page():
    # Create two columns for the title and the button
    col1, col2 = st.columns([3, 1])

    # Title on the left
    with col1:
        st.title("Database Results Table")

    # Button on the right to go back to the comparison page
    with col2:
        st.markdown("""
            <div style='text-align: right; margin-top: 10px;'>
                <a href='?view=main' target='_self' style='text-decoration: none;'>
                    <button style='padding: 10px 20px; font-size: 16px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;'>Go to Comparisons</button>
                </a>
            </div>
        """, unsafe_allow_html=True)

    client = get_firestore_client()

    # Dropdown to select squadron
    squadron = st.selectbox("Select Squadron to View:", [str(i) for i in range(1, 41)])

    # Define squadron-specific session state keys
    auth_key = f"{squadron}_results_authenticated"

    # Fetch the squadron document to check if a password is set
    squadron_ref = client.collection('Rankings').document(squadron)
    squadron_doc = squadron_ref.get()

    if squadron_doc.exists:
        squadron_data = squadron_doc.to_dict()

        # Initialize the authentication status for this specific squadron
        if auth_key not in st.session_state:
            st.session_state[auth_key] = False

        # Prompt for password if not already authenticated for this squadron
        if not st.session_state[auth_key]:
            # Password protection is enabled for viewing results
            password_attempt = st.text_input("Enter the password for viewing results", type="password")

            if st.button("View Squadron Data"):
                if password_attempt == squadron_data.get('results_password'):
                    st.success("Access granted!")
                    st.session_state[auth_key] = True  # Authenticate this specific squadron
                else:
                    st.error("Incorrect password.")
                    return  # Exit the function if the password is wrong

        # Display squadron data if the password has been verified
        if st.session_state[auth_key]:
            display_squadron_data(client, squadron)

            # Show delete button after successful password entry
            if not st.session_state.get('confirm_delete'):
                if st.button("Delete All Squadron Data"):
                    # Set confirmation flag in session state
                    st.session_state['confirm_delete'] = True

            # Check for confirmation state and display warning/confirmation button
            if st.session_state.get('confirm_delete'):
                st.warning("Are you sure you want to delete all data for this squadron? This action cannot be undone.")
                if st.button("Confirm Delete"):
                    # Proceed with deletion if confirmed
                    delete_squadron_data(client, squadron_ref, squadron)

                    # Reset the confirmation state and viewing state after deletion
                    st.session_state['confirm_delete'] = False
                    st.session_state[auth_key] = False  # Clear authentication for this squadron after deletion
                    st.rerun()  # Reload the page to reflect deletion

    else:
        st.write("No data available for this squadron.")




def delete_squadron_data(client, squadron_ref, squadron):
    """Function to delete all data for a specified squadron."""
    # Delete all documents in the "Packages" sub-collection for the selected squadron
    packages_ref = squadron_ref.collection('Packages')
    packages = packages_ref.stream()
    deleted_count = 0  # To count deleted documents

    for package in packages:
        st.write("Deleting package:", package.id)  # Debugging statement
        package.reference.delete()  # Delete each document in "Packages"
        deleted_count += 1

    st.write(f"Total documents deleted from 'Packages': {deleted_count}")  # Debugging statement

    # Optionally delete the main squadron document to completely remove it
    squadron_ref.delete()
    st.write("Main squadron document deleted")  # Debugging statement

    st.success(f"All data for Squadron {squadron} has been deleted.")


def display_squadron_data(client, squadron):
    # Fetch data for the selected squadron
    squadron_data = get_squadron_data(client, squadron)

    # Display data by year with only Name and Score (Rating), sorted by Score
    if not squadron_data.empty:
        st.write(f"Displaying data for Squadron {squadron}:")

        # Filter only Name, Class year, and Rating columns
        display_data = squadron_data[['Name', 'Class year', 'Rating', 'Compare_Count']]

        # Sort by Rating in descending order (highest score at the top)
        display_data = display_data.sort_values(by='Rating', ascending=False)

        # Group the data by Class year and display in separate columns
        grouped_data = list(display_data.groupby('Class year'))
        columns = st.columns(len(grouped_data))  # Create a column for each year group
        for (year, group), col in zip(grouped_data, columns):
            col.subheader(f"Class Year: {year}")
            col.dataframe(group[['Name', 'Rating', 'Compare_Count']].reset_index(drop=True))
    else:
        st.write("No data available for this squadron.")
