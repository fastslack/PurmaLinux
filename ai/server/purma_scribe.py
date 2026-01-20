#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ███████╗ ██████╗██████╗ ██╗██████╗ ███████╗                               ║
║     ██╔════╝██╔════╝██╔══██╗██║██╔══██╗██╔════╝                               ║
║     ███████╗██║     ██████╔╝██║██████╔╝█████╗                                 ║
║     ╚════██║██║     ██╔══██╗██║██╔══██╗██╔══╝                                 ║
║     ███████║╚██████╗██║  ██║██║██████╔╝███████╗                               ║
║     ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═════╝ ╚══════╝                               ║
║                                                                              ║
║                    PurmaLinux AI Voice Assistant                             ║
║            Speech-to-Text + Text-to-Speech + AI Summarization                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import wave
import tempfile
import subprocess
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue

# Audio recording
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# Whisper for speech recognition
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Alternative: faster-whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class TranscriptionStatus(Enum):
    """Status of a transcription job"""
    PENDING = "pending"
    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Transcription:
    """A transcription record"""
    id: str
    audio_path: Optional[str]
    text: str
    language: str
    duration_seconds: float
    word_count: int
    confidence: Optional[float]
    summary: Optional[str]
    status: str
    created_at: str
    model_used: str
    segments: Optional[List[Dict[str, Any]]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AudioRecorder:
    """Record audio from microphone"""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None

        self.is_recording = False
        self.frames = []
        self.audio_queue = queue.Queue()

        self._audio = None
        self._stream = None
        self._record_thread = None

    def _init_audio(self):
        """Initialize PyAudio"""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available. Install: pip install pyaudio")

        if self._audio is None:
            self._audio = pyaudio.PyAudio()

    def list_devices(self) -> List[Dict[str, Any]]:
        """List available audio input devices"""
        self._init_audio()
        devices = []

        for i in range(self._audio.get_device_count()):
            info = self._audio.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({
                    "index": i,
                    "name": info["name"],
                    "channels": info["maxInputChannels"],
                    "sample_rate": int(info["defaultSampleRate"])
                })

        return devices

    def start_recording(self, device_index: Optional[int] = None):
        """Start recording audio"""
        if self.is_recording:
            return

        self._init_audio()
        self.frames = []
        self.is_recording = True

        self._stream = self._audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size
        )

        self._record_thread = threading.Thread(target=self._record_loop)
        self._record_thread.start()

    def _record_loop(self):
        """Recording loop running in separate thread"""
        while self.is_recording:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
                self.audio_queue.put(data)
            except Exception as e:
                print(f"Recording error: {e}")
                break

    def stop_recording(self) -> bytes:
        """Stop recording and return audio data"""
        self.is_recording = False

        if self._record_thread:
            self._record_thread.join(timeout=1.0)

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        audio_data = b"".join(self.frames)
        self.frames = []

        return audio_data

    def save_to_file(self, audio_data: bytes, filepath: str):
        """Save audio data to WAV file"""
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)

    def get_duration(self, audio_data: bytes) -> float:
        """Get duration of audio in seconds"""
        return len(audio_data) / (self.sample_rate * self.channels * 2)

    def cleanup(self):
        """Clean up audio resources"""
        if self._audio:
            self._audio.terminate()
            self._audio = None


