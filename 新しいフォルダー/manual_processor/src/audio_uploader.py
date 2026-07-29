"""
Audio Uploader Module (Plan C)
Handles uploading generated MP3 audio files to Google Drive API / Cloud Storage / Web Server
and returns a public web URL accessible via smartphone QR code.
"""

import os
import logging
import urllib.parse
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioUploader:
    """Uploads audio files to cloud storage or Google Drive and constructs public web URLs"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Audio Uploader.
        
        Args:
            base_url: Optional public base URL or Google Drive Folder URL/ID
        """
        self.base_url = base_url or os.getenv("AUDIO_PUBLIC_BASE_URL") or os.getenv("AUDIO_BASE_URL") or os.getenv("GOOGLE_DRIVE_FOLDER_URL")
        self.credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "credentials.json")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    
    def upload_to_google_drive(self, audio_file_path: Path) -> Optional[str]:
        """
        Directly upload MP3 audio file to Google Drive using Service Account credentials,
        make it publicly readable, and return direct streaming view link.
        """
        if not os.path.exists(self.credentials_path):
            return None

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            drive_service = build('drive', 'v3', credentials=creds)

            file_metadata = {'name': audio_file_path.name}
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]

            media = MediaFileUpload(str(audio_file_path), mimetype='audio/mpeg', resumable=True)
            uploaded_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()

            file_id = uploaded_file.get('id')
            logger.info(f"Uploaded {audio_file_path.name} to Google Drive. File ID: {file_id}")

            # Make file publicly readable
            user_permission = {
                'type': 'anyone',
                'role': 'reader',
            }
            drive_service.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields='id',
            ).execute()

            # Return direct stream/view URL suitable for mobile playback
            direct_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            logger.info(f"Google Drive Public URL: {direct_url}")
            return direct_url

        except Exception as e:
            logger.warning(f"Google Drive API Upload failed: {e}")
            return None

    def get_public_url(self, audio_file_path: Path) -> str:
        """
        Upload audio file or resolve public URL for smartphone QR code access.
        Supports Google Drive Service Account API upload & shared folder links.
        
        Args:
            audio_file_path: Path to the local MP3 audio file
            
        Returns:
            Public web URL string
        """
        if not audio_file_path.exists():
            logger.warning(f"Audio file does not exist: {audio_file_path}")
            return ""
        
        file_name = audio_file_path.name
        
        # 1. Try Google Drive API direct upload if credentials file exists
        gdrive_url = self.upload_to_google_drive(audio_file_path)
        if gdrive_url:
            return gdrive_url

        # 2. Check if configured for Google Drive shared folder or base URL
        if self.base_url:
            clean_url = self.base_url.strip()
            
            if "drive.google.com" in clean_url or "drive.google" in clean_url:
                logger.info(f"Using Google Drive shared folder link for QR code: {clean_url}")
                return clean_url
            
            clean_base = clean_url.rstrip('/')
            encoded_name = urllib.parse.quote(file_name)
            public_url = f"{clean_base}/{encoded_name}"
            logger.info(f"Generated cloud audio URL from base_url: {public_url}")
            return public_url
        
        # 3. Try HTTP upload service if AUDIO_UPLOAD_ENDPOINT is defined
        upload_endpoint = os.getenv("AUDIO_UPLOAD_ENDPOINT")
        if upload_endpoint:
            try:
                import urllib.request
                import json
                
                with open(audio_file_path, "rb") as f:
                    file_data = f.read()
                
                req = urllib.request.Request(upload_endpoint, data=file_data, method="POST")
                req.add_header("Content-Type", "audio/mpeg")
                req.add_header("X-File-Name", file_name)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_body = response.read().decode('utf-8')
                    res_json = json.loads(res_body)
                    public_url = res_json.get("url") or res_json.get("file_url")
                    if public_url:
                        logger.info(f"Uploaded audio to endpoint: {public_url}")
                        return public_url
            except Exception as e:
                logger.warning(f"HTTP upload failed: {e}")
        
        # 4. Fallback: file URI for local testing
        file_uri = audio_file_path.absolute().as_uri()
        logger.info(f"AUDIO_PUBLIC_BASE_URL not set in .env. Using fallback URI: {file_uri}")
        return file_uri


def upload_audio_summary(audio_file_path: Path, base_url: Optional[str] = None) -> str:
    """
    Convenience function to get public URL for audio file
    """
    uploader = AudioUploader(base_url=base_url)
    return uploader.get_public_url(audio_file_path)


