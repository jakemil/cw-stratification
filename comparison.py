# comparison.py
import streamlit as st
import pandas as pd
import random
import time
from firestore_utils import get_firestore_client, get_squadron_data, create_squadron_data

def update_elo(winner_rating, loser_rating, K=32):
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))
    return winner_rating + K * (1 - expected_winner), loser_rating + K * (0 - expected_loser)

def comparison_page():
    # Create two columns for the title and the button
    col1, col2 = st.columns([3, 1])

    # Title on the left
    with col1:
        st.title("Bullet Rating Comparison")

    # Button on the right
    with col2:
        st.markdown("""
            <div style='text-align: right; margin-top: 10px;'>
                <a href='?view=results' target='_self' style='text-decoration: none;'>
                    <button style='padding: 10px 20px; font-size: 16px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;'>Go to Rankings Page</button>
                </a>
            </div>
        """, unsafe_allow_html=True)

    client = get_firestore_client()

    # Dropdown to select squadron
    squadrons = [str(i) for i in range(1, 41)]
    selected_squadron = st.selectbox("Select Squadron:", squadrons)
    
    # Define squadron-specific session state keys
    auth_key = f"{selected_squadron}_ranking_authenticated"

    # Check if squadron data and password exist
    squadron_ref = client.collection('Rankings').document(selected_squadron)
    squadron_doc = squadron_ref.get()

    if squadron_doc.exists:
        squadron_data = squadron_doc.to_dict()

        # Initialize the authentication status for this specific squadron
        if auth_key not in st.session_state:
            st.session_state[auth_key] = False

        # Prompt for password if not already authenticated for this squadron
        if not st.session_state[auth_key]:
            # Prompt user to enter the ranking password
            password_attempt = st.text_input("Enter the ranking password to access comparisons", type="password")

            if st.button("Access Squadron for Ranking"):
                if password_attempt == squadron_data.get('ranking_password'):
                    st.success("Access granted!")
                    st.session_state[auth_key] = True  # Authenticate this specific squadron
                else:
                    st.error("Incorrect password.")
                    return  # Stop here if password is incorrect

        # If authenticated, display the comparison interface
        if st.session_state[auth_key]:
            display_comparison_interface(client, selected_squadron)
              
    else:
        # No data available, prompt user to upload a file and set passwords
        st.warning(f"No data available for Squadron {selected_squadron}. Please upload data to create it.")
        uploaded_file = st.file_uploader("Choose an Excel file to upload squadron data", type=['xlsx'])

        if uploaded_file is not None:
            # Prompt for two passwords: one for ranking and one for results
            ranking_password = st.text_input("Set a password for ranking access", type="password")
            results_password = st.text_input("Set a password for results access", type="password")

            if ranking_password and results_password and st.button("Upload and Set Passwords"):
                # Load data from the uploaded Excel file
                data = pd.read_excel(uploaded_file)
                
                # Find 'Name' and 'Class year' columns, ignoring case
                name_column = next((col for col in data.columns if col.lower() == 'name'), None)
                class_year_column = next((col for col in data.columns if col.lower() == 'class year'), None)

                # Check if the required columns are present
                if name_column is None or class_year_column is None:
                    st.error("The uploaded file must contain 'Name' and 'Class year' columns.")
                    return

                # Use the found column names to avoid case issues
                filtered_data = data.copy()
                filtered_data = filtered_data.rename(columns={name_column: 'Name', class_year_column: 'Class year'})
                filtered_data['Rating'] = 1200
                filtered_data['Compare_Count'] = 0

                # Store passwords and initial data in Firestore
                squadron_ref.set({
                    'ranking_password': ranking_password,
                    'results_password': results_password
                })
                create_squadron_data(client, selected_squadron, filtered_data)
                st.success("Squadron data uploaded, and passwords set successfully!")
                st.rerun()  # Reload to apply password protection




