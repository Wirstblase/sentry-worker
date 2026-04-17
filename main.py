import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
from sentry_client import SentryClient
from stream_processor import StreamProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup clients
sentry_client = SentryClient()
stream_processor = StreamProcessor(sentry_client)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    stream_processor.start()
    yield
    # Shutdown
    stream_processor.stop()
    sentry_client.stop()

app = FastAPI(title="Sentry Stream Processor", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class Settings(BaseModel):
    confidence_threshold: Optional[float] = None
    cooldown_seconds: Optional[int] = None
    blur_threshold: Optional[float] = None
    model_name: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

async def gen_frames():
    while True:
        frame = stream_processor.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            await asyncio.sleep(0.03)  # Roughly 30fps
        else:
            await asyncio.sleep(0.1)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(gen_frames(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get("/api/status")
async def get_status():
    stats = sentry_client.get_stats()
    return {
        "processor_running": stream_processor.running,
        "sentry_stats": stats,
        "current_model": stream_processor.model_name
    }

@app.post("/api/start")
async def start_processing():
    stream_processor.start()
    return {"status": "started"}

@app.post("/api/stop")
async def stop_processing():
    stream_processor.stop()
    return {"status": "stopped"}

@app.get("/api/settings")
async def get_settings():
    return {
        "confidence_threshold": stream_processor.confidence_threshold,
        "cooldown_seconds": stream_processor.cooldown_seconds,
        "blur_threshold": stream_processor.blur_threshold,
        "model_name": stream_processor.model_name
    }

@app.post("/api/settings")
async def update_settings(settings: Settings):
    if settings.confidence_threshold is not None:
         stream_processor.confidence_threshold = settings.confidence_threshold
    if settings.cooldown_seconds is not None:
         stream_processor.cooldown_seconds = settings.cooldown_seconds
    if settings.blur_threshold is not None:
         stream_processor.blur_threshold = settings.blur_threshold
    if settings.model_name is not None and settings.model_name != stream_processor.model_name:
         stream_processor.set_model(settings.model_name)
    return {"status": "updated"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
