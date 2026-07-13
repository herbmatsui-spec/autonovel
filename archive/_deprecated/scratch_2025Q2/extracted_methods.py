# EXTRACTED BLOCK
Created At: 2026-06-16T02:59:12Z
Completed At: 2026-06-16T02:59:12Z
File Path: `file:///i:/claude2/backend/engine_prompts.py`
Total Lines: 679
Total Bytes: 58771
Showing lines 150 to 250
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
150:                 "char_static_ctx": char_static_ctx,

151:                 "hook_inst": hook_inst

152:             }

153:         )

154: 

155:     def build_beat_mapping_prompt(self, final_content: str, beats: List[str]) -> str:

156:         beats_json = json.dumps(beats, ensure_ascii=False, indent=2)

157:         return (

158:             "縺ゅ↑縺溘ｯ蟆剰ｪｬ縺ｮ讒矩繧貞譫舌☆繧句━遘縺ｪ繧ｨ繝繧｣繧ｿ繝ｼ縺ｧ縺吶\n"

159:             "謠千､ｺ縺輔ｌ縺溘仙ｰ剰ｪｬ譛ｬ譁縲代ｒ縲∵欠螳壹＆繧後◆縲舌ン繝ｼ繝医Μ繧ｹ繝医代ｮ蜷鬆逶ｮ縺ｫ螳悟ｨ縺ｫ蟇ｾ蠢懊☆繧句ｽ｢縺ｧ縲∝蜑ｲ繝ｻ繝槭ャ繝斐Φ繧ｰ縺励※縺上□縺輔＞縲\n\n"

160:             f"縲舌ン繝ｼ繝医Μ繧ｹ繝医:\n{beats_json}\n\n"

161:             f"縲仙ｰ剰ｪｬ譛ｬ譁縲:\n{final_content}\n\n"

162:             "縲仙ｺ蜉帶欠遉ｺ縲曾n"

163:             "莉･荳九ｮJSON蠖｢蠑上ｮ繝ｪ繧ｹ繝医ｮ縺ｿ繧貞ｺ蜉帙＠縺ｦ縺上□縺輔＞縲ゅ槭ｼ繧ｯ繝繧ｦ繝ｳ縺ｮ陬鬟ｾ繧ｳ繝ｼ繝峨ヶ繝ｭ繝繧ｯｼ```json 縺ｪ縺ｩｼ峨ｯ蜷ｫ繧√↑縺縺ｧ縺上□縺輔＞縲\n"

164:             "繝ｪ繧ｹ繝医ｮ隕∫ｴ謨ｰ縺ｯ縲舌ン繝ｼ繝医Μ繧ｹ繝医代ｮ隕∫ｴ謨ｰ縺ｨ蜷後§縺ｫ縺励∝推隕∫ｴ縺ｯ蟇ｾ蠢懊☆繧九ン繝ｼ繝医↓繝槭ャ繝斐Φ繧ｰ縺輔ｌ縺滓悽譁縺ｮ繝繧ｭ繧ｹ繝域ｮｵ關ｽ縺ｨ縺励∪縺吶\n"

165:             "譛ｬ譁荳ｭ縺ｮ縺吶∋縺ｦ
<truncated 4718 bytes>
rint', ''),

223:                 "target_word_count": target_word_count,

224:                 "tone_inst": tone_inst,

225:                 "style_sample": f"縲先枚菴鍋ｶ呎価縲曾n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",

226:                 "director_notes": f"縲絶國ｸ丈ｿｮ豁｣謖遉ｺ縲曾n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",

227:                 "CONTENT_SEPARATOR": CONTENT_SEPARATOR

228:             }

229:         )

230: 

231:     def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,

232:                                char_static_ctx: str, char_dynamic_ctx: str, prev_ctx: str, **kwargs) -> Tuple[str, str]:

233:         scenes_data = plot_data.get("scenes", [])

234:         quota_inst = self._build_quota_section(scenes_data, target_word_count)

235:         show_tell_inst = self._build_show_tell_section(scenes_data)

236:         

237:         settings_ctx = kwargs.get('settings_ctx', '{}')

238:         if isinstance(settings_ctx, str):

239:             try:

240:                 settings_ctx = json.loads(settings_ctx)

241:             except:

242:                 settings_ctx = {}

