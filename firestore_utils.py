# firestore_utils.py
from google.cloud import firestore
from google.oauth2 import service_account
import streamlit as st
import pandas as pd

# For local testing
#  def get_firestore_client():
#     return firestore.Client.from_service_account_json('key.json')

def get_firestore_client():
    # Load credentials from Streamlit secrets
    firebase_secrets = st.secrets["firebase"]
    credentials = service_account.Credentials.from_service_account_info(firebase_secrets)
    return firestore.Client(credentials=credentials)

def get_squadron_data(client, squadron):
    squadron_ref = client.collection('Rankings').document(squadron).collection('Packages')
    docs = squadron_ref.stream()
    data = [doc.to_dict() for doc in docs]
    return pd.DataFrame(data) if data else pd.DataFrame()

def create_squadron_data(client, squadron, initial_data):
    squadron_ref = client.collection('Rankings').document(squadron).collection('Packages')
    for _, row in initial_data.iterrows():
        squadron_ref.document(row['Name']).set(row.to_dict())
