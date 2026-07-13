Created At: 2026-06-01T08:11:01Z
Completed At: 2026-06-01T08:11:01Z
File Path: `file:///i:/%E6%9C%89%E6%96%99%E8%AB%8B%E6%B1%82/R8.4/%E5%80%8B%E4%BA%BA%E9%87%91%E9%8A%AD%E4%B8%80%E8%A6%A7%E8%A1%A8%28%E5%B9%B4%E9%96%93%29%E4%BB%A4%E5%92%8C8%E5%B9%B4%E5%BA%A6/claude2/agents/writing.py`
Total Lines: 831
Total Bytes: 49493
Showing lines 330 to 435
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
330:                 continue
331:                 
332:             raw_content = raw_content1 + "\n\n" + raw_content2
333:             meta = meta2
334:             
335:             if raw_content and len(raw_content.strip()) > 50: # 最低限の長さを担保
336:                 final_content = raw_content
337:                 final_meta = OutputSanitizer.normalize_metadata(meta)
338:                 
339:                 # 整合性チェック
340:                 threshold = self.engine.narrative.get_integrity_threshold(ctx["genre_str"], ctx.get("prev_integrity", 100), engine_key=engine_key)
341:                 is_integrity_ok, rate, _ = await monitor.check_integrity(keywords, blueprint, raw_content, threshold=threshold)
342:                 
343:                 # [V4.6] 設定の因果関係描写を判定（重点監査トリガー）
344:                 from config import AUDIT_TRIGGER_KEYWORDS
345:                 is_causal_ok = True
346:                 causal_reason = ""
347:                 
348:                 if any(kw in raw_content for kw in AUDIT_TRIGGER_KEYWORDS):
349:                     bible = ctx.get("bible")
350:                     world_settings_str = ""
351:                     active_constraints = []
352:                     if bible:
353:                         settings_dict = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")
354:                         world
<truncated 4144 bytes>
ch = eval_result.get("recommended_patch", "")
410:                         if patch:
411:                             sys_inst += f"\n\n【🚨自己評価フィードバックパッチ】\n{patch}"
412:                             
413:                 if (is_integrity_ok and is_causal_ok and dogfeed_ok) or is_easy_mode:
414:                     logger.info(f"Ep.{ep_num} generation successful (Integrity: {rate:.2f}, Causality: {is_causal_ok})")
415:                     break
416:                 else:
417:                     msg = f"Ep.{ep_num} audit failed."
418:                     if not is_integrity_ok: msg += f" (Integrity Rate: {rate:.2f} < {threshold})"
419:                     if not is_causal_ok: msg += f" (Causality: {causal_reason})"
420:                     if not dogfeed_ok: msg += " (Dogfeeding Score too low)"
421:                     logger.warning(f"{msg} Retrying...")
422:             else:
423:                 logger.warning(f"Ep.{ep_num} generation yielded too little content ({len(raw_content) if raw_content else 0} chars). Retrying...")
424: 
425:         if not final_content:
426:             logger.error(f"🚨 Ep.{ep_num} generation FAILED after {max_retries} attempts.")
427:             if reporter:
428:                 reporter.report(f"❌ 第{ep_num}話の本文生成に失敗しました（リトライ上限到達）。", "error")
429: 
430:         return final_content, final_meta, is_integrity_ok
431: 
432:     async def _surgical_causality_healing_pass(self, content: str, world_settings: str, blueprint: str, failure_reason: str, snippets: List[str] = None) -> str:
433:         """因果関係の欠落をピンポイントで修正・加筆する外科的パス"""
434:         
435:         # もしsnippetsがある場合は、関連部分だけを抜き出してLLMに渡すように最適化する
The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.

