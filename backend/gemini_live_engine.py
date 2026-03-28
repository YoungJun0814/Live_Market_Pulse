from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

from google import genai
from google.genai import types

from backend.config import GEMINI_LIVE_MODEL

AsyncBytesCallback = Callable[[bytes], Awaitable[None] | None]
AsyncTextCallback = Callable[[str], Awaitable[None] | None]


class GeminiLiveEngine:
    """
    Owns a single Gemini Live session and exposes async callbacks for
    transcripts, generated text, and optional synthesized audio chunks.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = GEMINI_LIVE_MODEL,
        system_instruction: str | None = None,
        on_input_transcript: AsyncTextCallback | None = None,
        on_output_transcript: AsyncTextCallback | None = None,
        on_output_audio: AsyncBytesCallback | None = None,
    ) -> None:
        self.model_name = model_name
        self.system_instruction = system_instruction or (
            "You are monitoring a live financial news broadcast. "
            "Transcribe key events, detect sudden market-moving headlines, "
            "and respond with concise market-impact summaries."
        )
        self.on_input_transcript = on_input_transcript
        self.on_output_transcript = on_output_transcript
        self.on_output_audio = on_output_audio

        self.client = genai.Client(api_key=api_key)
        self.session: Any | None = None
        self._session_cm: Any | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._closed = True

    @property
    def is_running(self) -> bool:
        return self.session is not None and not self._closed

    async def start_session(self) -> None:
        if self.is_running:
            return

        config = types.LiveConnectConfig(
            responseModalities=[types.Modality.AUDIO],
            systemInstruction=self.system_instruction,
            inputAudioTranscription=types.AudioTranscriptionConfig(),
            outputAudioTranscription=types.AudioTranscriptionConfig(),
        )
        self._session_cm = self.client.aio.live.connect(
            model=self.model_name,
            config=config,
        )
        self.session = await self._session_cm.__aenter__()
        self._closed = False
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def send_audio(self, pcm_chunk: bytes) -> None:
        if not self.session or not pcm_chunk:
            return

        await self.session.send_realtime_input(
            audio=types.Blob(
                data=pcm_chunk,
                mimeType="audio/pcm;rate=16000",
            )
        )

    async def send_text_instruction(self, text: str) -> None:
        if not self.session or not text.strip():
            return

        await self.session.send_realtime_input(text=text)

    async def end_audio_stream(self) -> None:
        if not self.session:
            return
        await self.session.send_realtime_input(audio_stream_end=True)

    async def _receive_loop(self) -> None:
        assert self.session is not None

        try:
            async for message in self.session.receive():
                server_content = getattr(message, "server_content", None)
                if server_content is None:
                    continue

                input_transcription = getattr(server_content, "input_transcription", None)
                if input_transcription and getattr(input_transcription, "text", None):
                    await self._emit_text(
                        self.on_input_transcript,
                        input_transcription.text,
                    )

                output_transcription = getattr(server_content, "output_transcription", None)
                if output_transcription and getattr(output_transcription, "text", None):
                    await self._emit_text(
                        self.on_output_transcript,
                        output_transcription.text,
                    )

                model_turn = getattr(server_content, "model_turn", None)
                if model_turn is None:
                    continue

                for part in getattr(model_turn, "parts", []) or []:
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data and getattr(inline_data, "data", None):
                        await self._emit_audio(inline_data.data)

                    text = getattr(part, "text", None)
                    if text:
                        await self._emit_text(self.on_output_transcript, text)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._emit_text(
                self.on_output_transcript,
                f"[GeminiLiveEngine] receive loop stopped: {exc}",
            )

    async def stop(self) -> None:
        self._closed = True

        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None

        if self.session is not None:
            await self.session.close()
            self.session = None

        if self._session_cm is not None:
            with contextlib.suppress(Exception):
                await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None

    async def _emit_audio(self, data: bytes) -> None:
        if self.on_output_audio is None:
            return
        maybe_awaitable = self.on_output_audio(data)
        if asyncio.iscoroutine(maybe_awaitable):
            await maybe_awaitable

    async def _emit_text(
        self,
        callback: AsyncTextCallback | None,
        text: str,
    ) -> None:
        if callback is None or not text.strip():
            return
        maybe_awaitable = callback(text)
        if asyncio.iscoroutine(maybe_awaitable):
            await maybe_awaitable