class SpeechRecognizer:
    """Speech-to-text using Whisper"""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self.use_faster_whisper = FASTER_WHISPER_AVAILABLE

    def load_model(self):
        """Load the Whisper model"""
        if self.model is not None:
            return

        if self.use_faster_whisper:
            # Use faster-whisper for better performance
            self.model = WhisperModel(
                self.model_name,
                device="cpu",  # or "cuda" for GPU
                compute_type="int8"  # Faster inference
            )
        elif WHISPER_AVAILABLE:
            self.model = whisper.load_model(self.model_name)
        else:
            raise RuntimeError(
                "No speech recognition backend available. "
                "Install: pip install openai-whisper or pip install faster-whisper"
            )

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe"  # or "translate" for translation to English
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            task: 'transcribe' or 'translate'

        Returns:
            Dict with text, language, segments, and confidence
        """
        self.load_model()

        if self.use_faster_whisper:
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                beam_size=5,
                vad_filter=True
            )

            segments_list = []
            full_text = []

            for segment in segments:
                segments_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "confidence": segment.avg_logprob
                })
                full_text.append(segment.text)

            return {
                "text": " ".join(full_text).strip(),
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": segments_list
            }

        else:
            # Use standard whisper
            result = self.model.transcribe(
                audio_path,
                language=language,
                task=task
            )

            segments_list = []
            for segment in result.get("segments", []):
                segments_list.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "confidence": segment.get("avg_logprob")
                })

            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "language_probability": None,
                "duration": segments_list[-1]["end"] if segments_list else 0,
                "segments": segments_list
            }

    def transcribe_stream(
        self,
        audio_queue: queue.Queue,
        callback: Callable[[str], None],
        stop_event: threading.Event
    ):
        """
        Stream transcription (experimental).
        Processes audio chunks as they arrive.
        """
        self.load_model()

        buffer = b""
        min_chunk_duration = 2.0  # Process every 2 seconds

        while not stop_event.is_set():
            try:
                chunk = audio_queue.get(timeout=0.1)
                buffer += chunk

                # Check if we have enough audio
                duration = len(buffer) / (16000 * 2)  # 16kHz, 16-bit

                if duration >= min_chunk_duration:
                    # Save to temp file and transcribe
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        temp_path = f.name
                        with wave.open(f.name, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(16000)
                            wf.writeframes(buffer)

                    result = self.transcribe(temp_path)
                    callback(result["text"])

                    os.unlink(temp_path)
                    buffer = b""

            except queue.Empty:
                continue


class TextToSpeech:
    """Text-to-speech synthesis"""

    def __init__(self):
        self.engine = self._detect_engine()

    def _detect_engine(self) -> str:
        """Detect available TTS engine"""
        # Check for piper (high quality neural TTS)
        if self._command_exists("piper"):
            return "piper"
        # Check for espeak-ng
        if self._command_exists("espeak-ng"):
            return "espeak-ng"
        # Check for espeak
        if self._command_exists("espeak"):
            return "espeak"
        # Check for festival
        if self._command_exists("festival"):
            return "festival"
        # macOS
        if self._command_exists("say"):
            return "say"

        return "none"

    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(
                ["which", cmd],
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        output_file: Optional[str] = None
    ) -> bool:
        """
        Convert text to speech.

        Args:
            text: Text to speak
            voice: Voice name/model (engine-specific)
            speed: Speaking speed multiplier
            output_file: Optional file to save audio to

        Returns:
            True if successful
        """
        if not text:
            return False

        try:
            if self.engine == "piper":
                return self._speak_piper(text, voice, speed, output_file)
            elif self.engine == "espeak-ng":
                return self._speak_espeak(text, voice, speed, output_file, "espeak-ng")
            elif self.engine == "espeak":
                return self._speak_espeak(text, voice, speed, output_file, "espeak")
            elif self.engine == "festival":
                return self._speak_festival(text, output_file)
            elif self.engine == "say":
                return self._speak_macos(text, voice, speed, output_file)
            else:
                print("No TTS engine available")
                return False
        except Exception as e:
            print(f"TTS error: {e}")
            return False

    def _speak_piper(
        self,
        text: str,
        voice: Optional[str],
        speed: float,
        output_file: Optional[str]
    ) -> bool:
        """Use Piper for TTS"""
        model = voice or "en_US-lessac-medium"

        cmd = ["piper", "--model", model]

        if output_file:
            cmd.extend(["--output_file", output_file])
        else:
            cmd.extend(["--output-raw"])

        if speed != 1.0:
            cmd.extend(["--length_scale", str(1.0 / speed)])

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if not output_file else None,
            stderr=subprocess.PIPE
        )

        stdout, stderr = proc.communicate(input=text.encode())

        if not output_file and stdout:
            # Play raw audio
            subprocess.run(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                input=stdout,
                capture_output=True
            )

        return proc.returncode == 0

    def _speak_espeak(
        self,
        text: str,
        voice: Optional[str],
        speed: float,
        output_file: Optional[str],
        cmd_name: str
    ) -> bool:
        """Use espeak/espeak-ng for TTS"""
        cmd = [cmd_name]

        if voice:
            cmd.extend(["-v", voice])
        else:
            cmd.extend(["-v", "en"])

        # Speed: default is 175 wpm
        wpm = int(175 * speed)
        cmd.extend(["-s", str(wpm)])

        if output_file:
            cmd.extend(["-w", output_file])

        cmd.append(text)

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def _speak_festival(self, text: str, output_file: Optional[str]) -> bool:
        """Use Festival for TTS"""
        if output_file:
            # Save to file
            script = f'(utt.save.wave (SayText "{text}") "{output_file}")'
            subprocess.run(
                ["festival", "-b"],
                input=script.encode(),
                capture_output=True
            )
        else:
            subprocess.run(
                ["festival", "--tts"],
                input=text.encode(),
                capture_output=True
            )
        return True

    def _speak_macos(
        self,
        text: str,
        voice: Optional[str],
        speed: float,
        output_file: Optional[str]
    ) -> bool:
        """Use macOS 'say' command"""
        cmd = ["say"]

        if voice:
            cmd.extend(["-v", voice])

        # Rate: default is about 175-200
        rate = int(175 * speed)
        cmd.extend(["-r", str(rate)])

        if output_file:
            cmd.extend(["-o", output_file])

        cmd.append(text)

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def list_voices(self) -> List[Dict[str, str]]:
        """List available voices"""
        voices = []

        if self.engine == "piper":
            # Piper uses model files, list available ones
            voices.append({"id": "en_US-lessac-medium", "name": "Lessac (US)", "language": "en"})
            voices.append({"id": "en_GB-alba-medium", "name": "Alba (UK)", "language": "en"})
            voices.append({"id": "es_ES-davefx-medium", "name": "Dave (ES)", "language": "es"})

        elif self.engine in ("espeak", "espeak-ng"):
            result = subprocess.run(
                [self.engine, "--voices"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    voices.append({
                        "id": parts[4] if len(parts) > 4 else parts[3],
                        "name": parts[3],
                        "language": parts[1]
                    })

        elif self.engine == "say":
            result = subprocess.run(
                ["say", "-v", "?"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    voices.append({
                        "id": parts[0],
                        "name": parts[0],
                        "language": parts[1].strip("_")[:2] if len(parts) > 1 else "en"
                    })

        return voices


class TranscriptionStorage:
    """Storage for transcription history"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id TEXT PRIMARY KEY,
                    audio_path TEXT,
                    text TEXT NOT NULL,
                    language TEXT,
                    duration_seconds REAL,
                    word_count INTEGER,
                    confidence REAL,
                    summary TEXT,
                    status TEXT,
                    created_at TEXT,
                    model_used TEXT,
                    segments TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transcriptions_created
                ON transcriptions(created_at DESC)
            """)
            conn.commit()

    def save(self, transcription: Transcription):
        """Save a transcription"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO transcriptions
                (id, audio_path, text, language, duration_seconds, word_count,
                 confidence, summary, status, created_at, model_used, segments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transcription.id,
                transcription.audio_path,
                transcription.text,
                transcription.language,
                transcription.duration_seconds,
                transcription.word_count,
                transcription.confidence,
                transcription.summary,
                transcription.status,
                transcription.created_at,
                transcription.model_used,
                json.dumps(transcription.segments) if transcription.segments else None
            ))
            conn.commit()

    def get(self, transcription_id: str) -> Optional[Transcription]:
        """Get a transcription by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM transcriptions WHERE id = ?",
                (transcription_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_transcription(row)
        return None

    def get_recent(self, limit: int = 20) -> List[Transcription]:
        """Get recent transcriptions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM transcriptions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_transcription(row) for row in cursor.fetchall()]

    def search(self, query: str) -> List[Transcription]:
        """Search transcriptions by text content"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM transcriptions WHERE text LIKE ? ORDER BY created_at DESC",
                (f"%{query}%",)
            )
            return [self._row_to_transcription(row) for row in cursor.fetchall()]

    def delete(self, transcription_id: str) -> bool:
        """Delete a transcription"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM transcriptions WHERE id = ?",
                (transcription_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_transcription(self, row: sqlite3.Row) -> Transcription:
        """Convert database row to Transcription"""
        return Transcription(
            id=row["id"],
            audio_path=row["audio_path"],
            text=row["text"],
            language=row["language"],
            duration_seconds=row["duration_seconds"],
            word_count=row["word_count"],
            confidence=row["confidence"],
            summary=row["summary"],
            status=row["status"],
            created_at=row["created_at"],
            model_used=row["model_used"],
            segments=json.loads(row["segments"]) if row["segments"] else None
        )


class ScribeEngine:
    """Main Purma Scribe engine"""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".local" / "share" / "purma" / "scribe"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir = self.data_dir / "recordings"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self.storage = TranscriptionStorage(self.data_dir / "scribe.db")

        self.recorder = AudioRecorder() if PYAUDIO_AVAILABLE else None
        self.recognizer = SpeechRecognizer()
        self.tts = TextToSpeech()

        self.current_recording_id: Optional[str] = None
        self.is_recording = False

        # Ollama client for AI summarization
        self.ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def get_status(self) -> Dict[str, Any]:
        """Get Scribe status"""
        return {
            "recording_available": PYAUDIO_AVAILABLE,
            "whisper_available": WHISPER_AVAILABLE or FASTER_WHISPER_AVAILABLE,
            "tts_engine": self.tts.engine,
            "is_recording": self.is_recording,
            "current_recording_id": self.current_recording_id,
            "audio_devices": self.recorder.list_devices() if self.recorder else [],
            "tts_voices": self.tts.list_voices()
        }

    def start_recording(self, device_index: Optional[int] = None) -> Dict[str, Any]:
        """Start audio recording"""
        if not self.recorder:
            return {"success": False, "error": "Recording not available"}

        if self.is_recording:
            return {"success": False, "error": "Already recording"}

        import secrets
        self.current_recording_id = secrets.token_urlsafe(8)
        self.is_recording = True

        self.recorder.start_recording(device_index)

        return {
            "success": True,
            "recording_id": self.current_recording_id,
            "message": "Recording started"
        }

    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and save audio"""
        if not self.is_recording:
            return {"success": False, "error": "Not recording"}

        audio_data = self.recorder.stop_recording()
        self.is_recording = False

        # Save audio file
        audio_path = self.audio_dir / f"{self.current_recording_id}.wav"
        self.recorder.save_to_file(audio_data, str(audio_path))

        duration = self.recorder.get_duration(audio_data)

        recording_id = self.current_recording_id
        self.current_recording_id = None

        return {
            "success": True,
            "recording_id": recording_id,
            "audio_path": str(audio_path),
            "duration_seconds": duration,
            "message": "Recording saved"
        }

    async def transcribe_recording(
        self,
        recording_id: str,
        language: Optional[str] = None,
        summarize: bool = False
    ) -> Dict[str, Any]:
        """Transcribe a saved recording"""
        audio_path = self.audio_dir / f"{recording_id}.wav"

        if not audio_path.exists():
            return {"success": False, "error": "Recording not found"}

        try:
            # Transcribe
            result = self.recognizer.transcribe(str(audio_path), language)

            # Calculate word count
            word_count = len(result["text"].split())

            # Create transcription record
            transcription = Transcription(
                id=recording_id,
                audio_path=str(audio_path),
                text=result["text"],
                language=result["language"],
                duration_seconds=result["duration"],
                word_count=word_count,
                confidence=result.get("language_probability"),
                summary=None,
                status=TranscriptionStatus.COMPLETED.value,
                created_at=datetime.now().isoformat(),
                model_used=self.recognizer.model_name,
                segments=result.get("segments")
            )

            # Optionally summarize with AI
            if summarize and result["text"]:
                summary = await self._summarize_text(result["text"])
                transcription.summary = summary

            self.storage.save(transcription)

            return {
                "success": True,
                "transcription": transcription.to_dict()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        summarize: bool = False
    ) -> Dict[str, Any]:
        """Transcribe an audio file"""
        if not Path(file_path).exists():
            return {"success": False, "error": "File not found"}

        try:
            import secrets
            transcription_id = secrets.token_urlsafe(8)

            result = self.recognizer.transcribe(file_path, language)
            word_count = len(result["text"].split())

            transcription = Transcription(
                id=transcription_id,
                audio_path=file_path,
                text=result["text"],
                language=result["language"],
                duration_seconds=result["duration"],
                word_count=word_count,
                confidence=result.get("language_probability"),
                summary=None,
                status=TranscriptionStatus.COMPLETED.value,
                created_at=datetime.now().isoformat(),
                model_used=self.recognizer.model_name,
                segments=result.get("segments")
            )

            if summarize and result["text"]:
                summary = await self._summarize_text(result["text"])
                transcription.summary = summary

            self.storage.save(transcription)

            return {
                "success": True,
                "transcription": transcription.to_dict()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def quick_transcribe(
        self,
        duration_seconds: int = 5,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record and transcribe quickly"""
        if not self.recorder:
            return {"success": False, "error": "Recording not available"}

        # Start recording
        start_result = self.start_recording()
        if not start_result["success"]:
            return start_result

        # Wait for specified duration
        await asyncio.sleep(duration_seconds)

        # Stop recording
        stop_result = self.stop_recording()
        if not stop_result["success"]:
            return stop_result

        # Transcribe
        return await self.transcribe_recording(
            stop_result["recording_id"],
            language=language
        )

    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        save_to_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert text to speech"""
        success = self.tts.speak(text, voice, speed, save_to_file)

        return {
            "success": success,
            "text": text,
            "voice": voice,
            "speed": speed,
            "output_file": save_to_file
        }

    async def _summarize_text(self, text: str) -> Optional[str]:
        """Summarize text using Ollama"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "purma",
                        "prompt": f"Summarize the following transcription in 2-3 sentences:\n\n{text}",
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()

        except Exception as e:
            print(f"Summarization error: {e}")

        return None

    def get_transcription(self, transcription_id: str) -> Optional[Dict[str, Any]]:
        """Get a transcription by ID"""
        transcription = self.storage.get(transcription_id)
        if transcription:
            return transcription.to_dict()
        return None

    def get_recent_transcriptions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent transcriptions"""
        transcriptions = self.storage.get_recent(limit)
        return [t.to_dict() for t in transcriptions]

    def search_transcriptions(self, query: str) -> List[Dict[str, Any]]:
        """Search transcriptions"""
        transcriptions = self.storage.search(query)
        return [t.to_dict() for t in transcriptions]

    def delete_transcription(self, transcription_id: str) -> bool:
        """Delete a transcription and its audio file"""
        transcription = self.storage.get(transcription_id)
        if transcription:
            # Delete audio file if it exists
            if transcription.audio_path:
                audio_path = Path(transcription.audio_path)
                if audio_path.exists():
                    audio_path.unlink()

            return self.storage.delete(transcription_id)
        return False

    def list_voices(self) -> List[Dict[str, str]]:
        """List available TTS voices"""
        return self.tts.list_voices()

    def cleanup(self):
        """Clean up resources"""
        if self.recorder:
            self.recorder.cleanup()


# Global scribe instance
_scribe_engine: Optional[ScribeEngine] = None


def get_scribe_engine() -> ScribeEngine:
    """Get or create the global scribe engine instance"""
    global _scribe_engine
    if _scribe_engine is None:
        _scribe_engine = ScribeEngine()
    return _scribe_engine


# CLI interface
if __name__ == "__main__":
    import sys

    scribe = get_scribe_engine()

    if len(sys.argv) < 2:
        print("Purma Scribe - AI Voice Assistant")
        print("Usage: purma_scribe.py <command> [args]")
        print("\nCommands:")
        print("  status            - Show Scribe status")
        print("  record <seconds>  - Record and transcribe")
        print("  transcribe <file> - Transcribe audio file")
        print("  speak <text>      - Text to speech")
        print("  voices            - List TTS voices")
        print("  history           - Show recent transcriptions")
        sys.exit(0)

    command = sys.argv[1]

    if command == "status":
        status = scribe.get_status()
        print(f"Recording: {'available' if status['recording_available'] else 'unavailable'}")
        print(f"Whisper: {'available' if status['whisper_available'] else 'unavailable'}")
        print(f"TTS Engine: {status['tts_engine']}")

    elif command == "voices":
        voices = scribe.list_voices()
        print("Available voices:")
        for voice in voices:
            print(f"  {voice['id']}: {voice['name']} ({voice['language']})")

    elif command == "speak" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        result = scribe.speak(text)
        print(f"Spoke: {text}" if result["success"] else f"Error: {result.get('error')}")

    elif command == "history":
        transcriptions = scribe.get_recent_transcriptions(10)
        for t in transcriptions:
            print(f"\n[{t['id']}] {t['created_at']}")
            print(f"  Duration: {t['duration_seconds']:.1f}s, Language: {t['language']}")
            print(f"  Text: {t['text'][:100]}...")

    elif command == "transcribe" and len(sys.argv) > 2:
        import asyncio
        file_path = sys.argv[2]
        result = asyncio.run(scribe.transcribe_file(file_path))
        if result["success"]:
            t = result["transcription"]
            print(f"Transcription ID: {t['id']}")
            print(f"Language: {t['language']}")
            print(f"Duration: {t['duration_seconds']:.1f}s")
            print(f"Text: {t['text']}")
        else:
            print(f"Error: {result['error']}")
