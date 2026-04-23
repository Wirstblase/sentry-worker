import requests
import logging
import threading
import time
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class SentryClient:
    def __init__(self, base_url="http://workshop-pi.local:5000", download_dir="downloads"):
        self.base_url = base_url
        self.download_dir = download_dir
        self.pending_downloads = []
        self.last_activity_time = time.time()
        self.inactivity_threshold = 300  # 5 minutes without snaps before downloading
        self.download_thread = None
        self.running = True
        
        # Ensure download directory exists
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        
        # Start background thread to monitor inactivity
        self.download_thread = threading.Thread(target=self._monitor_downloads, daemon=True)
        self.download_thread.start()

    def get_status(self):
        try:
            resp = requests.get(f"{self.base_url}/api/sentry/status", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get sentry status: {e}")
        return {"active": False}

    def enable(self):
        try:
            resp = requests.post(f"{self.base_url}/api/sentry/enable", timeout=15)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"Enable failed: {resp.text}")
        except requests.RequestException as e:
            logger.error(f"Failed to enable sentry mode: {e}")
        return {"active": False}

    def ensure_active(self):
        status = self.get_status()
        if not status.get("active", False):
            logger.info("Sentry mode not active, enabling...")
            self.enable()

    def is_ready(self):
        try:
            resp = requests.get(f"{self.base_url}/api/sentry/ready", timeout=2)
            if resp.status_code == 200:
                return resp.json().get("ready", False)
        except requests.RequestException as e:
            logger.error(f"Failed to check sentry ready status: {e}")
        return False

    def snap(self, mode="auto"):
        try:
            payload = {"mode": mode}
            resp = requests.post(f"{self.base_url}/api/sentry/snap", json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                filename = data.get("filename")
                if filename:
                    logger.info(f"Successfully snapped: {filename}")
                    self.pending_downloads.append(filename)
                    self.last_activity_time = time.time()
                return data
            else:
                logger.error(f"Failed to snap picture - Status {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            logger.error(f"Error calling snap: {e}")
        return None

    def _monitor_downloads(self):
        while self.running:
            time.sleep(10)
            if self.pending_downloads:
                time_since_activity = time.time() - self.last_activity_time
                if time_since_activity > self.inactivity_threshold:
                    self._process_downloads()

    def _process_downloads(self):
        logger.info(f"Processing {len(self.pending_downloads)} pending downloads...")
        # Copy to avoid modifying while iterating, but realistically thread safe enough for now
        to_download = list(self.pending_downloads)
        
        for filename in to_download:
            try:
                logger.info(f"Downloading {filename}...")
                resp = requests.get(f"{self.base_url}/api/gallery/{filename}", stream=True, timeout=30)
                if resp.status_code == 200:
                    filepath = os.path.join(self.download_dir, filename)
                    with open(filepath, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    logger.info(f"Successfully downloaded {filename}")
                    self.pending_downloads.remove(filename)
                else:
                    logger.error(f"Failed to download {filename}: Status {resp.status_code}")
            except requests.RequestException as e:
                logger.error(f"Error downloading {filename}: {e}")
                
    def get_stats(self):
        # Scan local download dir
        try:
            local_files = [f for f in os.listdir(self.download_dir) if f.endswith('.jpg')]
        except FileNotFoundError:
            local_files = []
            
        return {
            "pending_count": len(self.pending_downloads),
            "downloaded_count": len(local_files),
            "inactivity_timer": max(0, int(self.inactivity_threshold - (time.time() - self.last_activity_time))) if self.pending_downloads else 0
        }

    def stop(self):
        self.running = False
        if self.download_thread:
            self.download_thread.join(timeout=2)
