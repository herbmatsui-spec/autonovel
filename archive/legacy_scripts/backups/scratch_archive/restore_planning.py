
file_path = "agents/planning.py"

# Read current planning.py
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Rebuild expand_plots and clean speculative duplicate
new_lines = []

# Up to line 672 in original (which is where max_ability_retries starts)
# Let's find "max_ability_retries = 3" in the original lines.
stop_idx = -1
for idx, line in enumerate(lines):
    if "max_ability_retries = 3" in line:
        stop_idx = idx
        break

if stop_idx == -1:
    # If not found, let's find the loop start
    for idx, line in enumerate(lines):
        if "sem = asyncio.Semaphore" in line:
            # We want to keep everything up to when `_process_episode` loop does ability checks
            # Let's find "should_audit = ncs_score >= 40"
            if "should_audit = ncs_score >= 40" in lines[idx+20]:
                pass
    # Let's hardcode the search for lines we want to cut
    for idx, line in enumerate(lines):
        if "max_ability_retries = 3" in line or "AbilityConsistencyChecker" in line or "Ability consistency check" in line:
            stop_idx = idx
            break

print("Stop idx for original:", stop_idx)

# Let's read planning.py up to "max_ability_retries = 3"
# Actually, let's just write the modified expand_plots method completely.
# Let's find the exact index of `async def expand_plots(`
start_expand_idx = -1
for idx, line in enumerate(lines):
    if "async def expand_plots(" in line:
        start_expand_idx = idx
        break

print("Start expand idx:", start_expand_idx)

# Let's find where rewrite_single_plot starts (which is after expand_plots loop)
rewrite_start_idx = -1
for idx, line in enumerate(lines):
    if "async def rewrite_single_plot(" in line:
        rewrite_start_idx = idx
        break

print("Rewrite start idx:", rewrite_start_idx)

header = lines[:start_expand_idx]
footer = lines[rewrite_start_idx:]

