"""
QR Code Generator Module
Generates QR code images from URLs or file paths for embedding in Word documents
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import qrcode
    _HAS_QRCODE = True
except ImportError:
    _HAS_QRCODE = False
    qrcode = None

logger = logging.getLogger(__name__)


def generate_qr_code(data_url: str, output_path: Path, size_pixels: int = 300) -> Optional[Path]:
    """
    Generate a PNG QR code image for a given URL or string.
    
    Args:
        data_url: The URL or text string to encode in the QR code
        output_path: Path to save the PNG file
        size_pixels: Box size / dimension helper
        
    Returns:
        Path to the generated QR code image file, or None if failed
    """
    if not _HAS_QRCODE:
        logger.warning("qrcode library is not installed. Skipping QR code generation.")
        return None
    
    if not data_url:
        logger.warning("Empty data_url provided for QR code generation.")
        return None
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(data_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(output_path))
        
        logger.info(f"QR code image generated: {output_path} (Encoded URL: {data_url})")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return None
