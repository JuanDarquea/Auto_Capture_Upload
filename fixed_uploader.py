import os
# print("Current working directory:", os.getcwd())
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
        self.drive_files = {}  # Will store files currently in Google Drive
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
        
        if os.path.exists('token.json'):
            print("Found existing token.json")
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                print("Loaded credentials from token.json")
            except Exception as e:
                print(f"Error loading token.json: {e}")
        
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
                try:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("Authentication completed successfully")
                except Exception as e:
                    print(f"Authentication failed: {e}")
                    return False
            
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
    
    def scan_google_drive_folder(self):
        """Scan the Google Drive folder to see what files already exist"""
        print("📡 Scanning Google Drive folder for existing files...")
        
        try:
            # Query for all files in the specific Drive folder
            query = f"'{DRIVE_FOLDER_ID}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(name, id, createdTime, size)"
            ).execute()
            
            files = results.get('files', [])
            self.drive_files = {}
            
            print(f"📊 Found {len(files)} files in Google Drive folder:")
            for file in files:
                filename = file['name']
                file_id = file['id']
                created_time = file.get('createdTime', 'Unknown')
                file_size = file.get('size', '0')
                
                # Convert size to MB for display
                size_mb = int(file_size) / (1024 * 1024) if file_size.isdigit() else 0
                
                self.drive_files[filename] = {
                    'id': file_id,
                    'created': created_time,
                    'size': file_size
                }
                
                print(f"  📁 {filename} ({size_mb:.2f} MB)")
            
            print(f"✅ Google Drive scan completed - {len(self.drive_files)} files found")
            return True
            
        except HttpError as error:
            print(f"❌ Error scanning Google Drive folder: {error}")
            return False
    
    def get_all_screenshots(self):
        """Find ALL .jpg files in the local folder"""
        print(f"📂 Scanning local folder: {LOCAL_FOLDER}")
        if not os.path.exists(LOCAL_FOLDER):
            print(f"❌ Folder does not exist: {LOCAL_FOLDER}")
            return []
            
        jpg_pattern = os.path.join(LOCAL_FOLDER, "*.jpg")
        jpg_files = glob.glob(jpg_pattern)
        
        print(f"📊 Found {len(jpg_files)} .jpg files in local folder")
        return jpg_files
    
    def get_missing_screenshots(self, all_local_files):
        """Compare local files with Google Drive files to find missing ones"""
        print("🔍 Comparing local folder with Google Drive folder...")
        missing_files = []
        
        for file_path in all_local_files:
            filename = os.path.basename(file_path)
            
            # Check if file exists in Google Drive
            if filename not in self.drive_files:
                missing_files.append(file_path)
                print(f"❌ Missing in Drive: {filename}")
            else:
                print(f"✅ Already in Drive: {filename}")
        
        # Sort by modification time (oldest first) to upload in chronological order
        missing_files.sort(key=os.path.getmtime)
        
        print(f"\n📊 Comparison Results:")
        print(f"📁 Local files: {len(all_local_files)}")
        print(f"☁️  Drive files: {len(self.drive_files)}")
        print(f"📤 Missing files to upload: {len(missing_files)}")
        
        return missing_files
    
    def show_upload_preview(self, file_list):
        """Show user what will be uploaded and ask for confirmation"""
        if not file_list:
            print("✅ No files need to be uploaded! All screenshots are already in Google Drive.")
            return False  # Nothing to upload
        
        print(f"\n📋 UPLOAD PREVIEW - Found {len(file_list)} file(s) missing from Google Drive:")
        print("=" * 70)
        
        for i, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)  # Convert to MB
            
            print(f"{i:2d}. 📸 {filename}")
            print(f"    📅 Date: {file_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    📏 Size: {file_size_mb:.2f} MB")
            print()
        
        print("=" * 70)
        print(f"📊 Total files: {len(file_list)}")
        total_size = sum(os.path.getsize(f) for f in file_list) / (1024 * 1024)
        print(f"📦 Total size: {total_size:.2f} MB")
        print(f"🗂️  Destination: Google Drive → AI Road → Capturas de pantalla")
        print("=" * 70)
        
        # Ask for confirmation
        while True:
            response = input("\n❓ Do you want to upload these missing files? (y/n): ").lower().strip()
            if response in ['y', 'yes', 'si', 's']:
                print("✅ Upload confirmed! Starting upload process...")
                return True
            elif response in ['n', 'no']:
                print("❌ Upload cancelled by user.")
                return False
            else:
                print("⚠️  Please enter 'y' for yes or 'n' for no")
    
    def upload_to_drive(self, file_path):
        """Upload a file to Google Drive"""
        filename = os.path.basename(file_path)
        file_mod_time = os.path.getmtime(file_path)
        
        try:
            print(f"📤 Starting upload of '{filename}'...")
            
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
            
            print(f"✅ Successfully uploaded '{filename}'")
            print(f"📁 File ID: {file.get('id')}")
            return True
            
        except HttpError as error:
            print(f"❌ Error uploading '{filename}': {error}")
            return False
    
    def upload_multiple_screenshots(self, file_list):
        """Upload multiple screenshots"""
        if not file_list:
            print("⏭️  No files to upload")
            return True
        
        successful_uploads = 0
        failed_uploads = 0
        
        print(f"🚀 Starting batch upload of {len(file_list)} files...")
        
        for i, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            print(f"\n--- Upload {i}/{len(file_list)} ---")
            print(f"📸 File: {filename}")
            print(f"📅 Date: {file_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if self.upload_to_drive(file_path):
                successful_uploads += 1
            else:
                failed_uploads += 1
            
            # Save log after each upload to prevent data loss
            self.save_upload_log()
        
        print(f"\n📊 Upload Summary:")
        print(f"✅ Successful: {successful_uploads}")
        print(f"❌ Failed: {failed_uploads}")
        print(f"📝 Total processed: {len(file_list)}")
        
        return failed_uploads == 0
    
    def run(self):
        """Main execution function"""
        print("🚀 Starting Screenshot Auto-Uploader (Drive Sync version)")
        print(f"📂 Local folder: {LOCAL_FOLDER}")
        print(f"☁️  Google Drive folder: AI Road → Capturas de pantalla")
        
        # Authenticate with Google Drive
        if not self.authenticate_google_drive():
            print("❌ Authentication failed")
            return
        
        # Scan Google Drive folder first
        if not self.scan_google_drive_folder():
            print("❌ Failed to scan Google Drive folder")
            return
        
        # Get all screenshots in local folder
        all_local_screenshots = self.get_all_screenshots()
        if not all_local_screenshots:
            print("❌ No screenshots found in local folder")
            return
        
        # Find screenshots missing from Google Drive
        missing_screenshots = self.get_missing_screenshots(all_local_screenshots)
        
        # Show preview and ask for confirmation
#        if not self.show_upload_preview(missing_screenshots):
#            print("🛑 Upload process stopped.")
#            return
        
        # Upload all missing screenshots
        success = self.upload_multiple_screenshots(missing_screenshots)
        
        if success:
            print("\n🎉 All uploads completed successfully!")
            print("📱 Your screenshots are now ready to download on your phone!")
        else:
            print("\n⚠️  Some uploads failed - check the log above")

if __name__ == "__main__":
    print("Starting Google Drive sync uploader...")
    uploader = ScreenshotUploader()
    uploader.run()