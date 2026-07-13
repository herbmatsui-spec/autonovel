Created At: 2026-06-16T02:58:04Z
Completed At: 2026-06-16T02:58:04Z
File Path: `file:///i:/claude2/backend/engine_prompts.py`
Total Lines: 752
Total Bytes: 53375
Showing lines 220 to 260
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
220: 

221: 【作品文脈（動的状態）】

222: 動的状態: {{ char_dynamic_ctx }}

223: 既知の文脈: {{ prev_ctx }}

224: 

225: 【指令】

226: ■ 台本 (絶対遵守): {{ script_text }}

227: ■ プロット設計図: {{ blueprint }}

228: ■ 目標文字数: {{ target_word_count }} 字以上

229: {{ tone_inst }}

230: {{ style_sample }}

231: {{ director_notes }}

232: 

233: --- 出力形式 ---

234: [thought_process]

235: {{ CONTENT_SEPARATOR }}

236: [NOVEL_CONTENT]

237: {{ CONTENT_SEPARATOR }}

238: [METADATA_JSON]

239: """)

240: 

241:         return template.render(

242:             quota_inst=quota_inst,

243:             show_tell_inst=show_tell_inst,

244:             forbidden_inst=forbidden_inst,

245:             assertion_inst=assertion_inst,

246:             char_dynamic_ctx=kwargs.get('char_dynamic_ctx', ''),

247:             prev_ctx=kwargs.get('prev_ctx', ''),

248:             script_text=script_text,

249:             blueprint=plot_data.get('detailed_blueprint', ''),

250:             target_word_count=target_word_count,

251:             tone_inst=tone_inst,

252:             style_sample=f"【文体継承】\n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",

253:             director_notes=f"【⚠️修正指示】\n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",

254:         )

255: 

256:     def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,

257:                               char_static_ctx: str, char_dynamic_ctx: str, prev_ctx: str, **kwargs) -> Tuple[str, str]:

258:         # 各セクションをモジュールとして構築

259:         scenes_data = plot_data.get("scenes", [])

260:         quota_inst = self._build_quota_section(scenes_data, target_word_count)

The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.

