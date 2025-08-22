import os
import json
import glob
from datetime import datetime
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configuration
LOCAL_FOLDER = r"C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Capturas de pantalla"
DRIVE_FOLDER_ID = "1FbAfXLxmJbpcEtm0ctoDrjydNriRyECA"
SCOPES = ['https://www.googleapis.com/auth/drive']
LOG_FILE = "upload_log.json"

class ScreenshotUploader:
    def __init__(self):
        print("Initializing uploader...")
        self.service = None
        try:
            self.uploaded_files = self.load_upload_log()
            print("Upload log loaded successfully")
        except Exception as e:
            print(f"Error loading log: {e}")
            self.uploaded_files = {}
    
    def load_upload_log(self):
        """Load the log of previously uploaded files"""
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"Loaded {len(data)} entries from log")
                    return data
            except Exception as e:
                print(f"Error reading log file: {e}")
                return {}
        else:
            print("No existing log file found")
            return {}
    
    def save_upload_log(self):
        """Save the log of uploaded files"""
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.uploaded_files, f, indent=2, ensure_ascii=False)
            print("Upload log saved")
        except Exception as e:
            print(f"Error saving log: {e}")
    
    def authenticate_google_drive(self):
        """Authenticate with Google Drive API"""
        print("Starting authentication...")
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists('token.json'):
            print("Found existing token.json")
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                print("Loaded credentials from token.json")
            except Exception as e:
                print(f"Error loading token.json: {e}")
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                try:
                    creds.refresh(Request())
                    print("Credentials refreshed successfully")
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                print("Starting new authentication flow...")
                print("This will open your browser for Google authentication")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("Authentication completed successfully")
                except Exception as e:
                    print(f"Authentication failed: {e}")
                    return False
            
            # Save the credentials for the next run
            try:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                print("Credentials saved to token.json")
            except Exception as e:
                print(f"Error saving token.json: {e}")
        
        try:
            self.service = build('drive', 'v3', credentials=creds)
            print("✅ Successfully authenticated with Google Drive")
            return True
        except Exception as e:
            print(f"Error building Drive service: {e}")
            return False
    
    def get_newest_screenshot(self):
        """Find the newest .jpg file in the local folder"""
        print(f"Scanning folder: {LOCAL_FOLDER}")
        if not os.path.exists(LOCAL_FOLDER):
            print(f"❌ Folder does not exist: {LOCAL_FOLDER}")
            return None
            
        jpg_pattern = os.path.join(LOCAL_FOLDER, "*.jpg")
        jpg_files = glob.glob(jpg_pattern)
        
        print(f"Found {len(jpg_files)} .jpg files")
        
        if not jpg_files:
            print("❌ No .jpg files found in the folder")
            return None
        
        # Find the newest file by modification time
        newest_file = max(jpg_files, key=os.path.getmtime)
        return newest_file
    
    def file_exists_in_drive(self, filename):
        """Check if a file with the same name already exists in the Drive folder"""
        try:
            query = f"'{DRIVE_FOLDER_ID}' in parents and name='{filename}' and trashed=false"
            results = self.service.files().list(q=query).execute()
            items = results.get('files', [])
            return len(items) > 0
        except HttpError as error:
            print(f"❌ Error checking file existence: {error}")
            return False
    
    def upload_to_drive(self, file_path):
        """Upload a file to Google Drive"""
        filename = os.path.basename(file_path)
        
        # Check if file was already uploaded (by our log)
        file_mod_time = os.path.getmtime(file_path)
        if filename in self.uploaded_files:
            if self.uploaded_files[filename] >= file_mod_time:
                print(f"⏭️  File '{filename}' already uploaded")
                return True
        
        # Check if file exists in Drive (additional safety check)
        print("Checking if file already exists in Drive...")
        if self.file_exists_in_drive(filename):
            print(f"⚠️  File '{filename}' already exists in Drive folder")
            # Update our log to reflect this
            self.uploaded_files[filename] = file_mod_time
            self.save_upload_log()
            return True
        
        try:
            print(f"Starting upload of '{filename}'...")
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [DRIVE_FOLDER_ID]
            }
            
            # Create media upload object
            media = MediaFileUpload(file_path, mimetype='image/jpeg')
            
            # Upload the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # Update upload log
            self.uploaded_files[filename] = file_mod_time
            self.save_upload_log()
            
            print(f"✅ Successfully uploaded '{filename}' to Google Drive")
            print(f"📁 File ID: {file.get('id')}")
            return True
            
        except HttpError as error:
            print(f"❌ Error uploading file: {error}")
            return False
    
    def run(self):
        """Main execution function"""
        print("🚀 Starting Screenshot Auto-Uploader")
        print(f"📂 Scanning folder: {LOCAL_FOLDER}")
        
        # Authenticate with Google Drive
        if not self.authenticate_google_drive():
            print("❌ Authentication failed")
            return
        
        # Find newest screenshot
        newest_file = self.get_newest_screenshot()
        if not newest_file:
            print("❌ No screenshots found to upload")
            return
        
        filename = os.path.basename(newest_file)
        file_date = datetime.fromtimestamp(os.path.getmtime(newest_file))
        print(f"📸 Found newest screenshot: '{filename}'")
        print(f"📅 File date: {file_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Upload to Drive
        success = self.upload_to_drive(newest_file)
        
        if success:
            print("🎉 Upload process completed successfully!")
        else:
            print("❌ Upload process failed")

if __name__ == "__main__":
    print("Starting uploader...")
    uploader = ScreenshotUploader()
    uploader.run()