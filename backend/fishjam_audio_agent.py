from __future__ import annotations

import asyncio
import contextlib
import os

from fishjam import AgentOptions, FishjamClient
from fishjam.agent import Agent, AgentSession, IncomingTrackData, OutgoingTrack
from fishjam.integrations.gemini import GeminiIntegration

from backend.config import (
    FISHJAM_ID,
    FISHJAM_MANAGEMENT_TOKEN,
    FISHJAM_ROOM_ID,
    GEMINI_LIVE_MODEL,
)
from backend.gemini_live_engine import GeminiLiveEngine


class FishjamAudioAgent:
    """
    Bridges Fishjam room audio into Gemini Live and optionally publishes
    Gemini's synthesized audio back into the same room.
    """

    def __init__(
        self,
        room_id: str = FISHJAM_ROOM_ID,
        fishjam_id: str = FISHJAM_ID,
        management_token: str = FISHJAM_MANAGEMENT_TOKEN,
        gemini_engine: GeminiLiveEngine | None = None,
    ) -> None:
        self.room_id = room_id
        self.fishjam_id = fishjam_id
        self.management_token = management_token
        self.gemini_engine = gemini_engine or GeminiLiveEngine(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model_name=GEMINI_LIVE_MODEL,
        )

        self.client: FishjamClient | None = None
        self.agent: Agent | None = None
        self.session: AgentSession | None = None
        self.outgoing_track: OutgoingTrack | None = None
        self._session_cm = None
        self._receive_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._validate_env()
        self.gemini_engine.on_output_audio = self._publish_output_audio

        self.client = FishjamClient(
            fishjam_id=self.fishjam_id,
            management_token=self.management_token,
        )
        self.agent = self.client.create_agent(
            self.room_id,
            AgentOptions(output=GeminiIntegration.GEMINI_INPUT_AUDIO_SETTINGS),
        )

        await self.gemini_engine.start_session()

        self._session_cm = self.agent.connect()
        self.session = await self._session_cm.__aenter__()
        self.outgoing_track = await self.session.add_track(
            GeminiIntegration.GEMINI_OUTPUT_AUDIO_SETTINGS
        )
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def run_forever(self) -> None:
        await self.start()
        assert self._receive_task is not None
        await self._receive_task

    async def stop(self) -> None:
        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None

        if self.session is not None:
            await self.session.disconnect()
            self.session = None

        if self._session_cm is not None:
            with contextlib.suppress(Exception):
                await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None

        await self.gemini_engine.stop()
        self.outgoing_track = None
        self.agent = None
        self.client = None

    async def _receive_loop(self) -> None:
        assert self.session is not None

        async for message in self.session.receive():
            if not isinstance(message, IncomingTrackData):
                continue
            if not message.data:
                continue
            await self.gemini_engine.send_audio(message.data)

    async def _publish_output_audio(self, pcm_chunk: bytes) -> None:
        if self.outgoing_track is None or not pcm_chunk:
            return
        await self.outgoing_track.send_chunk(pcm_chunk)

    def _validate_env(self) -> None:
        missing = [
            name
            for name, value in (
                ("FISHJAM_ID", self.fishjam_id),
                ("FISHJAM_MANAGEMENT_TOKEN", self.management_token),
                ("FISHJAM_ROOM_ID", self.room_id),
                ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "")),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing required environment variables for FishjamAudioAgent: "
                + ", ".join(missing)
            )


async def _main() -> None:
    agent = FishjamAudioAgent()
    try:
        await agent.run_forever()
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(_main())