def display_comparison_interface(client, selected_squadron):
    # Fetch and display data for comparisons as per the original logic
    elo_data = get_squadron_data(client, selected_squadron)

    if not elo_data.empty:
        st.info(f"Squadron {selected_squadron} data loaded. File upload is disabled.")

        # Comparison logic
        if 'bullet_1' not in st.session_state or 'bullet_2' not in st.session_state:
            # Get unique class years with at least two entries
            # Calculate total comparisons for each class year
            class_years = elo_data['Class year'].unique()
            valid_class_years = [
                year for year in class_years if len(elo_data[elo_data['Class year'] == year]) >= 2
            ]

            if not valid_class_years:
                st.warning("Not enough bullet packages available for comparison.")
                return

            # Find the class year with the least number of comparisons
            class_year_comparisons = {
                year: elo_data[elo_data['Class year'] == year]['Compare_Count'].mean()
                for year in valid_class_years
            }

            selected_class_year = min(class_year_comparisons, key=class_year_comparisons.get)

            # Filter and select bullet packages for the chosen class year
            class_elo_data = elo_data[elo_data['Class year'] == selected_class_year]
            class_elo_data = class_elo_data.sort_values(by=['Compare_Count', 'Rating'])
            selected_bullets = class_elo_data.head(2).reset_index(drop=True)

            bullet_1 = selected_bullets.iloc[0]
            bullet_2 = selected_bullets.iloc[1]

            # Store bullet packages in session state
            st.session_state['bullet_1'] = bullet_1
            st.session_state['bullet_2'] = bullet_2
            st.session_state['selected_class_year'] = selected_class_year


        # Comparison form
        with st.form(key='comparison_form'):
            bullet_1 = st.session_state['bullet_1']
            bullet_2 = st.session_state['bullet_2']
            selected_class_year = st.session_state['selected_class_year']

            st.subheader(f"Compare Bullet Packages from Class Year {selected_class_year}")

            col1, col2 = st.columns(2)

            # Filter only columns with "bullet" in their name (case-insensitive)
            bullet_columns = [col for col in bullet_1.index if 'bullet' in col.lower()]

            # Display bullet package 1
            with col1:
                st.write("### Bullet Package 1:")
                bullet_1_content = bullet_1[bullet_columns].to_frame().to_html(header=False)
                st.markdown(f"<div style='word-wrap: break-word;'>{bullet_1_content}</div>", unsafe_allow_html=True)

            # Display bullet package 2
            with col2:
                st.write("### Bullet Package 2:")
                bullet_2_content = bullet_2[bullet_columns].to_frame().to_html(header=False)
                st.markdown(f"<div style='word-wrap: break-word;'>{bullet_2_content}</div>", unsafe_allow_html=True)

            # Let user select which bullet package they think is better
            winner = st.radio("Which bullet package is better?", ("Bullet 1", "Bullet 2"))
            submit_button = st.form_submit_button("Submit Comparison")

        # Process the form submission
        if submit_button:
            bullet_1_rating = float(bullet_1['Rating'])
            bullet_2_rating = float(bullet_2['Rating'])

            # Update Elo ratings based on the selected winner
            if winner == "Bullet 1":
                new_bullet_1_elo, new_bullet_2_elo = update_elo(bullet_1_rating, bullet_2_rating)
            else:
                new_bullet_2_elo, new_bullet_1_elo = update_elo(bullet_2_rating, bullet_1_rating)

            # Update Firestore with new ratings and compare counts
            squadron_ref = client.collection('Rankings').document(selected_squadron).collection('Packages')
            squadron_ref.document(bullet_1['Name']).update({
                'Rating': new_bullet_1_elo,
                'Compare_Count': int(bullet_1['Compare_Count']) + 1
            })
            squadron_ref.document(bullet_2['Name']).update({
                'Rating': new_bullet_2_elo,
                'Compare_Count': int(bullet_2['Compare_Count']) + 1
            })

            st.success("ELO ratings updated successfully!")

            # Clear session state for the next comparison
            del st.session_state['bullet_1']
            del st.session_state['bullet_2']
            del st.session_state['selected_class_year']

            # Rerun the app to load a new comparison
            time.sleep(2)
            st.rerun()
