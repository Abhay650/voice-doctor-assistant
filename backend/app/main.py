from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pipecat.transports.smallwebrtc.request_handler import (SmallWebRTCPatchRequest, SmallWebRTCRequest,
                                                            SmallWebRTCRequestHandler)

from . import config, db


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Voice Doctor Appointment Assistant", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
webrtc_handler = SmallWebRTCRequestHandler()


@app.get("/api/health")
def health():
    return {"ok": True, "clinic": config.CLINIC_NAME, "llm": config.GEMINI_MODEL,
            "gemini_key": bool(config.GOOGLE_API_KEY), "elevenlabs_key": bool(config.ELEVENLABS_API_KEY)}


@app.get("/api/doctors")
def doctors():
    return db.list_doctors_with_slots()


@app.get("/api/appointments")
def appointments():
    return db.list_appointments()


@app.post("/api/reset")
def reset():
    db.reset_appointments()
    return {"ok": True}


@app.post("/api/offer")
async def offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    if not (config.GOOGLE_API_KEY and config.ELEVENLABS_API_KEY):
        raise HTTPException(400, "Missing GOOGLE_API_KEY or ELEVENLABS_API_KEY in backend/.env")
    from .bot import run_bot  # imported lazily so the dashboard API works even before keys are set

    async def on_connection(connection):
        logger.info("new WebRTC connection")
        background_tasks.add_task(run_bot, connection)

    return await webrtc_handler.handle_web_request(request=request, webrtc_connection_callback=on_connection)


@app.patch("/api/offer")
async def ice_candidate(request: SmallWebRTCPatchRequest):
    await webrtc_handler.handle_patch_request(request)
    return {"status": "success"}
