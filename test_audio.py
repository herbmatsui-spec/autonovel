import sys
sys.path.insert(0, 'E:/hhh')
from src.easy_mode.phase3.media_mix import MediaMixExporter

# Test with ASCII text first
exporter = MediaMixExporter(genre='fantasy', preset={})
text = 'Narrator: It was raining. Bob said "It\'s cold tonight."'
print('Text:', text)
try:
    script = exporter.convert_to_audio_drama(text)
    print('Script created successfully')
    print('Script type:', type(script))
    print('Script voice_lines count:', len(script.voice_lines) if script.voice_lines else 0)
    if script.voice_lines:
        for i, vl in enumerate(script.voice_lines):
            print(f'  VoiceLine {i}: character={vl.character}, text={vl.text}')
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()