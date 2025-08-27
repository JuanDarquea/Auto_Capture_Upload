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
import sys
import argparse
import time
import random

def parse_arguments(): 
    # argparse is Python's built-in library for handling command line arguments
    parser = argparse.ArgumentParser(description='Screenshot uploader with startup/shutdown modes')
    # This creates a --mode flag that only accepts 'startup', 'shutdown', or defaults to 'normal'
    parser.add_argument('--mode', choices=['startup', 'shutdown'], default='normal',
                       help='Run mode: startup, shutdown, or normal')
    # This creates a --silent flag that doesn't need a value (it's either there or not)
    parser.add_argument('--silent', action='store_true',
                       help='Run without user confirmation prompts')
    return parser.parse_args() # This actually reads the command line and returns the values

# Configuration
LOCAL_FOLDER = r"C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Capturas de pantalla"
DRIVE_FOLDER_ID = "1FbAfXLxmJbpcEtm0ctoDrjydNriRyECA"
SCOPES = ['https://www.googleapis.com/auth/drive']
LOG_FILE = "upload_log.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXECUTION_LOG_PATH = os.path.join(SCRIPT_DIR, "execution_log.txt")
DETAILED_LOG_PATH = os.path.join(SCRIPT_DIR, "detailed_execution_log.json")

