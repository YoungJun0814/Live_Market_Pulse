"""
Fishjam Audio Agent — Gemini Live Bridge
Connects a Fishjam room to Google Gemini Live using the v0.25 SDK API.
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from fishjam import AgentOptions, FishjamClient
from fishjam.integrations.gemini import GeminiIntegration
from google.genai.types import Blob, Modality


FISHJAM_ID = os.environ["FISHJAM_ID"]
FISHJAM_MANAGEMENT_TOKEN = os.environ["FISHJAM_MANAGEMENT_TOKEN"]
FISHJAM_ROOM_ID = os.environ.get("FISHJAM_ROOM_ID", "")
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")


async def run_agent(room_id: str) -> None:
    print(f"[FishjamAgent] Connecting to room {room_id} ...")

    fishjam_client = FishjamClient(
        fishjam_id=FISHJAM_ID,
        management_token=FISHJAM_MANAGEMENT_TOKEN,
    )

    # Use preset to match required 16 kHz input audio format
    agent_options = AgentOptions(output=GeminiIntegration.GEMINI_INPUT_AUDIO_SETTINGS)
    agent = fishjam_client.create_agent(room_id, agent_options)

    gen_ai = GeminiIntegration.create_client(api_key=GEMINI_API_KEY)

    async with agent.connect() as fishjam_session:
        # Use preset to match required 24 kHz output audio format
        outgoing_track = await fishjam_session.add_track(
            GeminiIntegration.GEMINI_OUTPUT_AUDIO_SETTINGS
        )
        print("[FishjamAgent] Connected to Fishjam room. Starting Gemini session ...")

        async with gen_ai.aio.live.connect(
            model=GEMINI_MODEL,
            config={"response_modalities": [Modality.AUDIO]},
        ) as gemini_session:
            print("[FishjamAgent] Gemini Live session started. Bridging audio ...")

            # Fishjam → Google
            async def forward_audio_to_gemini() -> None:
                async for track_data in fishjam_session.receive():
                    if track_data.data:
                        await gemini_session.send_realtime_input(
                            audio=Blob(
                                mime_type=GeminiIntegration.GEMINI_AUDIO_MIME_TYPE,
                                data=track_data.data,
                            )
                        )

            # Google → Fishjam
            async def forward_audio_to_fishjam() -> None:
                async for msg in gemini_session.receive():
                    server_content = msg.server_content
                    if server_content is None:
                        continue
                    if server_content.interrupted:
                        await outgoing_track.interrupt()
                    if server_content.model_turn and server_content.model_turn.parts:
                        for part in server_content.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                await outgoing_track.send_chunk(part.inline_data.data)

            await asyncio.gather(
                forward_audio_to_gemini(),
                forward_audio_to_fishjam(),
            )


async def _main() -> None:
    room_id = FISHJAM_ROOM_ID
    if not room_id:
        # Auto-create a room if none is configured
        print("[FishjamAgent] No FISHJAM_ROOM_ID set - creating a new room ...")
        fishjam_client = FishjamClient(
            fishjam_id=FISHJAM_ID,
            management_token=FISHJAM_MANAGEMENT_TOKEN,
        )
        room = fishjam_client.create_room()
        room_id = room.id
        print(f"[FishjamAgent] Created room: {room_id}")

    await run_agent(room_id)


if __name__ == "__main__":
    asyncio.run(_main())
