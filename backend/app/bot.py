"""Pipecat voice pipeline:  browser mic -> VAD -> ElevenLabs STT -> Gemini (tools) -> ElevenLabs TTS -> browser speaker"""
from loguru import logger
from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.adapters.llm.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (LLMContextAggregatorPair,
                                                                   LLMUserAggregatorParams)
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from . import config, db, tools

SYSTEM_PROMPT = """You are Aria, the phone receptionist at {clinic}. You speak with callers by voice, so keep every reply to one or two short, natural sentences. No markdown, lists, emojis or symbols.
Today is {today} (clinic time).

You can do three things: check a doctor's availability, book an appointment, cancel an appointment.

Identity: you identify the caller ONLY by the phone number they say out loud. Never ask for a login, OTP or caller ID.
Phone number rule (strict): before you book or cancel, ask for the caller's 10-digit phone number, then read it back digit by digit ("nine, eight, seven...") and ask "Is that correct?". Only after the caller says yes, call the tool with phone_confirmed=true. If they correct you, read the new number back again.

Booking flow: find out the speciality or doctor and preferred day. Call check_doctor_availability, then offer at most three slots, spoken naturally ("Thursday the twenty-sixth at ten thirty in the morning"). When they pick one, get their name and phone number, confirm the number, then call book_appointment with the slot_id from the availability result. After it succeeds, confirm doctor, day and time in one sentence.
Cancel flow: get and confirm the phone number, then call cancel_appointment. If several appointments exist, ask which one. Confirm once cancelled.

Rules: never invent doctors or slots; only use what the tools return. If a tool returns an error, explain simply and fix it (offer other slots, re-ask the number). Convert spoken dates to YYYY-MM-DD for tool arguments using today's date. Ask one question at a time. If asked for anything outside appointments, politely say you can only help with booking, checking and cancelling appointments."""

TOOL_SCHEMAS = ToolsSchema(standard_tools=[
    FunctionSchema(
        name="check_doctor_availability",
        description="List open appointment slots. Filter by doctor name, speciality and/or date. Call with no filters to see what is available.",
        properties={
            "doctor_name": {"type": "string", "description": "Doctor name, e.g. 'Sharma'. Optional."},
            "speciality": {"type": "string", "description": "e.g. 'cardiologist', 'dermatologist', 'pediatrician'. Optional."},
            "date": {"type": "string", "description": "YYYY-MM-DD, or 'today' / 'tomorrow'. Optional."},
        }, required=[]),
    FunctionSchema(
        name="book_appointment",
        description="Book a slot for the caller. Only call after the caller has confirmed their phone number out loud.",
        properties={
            "slot_id": {"type": "integer", "description": "slot_id from check_doctor_availability."},
            "phone_number": {"type": "string", "description": "Caller's 10-digit phone number as digits."},
            "patient_name": {"type": "string", "description": "Caller's name."},
            "phone_confirmed": {"type": "boolean", "description": "True only after reading the number back and hearing the caller say yes."},
        }, required=["slot_id", "phone_number", "patient_name", "phone_confirmed"]),
    FunctionSchema(
        name="cancel_appointment",
        description="Cancel the caller's upcoming appointment, found by their phone number.",
        properties={
            "phone_number": {"type": "string", "description": "Caller's 10-digit phone number as digits."},
            "phone_confirmed": {"type": "boolean", "description": "True only after reading the number back and hearing the caller say yes."},
            "appointment_id": {"type": "integer", "description": "Only needed when the caller has several appointments."},
        }, required=["phone_number", "phone_confirmed"]),
])


async def run_bot(connection):
    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    stt = ElevenLabsRealtimeSTTService(api_key=config.ELEVENLABS_API_KEY)
    tts = ElevenLabsTTSService(
        api_key=config.ELEVENLABS_API_KEY,
        settings=ElevenLabsTTSService.Settings(voice=config.ELEVENLABS_VOICE_ID, model="eleven_flash_v2_5"),
    )
    prompt = SYSTEM_PROMPT.format(clinic=config.CLINIC_NAME, today=db.now().strftime("%A, %d %B %Y"))
    llm = GoogleLLMService(
        api_key=config.GOOGLE_API_KEY,
        settings=GoogleLLMService.Settings(model=config.GEMINI_MODEL, system_instruction=prompt),
    )

    context = LLMContext(messages=[{"role": "user", "content": "A caller just connected. Greet them briefly as Aria and ask how you can help."}],
                         tools=TOOL_SCHEMAS)
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()))  # bonus: Silero VAD

    pipeline = Pipeline([transport.input(), stt, user_agg, llm, tts, transport.output(), assistant_agg])
    task = PipelineWorker(pipeline)  # RTVI (transcripts, speaking events, server messages) is added automatically

    def make_handler(fn):
        async def handler(params: FunctionCallParams):
            logger.info(f"tool {params.function_name} args={params.arguments}")
            try:
                result = fn(**params.arguments)
            except TypeError as e:  # model sent unexpected/missing args
                result = {"ok": False, "error": f"Bad arguments: {e}"}
            except Exception as e:  # noqa: BLE001
                logger.exception("tool failed")
                result = {"ok": False, "error": f"Internal error: {e}"}
            event = result.pop("_event", None)
            if event:  # tell the dashboard immediately so it can refresh + show a confirmation card
                await task.rtvi.send_server_message(event)
            await params.result_callback(result)
        return handler

    for name, fn in [("check_doctor_availability", tools.check_doctor_availability),
                     ("book_appointment", tools.book_appointment),
                     ("cancel_appointment", tools.cancel_appointment)]:
        llm.register_function(name, make_handler(fn))

    @transport.event_handler("on_client_connected")
    async def on_connected(_, __):
        logger.info("caller connected")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(_, __):
        logger.info("caller disconnected")
        await task.cancel()

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(task)
    await runner.run()