class ScreenshotUploader:
    def __init__(self):
        print("Initializing uploader...")
        self.service = None
        self.drive_files = {}  # Will store files currently in Google Drive
        self.silent_mode = False # This is the robot's "personality setting"
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

    def create_detailed_log_entry(self, mode, file_details, success_count, failed_count):
        """
        Create detailed JSON log entry for data analysis
        This creates machine-readable logs that you can analyze later
        """
        import json
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "execution_summary": {
                "total_files": len(file_details),
                "successful_uploads": success_count,
                "failed_uploads": failed_count,
                "success_rate": (success_count / len(file_details) * 100) if file_details else 100
            },
            "files": file_details,
            "system_info": {
                "python_version": sys.version.split()[0],
                "os": os.name
            }
        }
        
        try:
            with open(DETAILED_LOG_PATH, "a", encoding='utf-8') as f:
                f.write(json.dumps(log_data, indent=2) + "\n" + "="*50 + "\n")
            print("Detailed log entry created")
            print(f"📍 Detailed log location: {DETAILED_LOG_PATH}")
        except Exception as e:
            print(f"Could not write detailed log: {e}")
            print(f"🔍 Attempted path: {DETAILED_LOG_PATH}")

    def upload_with_retry(self, file_path, max_retries=3):
        """
        Upload with intelligent retry logic
        
        Features:
        - Exponential backoff: Wait longer between each retry
        - Jitter: Add randomness to avoid thundering herd problems
        - Different handling for different error types
        
        Args:
            file_path (str): Path to file to upload
            max_retries (int): Maximum number of retry attempts
        
        Returns:
            bool: True if upload succeeded, False otherwise
        """
        import time
        import random # For jitter

        filename = os.path.basename(file_path)
        
        for attempt in range(max_retries):
            try:
                print(f"Upload attempt {attempt + 1}/{max_retries} for '{filename}'...")
                
                if self.upload_to_drive(file_path):
                    if attempt > 0:
                        print(f"Success on retry {attempt + 1} for '{filename}'")
                    return True
                    
            except Exception as e:
                error_type = type(e).__name__
                print(f"Attempt {attempt + 1} failed for '{filename}': {error_type}")
                
                # Don't retry on certain types of errors
                if "authentication" in str(e).lower() or "credentials" in str(e).lower():
                    print("Authentication error - not retrying")
                    return False
                
                if "file not found" in str(e).lower():
                    print("File not found - not retrying")
                    return False
                
                # Use our error classification
                should_retry, error_category = self.classify_error(e)
                
                if not should_retry:
                    print(f"🚫 {error_category} error - not retrying")
                    return False

                # If this isn't the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    base_delay = 2 ** attempt  # 1, 2, 4, 8 seconds
                    jitter = random.uniform(0.1, 0.5)  # Add 0.1-0.5 seconds randomness
                    delay = base_delay + jitter
                    
                    print(f"Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
        
        print(f"All {max_retries} attempts failed for '{filename}'")
        return False

    def classify_error(self, error):
        """
        Classify errors to determine retry strategy
        
        Returns:
            tuple: (should_retry: bool, error_category: str)
        """
        error_str = str(error).lower()
        
        # Never retry these errors
        if any(keyword in error_str for keyword in ['authentication', 'credentials', 'permission']):
            return False, "authentication"
        
        if any(keyword in error_str for keyword in ['file not found', 'path not found']):
            return False, "file_system"
        
        if any(keyword in error_str for keyword in ['quota exceeded', 'storage full']):
            return False, "quota"
        
        # Retry these errors
        if any(keyword in error_str for keyword in ['network', 'connection', 'timeout']):
            return True, "network"
        
        if any(keyword in error_str for keyword in ['rate limit', 'too many requests']):
            return True, "rate_limit"
        
        if any(keyword in error_str for keyword in ['server error', '500', '502', '503']):
            return True, "server"
        
        # Unknown errors - retry cautiously
        return True, "unknown"
    
    def log_execution(self, mode, success, file_count=0, error_message=None):
        """Log execution results"""
        """
        Professional logging system for automation tracking
        
        Args:
            mode (str): 'startup', 'shutdown', or 'manual'
            success (bool): True if execution succeeded
            file_count (int): Number of files processed
            error_message (str, optional): Error details if success=False
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "SUCCESS" if success else "FAILED"
        # Create a structured log entry
        log_entry = f"[{timestamp}] {mode.upper()} MODE - {status} - {file_count} files processed\n"

        if error_message:
            log_entry += f" | Error: {error_message}"
        
        log_entry += "\n"        
        try:
            # Append to log file (creates file if it doesn't exist)
            with open(EXECUTION_LOG_PATH, "a", encoding='utf-8') as f:
                f.write(log_entry)
                print(f"Logged: {status} - {file_count} files processed")
                print(f"Log location: {EXECUTION_LOG_PATH}") 
        except Exception as e:
            print(f"Could not write to log: {e}")
            print(f"Attempted path: {EXECUTION_LOG_PATH}")
            # Don't let logging failure break the main functionality
    
    def authenticate_google_drive(self):
        """Authenticate with Google Drive API"""
        print("\nStarting authentication...")
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists('token.json'):
            print("Found existing token.json")
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                print("Loaded credentials from token.json")
            except Exception as e:
                print(f"Error loading token.json: {e}")
                # If token.json is invalid, ask user if it should remove it
                user_input = input("Token is invalid. Remove token.json? (y/n): ")
                if user_input.lower() == 'y':
                    os.remove('token.json')
                    print("token.json removed")
                creds = None
        

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
            print("Successfully authenticated with Google Drive")
            return True
        except Exception as e:
            print(f"Error building Drive service: {e}")
            return False
    
    def scan_google_drive_folder(self):
        """Scan the Google Drive folder to see what files already exist"""
        print("\nScanning Google Drive folder for existing files...")
        
        try:
            # Query for all files in the specific Drive folder
            query = f"'{DRIVE_FOLDER_ID}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(name, id, createdTime, size)"
            ).execute()
            
            files = results.get('files', [])
            self.drive_files = {}
            
            print(f"Found {len(files)} files in Google Drive folder:")
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
                
                print(f"  {filename} ({size_mb:.2f} MB)")
            
            print(f"Google Drive scan completed - {len(self.drive_files)} files found")
            return True
            
        except HttpError as error:
            print(f"Error scanning Google Drive folder: {error}")
            return False
    
    def get_all_screenshots(self):
        """Find ALL .jpg files in the local folder"""
        print(f"\nScanning local folder: {LOCAL_FOLDER}")
        if not os.path.exists(LOCAL_FOLDER):
            print(f"Folder does not exist: {LOCAL_FOLDER}")
            return []
            
        jpg_pattern = os.path.join(LOCAL_FOLDER, "*.jpg")
        jpg_files = glob.glob(jpg_pattern)
        
        print(f"📊 Found {len(jpg_files)} .jpg files in local folder")
        return jpg_files
    
    def get_missing_screenshots(self, all_local_files):
        """Compare local files with Google Drive files to find missing ones"""
        print("\nComparing local folder with Google Drive folder...")
        missing_files = []
        
        for file_path in all_local_files:
            filename = os.path.basename(file_path)
            
            # Check if file exists in Google Drive
            if filename not in self.drive_files:
                missing_files.append(file_path)
                print(f"Missing in Drive: {filename}")
            else:
                print(f"Already in Drive: {filename}")
        
        # Sort by modification time (oldest first) to upload in chronological order
        missing_files.sort(key=os.path.getmtime)
        
        print(f"\nComparison Results:")
        print(f"Local files: {len(all_local_files)}")
        print(f"Drive files: {len(self.drive_files)}")
        print(f"Missing files to upload: {len(missing_files)}")
        
        return missing_files
    
    def show_upload_preview(self, file_list):
        """Show user what will be uploaded and ask for confirmation"""
        if not file_list:
            print("No files need to be uploaded! All screenshots are already in Google Drive.")
            return False  # Nothing to upload
        
        # Always show the preview (good for logging/debugging)
        print(f"\nUPLOAD PREVIEW - Found {len(file_list)} file(s) missing from Google Drive:")
        print("=" * 70)
        
        for i, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)  # Convert to MB
            
            print(f"{i:2d}. {filename}")
            print(f"     Date: {file_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Size: {file_size_mb:.2f} MB")
            print()
        
        print("=" * 70)
        print(f"Total files: {len(file_list)}")
        total_size = sum(os.path.getsize(f) for f in file_list) / (1024 * 1024)
        print(f"Total size: {total_size:.2f} MB")
        print(f"Destination: Google Drive → AI Road → Capturas de pantalla")
        print("=" * 70)

        # Skip confirmation in silent mode
        if self.silent_mode:
            print("Silent mode: Auto-confirming upload...")
            return True
        
        # Ask for confirmation
        while True:
            response = input("\nDo you want to upload these missing files? (y/n): ").lower().strip()
            if response in ['y', 'yes', 'si', 's']:
                print("Upload confirmed! Starting upload process...")
                return True
            elif response in ['n', 'no']:
                print("Upload cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no")
    
    def upload_to_drive(self, file_path):
        """Upload a file to Google Drive"""
        filename = os.path.basename(file_path)
        file_mod_time = os.path.getmtime(file_path)
        
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
            
            print(f"Successfully uploaded '{filename}'")
            print(f"File ID: {file.get('id')}")
            return True
            
        except HttpError as error:
            print(f"Error uploading '{filename}': {error}")
            return False
    
    def upload_multiple_screenshots(self, file_list):
        """Upload multiple screenshots"""
        """Enhanced batch upload with retry logic and detailed reporting"""
        if not file_list:
            print("No files to upload")
            return True
        
        successful_uploads = 0
        failed_uploads = 0
        file_details = []  # For detailed logging
        
        print(f"🚀 Starting batch upload of {len(file_list)} files...")
        
        for i, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            
            print(f"\n--- Upload {i}/{len(file_list)} ---")
            print(f"File: {filename}")
            print(f"Date: {file_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Size: {file_size:.2f} MB")

             # Record file details for logging
            file_detail = {
                "filename": filename,
                "size_mb": round(file_size, 2),
                "date": file_date.isoformat(),
                "upload_attempts": 0,
                "success": False,
                "error": None
            }
            
            start_time = time.time() 

            if self.upload_to_drive(file_path):
                successful_uploads += 1
                file_detail["success"] = True
                upload_time = time.time() - start_time
                file_detail["upload_time_seconds"] = round(upload_time, 2)
                print(f"Upload completed in {upload_time:.1f}s")
            else:
                failed_uploads += 1
                file_detail["error"] = "All retry attempts failed"
                print(f"Upload failed permanently")

            file_details.append(file_detail)
            
            # Save log after each upload to prevent data loss (in case of system crash)
            self.save_upload_log()

            # Small delay between uploads to be respectful to the API
            if i < len(file_list):  # Don't delay after the last file
                time.sleep(0.5)

        # Create detailed log entry
        self.create_detailed_log_entry("batch_upload", file_details, successful_uploads, failed_uploads)
        
        print(f"\nUpload Summary:")
        print(f"Successful: {successful_uploads}")
        print(f"Failed: {failed_uploads}")
        print(f"Total processed: {len(file_list)}")
        
        success_rate = (successful_uploads / len(file_list)) * 100
        print(f"Success rate: {success_rate:.1f}%")

        return failed_uploads == 0
    
    def run(self):
        """Main execution function"""
        mode = "manual"  # Default mode

        # Detect if we're running in automated mode
        if hasattr(self, 'silent_mode') and self.silent_mode:
            # Try to detect mode from command line arguments
#            import sys
            for arg in sys.argv:
                if 'startup' in arg:
                    mode = "startup"
                    break
                elif 'shutdown' in arg:
                    mode = "shutdown"
                    break

        print("\n🚀 Starting Screenshot Auto-Uploader (Drive Sync version)")
        print(f"📂 Local folder: {LOCAL_FOLDER}")
        print(f"☁️  Google Drive folder: AI Road → Capturas de pantalla")

        files_processed = 0
        error_occurred = None
        
        try:
            # Authenticate with Google Drive
            if not self.authenticate_google_drive():
               raise Exception("Authentication failed")

            # Scan Google Drive folder first
            if not self.scan_google_drive_folder():
                raise Exception("Failed to scan Google Drive folder")
            
            # Get all screenshots in local folder
            all_local_screenshots = self.get_all_screenshots()
            if not all_local_screenshots:
                self.log_execution(mode, True, 0)  # Success with 0 files
                print("No screenshots found in local folder")
                return
        
            # Find screenshots missing from Google Drive
            missing_screenshots = self.get_missing_screenshots(all_local_screenshots)
            
            # Show preview and ask for confirmation
#           if not self.show_upload_preview(missing_screenshots):
#               print("Upload process stopped.")
#               return

            # Count files that will be processed
            files_processed = len(missing_screenshots)

            # Upload all missing screenshots
            success = self.upload_multiple_screenshots(missing_screenshots)
            
            if success:
                print("\nAll uploads completed successfully!")
                print("Your screenshots are now ready to download on your phone!")
                self.log_execution(mode, True, files_processed)
            else:
                print("\nSome uploads failed - check the log above")
        except Exception as e:
            error_occurred = str(e)
            print(f"\nError during execution: {error_occurred}")
            self.log_execution(mode, False, files_processed, error_occurred)

if __name__ == "__main__":
    args = parse_arguments() # Parse what the user (or Windows) told us to do

    print(f"Starting Google Drive sync uploader in {args.mode} mode...")
    # Create our uploader object (your existing class)
    uploader = ScreenshotUploader()

    # Modify the uploader behavior based on mode, before it runs
    if args.mode in ['startup', 'shutdown']:
        uploader.silent_mode = True # Don't ask questions, just do the work
        print(f"Running in {args.mode} mode - automated execution")

    uploader.run() # Your existing logic takes over from here
