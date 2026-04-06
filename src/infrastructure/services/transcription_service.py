"""Transcription service — uses OpenAI Whisper API for audio-to-text."""

import io
import os
import tempfile
from typing import Optional

import httpx


# Whisper API max file size is 25MB
_WHISPER_MAX_BYTES = 25 * 1024 * 1024
_OPENAI_AUDIO_URL = "https://api.openai.com/v1/audio/transcriptions"


class TranscriptionService:
    """Handles audio transcription via OpenAI Whisper API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def transcribe(self, file_path: str, language: str = "en") -> str:
        """Transcribe an audio file on disk.

        If the file exceeds 25 MB it is split into chunks and each chunk is
        transcribed independently, then the results are concatenated.

        Args:
            file_path: Path to the audio file.
            language: ISO-639-1 language code (default ``"en"``).

        Returns:
            The transcript text.
        """
        file_size = os.path.getsize(file_path)

        if file_size <= _WHISPER_MAX_BYTES:
            return await self._transcribe_single(file_path, language)

        # File exceeds 25 MB — split into chunks and transcribe each
        return await self._transcribe_chunked(file_path, language)

    async def transcribe_from_url(self, url: str, language: str = "en") -> str:
        """Download an audio file from *url* and transcribe it.

        Args:
            url: Public URL of the audio file.
            language: ISO-639-1 language code.

        Returns:
            The transcript text.
        """
        tmp_path = await self._download(url)
        try:
            return await self.transcribe(tmp_path, language)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _transcribe_single(self, file_path: str, language: str) -> str:
        """Send a single file (<=25 MB) to the Whisper API."""
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=300) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "audio/mpeg")}
                data = {"model": "whisper-1", "language": language}
                resp = await client.post(
                    _OPENAI_AUDIO_URL, headers=headers, files=files, data=data
                )
                resp.raise_for_status()
                return resp.json().get("text", "")

    async def _transcribe_chunked(self, file_path: str, language: str) -> str:
        """Split a large file into <=25 MB byte-chunks and transcribe each."""
        transcripts: list[str] = []

        with open(file_path, "rb") as f:
            chunk_index = 0
            while True:
                chunk_data = f.read(_WHISPER_MAX_BYTES)
                if not chunk_data:
                    break

                # Write chunk to a temp file so httpx can stream it
                suffix = os.path.splitext(file_path)[1] or ".mp3"
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix, prefix=f"chunk{chunk_index}_"
                )
                tmp.write(chunk_data)
                tmp.close()

                try:
                    text = await self._transcribe_single(tmp.name, language)
                    transcripts.append(text)
                finally:
                    os.remove(tmp.name)

                chunk_index += 1

        return " ".join(transcripts)

    async def _download(self, url: str) -> str:
        """Download a URL to a temporary file and return its path."""
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            suffix = ".mp3"
            if "." in url.split("/")[-1]:
                suffix = "." + url.split("/")[-1].rsplit(".", 1)[-1]

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(resp.content)
            tmp.close()
            return tmp.name
