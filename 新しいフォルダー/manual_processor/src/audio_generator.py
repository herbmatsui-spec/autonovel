"""
Audio Generator Module
Creates audio files from text using Google Text-to-Speech API
"""

import logging
import io
from pathlib import Path
from typing import Optional

try:
    from google.cloud import texttospeech
except ImportError:
    texttospeech = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

logger = logging.getLogger(__name__)


class AudioGenerator:
    """Generates audio files from text with Google Cloud TTS and gTTS fallback"""
    
    def __init__(self):
        """Initialize audio generator"""
        self.client = None
        if texttospeech is not None:
            try:
                self.client = texttospeech.TextToSpeechClient()
                logger.debug("Google Cloud TextToSpeechClient initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Google Cloud TTS client: {e}")
                self.client = None
    
    def generate_audio(self, text: str, output_path: Path) -> Path:
        """
        Generate audio file from text
        """
        if not text.strip():
            return self._create_silent_audio(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try Google Cloud TTS first
        if self.client:
            try:
                synthesis_input = texttospeech.SynthesisInput(text=text)
                voice = texttospeech.VoiceSelectionParams(
                    language_code="ja-JP",
                    name="ja-JP-Standard-A",
                    ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                )
                response = self.client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                with open(output_path, "wb") as out:
                    out.write(response.audio_content)
                logger.info(f"Audio content written to file via Cloud TTS: {output_path}")
                return output_path
            except Exception as e:
                logger.warning(f"Google Cloud TTS synthesis failed: {e}. Trying gTTS fallback...")

        # Fallback 1: gTTS
        if gTTS is not None:
            try:
                tts = gTTS(text=text, lang="ja")
                tts.save(str(output_path))
                logger.info(f"Audio content written to file via gTTS: {output_path}")
                return output_path
            except Exception as e:
                logger.warning(f"gTTS synthesis failed: {e}")

        # Fallback 2: Silent WAV/MP3 file
        logger.info("Falling back to silent audio file generation")
        return self._create_silent_audio(output_path)
    
    def _create_silent_audio(self, output_path: Path) -> Path:
        """Create a silent audio file for empty text"""
        # Create a minimal silent MP3 (1 second of silence)
        import wave
        import struct
        
        # WAV header for 1 second of silence at 44.1kHz, 16-bit, mono
        sample_rate = 44100
        duration = 1.0  # seconds
        num_samples = int(sample_rate * duration)
        
        # Create WAV file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path = output_path.with_suffix('.wav')
        
        with wave.open(str(wav_path), 'w') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            
            # Write silence (all zeros)
            for _ in range(num_samples):
                wav_file.writeframes(struct.pack('<h', 0))
        
        # Convert WAV to MP3 would require additional libraries like pydub
        # For simplicity, we'll just use WAV file for now
        # In a production environment, you'd use ffmpeg or pydub to convert to MP3
        # Renaming to .mp3 for consistency (though it's actually WAV)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.move(str(wav_path), str(output_path))
        
        logger.info(f"Silent audio file created: {output_path}")
        return output_path


def create_audio_summary(text: str, output_path: Path) -> Path:
    """
    Convenience function to generate audio from text
    
    Args:
        text: Text to convert to speech
        output_path: Output file path
        
    Returns:
        Path to generated audio file
    """
    generator = AudioGenerator()
    return generator.generate_audio(text, output_path)