243:         if not isinstance(settings_ctx, dict):

244:             settings_ctx = {}

245: 

246:         assertion_inst = self._build_assertion_section(settings_ctx.get('active_constraints', []))

247:         

248:         phase = plot_data.get("current_chain_phase", "Hate")

249:         tone_inst = f"縲舌ヵ繧ｧ繝ｼ繧ｺ繝医ｼ繝ｳ: {phase}縲曾n"

250:         if phase == "Hate": tone_inst += "隱ｭ閠縺ｮ縲弱＊縺ｾ縺√乗ｬｲ豎ゅｒ譛螟ｧ蛹悶○繧医よ雰縺ｮ蛯ｲ諷｢縺輔→荳榊ｽ薙↑霎ｱ繧√ｒ蝓ｷ諡励↓謠丞吶○繧医\n"

The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.


================================================================================

# EXTRACTED BLOCK
Created At: 2026-06-16T03:06:51Z
Completed At: 2026-06-16T03:06:51Z
File Path: `file:///C:/Users/keide/.gemini/antigravity-ide/brain/96401c88-aaff-41af-9694-5d7e6bcb52bd/scratch/replace_apc.py`
Total Lines: 64
Total Bytes: 4018
Showing lines 1 to 64
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
1: import sys
2: 
3: path = 'i:/claude2/backend/engine_prompts.py'
4: content = open(path, encoding='utf-8').read()
5: 
6: target = """    def build_apc_system_prompt(self, style_key: str, write_rule_type: str, settings_ctx_json: str, hooks_inst: str, char_static_ctx: str) -> str:
7:         style_inst = self.get_style_instruction(style_key)
8:         rule_set_content = get_rule_set(write_rule_type)
9:         style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])
10:         is_light = "light" in style_key or "short" in style_key or style_def.get("dialogue_ratio") == "60%"
11:         direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]
12:         commercial_inst = f"\\n【商用執筆プロトコル】\\n{direction}\\n- 文字数の水増しではなく『描写の解像度』で目標を達成せよ。\\n- 読者の興味を引く『フック』を各シーンの終わりに配置せよ。"
13: 
14:         hook_inst = self._build_hook_strategy_section()
15: 
16:         sys_inst = (
17:             f"{style_inst}\\n{rule_set_content}\\n{commercial_inst}\\n"
18:             f"【作品設定・描写フック】: {settings_ctx_json}\\n{hooks_inst}\\n"
19:             f"【キャラクター不変属性】\\n{char_static_ctx}\\n"
20:             f"{hook_inst}\\n"
21:             "【AI定型句の禁止】: 蹂躙、驚愕、絶望、静寂、圧倒、歓喜を禁じ、具体的肉体反応で描写せよ。\\n"
22:             "【説明語りの禁止】: 地の文や台詞
<truncated 744 bytes>
ys_inst"""
29: 
30: # Let's search dynamically due to potential Shift-JIS garbling representation or escape sequence differences.
31: idx = content.find('def build_apc_system_prompt')
32: if idx != -1:
33:     end_idx = content.find('def build_beat_mapping_prompt')
34:     if end_idx != -1:
35:         target_block = content[idx:end_idx]
36:         replacement_block = """def build_apc_system_prompt(self, style_key: str, write_rule_type: str, settings_ctx_json: str, hooks_inst: str, char_static_ctx: str) -> str:
37:         style_inst = self.get_style_instruction(style_key)
38:         rule_set_content = get_rule_set(write_rule_type)
39:         style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])
40:         is_light = "light" in style_key or "short" in style_key or style_def.get("dialogue_ratio") == "60%"
41:         direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]
42:         commercial_inst = f"\\n【商用執筆プロトコル】\\n{direction}\\n- 文字数の水増しではなく『描写の解像度』で目標を達成せよ。\\n- 読者の興味を引く『フック』を各シーンの終わりに配置せよ。"
43: 
44:         hook_inst = self._build_hook_strategy_section()
45: 
46:         return self.registry.render(
47:             "apc_system",
48:             {
49:                 "style_inst": style_inst,
50:                 "rule_set_content": rule_set_content,
51:                 "commercial_inst": commercial_inst,
52:                 "settings_ctx_json": settings_ctx_json,
53:                 "hooks_inst": hooks_inst,
54:                 "char_static_ctx": char_static_ctx,
55:                 "hook_inst": hook_inst
56:             }
57:         )
58: 
59:     """
60:         content = content[:idx] + replacement_block + content[end_idx:]
61:         print("APC prompt replaced successfully")
62: 
63: open(path, 'w', encoding='utf-8').write(content)
64: 
The above content shows the entire, complete file contents of the requested file.


