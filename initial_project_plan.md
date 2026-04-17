# AI-Powered Sentry Camera Stream Processor

This plan details the implementation of a cross-platform Python 3 application that reads an MJPEG video stream, performs real-time object detection (specifically birds, but expandable), and intelligently triggers remote photo captures via the provided Sentry API.

## Architectural Overview & Technology Stack

To achieve excellent real-time performance on both an M4 MacBook Air (Apple Silicon) and a Windows PC (RTX/CUDA), we will use the following tools:

1. **AI / Computer Vision**:
   - **`ultralytics` (YOLOv8/11)**: The state-of-the-art framework for real-time object detection. The pre-trained COCO models natively recognize "birds" (along with 79 other common objects like people, cars, etc.). You can easily fine-tune or swap models later.
   - **Hardware Acceleration via PyTorch**: PyTorch automatically supports `mps` (Metal Performance Shaders on Mac) and `cuda` (on Nvidia RTX), allowing the YOLO model to run highly efficiently without blocking the CPU.
   - **`opencv-python` (cv2)**: Ideal for robustly establishing a connection to the MJPEG stream (`/api/preview/stream`), extracting frames, and drawing bounding boxes.

2. **API Interaction & Logic**:
   - **`requests`**: Used to send commands to the Sentry Camera (e.g., `POST /api/sentry/toggle`, `GET /api/sentry/ready`, `POST /api/sentry/snap`).
   - We will implement a smart **Capture Logic Heuristic**:
     - *Debounce/Stability*: A bird must be detected in $N$ consecutive frames above a certain confidence threshold.
     - *Cooldown*: After triggering a snap, wait $X$ seconds before snapping again to avoid spamming the camera storage.
     - *Positioning*: Prefer snapping when the detected box is relatively stable and roughly centralized.

3. **User Interface (UI)**:
   - **`FastAPI` + `Uvicorn`**: A very lightweight, fast backend to manage the background streaming thread and serve the UI.
   - **HTML / Vanilla CSS / JS**: A beautiful, modern, dark-mode web application implementing glassmorphism, dynamic animations, and real-time status updates (polling the backend).
   - This setup avoids heavy desktop UI frameworks, keeps your app modular, and makes it accessible over your local network.

4. **Helper Scripts**:
   - Standard shell scripts (`.sh` for Mac, `.bat` for Windows) to magically handle environment creation (`venv`), pip dependency installation, and running the server.

---

## Proposed System Structure

### 1. Requirements and Setup
- **`requirements.txt`**: Will define required packages like `fastapi`, `uvicorn`, `ultralytics`, `opencv-python`, `requests`.
- **`setup.sh` / `setup.bat`**: Idempotent scripts that create a `venv` and install the requirements.
- **`run.sh` / `run.bat`**: Bootstraps the application via `uvicorn app.main:app`.

### 2. Backend (`app/`)
- **`main.py`**: The FastAPI application entry point. Defines API routes for the frontend (e.g., enable/disable processing, get logs, get capture history).
- **`sentry_client.py`**: A helper class interacting with your HTTP endpoints at `http://workshop-pi.local:5000/api/sentry/...` based on the provided `sentry_api_docs.md`.
- **`stream_processor.py`**: A background thread running `cv2.VideoCapture`. On each frame, it pushes to the YOLO PyTorch model. If a bird is detected under the right conditions, it calls `sentry_client.snap()`.

### 3. Frontend (`frontend/`)
- **`index.html`**: A single-page application structure highlighting a clean, intuitive layout.
- **`styles.css`**: Premium aesthetics. Uses deep slate backgrounds, semi-transparent panels (glassmorphism), vibrant accent colors (like a neon cyan), and smooth CSS transitions.
- **`app.js`**: Fetches the status from the FastAPI backend and provides dynamic interactivity to the dashboard (showing when a bird is currently detected, logs of recent successful photos, etc.).

---

## User Review Required

> [!IMPORTANT]
> Please review the core technology choices (FastAPI + YOLO via Ultralytics). YOLO on PyTorch is currently the absolute best approach for blending developer simplicity with extreme cross-platform hardware acceleration (M4 & CUDA). 

> [!NOTE]
> For the UI, we're planning a lightweight web-app (accessed via localhost:8000) instead of a PyQt/Tkinter desktop app. It will have a modern, sleek appearance that aligns perfectly with your aesthetic requirements.

---

## Open Questions

1. **Viewing the Analytics Stream**: Would you like the Stream Processor to re-broadcast the video stream *with bounding boxes drawn over it*, so you can see what the AI is seeing live in the UI? (This is standard practice and highly recommended!).
2. **Downloading Photos Local**: When the AI triggers `/api/sentry/snap`, Sentry Mode saves the image on the Pi. Should this app automatically download those files to your Mac/PC to keep a local archive of the birds?
3. **ML Model Size**: Ultralytics offers various YOLO sizes. We will default to YOLOv11 NANO (`yolo11n.pt`). It is extremely fast and very accurate for close-up birds. Let me know if you would prefer tracking a slightly larger, slower, but more accurate model.

## Verification Plan

### Automated/Local Tests
- Ensure `requirements.txt` correctly provisions a working environment.
- Start the server and confirm FastAPI is listening on `http://127.0.0.1:8000`.
- Pass a local test bird video via `cv2.VideoCapture(test.mp4)` to verify the PyTorch model initializes `mps` or `cuda` perfectly and accurately draws a bounding box on the bird.

### Manual Verification
- Ask the user to run `setup.sh` on their Mac M4 and start the server.
- Connect the stream to `workshop-pi.local:5000`.
- Physically present a bird (or a picture of a bird on a phone) to the camera to trigger the logic.
- Verify the Sentry Camera's endpoints are successfully called without race conditions, and photos are saved.
