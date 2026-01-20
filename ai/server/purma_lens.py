#!/usr/bin/env python3
"""
PurmaLinux - Purma Lens
Contextual Vision System with AI
Real-time screen analysis and intelligent assistance
"""

import os
import sys
import json
import asyncio
import subprocess
import tempfile
import base64
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import httpx

# ============================================
# Configuration
# ============================================

HOME = Path.home()
LENS_DIR = HOME / ".local" / "share" / "purma" / "lens"
CAPTURES_DIR = LENS_DIR / "captures"
CACHE_DIR = LENS_DIR / "cache"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
VISION_MODEL = os.getenv("PURMA_VISION_MODEL", "llava")  # or moondream, bakllava
DEFAULT_MODEL = os.getenv("PURMA_MODEL", "purma")

# Create directories
LENS_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ============================================
# Enums and Data Classes
# ============================================

class CaptureMode(Enum):
    FULLSCREEN = "fullscreen"
    WINDOW = "window"
    REGION = "region"
    CLIPBOARD = "clipboard"

class ContentType(Enum):
    TEXT = "text"
    CODE = "code"
    TERMINAL = "terminal"
    BROWSER = "browser"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    UNKNOWN = "unknown"

class ActionType(Enum):
    COPY = "copy"
    SEARCH = "search"
    TRANSLATE = "translate"
    EXPLAIN = "explain"
    FIX_CODE = "fix_code"
    RUN_COMMAND = "run_command"
    OPEN_URL = "open_url"
    SAVE = "save"

@dataclass
class CaptureResult:
    """Result of a screen capture"""
    id: str
    path: str
    timestamp: str
    mode: CaptureMode
    width: int = 0
    height: int = 0
    size_bytes: int = 0

@dataclass
class OCRResult:
    """Result of OCR text extraction"""
    text: str
    confidence: float
    language: str
    blocks: List[Dict] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)

@dataclass
class VisionAnalysis:
    """Result of AI vision analysis"""
    description: str
    content_type: ContentType
    elements: List[Dict] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    text_detected: bool = False
    code_detected: bool = False
    error_detected: bool = False
    url_detected: bool = False
    suggestions: List[str] = field(default_factory=list)

@dataclass
class ContextSuggestion:
    """Contextual action suggestion"""
    action: ActionType
    title: str
    description: str
    command: Optional[str] = None
    data: Optional[str] = None
    priority: int = 1
    icon: str = ""

@dataclass
class LensCapture:
    """Complete lens capture with analysis"""
    capture: CaptureResult
    ocr: Optional[OCRResult] = None
    analysis: Optional[VisionAnalysis] = None
    suggestions: List[ContextSuggestion] = field(default_factory=list)
    extracted_data: Dict = field(default_factory=dict)

# ============================================
# Screen Capture
# ============================================