================================================================================

# EXTRACTED BLOCK
Created At: 2026-06-16T03:07:19Z
Completed At: 2026-06-16T03:07:20Z

				The command completed successfully.
				Output:
				Found 3 occurrences.

--------------------------------------------------

def build_beat_mapping_prompt(self, final_content: str, beats: List[str]) -> str:\r\n156:         beats_json = json.dumps(beats, ensure_ascii=False, indent=2)\r\n157:         return (\r\n158:             \"あなた�小説の構�を�析する優�なエ�ィターです�\\n\"\r\n159:             \"提示された�小説本�】を、指定された【ビートリスト�目に完�に対応する形で、�割・マッピングしてください�\\n\\n\"\r\n160:             f\"【ビートリスト�:\\n{beats_json}\\n\\n\"\r\n161:             f\"【小説本�:\\n{final_content}\\n\\n\"\r\n162:             \"【�力指示】\n\"\r\n163:             \"以下�JSON形式�リスト�みを�力してください。�ク�ウンの�飾コードブロ�ク�```json など�含めな�でください�\\n\"\r\n164:             \"リスト�要�数は【ビートリスト�要�数と同じにし�各要�は対応するビートにマッピングされた本�の�キスト段落とします�\\n\"\r\n165:             \"本�中のすべて\n<truncated 4718 bytes>\nrint', ''),\r\n223:                 \"target_word_count\": target_word_count,\r\n224:                 \"tone_inst\": tone_inst,\r\n225:                 \"style_sample\": f\"【文体継承】\n{kwargs.get('prose_sample')}\" if kwargs.get('prose_sample') else \"\",\r\n226:                 \"director_notes\": f\"【⚠�修正�示】\n{kwargs.get('director_notes')}\" if kwargs.get('director_notes') else \"\",\r\n227:                 \"CONTENT_SEPARATOR\": CONTENT_SEPARATOR\r\n228:             }\r\n229:         )\r\n230: \r\n231:     def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,\r\n232:                                char_static_ctx: str, char_dynam
<truncated 1966 bytes>
5:                 \"hook_inst\": hook_inst\n56:             }\n57:         )\n58: \n59:     \"\"\"\n60:         content = content[:idx] + replacement_block + content[end_idx:]\n61:         print(\"APC prompt replaced successfully\")\n62: \n63: open(path, 'w', encoding='utf-8').write(content)\n64: \nThe above content shows the entire, complete file contents of the requested file.\n"}



--------------------------------------------------

def build_beat_mapping_prompt\\\" in line or \\\"def build_delta_polish_prompt\\\" in line:\\n            found_defs.append(line)\\n\\nprint(f\\\"Found {len(found_defs)} occurrences.\\\")\\nfor fd in found_defs[-3:]: # Print last 3 occurrences\\n    print(\\\"-\\\" * 50)\\n    # Print a snippet\\n    idx = fd.find(\\\"def build_beat_mapping_prompt\\\")\\n    if idx != -1:\\n        print(fd[idx:idx+2000])\\n    idx2 = fd.find(\\\"def build_delta_polish_prompt\\\")\\n    if idx2 != -1:\\n        print(fd[idx2:idx2+2000])\\n\"","Description":"\"Scan transcript.jsonl to find the lost method definitions\"","IsArtifact":"false","Overwrite":"true","TargetFile":"\"i:\\\\claude2\\\\scratch\\\\find_lost_methods.py\"","toolAction":"\"Writing find_lost_methods.py script\"","toolSummary":"\"Write find_lost_methods.py\""}}]}



