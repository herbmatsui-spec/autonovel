class ProcessingError(Exception):
    """Processing-related errors"""
    pass

class OCRNotFoundError(ProcessingError):
    """OCR processing errors"""
    pass

class APIError(ProcessingError):
    """API-related errors"""
    pass

class ConfigurationError(APIError):
    """Configuration errors"""
    pass

class TTSError(APIError):
    """Text-to-speech errors"""
    pass

class FileIOError(ProcessingError):
    """File I/O errors"""
    pass