class ScreenCapture:
    """Cross-platform screen capture"""

    def __init__(self):
        self.capture_tool = self._detect_capture_tool()

    def _detect_capture_tool(self) -> str:
        """Detect available screenshot tool"""
        tools = [
            ("grim", "grim"),           # Wayland
            ("maim", "maim"),           # X11
            ("scrot", "scrot"),         # X11 fallback
            ("gnome-screenshot", "gnome-screenshot"),
            ("spectacle", "spectacle"),
        ]

        for cmd, name in tools:
            try:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return name
            except:
                continue

        return "import"  # ImageMagick fallback

    def capture(
        self,
        mode: CaptureMode = CaptureMode.FULLSCREEN,
        output_path: Optional[str] = None,
        delay: float = 0
    ) -> Optional[CaptureResult]:
        """Capture screen"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(CAPTURES_DIR / f"capture_{timestamp}.png")

        try:
            if delay > 0:
                import time
                time.sleep(delay)

            cmd = self._build_capture_command(mode, output_path)
            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode != 0:
                # Try fallback
                cmd = ["import", "-window", "root", output_path]
                subprocess.run(cmd, capture_output=True, timeout=30)

            if Path(output_path).exists():
                stat = Path(output_path).stat()

                # Get image dimensions
                width, height = self._get_image_dimensions(output_path)

                capture_id = hashlib.md5(output_path.encode()).hexdigest()[:12]

                return CaptureResult(
                    id=capture_id,
                    path=output_path,
                    timestamp=datetime.now().isoformat(),
                    mode=mode,
                    width=width,
                    height=height,
                    size_bytes=stat.st_size,
                )

        except Exception as e:
            print(f"Capture error: {e}")

        return None

    def _build_capture_command(self, mode: CaptureMode, output: str) -> List[str]:
        """Build capture command based on tool and mode"""
        tool = self.capture_tool

        if tool == "grim":
            if mode == CaptureMode.REGION:
                return ["grim", "-g", "$(slurp)", output]
            elif mode == CaptureMode.WINDOW:
                return ["grim", "-g", "$(swaymsg -t get_tree | jq -r '.. | select(.focused?) | .rect | \"\\(.x),\\(.y) \\(.width)x\\(.height)\"')", output]
            return ["grim", output]

        elif tool == "maim":
            if mode == CaptureMode.REGION:
                return ["maim", "-s", output]
            elif mode == CaptureMode.WINDOW:
                return ["maim", "-i", "$(xdotool getactivewindow)", output]
            return ["maim", output]

        elif tool == "scrot":
            if mode == CaptureMode.REGION:
                return ["scrot", "-s", output]
            elif mode == CaptureMode.WINDOW:
                return ["scrot", "-u", output]
            return ["scrot", output]

        # Fallback
        return ["import", "-window", "root", output]

    def _get_image_dimensions(self, path: str) -> Tuple[int, int]:
        """Get image dimensions"""
        try:
            result = subprocess.run(
                ["identify", "-format", "%wx%h", path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                dims = result.stdout.strip().split("x")
                return int(dims[0]), int(dims[1])
        except:
            pass
        return 0, 0

    def capture_region_interactive(self, output_path: Optional[str] = None) -> Optional[CaptureResult]:
        """Interactive region capture"""
        return self.capture(CaptureMode.REGION, output_path)

    def capture_window(self, output_path: Optional[str] = None) -> Optional[CaptureResult]:
        """Capture active window"""
        return self.capture(CaptureMode.WINDOW, output_path)

    def get_from_clipboard(self) -> Optional[CaptureResult]:
        """Get image from clipboard"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(CAPTURES_DIR / f"clipboard_{timestamp}.png")

            # Try wl-paste for Wayland
            result = subprocess.run(
                ["wl-paste", "-t", "image/png"],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout:
                with open(output_path, "wb") as f:
                    f.write(result.stdout)
            else:
                # Try xclip for X11
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout:
                    with open(output_path, "wb") as f:
                        f.write(result.stdout)

            if Path(output_path).exists():
                stat = Path(output_path).stat()
                width, height = self._get_image_dimensions(output_path)
                capture_id = hashlib.md5(output_path.encode()).hexdigest()[:12]

                return CaptureResult(
                    id=capture_id,
                    path=output_path,
                    timestamp=datetime.now().isoformat(),
                    mode=CaptureMode.CLIPBOARD,
                    width=width,
                    height=height,
                    size_bytes=stat.st_size,
                )

        except Exception as e:
            print(f"Clipboard error: {e}")

        return None

# ============================================
# OCR Engine
# ============================================

class OCREngine:
    """Text extraction using OCR"""

    def __init__(self):
        self.tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        """Check if tesseract is available"""
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def extract_text(
        self,
        image_path: str,
        language: str = "eng+spa"
    ) -> OCRResult:
        """Extract text from image using OCR"""
        if not self.tesseract_available:
            return OCRResult(
                text="",
                confidence=0,
                language=language,
                lines=[]
            )

        try:
            # Run tesseract
            result = subprocess.run(
                [
                    "tesseract", image_path, "stdout",
                    "-l", language,
                    "--psm", "3",  # Automatic page segmentation
                    "-c", "tessedit_create_tsv=0"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                text = result.stdout.strip()
                lines = [line.strip() for line in text.split("\n") if line.strip()]

                # Estimate confidence (basic heuristic)
                confidence = 0.8 if len(text) > 10 else 0.5

                return OCRResult(
                    text=text,
                    confidence=confidence,
                    language=language,
                    lines=lines,
                )

        except Exception as e:
            print(f"OCR error: {e}")

        return OCRResult(text="", confidence=0, language=language, lines=[])

    def extract_with_positions(self, image_path: str, language: str = "eng+spa") -> OCRResult:
        """Extract text with bounding boxes"""
        if not self.tesseract_available:
            return OCRResult(text="", confidence=0, language=language)

        try:
            # Use TSV output for positions
            result = subprocess.run(
                [
                    "tesseract", image_path, "stdout",
                    "-l", language,
                    "--psm", "3",
                    "tsv"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                blocks = []
                lines_text = []
                current_line = ""
                current_line_num = -1

                for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                    parts = line.split("\t")
                    if len(parts) >= 12:
                        try:
                            level = int(parts[0])
                            conf = float(parts[10])
                            text = parts[11]

                            if text.strip():
                                line_num = int(parts[4])
                                if line_num != current_line_num:
                                    if current_line:
                                        lines_text.append(current_line.strip())
                                    current_line = text + " "
                                    current_line_num = line_num
                                else:
                                    current_line += text + " "

                                blocks.append({
                                    "text": text,
                                    "confidence": conf,
                                    "x": int(parts[6]),
                                    "y": int(parts[7]),
                                    "width": int(parts[8]),
                                    "height": int(parts[9]),
                                })
                        except:
                            continue

                if current_line:
                    lines_text.append(current_line.strip())

                full_text = "\n".join(lines_text)
                avg_conf = sum(b["confidence"] for b in blocks) / len(blocks) if blocks else 0

                return OCRResult(
                    text=full_text,
                    confidence=avg_conf / 100,
                    language=language,
                    blocks=blocks,
                    lines=lines_text,
                )

        except Exception as e:
            print(f"OCR with positions error: {e}")

        return OCRResult(text="", confidence=0, language=language)

# ============================================
# Vision Analyzer
# ============================================

class VisionAnalyzer:
    """AI-powered image analysis"""

    def __init__(self, ollama_host: str = OLLAMA_HOST, model: str = VISION_MODEL):
        self.ollama_host = ollama_host
        self.model = model
        self.cache: Dict[str, VisionAnalysis] = {}

    async def analyze(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> VisionAnalysis:
        """Analyze image using vision model"""

        # Check cache
        cache_key = hashlib.md5(f"{image_path}:{prompt}".encode()).hexdigest()
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        # Read and encode image
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return VisionAnalysis(
                description=f"Error reading image: {e}",
                content_type=ContentType.UNKNOWN,
            )

        # Build prompt
        if not prompt:
            prompt = """Analyze this screenshot and describe:
1. What type of content is shown (code editor, terminal, browser, document, etc.)
2. Main elements visible
3. Any text, errors, or important information
4. Suggested actions the user might want to take

Be concise and practical. Focus on actionable information."""

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "images": [image_data],
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    description = data.get("response", "")

                    # Parse response to extract structured data
                    analysis = self._parse_analysis(description)
                    self.cache[cache_key] = analysis
                    return analysis

        except Exception as e:
            print(f"Vision analysis error: {e}")

        # Fallback to basic analysis without vision model
        return self._basic_analysis(image_path)

    def _parse_analysis(self, description: str) -> VisionAnalysis:
        """Parse AI response into structured analysis"""
        content_type = ContentType.UNKNOWN
        elements = []
        suggestions = []

        description_lower = description.lower()

        # Detect content type
        if any(word in description_lower for word in ["terminal", "command", "shell", "bash", "console"]):
            content_type = ContentType.TERMINAL
        elif any(word in description_lower for word in ["code", "editor", "ide", "programming", "vscode", "vim"]):
            content_type = ContentType.CODE
        elif any(word in description_lower for word in ["browser", "web", "chrome", "firefox", "website"]):
            content_type = ContentType.BROWSER
        elif any(word in description_lower for word in ["document", "pdf", "word", "text editor", "libreoffice"]):
            content_type = ContentType.DOCUMENT
        elif any(word in description_lower for word in ["image", "photo", "picture", "gimp"]):
            content_type = ContentType.IMAGE

        # Detect features
        text_detected = any(word in description_lower for word in ["text", "words", "reading", "written"])
        code_detected = any(word in description_lower for word in ["code", "function", "variable", "syntax"])
        error_detected = any(word in description_lower for word in ["error", "exception", "failed", "warning"])
        url_detected = "http" in description_lower or "url" in description_lower or "link" in description_lower

        # Extract suggestions from description
        if "suggest" in description_lower or "could" in description_lower or "might" in description_lower:
            # Try to find suggestion sentences
            sentences = description.split(".")
            for sentence in sentences:
                if any(word in sentence.lower() for word in ["suggest", "could", "might", "try", "consider"]):
                    suggestions.append(sentence.strip())

        return VisionAnalysis(
            description=description,
            content_type=content_type,
            elements=elements,
            text_detected=text_detected,
            code_detected=code_detected,
            error_detected=error_detected,
            url_detected=url_detected,
            suggestions=suggestions[:5],
        )

    def _basic_analysis(self, image_path: str) -> VisionAnalysis:
        """Basic analysis without AI"""
        return VisionAnalysis(
            description="Captura de pantalla guardada. Usa OCR para extraer texto.",
            content_type=ContentType.UNKNOWN,
        )

    async def ask_about_image(self, image_path: str, question: str) -> str:
        """Ask a specific question about the image"""
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": question,
                        "images": [image_data],
                        "stream": False,
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "No se pudo analizar la imagen")

        except Exception as e:
            return f"Error: {e}"

        return "No se pudo analizar la imagen"

# ============================================
# Context Suggester
# ============================================

class ContextSuggester:
    """Generate contextual action suggestions"""

    def __init__(self):
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        )
        self.email_pattern = re.compile(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            re.IGNORECASE
        )
        self.code_patterns = {
            'python': re.compile(r'def\s+\w+|import\s+\w+|class\s+\w+'),
            'javascript': re.compile(r'function\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+'),
            'bash': re.compile(r'^\s*\$|sudo\s|apt\s|npm\s|pip\s'),
            'error': re.compile(r'error|exception|failed|traceback|errno', re.IGNORECASE),
        }

    def generate_suggestions(
        self,
        ocr_result: Optional[OCRResult],
        analysis: Optional[VisionAnalysis]
    ) -> List[ContextSuggestion]:
        """Generate contextual suggestions"""
        suggestions = []
        text = ocr_result.text if ocr_result else ""

        # URL detection
        urls = self.url_pattern.findall(text)
        for url in urls[:3]:
            suggestions.append(ContextSuggestion(
                action=ActionType.OPEN_URL,
                title="Abrir URL",
                description=url[:50] + "..." if len(url) > 50 else url,
                command=f"xdg-open '{url}'",
                data=url,
                priority=3,
                icon="",
            ))

        # Email detection
        emails = self.email_pattern.findall(text)
        for email in emails[:2]:
            suggestions.append(ContextSuggestion(
                action=ActionType.COPY,
                title="Copiar email",
                description=email,
                command=f"echo '{email}' | wl-copy",
                data=email,
                priority=2,
                icon="",
            ))

        # Error detection
        if analysis and analysis.error_detected:
            suggestions.append(ContextSuggestion(
                action=ActionType.EXPLAIN,
                title="Explicar error",
                description="Analizar y explicar el error detectado",
                priority=5,
                icon="",
            ))

        # Code detection
        if analysis and analysis.code_detected:
            suggestions.append(ContextSuggestion(
                action=ActionType.FIX_CODE,
                title="Analizar codigo",
                description="Revisar el codigo visible",
                priority=3,
                icon="",
            ))

        # Terminal content
        if analysis and analysis.content_type == ContentType.TERMINAL:
            # Look for command patterns
            for line in text.split("\n"):
                if line.strip().startswith("$") or line.strip().startswith("#"):
                    cmd = line.strip().lstrip("$#").strip()
                    if cmd and len(cmd) < 100:
                        suggestions.append(ContextSuggestion(
                            action=ActionType.RUN_COMMAND,
                            title="Copiar comando",
                            description=cmd[:60] + "..." if len(cmd) > 60 else cmd,
                            command=f"echo '{cmd}' | wl-copy",
                            data=cmd,
                            priority=4,
                            icon="",
                        ))
                        break

        # Generic text actions
        if text and len(text) > 10:
            suggestions.append(ContextSuggestion(
                action=ActionType.COPY,
                title="Copiar texto",
                description=f"Copiar {len(text)} caracteres",
                command=None,
                data=text,
                priority=1,
                icon="",
            ))

            suggestions.append(ContextSuggestion(
                action=ActionType.TRANSLATE,
                title="Traducir texto",
                description="Traducir el texto extraido",
                priority=2,
                icon="",
            ))

            suggestions.append(ContextSuggestion(
                action=ActionType.SEARCH,
                title="Buscar en web",
                description="Buscar el texto seleccionado",
                command=f"xdg-open 'https://duckduckgo.com/?q={text[:100]}'",
                priority=1,
                icon="",
            ))

        # Always add save option
        suggestions.append(ContextSuggestion(
            action=ActionType.SAVE,
            title="Guardar captura",
            description="Guardar imagen en Imagenes",
            priority=1,
            icon="",
        ))

        # Sort by priority
        suggestions.sort(key=lambda x: -x.priority)

        return suggestions[:8]

    def extract_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from text"""
        data = {
            "urls": self.url_pattern.findall(text),
            "emails": self.email_pattern.findall(text),
            "has_code": bool(self.code_patterns['python'].search(text) or
                           self.code_patterns['javascript'].search(text)),
            "has_error": bool(self.code_patterns['error'].search(text)),
            "has_commands": bool(self.code_patterns['bash'].search(text)),
            "word_count": len(text.split()),
            "line_count": len(text.split("\n")),
        }

        # Extract potential file paths
        path_pattern = re.compile(r'[/~][\w./\-_]+\.\w+')
        data["file_paths"] = path_pattern.findall(text)

        # Extract IP addresses
        ip_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
        data["ip_addresses"] = ip_pattern.findall(text)

        return data

# ============================================
# Main Lens Engine
# ============================================

class LensEngine:
    """Main Purma Lens engine"""

    def __init__(self):
        self.capture = ScreenCapture()
        self.ocr = OCREngine()
        self.vision = VisionAnalyzer()
        self.suggester = ContextSuggester()
        self.recent_captures: List[LensCapture] = []
        self.max_recent = 20

    async def capture_and_analyze(
        self,
        mode: CaptureMode = CaptureMode.FULLSCREEN,
        do_ocr: bool = True,
        do_vision: bool = True,
        delay: float = 0
    ) -> Optional[LensCapture]:
        """Capture screen and analyze"""

        # Capture
        capture_result = self.capture.capture(mode, delay=delay)
        if not capture_result:
            return None

        # OCR
        ocr_result = None
        if do_ocr:
            ocr_result = self.ocr.extract_text(capture_result.path)

        # Vision analysis
        analysis = None
        if do_vision:
            analysis = await self.vision.analyze(capture_result.path)

        # Generate suggestions
        suggestions = self.suggester.generate_suggestions(ocr_result, analysis)

        # Extract structured data
        extracted_data = {}
        if ocr_result and ocr_result.text:
            extracted_data = self.suggester.extract_data(ocr_result.text)

        lens_capture = LensCapture(
            capture=capture_result,
            ocr=ocr_result,
            analysis=analysis,
            suggestions=suggestions,
            extracted_data=extracted_data,
        )

        # Add to recent
        self.recent_captures.insert(0, lens_capture)
        self.recent_captures = self.recent_captures[:self.max_recent]

        return lens_capture

    async def analyze_image(
        self,
        image_path: str,
        do_ocr: bool = True,
        do_vision: bool = True
    ) -> Optional[LensCapture]:
        """Analyze existing image"""
        if not Path(image_path).exists():
            return None

        stat = Path(image_path).stat()
        width, height = self.capture._get_image_dimensions(image_path)

        capture_result = CaptureResult(
            id=hashlib.md5(image_path.encode()).hexdigest()[:12],
            path=image_path,
            timestamp=datetime.now().isoformat(),
            mode=CaptureMode.FULLSCREEN,
            width=width,
            height=height,
            size_bytes=stat.st_size,
        )

        # OCR
        ocr_result = None
        if do_ocr:
            ocr_result = self.ocr.extract_text(image_path)

        # Vision analysis
        analysis = None
        if do_vision:
            analysis = await self.vision.analyze(image_path)

        # Generate suggestions
        suggestions = self.suggester.generate_suggestions(ocr_result, analysis)

        # Extract data
        extracted_data = {}
        if ocr_result and ocr_result.text:
            extracted_data = self.suggester.extract_data(ocr_result.text)

        return LensCapture(
            capture=capture_result,
            ocr=ocr_result,
            analysis=analysis,
            suggestions=suggestions,
            extracted_data=extracted_data,
        )

    async def quick_ocr(self, mode: CaptureMode = CaptureMode.REGION) -> Optional[str]:
        """Quick capture and OCR"""
        capture_result = self.capture.capture(mode)
        if not capture_result:
            return None

        ocr_result = self.ocr.extract_text(capture_result.path)
        return ocr_result.text if ocr_result else None

    async def ask_about_screen(self, question: str, mode: CaptureMode = CaptureMode.FULLSCREEN) -> str:
        """Capture and ask question about screen"""
        capture_result = self.capture.capture(mode)
        if not capture_result:
            return "Error: No se pudo capturar la pantalla"

        answer = await self.vision.ask_about_image(capture_result.path, question)
        return answer

    def get_recent_captures(self, limit: int = 10) -> List[Dict]:
        """Get recent captures"""
        return [
            {
                "id": c.capture.id,
                "path": c.capture.path,
                "timestamp": c.capture.timestamp,
                "mode": c.capture.mode.value,
                "has_ocr": c.ocr is not None and bool(c.ocr.text),
                "has_analysis": c.analysis is not None,
                "content_type": c.analysis.content_type.value if c.analysis else "unknown",
                "text_preview": c.ocr.text[:100] if c.ocr and c.ocr.text else None,
            }
            for c in self.recent_captures[:limit]
        ]

    def execute_suggestion(self, suggestion: ContextSuggestion) -> Dict[str, Any]:
        """Execute a suggestion action"""
        try:
            if suggestion.action == ActionType.COPY:
                if suggestion.data:
                    subprocess.run(
                        ["wl-copy", suggestion.data],
                        timeout=10
                    )
                    return {"success": True, "message": "Copiado al portapapeles"}

            elif suggestion.action == ActionType.OPEN_URL:
                if suggestion.command:
                    subprocess.run(suggestion.command, shell=True, timeout=10)
                    return {"success": True, "message": "URL abierta"}

            elif suggestion.action == ActionType.RUN_COMMAND:
                if suggestion.command:
                    subprocess.run(suggestion.command, shell=True, timeout=10)
                    return {"success": True, "message": "Comando copiado"}

            elif suggestion.action == ActionType.SEARCH:
                if suggestion.command:
                    subprocess.run(suggestion.command, shell=True, timeout=10)
                    return {"success": True, "message": "Busqueda abierta"}

            elif suggestion.action == ActionType.SAVE:
                # Already saved in captures dir
                return {"success": True, "message": "Captura guardada"}

            return {"success": False, "message": "Accion no implementada"}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def cleanup_old_captures(self, days: int = 7):
        """Clean up old captures"""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0

        for capture_file in CAPTURES_DIR.iterdir():
            if capture_file.is_file():
                mtime = datetime.fromtimestamp(capture_file.stat().st_mtime)
                if mtime < cutoff:
                    capture_file.unlink()
                    count += 1

        return count


# Global instance
lens_engine = LensEngine()