def build_delta_polish_prompt\\\" in line:\\n            found_defs.append(line)\\n\\nprint(f\\\"Found {len(found_defs)} occurrences.\\\")\\nfor fd in found_defs[-3:]: # Print last 3 occurrences\\n    print(\\\"-\\\" * 50)\\n    # Print a snippet\\n    idx = fd.find(\\\"def build_beat_mapping_prompt\\\")\\n    if idx != -1:\\n        print(fd[idx:idx+2000])\\n    idx2 = fd.find(\\\"def build_delta_polish_prompt\\\")\\n    if idx2 != -1:\\n        print(fd[idx2:idx2+2000])\\n\"","Description":"\"Scan transcript.jsonl to find the lost method definitions\"","IsArtifact":"false","Overwrite":"true","TargetFile":"\"i:\\\\claude2\\\\scratch\\\\find_lost_methods.py\"","toolAction":"\"Writing find_lost_methods.py script\"","toolSummary":"\"Write find_lost_methods.py\""}}]}






================================================================================

# EXTRACTED BLOCK
Created At: 2026-06-16T03:07:25Z
Completed At: 2026-06-16T03:07:26Z

				The command completed successfully.
				Output:
				Line 136 content contains method definition:

def build_beat_mapping_prompt(self, final_content: str, beats: List[str]) -> str:


156:         beats_json = json.dumps(beats, ensure_ascii=False, indent=2)


157:         return (


158:             "あなた�小説の構�を�析する優�なエ�ィターです�\n"


159:             "提示された�小説本�】を、指定された【ビートリスト�目に完�に対応する形で、�割・マッピングしてください�\n\n"


160:             f"【ビートリスト�:\n{beats_json}\n\n"


161:             f"【小説本�:\n{final_content}\n\n"


162:             "【�力指示】\n"


163:             "以下�JSON形式�リスト�みを�力してください。�ク�ウンの�飾コードブロ�ク�```json など�含めな�でください�\n"


164:             "リスト�要�数は【ビートリスト�要�数と同じにし�各要�は対応するビートにマッピングされた本�の�キスト段落とします�\n"


165:             "本�中のすべて

<truncated 4718 bytes>

rint', ''),


223:                 "target_word_count": target_word_count,


224:                 "tone_inst": tone_inst,


225:                 "style_sample": f"【文体継承】\n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",


226:                 "director_notes": f"【⚠�修正�示】\n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",


227:                 "CONTENT_SEPARATOR": CONTENT_SEPARATOR


228:             }


229:         )


230: 


231:     def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,


232:                                char_static_ctx: str, char_dynamic_ctx: str, prev_ctx: str, **kwargs) -> Tuple[str, str]:


233:         scenes_data = plot_
<truncated 1154 bytes>
definition:

def build_beat_mapping_prompt')

34:     if end_idx != -1:

35:         target_block = content[idx:end_idx]

36:         replacement_block = """def build_apc_system_prompt(self, style_key: str, write_rule_type: str, settings_ctx_json: str, hooks_inst: str, char_static_ctx: str) -> str:

37:         style_inst = self.get_style_instruction(style_key)

38:         rule_set_content = get_rule_set(write_rule_type)

39:         style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])

40:         is_light = "light" in style_key or "short" in style_key or style_def.get("dialogue_ratio") == "60%"

41:         direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]

42:         commercial_inst = f"\\n�y�p�M�v�g�R�z\\n{direction}\\n- �̐�ł͂Ȃ�w�`�ʂ̉𑜓x�x�ŖڕW�B�B\\n- �ǎ҂̋�w�t�b�N�x�e�V�[�̏I�ɔz�u�B"

43: 

44:         hook_inst = self._build_hook_strategy_section()

45: 

46:         return self.registry.render(

47:             "apc_system",

48:             {

49:                 "style_inst": style_inst,

50:                 "rule_set_content": rule_set_content,

51:                 "commercial_inst": commercial_inst,

52:                 "settings_ctx_json": settings_ctx_json,

53:                 "hooks_inst": hooks_inst,

54:                 "char_static_ctx": char_static_ctx,

55:                 "hook_inst": hook_inst

56:             }

57:         )

58: 

59:     """

60:         content = content[:idx] + replacement_block + content[end_idx:]

61:         print("APC prompt replaced successfully")

62: 

63: open(path, 'w', encoding='utf-8').write(content)

64: 

The above content shows the entire, complete file contents of the requested file.



================================================================================

Line 380 content contains method definition:

Error parsing line 380: 'cp932' codec can't encode character '\ufffd' in position 209: illegal multibyte sequence




================================================================================


