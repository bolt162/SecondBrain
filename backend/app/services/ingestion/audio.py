import os
import tempfile
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import aiofiles
from openai import AsyncOpenAI

from app.config import settings


@dataclass
class AudioTranscript:
    """Result of audio transcription."""
    text: str
    segments: list  # List of {"text": str, "start_ms": int, "end_ms": int}
    duration_ms: int
    language: Optional[str] = None


class AudioProcessor:
    """Processor for audio files using OpenAI Whisper."""

    SUPPORTED_FORMATS = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".mpeg", ".mpga", ".oga", ".ogg"}

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def is_supported(self, filename: str) -> bool:
        """Check if the file format is supported."""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.SUPPORTED_FORMATS

    async def transcribe(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> AudioTranscript:
        """
        Transcribe an audio file using Whisper.

        Args:
            file_path: Path to the audio file
            language: Optional language hint (ISO-639-1 code)

        Returns:
            AudioTranscript with text and segments
        """
        # Read the file
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()

        # Create a temporary file for the API
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1]

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            # Call Whisper API with timestamps
            with open(tmp_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    language=language,
                )

            # Parse response
            segments = []
            if hasattr(response, "segments") and response.segments:
                for seg in response.segments:
                    segments.append({
                        "text": seg.get("text", "").strip(),
                        "start_ms": int(seg.get("start", 0) * 1000),
                        "end_ms": int(seg.get("end", 0) * 1000),
                    })

            # Calculate duration
            duration_ms = 0
            if segments:
                duration_ms = segments[-1]["end_ms"]
            elif hasattr(response, "duration"):
                duration_ms = int(response.duration * 1000)

            return AudioTranscript(
                text=response.text,
                segments=segments,
                duration_ms=duration_ms,
                language=getattr(response, "language", None),
            )

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def extract_metadata(self, file_path: str) -> dict:
        """Extract metadata from audio file."""
        metadata = {
            "filename": os.path.basename(file_path),
            "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "processed_at": datetime.utcnow().isoformat(),
        }

        # Try to get duration using pydub if available
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            metadata["duration_seconds"] = len(audio) / 1000.0
            metadata["channels"] = audio.channels
            metadata["sample_rate"] = audio.frame_rate
        except Exception:
            pass

        return metadata


# Singleton instance
audio_processor = AudioProcessor()
