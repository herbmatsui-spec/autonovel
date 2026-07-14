import sys

sys.path.append('src')
from config.erotic_pacing import EroticCurve
from src.engine.prompts.erotic_specialist import EroticSpecialist

curve = EroticCurve.create_default(intensity=2)
context = {
    'platform_preset': 'kakuyomu_romance',
    'desire_level': 20,
    'sensory_focus': 'touch, gaze',
    'consent_state': 'established',
    'character_info': '主人公: 若き騎士アルフレッド\nヒロイン: 秘めた想いを抱く王女リサ',
    'scene_setting': '星空の下、塔の一室で二人は静かに語り合う。',
    'next_episode_hint': '次回は闇の森へ向かう旅が始まる。'
}

sp = EroticSpecialist()
scene = sp.build_scene_prompt(curve, context)
after = sp.build_aftercare_prompt(context)
print('--- Scene Prompt ---')
print('Scene length:', len(scene))
# print('Scene preview (first 200 chars):')
# print(repr(scene[:200]))
# print('...')
print('\n--- Aftercare Prompt ---')
print('Aftercare length:', len(after))
# print('Aftercare preview (first 200 chars):')
# print(repr(after[:200]))
# print('...')