# Let's construct expand_plots from scratch!
expand_plots_code = """    async def expand_plots(self, book_id: int, target_ep_list: List[int], arcs: List[Any], reporter=None, force: bool = False, branch_id: Optional[int] = None, branch_variant: Optional[str] = None, use_hierarchical: bool = True) -> List[Any]:
        if branch_id is None:
            book = await self.engine.repo.get_book(book_id)
            branch_id = book.current_branch_id if book and book.current_branch_id else 1

        book = await self.engine.repo.get_book(book_id)
        bible = await self.engine.repo.get_latest_bible(book_id)
        if not book or not bible: return []

        sem = asyncio.Semaphore(3)

        total = len(target_ep_list)
        done_count = 0

        async def _process_episode(ep_num):
            nonlocal done_count
            async with sem:
                try:
                    # ロックされているプロットは上書きせずスキップ
                    existing_plot = await self.engine.repo.get_plot(branch_id, ep_num)
                    if existing_plot and existing_plot.is_locked:
                        if reporter: reporter.report(f"🔒 第{ep_num}話はロックされているためスキップします。", "info")
                        done_count += 1
                        return existing_plot

                    settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")
                    roadmap = settings.get("full_story_roadmap") or getattr(bible, "full_story_roadmap", [])
                    ep_info = next((r for r in roadmap if (r.get("ep_num") if isinstance(r, dict) else getattr(r, "ep_num", 0)) == ep_num), {})
                    past_plots = await self.engine.repo.get_plots_between(branch_id, max(1, ep_num - 3), ep_num - 1)
                    
                    def _safe_to_dict(a, idx=None):
                        if isinstance(a, dict): return a
                        if hasattr(a, "model_dump"): return a.model_dump()
                        if hasattr(a, "dict"): return a.dict()
                        return {"arc_num": idx or 1, "title": "Main Arc", "start_ep": 1, "end_ep": 100, "summary": str(a)}

                    serializable_arcs = [_safe_to_dict(a, i+1) for i, a in enumerate(arcs)] if arcs else [{"arc_num": 1, "title": "Main Arc", "start_ep": 1, "end_ep": 100, "summary": ep_info.get("one_line_summary", "展開")}]
                    current_stress = book.cumulative_stress or 0
                    current_cost = book.cumulative_cost or 0.0
                    engine_key = getattr(bible, "engine_key", None)
                    narrative_res = await self.engine.narrative.compute_stress_phase(
                        book_id, branch_id, ep_num, current_stress, 
                        ep_info.get("is_catharsis", False), 
                        genre=book.genre or "fantasy", 
                        engine_key=engine_key,
                        cost_score=current_cost
                    )
                    narrative_inst = narrative_res.get("instruction", "")

                    # 監査レベルの決定。NCS（重要度スコア）が低い場合は一部の重い監査をスキップして高速化
                    is_critical = ep_info.get("is_catharsis", False) or ep_num <= 3 or ep_num >= (book.target_eps or 50) - 1

                    # プロット生成モードにもジャンル固有のトーン指示を反映させる
                    tone_inst = self.engine.narrative.get_tone_instruction(book.genre or "fantasy", engine_key=engine_key)
                    if tone_inst:
                        narrative_inst += f"\\n\\n【全体トーン制約】\\n{tone_inst}"
                        
                    # Speculative Branch Variant
                    if branch_variant == "Standard":
                        narrative_inst += "\\n\\n【⚠️分岐プロット（標準）】\\n標準的で王道な展開のプロットにしてください。"
                    elif branch_variant == "Catharsis":
                        narrative_inst += "\\n\\n【⚠️分岐プロット（カタルシス強め）】\\nこのエピソードは読者のカタルシスを最大化する構成（ざまぁ・圧倒的勝利等）に特化させてください。"
                    elif branch_variant == "Twist":
                        narrative_inst += "\\n\\n【⚠️分岐プロット（急展開）】\\nこのエピソードは予想外の急展開や強烈な危機など、物語の方向性が一気に変わるプロットにしてください。"

                    # 自己進化履歴から plot_patch をプロンプトに注入
                    history = await self.engine.repo.get_optimization_history(book_id)
                    plot_patch = ""
                    if history and "report_json" in history[0]:
                        report = history[0]["report_json"]
                        if isinstance(report, str):
                            try: report = json.loads(report)
                            except (json.JSONDecodeError, TypeError): report = {}
                        plot_patch = report.get("plot_patch", "") if isinstance(report, dict) else ""
                    
                    if plot_patch:
                        narrative_inst += f"\\n\\n【🧠 ドッグフィーディング自己進化命令 (プロット用)】\\n{plot_patch}"

                    # Enigma Engine Extended Context
                    truth_ledger = settings.get("truth_ledger", {})
                    foreshadowing_map = settings.get("foreshadowing_map", [])

                    # Improved NCS: Narrative Criticality Score
                    from config import AUDIT_TRIGGER_KEYWORDS
                    terminology = self.engine.narrative.get_terminology_map(book.genre or "fantasy", engine_key)
                    summary_text = (ep_info.get("one_line_summary", "") + ep_info.get("summary", "")).lower()
                    
                    criticality_triggers = set(AUDIT_TRIGGER_KEYWORDS)
                    criticality_triggers.update(terminology.values() if terminology else [])

                    ncs_score = 0
                    if ep_info.get("is_catharsis", False): ncs_score += 50
                    if any(kw in summary_text for kw in criticality_triggers): ncs_score += 30
                    if ep_num <= 3 or ep_num >= (book.target_eps or 50) - 2: ncs_score += 30

                    should_audit = ncs_score >= 40

                    # プロット生成と能力整合性チェック（矛盾がある場合はリトライ）
                    max_ability_retries = 3
                    ability_attempt = 0
                    ability_patch = ""
                    p_data = None

                    while ability_attempt < max_ability_retries:
                        current_narrative_inst = narrative_inst
                        if ability_patch:
                            current_narrative_inst += f"\\n\\n【🚨能力整合性エラー修正指示（絶対遵守）】\\n前回の詳細プロットにおいて、能力設定・代償の矛盾が検知されました。以下を修正して再構築してください：\\n{ability_patch}"

                        # Gemma4: Always use hierarchical + speculative expansion by default to ensure stability and quality
                        if (branch_variant == "Speculative" or branch_variant is None) and ability_attempt == 0:
                            if use_hierarchical:
                                if reporter: reporter.report(f"⏳ 第{ep_num}話: 階層的プロット分解(Beat Sheet)を生成中...", "info")
                                past_context = "\\n".join([f"- 第{getattr(p, 'ep_num', '?')}話: {getattr(p, 'summary', '未定義')}" for p in past_plots]) if past_plots else "なし"
                                rag_context = await self.engine.plot_rag.find_relevant_plots(ep_info.get("one_line_summary", ""), top_k=3, exclude_chapters=[ep_num])
                                full_context = past_context + "\\n" + rag_context
                                
                                from models.beat_sheet import BeatSheet
                                bs_prompt = self.engine.pm.build_beat_sheet_prompt(
                                    book.title, ep_num, ep_info, full_context, world_rules=settings
                                )
                                bs_res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, bs_prompt, response_schema=BeatSheet, reporter=reporter)
                                beat_sheet = BeatSheet.model_validate(bs_res.metadata) if bs_res.success else None
                                
                                if beat_sheet:
                                    # [Step B] 監査の左シフト: ビートシート段階での制約チェック
                                    is_bs_ok, bs_msg = await self.engine.narrative.audit_beat_sheet(beat_sheet, settings)
                                    if not is_bs_ok:
                                        if reporter: reporter.report(f"⚠️ ビートシート監査警告: {bs_msg}", "warning")
                                        current_narrative_inst += f"\\n\\n【⚠️ビートシート監査フィードバック】\\n{bs_msg}"
                                    
                                    # [Step C] ベクトル検索による動的文脈注入 (RAG)
                                    deep_memories = await self.engine.plot_rag.find_relevant_plots(beat_sheet.summary, top_k=3, exclude_chapters=[ep_num])
                                    
                                    # [Step D/E] 投機的並列生成と自動採択
                                    p_data = await self._speculative_plot_expansion(
                                        book, ep_num, ep_info, past_plots, serializable_arcs, current_stress,
                                        current_narrative_inst, engine_key or "", truth_ledger, foreshadowing_map, reporter,
                                        beat_sheet=beat_sheet, deep_memories=deep_memories
                                    )
                            
                            # もしbeat_sheet生成に失敗した、または非階層的モードの場合は従来の投機的プロット生成にフォールバック
                            if not p_data:
                                p_data = await self._speculative_plot_expansion(
                                    book, ep_num, ep_info, past_plots, serializable_arcs, current_stress,
                                    current_narrative_inst, engine_key or "", truth_ledger, foreshadowing_map, reporter
                                )
                        else:
                            # 従来型の逐次生成
                            if use_hierarchical:
                                if reporter: reporter.report(f"⏳ 第{ep_num}話: 階層的プロット分解(Beat Sheet)を生成中...", "info")
                                past_context = "\\n".join([f"- 第{getattr(p, 'ep_num', '?')}話: {getattr(p, 'summary', '未定義')}" for p in past_plots]) if past_plots else "なし"
                                rag_context = await self.engine.plot_rag.find_relevant_plots(ep_info.get("one_line_summary", ""), top_k=3, exclude_chapters=[ep_num])
                                full_context = past_context + "\\n" + rag_context
                                
                                from models.beat_sheet import BeatSheet
                                bs_prompt = self.engine.pm.build_beat_sheet_prompt(
                                    book.title, ep_num, ep_info, full_context, world_rules=settings
                                )
                                bs_res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, bs_prompt, response_schema=BeatSheet, reporter=reporter)
                                beat_sheet = BeatSheet.model_validate(bs_res.metadata) if bs_res.success else None

                                if beat_sheet:
                                    if reporter: reporter.report(f"⏳ 第{ep_num}話: ビートシートから展開(Expansion)を生成中...", "info")
                                    prompt = self.engine.pm.build_expand_from_beats_prompt(
                                        book.title, ep_num, beat_sheet, world_rules=settings, current_stress=current_stress,
                                        narrative_instruction=current_narrative_inst
                                    )
                                    res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=PlotEpisode, expected_ep_num=ep_num, reporter=reporter)
                                    if res.success:
                                        p_data = PlotEpisode.model_validate(res.metadata)
                            
                            if not p_data:
                                prompt = self.engine.pm.build_plot_expansion_prompt(
                                    book.title, ep_num, ep_info, past_plots, serializable_arcs, book.genre,
                                    current_stress=current_stress, narrative_instruction=current_narrative_inst,
                                    engine_key=engine_key or "",
                                    truth_ledger=truth_ledger, foreshadowing_map=foreshadowing_map
                                )
                                res = await self.engine._generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=PlotEpisode, expected_ep_num=ep_num, reporter=reporter)
                                if res.success:
                                    p_data = PlotEpisode.model_validate(res.metadata)

                        # 能力整合性監査を実行
                        if p_data:
                            from agents.audit import AbilityConsistencyChecker
                            checker = AbilityConsistencyChecker(self.engine)
                            db_chars = await self.engine.repo.get_characters(book_id)
                            characters_str = json.dumps([c.registry_data for c in db_chars], ensure_ascii=False)
                            world_settings_str = json.dumps(settings, ensure_ascii=False)
                            is_consistent, reason, patch = await checker.audit_ability_consistency(
                                p_data.detailed_blueprint, world_settings_str, characters_str
                            )
                            if is_consistent:
                                break
                            else:
                                ability_patch = patch
                                ability_attempt += 1
                                p_data = None
                        else:
                            break

                    if p_data:
                        # 敵役のIQ監査
                        antagonist_profile = ""
                        world_settings_str = json.dumps(settings, ensure_ascii=False)
                        if is_critical:
                            from agents.audit import PlotIntegrityMonitor
                            monitor = PlotIntegrityMonitor(self.engine)
                            is_antag_ok, antag_reason, antag_patch = await monitor.AntagonistIQAudit(
                                p_data.detailed_blueprint, world_settings_str, antagonist_profile, reporter=reporter
                            )
                            if not is_antag_ok and antag_patch:
                                p_data.detailed_blueprint += f"\\n\\n【⚠️敵役IQ監査修正指示】\\n{antag_patch}"
                        else:
                            if reporter:
                                reporter.report(f"ℹ️ 第{ep_num}話: 敵役行動の重点監査条件に該当しないため、監査をスキップし高速化しました。", "info")

                        # 因果律監査
                        from config import AUDIT_TRIGGER_KEYWORDS
                        found_triggers = [kw for kw in AUDIT_TRIGGER_KEYWORDS if kw in p_data.detailed_blueprint]
                        
                        if found_triggers:
                            logger.info(f"Ep.{ep_num} triggering causality audit (Triggers: {found_triggers[:3]})")
                            from agents.audit import PlotIntegrityMonitor
                            monitor = PlotIntegrityMonitor(self.engine)
                            is_consistent, reason, patch = await monitor.audit_blueprint_causality(p_data.detailed_blueprint, world_settings_str)
                            if not is_consistent and patch:
                                logger.info(f"Ep.{ep_num} plot causality patch applied: {reason}")
                                p_data.detailed_blueprint += f"\\n\\n【⚠️因果律修正パッチ】\\n{patch}"
                                if not p_data.healed_fields: p_data.healed_fields = []
                                p_data.healed_fields.append("causality_integrity")

                        p_data.ep_num = ep_num
                        next_cost_score = narrative_res.get("cost_score", 0.0)
                        
                        # Plot RAGへのインデックス
                        await self.engine.plot_rag.index_plot(p_data, ep_num)
                        await self.engine.repo.create_or_replace_plot(
                            book_id=book_id, branch_id=branch_id, ep_num=ep_num, 
                            thought_process=p_data.thought_process, title=p_data.title, 
                            summary=p_data.one_line_summary, detailed_blueprint=p_data.detailed_blueprint, 
                            next_hook=p_data.next_hook.model_dump() if p_data.next_hook else {}, 
                            tension=p_data.tension, stress=p_data.stress, catharsis=p_data.catharsis, 
                            love_meter=p_data.love_meter, is_catharsis=p_data.is_catharsis, 
                            catharsis_type=p_data.catharsis_type, 
                            scenes=[s.model_dump() for s in p_data.scenes] if p_data.scenes else [], 
                            status="expanded", misunderstanding_gap=p_data.misunderstanding_gap, 
                            lite_model_director_notes=p_data.lite_model_director_notes, 
                            script_content=p_data.script_content, current_chain_phase=p_data.current_chain_phase, 
                            resolution_style=p_data.resolution_style, burned_cost_or_loot=p_data.burned_cost_or_loot, 
                            antagonist_status=p_data.antagonist_status, thematic_milestone=p_data.thematic_milestone, 
                            state_integrity_score=p_data.state_integrity_score, healed_fields=p_data.healed_fields, 
                            is_micro_catharsis=p_data.is_micro_catharsis, 
                            information_asymmetry_level=p_data.information_asymmetry_level, 
                            cost_score=next_cost_score,
                            qol_delta=p_data.qol_delta, discovery_item=p_data.discovery_item, 
                            sanctuary_event=p_data.sanctuary_event
                        )
                        
                        # Truth Ledger の自動更新
                        if hasattr(p_data, "truth_ledger_updates") and p_data.truth_ledger_updates:
                            for char_name, new_facts in p_data.truth_ledger_updates.items():
                                if not new_facts: continue
                                db_chars = await self.engine.repo.get_characters(book_id)
                                char_obj = next((c for c in db_chars if c.name == char_name), None)
                                if char_obj:
                                    r_data = char_obj.registry_data
                                    if isinstance(r_data, str):
                                        try: r_data = json.loads(r_data)
                                        except: r_data = {}
                                    if isinstance(r_data, dict):
                                        kf = r_data.get("known_facts", [])
                                        for fact in new_facts:
                                            if fact not in kf:
                                                kf.append(fact)
                                        r_data["known_facts"] = kf
                                        await self.engine.repo.update_character_registry(book_id, char_obj.id, r_data)
                                        if reporter:
                                            reporter.report(f"📖 第{ep_num}話: {char_name}の知識(Truth Ledger)が更新されました。({len(new_facts)}件)", "info")
                                            
                        if reporter: 
                            reporter.update_progress(done_count, total, f"プロット詳細化中 ({done_count}/{total})", f"第{ep_num}話: {p_data.title}")
                            reporter.report(f"📝 第{ep_num}話 プロット詳細化完了: {p_data.title}", "info")
                        done_count += 1
                        return p_data
                    else:
                        if reporter: reporter.update_progress(done_count, total, f"プロット詳細化中 ({done_count}/{total})", f"第{ep_num}話: 生成失敗")
                    done_count += 1
                    return None
                except Exception as e:
                    logger.error(f"Error expanding plot for Ep.{ep_num}: {e}", exc_info=True)
                    done_count += 1
                    return None

        tasks = [_process_episode(ep_num) for ep_num in target_ep_list]
        results = await asyncio.gather(*tasks)
        await self.engine.repo.recalculate_book_cost(book_id, branch_id=branch_id)
        return [r for r in results if r is not None]
"""

# Let's make sure speculative execution doesn't duplicate at the footer.
# In footer, let's find `_speculative_plot_expansion` and remove it!
footer_lines = []
skip = False
for line in footer:
    if "async def _speculative_plot_expansion(" in line:
        skip = True
    elif skip and line.startswith("    async def ") or skip and line.startswith("class "):
        skip = False

    if not skip:
        footer_lines.append(line)

final_content = "".join(header) + "\n" + expand_plots_code + "\n" + "".join(footer_lines)

# Write the final perfect file back!
with open(file_path, "w", encoding="utf-8") as f:
    f.write(final_content)

print("Reconstructed planning.py successfully!")

