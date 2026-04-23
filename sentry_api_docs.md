# Sentry Mode API Documentation

This document describes the API endpoints available for interacting with the **Sentry Mode** feature of the camera system. These endpoints are designed for external monitoring software to query the system status, toggle indefinite streaming, and capture images.

> **External monitors should prefer the idempotent `POST /api/sentry/enable` and `POST /api/sentry/disable` endpoints.** `POST /api/sentry/toggle` is provided for interactive UI use only — it flips the current state and is therefore racy when called by multiple clients or after a startup-restore that already turned sentry mode on.

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

## `POST /api/sentry/enable`

Idempotently enables Sentry Mode. When activated, Sentry Mode enforces continuous preview streaming, prevents the auto-standby timer from stopping the camera, and pauses background processing to ensure exclusive camera access.

Safe to call repeatedly: if Sentry Mode is already active, this is a no-op and `already_active` will be `true`. The transition is performed atomically; concurrent callers will not race.

**Response**
- `200 OK` — Sentry Mode is on after this call.

```json
{
  "active": true,
  "already_active": false
}
```

- `500 Internal Server Error` — Failed to activate sentry mode (e.g., the preview could not be started). No state has been persisted.

```json
{
  "active": false,
  "error": "Failed to start preview"
}
```

---

## `POST /api/sentry/disable`

Idempotently disables Sentry Mode. The preview stream is left running (it is the user's responsibility to stop it via `POST /api/preview/stop` if desired); only the sentry-specific behaviour — exclusive camera access, OLED indicator, auto-standby suppression, and persisted `sentry_mode` flag — is cleared.

Safe to call repeatedly: if Sentry Mode is already inactive, this is a no-op and `already_inactive` will be `true`.

**Response**
- `200 OK` — Sentry Mode is off after this call.

```json
{
  "active": false,
  "already_inactive": false
}
```

---

## `POST /api/sentry/toggle`

Flips Sentry Mode (on → off, off → on) atomically. Intended for interactive UI use.

> **Not recommended for external monitoring software.** Two clients calling toggle near-simultaneously will cancel each other out, and after a server restart the persisted `sentry_mode` flag may be auto-restored before your monitor's first call — turning your "enable" toggle into an unintended "disable". Prefer `POST /api/sentry/enable` / `POST /api/sentry/disable`.

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
