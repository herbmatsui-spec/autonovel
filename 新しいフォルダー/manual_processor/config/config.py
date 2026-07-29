import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    google_api_key: str
    gemini_api_key: str
    ocr_model: str = "gemini-1.5-flash"
    summary_model: str = "gemini-1.5-flash"
    tts_model: str = "gemini-2.5-flash-tts"
    tts_fallback_model: str = "gemini-3.1-flash-tts"
    output_directory: Path = field(default_factory=lambda: Path("./output"))
    temp_directory: Path = field(default_factory=lambda: Path("./temp"))
    log_level: str = "INFO"
    max_file_size_mb: int = 50
    pdf_dpi: int = 300
    gemini_temperature: float = 0.3
    gemini_max_output_tokens: int = 2048
    tts_speaking_rate: float = 1.0
    tts_pitch: float = 0.0
    compact_layout: bool = False
    use_emojis: bool = False
    supported_extensions: List[str] = field(default_factory=lambda: [".pdf"])
    _instance: Optional['Config'] = None
    
    @classmethod
    def get_instance(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = cls.from_env()
        return cls._instance
    
    @classmethod
    def from_env(cls) -> 'Config':
        google_api_key = os.getenv("GOOGLE_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY is required in environment variables")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required in environment variables")
        
        output_dir = os.getenv("OUTPUT_DIRECTORY", "./output")
        temp_dir = os.getenv("TEMP_DIRECTORY", "./temp")
        
        return cls(
            google_api_key=google_api_key,
            gemini_api_key=gemini_api_key,
            output_directory=Path(output_dir),
            temp_directory=Path(temp_dir),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
            pdf_dpi=int(os.getenv("PDF_DPI", "300")),
            gemini_temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.3")),
            gemini_max_output_tokens=int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")),
            tts_speaking_rate=float(os.getenv("TTS_SPEAKING_RATE", "1.0")),
            tts_pitch=float(os.getenv("TTS_PITCH", "0.0")),
            compact_layout=os.getenv("COMPACT_LAYOUT", "false").lower() in ("true", "1", "yes"),
            use_emojis=os.getenv("USE_EMOJIS", "false").lower() in ("true", "1", "yes"),
        )
    
    def validate(self) -> List[str]:
        errors = []
        
        if not self.google_api_key:
            errors.append("GOOGLE_API_KEY is not set")
        
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is not set")
        
        if self.max_file_size_mb <= 0:
            errors.append("MAX_FILE_SIZE_MB must be positive")
        
        if self.pdf_dpi <= 0:
            errors.append("PDF_DPI must be positive")
        
        return errors
    
    def ensure_directories(self) -> None:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.temp_directory.mkdir(parents=True, exist_ok=True)