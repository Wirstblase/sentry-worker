# Sentry Mode API Documentation

This document describes the API endpoints available for interacting with the **Sentry Mode** feature of the camera system. These endpoints are designed for external monitoring software to query the system status, toggle indefinite streaming, and capture images.

---

## `GET /api/sentry/status`

Retrieves the current status of Sentry Mode and, if active, provides information about the video stream.

**Response**
- `200 OK`

```json
{
  "active": true,
  "uptime_s": 128.5,
  "stream_info": {
    "resolution": "1280x720",
    "framerate": "~30fps"
  }
}
```

*Note: If `active` is `false`, `uptime_s` will be `0.0` and `stream_info` will be `null`.*

---

## `POST /api/sentry/toggle`

Toggles Sentry Mode on or off. When activated, Sentry Mode enforces continuous preview streaming, prevents the auto-standby timer from stopping the camera, and pauses background processing to ensure exclusive camera access.

**Response**
- `200 OK` - Successfully toggled.

```json
{
  "active": true 
}
```

- `500 Internal Server Error` - Failed to activate sentry mode (e.g., if the preview could not be started).

```json
{
  "active": false,
  "error": "Failed to start preview"
}
```

---

## `GET /api/sentry/ready`

Checks whether the camera is currently ready to capture an image (i.e. the preview is actively running and the camera is not already busy capturing another frame). 

**Response**
- `200 OK`

```json
{
  "ready": true
}
```

---

## `POST /api/sentry/snap`

Triggers a photo capture while Sentry Mode is active. Returns the filename of the captured image, which can subsequently be downloaded by the external monitoring software using `GET /api/gallery/<filename>`.

**Request Body (Optional, JSON)**

```json
{
  "mode": "auto",
  "resolution": "1080p",
  "shutter": 10000,
  "gain": 1.0
}
```

- `mode` - Can be `"auto"`, `"instant"`, or `"manual"`. Defaults to `"auto"`.
- `resolution` - The target capture resolution format. Defaults to the system's globally configured default resolution.
- `shutter` - (For manual mode) Shutter speed in microseconds.
- `gain` - (For manual mode) Sensor gain.

**Response**
- `200 OK` - Successfully captured the image.

```json
{
  "filename": "IMG_20260417_153045.jpg",
  "files": [
    "IMG_20260417_153045.jpg"
  ]
}
```

- `409 Conflict` - Rejected because Sentry Mode is completely inactive. Sentry Mode must be enabled first to capture via this endpoint.

```json
{
  "error": "Sentry mode is not active"
}
```

- `500 Internal Server Error` - Capture failed due to hardware or internal errors.

---

## `GET /api/preview/stream`

Provides a live MJPEG stream of the camera preview. This endpoint returns a continuous series of JPEG frames and is ideal for embedding directly in web clients (e.g., `<img src="/api/preview/stream">`) or reading from external monitoring software while Sentry Mode is active.

**Response**
- `200 OK` (Content-Type: `multipart/x-mixed-replace; boundary=frame`)

---

## `GET /api/preview/snapshot`

Retrieves a single, near-instantaneous JPEG frame from the current camera preview. This is useful for fetching a quick, low-latency live shot without incurring the processing overhead of a full high-resolution capture.

**Response**
- `200 OK` (Content-Type: `image/jpeg`)
- `503 Service Unavailable` - If the preview is not currently running.

---

### Fetching Captured Images

To retrieve the image captured by `/api/sentry/snap`, use the standard gallery endpoint:

**`GET /api/gallery/<filename>`**

This endpoint returns the raw binary data of the captured photo (e.g. `image/jpeg`).
