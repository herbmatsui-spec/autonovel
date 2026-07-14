# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from src.agents.erotic_integrity import EroticIntegrityChecker

checker = EroticIntegrityChecker()

work = '''雨音が窓を優しく叩く夜、彼女は彼の前で呼吸を整えていた。

「いいよ」──震える声で彼女が囁く。潤んだ瞳が彼を見つめ、誘うように引き寄せた。
「求めて」と彼が返す。体温が上がる。部屋の空気が薫るように濃くなる。

【Build】
彼の指先がそっと彼女の頬に触れる。まるで絹を撫でるように、その感触が互いの肌を通して伝わった。視線が絡み合い、唇が触れる直前、彼女はさらに近づいた。

【Peak】
彼の掌が彼女の背中を滑らかに撫で下ろす。体温が溶け合い、まるで波が引くように彼女の身体がほどけていった。吐息が重なり、心音が響き合う。痛みではなく切なさが胸を満たした。溢れる感情が世界を塗り替える。二人の境界が溶けて一つになる。

【Afterglow】
静寂が二人を包む。彼女の呼吸が次第に沈静し、彼の胸の上で温もりが静まる。二人の距離感が再確認された。これからの時間が意味を持ち始める。明日への伏線が、彼の記憶にそっと刻まれた。'''

safe, issues, quality = checker.check_all(work)

with open('_test_output.txt', 'w', encoding='utf-8') as f:
    f.write(f'Safety: {"PASS" if safe else "FAIL"}\n')
    for i in issues:
        f.write(f'  - {i}\n')
    f.write(f'Quality Score: {quality.quality_score:.1f}/100\n')
    for k, v in quality.dimension_scores.items():
        f.write(f'  {k}: {v:.1f}\n')
    f.write(f'Strengths: {len(quality.strengths)}\n')
    f.write(f'Suggestions: {len(quality.suggestions)}\n')

print('OK')