Created At: 2026-06-16T03:07:44Z
Completed At: 2026-06-16T03:07:44Z
File Path: `file:///i:/claude2/scratch/recovered_engine_prompts.py`
Total Lines: 54
Total Bytes: 3950
Showing lines 1 to 54
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
1: Created At: 2026-06-16T02:59:12Z

2: Completed At: 2026-06-16T02:59:12Z

3: File Path: `file:///i:/claude2/backend/engine_prompts.py`

4: Total Lines: 679

5: Total Bytes: 58771

6: Showing lines 150 to 250

7: The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.

8:                  "char_static_ctx": char_static_ctx,

9:                  "hook_inst": hook_inst

10:              }

11:          )

12:  

13:      def build_beat_mapping_prompt(self, final_content: str, beats: List[str]) -> str:

14:          beats_json = json.dumps(beats, ensure_ascii=False, indent=2)

15:          return (

16:              "縺ゅ↑縺溘ｯ蟆剰ｪｬ縺ｮ讒矩繧貞譫舌☆繧句━遘縺ｪ繧ｨ繝繧｣繧ｿ繝ｼ縺ｧ縺吶\n"

17:              "謠千､ｺ縺輔ｌ縺溘仙ｰ剰ｪｬ譛ｬ譁縲代ｒ縲∵欠螳壹＆繧後◆縲舌ン繝ｼ繝医Μ繧ｹ繝医代ｮ蜷鬆逶ｮ縺ｫ螳悟ｨ縺ｫ蟇ｾ蠢懊☆繧句ｽ｢縺ｧ縲∝蜑ｲ繝ｻ繝槭ャ繝斐Φ繧ｰ縺励※縺上□縺輔＞縲\n\n"

18:              f"縲舌ン繝ｼ繝医Μ繧ｹ繝医:\n{beats_json}\n\n"

19:              f"縲仙ｰ剰ｪｬ譛ｬ譁縲:\n{final_content}\n\n"

20:              "縲仙ｺ蜉帶欠遉ｺ縲曾n"

21:              "莉･荳九ｮJSON蠖｢蠑上ｮ繝ｪ繧ｹ繝医ｮ縺ｿ繧貞ｺ蜉帙＠縺ｦ縺上□縺輔＞縲ゅ槭ｼ繧ｯ繝繧ｦ繝ｳ縺ｮ陬鬟ｾ繧ｳ繝ｼ繝峨ヶ繝
<truncated 579 bytes>
          "tone_inst": tone_inst,

28:                  "style_sample": f"縲先枚菴鍋ｶ呎価縲曾n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",

29:                  "director_notes": f"縲絶國ｸ丈ｿｮ豁｣謖遉ｺ縲曾n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",

30:                  "CONTENT_SEPARATOR": CONTENT_SEPARATOR

31:              }

32:          )

33:  

34:      def build_drafting_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int,

35:                                 char_static_ctx: str, char_dynamic_ctx: str, prev_ctx: str, **kwargs) -> Tuple[str, str]:

36:          scenes_data = plot_data.get("scenes", [])

37:          quota_inst = self._build_quota_section(scenes_data, target_word_count)

38:          show_tell_inst = self._build_show_tell_section(scenes_data)

39:          

40:          settings_ctx = kwargs.get('settings_ctx', '{}')

41:          if isinstance(settings_ctx, str):

42:              try:

43:                  settings_ctx = json.loads(settings_ctx)

44:              except:

45:                  settings_ctx = {}

46:          if not isinstance(settings_ctx, dict):

47:              settings_ctx = {}

48:  

49:          assertion_inst = self._build_assertion_section(settings_ctx.get('active_constraints', []))

50:          

51:          phase = plot_data.get("current_chain_phase", "Hate")

52:          tone_inst = f"縲舌ヵ繧ｧ繝ｼ繧ｺ繝医ｼ繝ｳ: {phase}縲曾n"

53:          if phase == "Hate": tone_inst += "隱ｭ閠縺ｮ縲弱＊縺ｾ縺√乗ｬｲ豎ゅｒ譛螟ｧ蛹悶○繧医よ雰縺ｮ蛯ｲ諷｢縺輔→荳榊ｽ薙↑霎ｱ繧√ｒ蝓ｷ諡励↓謠丞吶○繧医\n"

54: The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.
The above content shows the entire, complete file contents of the requested file.

