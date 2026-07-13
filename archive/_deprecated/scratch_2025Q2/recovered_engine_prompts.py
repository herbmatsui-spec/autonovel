Created At: 2026-06-16T02:59:12Z
Completed At: 2026-06-16T02:59:12Z
File Path: `file:///i:/claude2/backend/engine_prompts.py`
Total Lines: 679
Total Bytes: 58771
Showing lines 150 to 250
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
                 "char_static_ctx": char_static_ctx,
                 "hook_inst": hook_inst
             }
         )
 
     def build_beat_mapping_prompt(self, final_content: str, beats: List[str]) -> str:
         beats_json = json.dumps(beats, ensure_ascii=False, indent=2)
         return (
             "縺ゅ↑縺溘ｯ蟆剰ｪｬ縺ｮ讒矩繧貞譫舌☆繧句━遘縺ｪ繧ｨ繝繧｣繧ｿ繝ｼ縺ｧ縺吶\n"
             "謠千､ｺ縺輔ｌ縺溘仙ｰ剰ｪｬ譛ｬ譁縲代ｒ縲∵欠螳壹＆繧後◆縲舌ン繝ｼ繝医Μ繧ｹ繝医代ｮ蜷鬆逶ｮ縺ｫ螳悟ｨ縺ｫ蟇ｾ蠢懊☆繧句ｽ｢縺ｧ縲∝蜑ｲ繝ｻ繝槭ャ繝斐Φ繧ｰ縺励※縺上□縺輔＞縲\n\n"
             f"縲舌ン繝ｼ繝医Μ繧ｹ繝医:\n{beats_json}\n\n"
             f"縲仙ｰ剰ｪｬ譛ｬ譁縲:\n{final_content}\n\n"
             "縲仙ｺ蜉帶欠遉ｺ縲曾n"
             "莉･荳九ｮJSON蠖｢蠑上ｮ繝ｪ繧ｹ繝医ｮ縺ｿ繧貞ｺ蜉帙＠縺ｦ縺上□縺輔＞縲ゅ槭ｼ繧ｯ繝繧ｦ繝ｳ縺ｮ陬鬟ｾ繧ｳ繝ｼ繝峨ヶ繝ｭ繝繧ｯｼ```json 縺ｪ縺ｩｼ峨ｯ蜷ｫ繧√↑縺縺ｧ縺上□縺輔＞縲\n"
             "繝ｪ繧ｹ繝医ｮ隕∫ｴ謨ｰ縺ｯ縲舌ン繝ｼ繝医Μ繧ｹ繝医代ｮ隕∫ｴ謨ｰ縺ｨ蜷後§縺ｫ縺励∝推隕∫ｴ縺ｯ蟇ｾ蠢懊☆繧九ン繝ｼ繝医↓繝槭ャ繝斐Φ繧ｰ縺輔ｌ縺滓悽譁縺ｮ繝繧ｭ繧ｹ繝域ｮｵ關ｽ縺ｨ縺励∪縺吶\n"
             "譛ｬ譁荳ｭ縺ｮ縺吶∋縺ｦ
<truncated 4718 bytes>
rint', ''),
                 "target_word_count": target_word_count,
                 "tone_inst": tone_inst,
                 "style_sample": f"縲先枚菴鍋ｶ呎価縲曾n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",
                 "director_notes": f"縲絶國ｸ丈ｿｮ豁｣謖遉ｺ縲曾n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",
                 "CONTENT_SEPARATOR": CONTENT_SEPARATOR
             }
         )
 
     def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,
                                char_static_ctx: str, char_dynamic_ctx: str, prev_ctx: str, **kwargs) -> Tuple[str, str]:
         scenes_data = plot_data.get("scenes", [])
         quota_inst = self._build_quota_section(scenes_data, target_word_count)
         show_tell_inst = self._build_show_tell_section(scenes_data)
         
         settings_ctx = kwargs.get('settings_ctx', '{}')
         if isinstance(settings_ctx, str):
             try:
                 settings_ctx = json.loads(settings_ctx)
             except:
                 settings_ctx = {}
         if not isinstance(settings_ctx, dict):
             settings_ctx = {}
 
         assertion_inst = self._build_assertion_section(settings_ctx.get('active_constraints', []))
         
         phase = plot_data.get("current_chain_phase", "Hate")
         tone_inst = f"縲舌ヵ繧ｧ繝ｼ繧ｺ繝医ｼ繝ｳ: {phase}縲曾n"
         if phase == "Hate": tone_inst += "隱ｭ閠縺ｮ縲弱＊縺ｾ縺√乗ｬｲ豎ゅｒ譛螟ｧ蛹悶○繧医よ雰縺ｮ蛯ｲ諷｢縺輔→荳榊ｽ薙↑霎ｱ繧√ｒ蝓ｷ諡励↓謠丞吶○繧医\n"
The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.

