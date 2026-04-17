# Sentry worker

Simple real-time video stream analyzer designed to process mjpeg video streams. It tracks custom target objects (currently just birds) using lightweight computer vision models and automatically triggers a photo capture. This is mainly a low-effort project made for fun and it is absolutely a work in progress.

### Pre-requisites

Currently, this project is desinged to work with my DIY raspberry-pi based camera project. Therefore:
- The [s00f-cam](https://github.com/Wirstblase/s00f-camera-test-backend) , being on and connected to the same local network where the sentry worker intends to run on
- sentry mode set to True in the global config of the s00f-cam

### Features

- **Real-Time Object Detection**: Powered by YOLO architecture via the Ultralytics framework.
- **Cross-Platform Hardware Acceleration**: Automatically utilizes Apple Metal Performance Shaders (MPS) on M-series Macs or NVIDIA CUDA on Windows systems for near-zero latency inference.
- **Smart Capture Heuristics**: Evaluates image sharpness (Laplacian variance) and temporal stability to ensure photos are only taken when the subject is clear and in-frame.
- **Deferred Photo Archiving**: Intelligently monitors inactivity to download captured imagery only when the camera network is idle, preserving system bandwidth.
- **Simple Web UI**: Simple web ui to configure parameters and see the stream and the model in action:) currently hard coded mostly

### Architecture

The application is structured around a multi-threaded Python backend:

- **FastAPI / Uvicorn Server**: Provides the control API and serves the dashboard UI asynchronously.
- **Background Stream Processor**: Isolates OpenCV MJPEG stream parsing and PyTorch/YOLO inference from the web server, avoiding bottlenecking the user interface.
- **Sentry API Client**: Handles network state, polling the camera status, pushing shutter commands, and managing local picture queues.

### Requirements

- Python 3.9 or higher.
- A compatible operating system (macOS or Windows).
- Network access to the external camera feed (default endpoint expected at `http://workshop-pi.local:5000`).

### Installation

This project includes automated setup scripts to bootstrap your virtual environment and install all dependencies without polluting your system Python.

**macOS / Linux**

```bash
chmod +x setup.sh run.sh
./setup.sh
```

**Windows**

```cmd
setup.bat
```

### Usage

Start the web server and background processing threads by executing the run script.

**macOS / Linux**

```bash
./run.sh
```

**Windows**

```cmd
run.bat
```

Once running, navigate to `http://localhost:8000` in your web browser (Firefox, Safari, Chrome, etc.). The dashboard allows you to:

- Monitor the processed live stream complete with inference bounding boxes.
- View captured metrics and inactivity timers.
- Dynamically alter tracking confidence, blur tolerances, cooldown periods, and swap between ML model sizes on the fly.

### Configuration Parameters

Some parameters can be adjusted directly from the UI while the system is running:

- **Model Size**: Select between Nano, Small, and Medium YOLO network weights. Nano is recommended for strict real-time requirements.
- **Confidence Threshold**: The minimum confidence score (0.0 to 1.0) for an object to be considered valid track geometry.
- **Cooldown**: Duration in seconds to wait after a successful capture before taking another snapshot.
- **Blur Threshold**: The minimum acceptable variance of the Laplacian metric for the target's bounding box. Higher values should result in sharper images (in theory)

### Project Structure

- `main.py` - FastAPI application configuration and HTTP routing logic.
- `stream_processor.py` - Frame extraction, bounding box logic, and image quality evaluation.
- `sentry_client.py` - REST communications orchestrator managing the external hardware logic.
- `templates/` - HTML layout definitions.
- `static/` - Segregated CSS stylesheets and client-side JavaScript.

## Have fun :D
