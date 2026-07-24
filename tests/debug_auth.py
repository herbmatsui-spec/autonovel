import os
os.environ['AUTH_DISABLED'] = 'false'
os.environ['ALLOWED_API_KEYS'] = 'valid_key'
from src.backend.auth import validate_api_key_or_raise, AppError

try:
    validate_api_key_or_raise('invalid_key')
    print('SUCCESS (No exception)')
except Exception as e:
    print(f'RAISED: {type(e).__name__}: {e}')
