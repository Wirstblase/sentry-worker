import cv2
import time
import os
import sys
import subprocess
import threading
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
from collections import deque

logger = logging.getLogger(__name__)

class StreamProcessor:
    def __init__(self, sentry_client, stream_url="http://workshop-pi.local:5000/api/preview/stream"):
        self.sentry_client = sentry_client
        self.stream_url = stream_url
        self.running = False
        self._reader_thread = None
        self._inference_thread = None
        
        # Inference settings
        self.model_name = "yolo11n.pt"  # default
        self.model = YOLO(self.model_name)
        
        # Settings
        self.confidence_threshold = 0.55
        self.cooldown_seconds = 3
        self.blur_threshold = 2.0  # Laplacian variance threshold. Lower means more tolerant of blur.
        self.target_class = 14  # COCO class 14 is "bird"
        self.consecutive_frames_required = 3
        
        # snap!!!w
        self._snap_sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "snap!.mp3")

        # Screenshot saving
        self.screenshot_dir = "screenshots"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        
        # State
        self.last_snap_time = 0
        self.current_frame = None
        self.annotated_frame = None
        
        # Latest frame shared between reader and inference threads
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._frame_event = threading.Event()
        
        # Tracking history for stability
        self.bird_history = deque(maxlen=self.consecutive_frames_required)

    def set_model(self, model_name):
        logger.info(f"Loading new model: {model_name}")
        self.model_name = model_name
        self.model = YOLO(model_name)

    def start(self):
        if not self.running:
            self.running = True
            self.sentry_client.ensure_active()
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
            self._reader_thread.start()
            self._inference_thread.start()
            logger.info("StreamProcessor started (reader + inference threads).")

    def stop(self):
        if self.running:
            self.running = False
            self._frame_event.set()  # Unblock inference thread if waiting
            if self._reader_thread:
                self._reader_thread.join(timeout=3)
            if self._inference_thread:
                self._inference_thread.join(timeout=3)
            logger.info("StreamProcessor stopped.")

    def _calculate_blur(self, image):
        # Higher variance laplacian = sharper image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _play_snap_sound(self):
        """Play the snap sound file in a background thread (non-blocking)."""
        def _play():
            try:
                if not os.path.exists(self._snap_sound_path):
                    logger.warning(f"Snap sound file not found: {self._snap_sound_path}")
                    return
                if sys.platform == "darwin":
                    subprocess.run(["afplay", self._snap_sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif sys.platform == "win32":
                    subprocess.run(
                        ["powershell", "-c", f'(New-Object Media.SoundPlayer "{self._snap_sound_path}").PlaySync()'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                else:
                    # Linux: try mpv, then ffplay, then aplay as fallbacks
                    for cmd in (["mpv", "--no-video", self._snap_sound_path],
                                ["ffplay", "-nodisp", "-autoexit", self._snap_sound_path]):
                        try:
                            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                        except FileNotFoundError:
                            continue
                    logger.warning("No suitable audio player found on Linux")
            except Exception as e:
                logger.error(f"Failed to play snap sound: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def _save_screenshot(self):
        """Save the current annotated frame (with bounding boxes) to the screenshots directory."""
        if self.annotated_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detection_{timestamp}.jpg"
            filepath = os.path.join(self.screenshot_dir, filename)
            try:
                cv2.imwrite(filepath, self.annotated_frame)
                logger.info(f"Saved detection screenshot: {filepath}")
            except Exception as e:
                logger.error(f"Failed to save screenshot: {e}")

    def _reader_loop(self):
        while self.running:
            cap = None
            try:
                logger.info(f"[Reader] Connecting to stream: {self.stream_url}")
                cap = cv2.VideoCapture(self.stream_url)
                # Minimize OpenCV's internal buffer to 1 frame
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cap.isOpened():
                    logger.error("[Reader] Failed to open stream. Retrying in 5s...")
                    time.sleep(5)
                    continue

                logger.info("[Reader] Stream connected, reading frames.")
                while self.running and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("[Reader] Stream read returned false")
                        break

                    # Atomically publish the latest frame
                    with self._frame_lock:
                        self._latest_frame = frame
                    self._frame_event.set()

            except Exception as e:
                logger.error(f"[Reader] Stream error: {e}")
                time.sleep(2)
            finally:
                if cap is not None:
                    cap.release()

    def _inference_loop(self):
        while self.running:
            # Wait for a new frame to arrive (with timeout to allow clean shutdown)
            if not self._frame_event.wait(timeout=1.0):
                continue
            self._frame_event.clear()

            # Grab the latest frame (may skip many intermediate frames — that's the point)
            with self._frame_lock:
                frame = self._latest_frame
                self._latest_frame = None
            
            if frame is None:
                continue

            self.current_frame = frame.copy()

            try:
                # Run inference
                results = self.model(frame, classes=[self.target_class], conf=self.confidence_threshold, verbose=False)
                
                self.annotated_frame = results[0].plot()
                
                boxes = results[0].boxes
                
                bird_detected = False
                best_box = None
                best_blur = 0
                
                if len(boxes) > 0:
                    bird_detected = True
                    # Evaluate all birds, pick one that's sharpest
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Ensure within bounds
                        h, w = frame.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        
                        crop = frame[y1:y2, x1:x2]
                        if crop.size > 0:
                            blur_score = self._calculate_blur(crop)
                            if blur_score > best_blur:
                                best_blur = blur_score
                                best_box = box

                if bird_detected and best_box is not None:
                    self.bird_history.append(True)
                else:
                    self.bird_history.append(False)

                # Trigger logic
                now = time.time()
                if len(self.bird_history) == self.bird_history.maxlen and all(self.bird_history):
                    if (now - self.last_snap_time) > self.cooldown_seconds:
                        if best_blur > self.blur_threshold:
                            if self.sentry_client.is_ready():
                                logger.info(f"Triggering snap! Blur score: {best_blur:.2f}")
                                self._play_snap_sound()
                                self._save_screenshot()
                                self.sentry_client.snap(mode="auto")
                                self.last_snap_time = now
                                self.bird_history.clear() # Reset tracking
                            else:
                                logger.warning("Sentry not ready for snap")
                        else:
                            logger.info(f"Bird detected but rejected due to blur. Score: {best_blur:.2f} < {self.blur_threshold}")

                # Draw visual indicator for 2 seconds after snap
                if (now - self.last_snap_time) < 2.0:
                    cv2.putText(self.annotated_frame, "SNAP!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 255), 6, cv2.LINE_AA)

            except Exception as e:
                logger.error(f"[Inference] Error processing frame: {e}")

    def get_frame(self):
        # Used for emitting mjpeg to frontend
        if self.annotated_frame is not None:
             ret, buffer = cv2.imencode('.jpg', self.annotated_frame)
             if ret:
                 return buffer.tobytes()
        elif self.current_frame is not None:
             ret, buffer = cv2.imencode('.jpg', self.current_frame)
             if ret:
                 return buffer.tobytes()
        
        # Return empty byte if no frame
        return b''
