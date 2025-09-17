import streamlit as st
import os
import pickle
import concurrent.futures
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = 'client_secrets.json'
TOKEN_FILE = 'token_gdrive.pkl'

@st.cache_resource(show_spinner=False)
def authenticate_gdrive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return creds

@st.cache_data(show_spinner=False)
def list_gdrive_files_cached(_creds, mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
    service = build('drive', 'v3', credentials=_creds)
    results = service.files().list(q=f"mimeType='{mime_type}' and trashed=false", pageSize=50, fields="files(id, name)").execute()
    return results.get('files', [])

def download_gdrive_file_threaded(creds, file_id):
    service = build('drive', 'v3', credentials=creds)
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def gdrive_picker_ui():
    st.subheader('Google Drive File Picker')
    creds = authenticate_gdrive()
    with st.spinner("Listing Google Drive files..."):
        files = list_gdrive_files_cached(creds)
    file_names = [f["name"] for f in files]
    selected_files = st.multiselect('Select one or more DOCX files from your Google Drive:', file_names)
    results = []
    if st.button('Download Selected File(s)') and selected_files:
        with st.spinner("Downloading selected files from Google Drive..."):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_file = {
                    executor.submit(download_gdrive_file_threaded, creds, next(f['id'] for f in files if f['name'] == file_choice)): file_choice
                    for file_choice in selected_files
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    file_choice = future_to_file[future]
                    try:
                        file_data = future.result()
                        st.success(f"Downloaded {file_choice} from Google Drive!")
                        results.append((file_choice, file_data))
                    except Exception as e:
                        st.error(f"Failed to download {file_choice}: {e}")
        return results
    return []



