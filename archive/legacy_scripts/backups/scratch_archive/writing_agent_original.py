class WritingAgent:
    """本文執筆とパイプライン管理を担当"""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine

    async def generate_episodes(
        self, book_id: int, start_ep: int, end_ep: int, passion: float, target_word_count: int,
        do_refine: bool, reporter=None, env_state: Optional[Dict[str, str]] = None,
        is_easy_mode: bool = False
    ) -> int:
        book   = await self.engine.repo.get_book(book_id)
        char_db_models = await self.engine.repo.get_all_characters(book_id)
        # DBモデルを、属性アクセスが可能な Registry オブジェクトに変換
        chars: List[CharacterRegistry] = []
        for cm in char_db_models:
            try:
                reg_data = cm.registry_data if isinstance(cm.registry_data, dict) else json.loads(cm.registry_data or "{}")
                chars.append(CharacterRegistry.model_validate(reg_data))
            except Exception:
                continue
        bible  = await self.engine.repo.get_latest_bible(book_id)
        bible_settings: Dict[str, Any] = {}
        if bible and bible.settings:
            bible_settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")

        style_dna_dict = json.loads(book.style_dna) if isinstance(book.style_dna, str) else (book.style_dna or {})
        style_key      = str(style_dna_dict.get("mode", "style_web_standard"))
        write_rule_type = str(style_dna_dict.get("rule_set", "RULE_SET_A"))
        genre_str      = book.genre if book and book.genre else "ファンタジー"

        is_light = is_light_style(style_key, genre_str)

        self.engine.current_ep_num = 0

        # 改善案1: 研磨指針を最初からシステム指示に統合
        refine_direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]
        commercial_inst = f"\n【商用執筆プロトコル】\n{refine_direction}\n- 文字数の水増しではなく『描写の解像度』で目標を達成せよ。\n- 読者の興味を引く『フック』を各シーンの終わりに配置せよ。"

        integrity_monitor = PlotIntegrityMonitor(self.engine)
        logic_validator = InternalLogicValidator(self.engine)

        from backend.engine_prompts import get_rule_set
        rule_set_content = get_rule_set(write_rule_type)
        style_inst       = self.engine.pm.get_style_instruction(style_key)

        current_stress   = book.cumulative_stress or 0
        total_len = 0

        for ep_num in range(start_ep, end_ep + 1):
            self.engine.current_ep_num = ep_num
            plot = await self.engine.repo.get_plot(book_id, ep_num)
            if not plot:
                continue

            stress_ctx = self.engine.narrative.compute_stress_phase(ep_num, current_stress, plot.is_catharsis, genre_str)
            phase_instruction = stress_ctx.get("instruction", "")
            force_catharsis = stress_ctx.get("force_catharsis", False)
            current_stress_for_episode = stress_ctx.get("next_stress", current_stress)

            static_ctx, dynamic_ctx, prev_ctx = await self.engine.ctx_mgr.get_optimal_context_split(book_id, ep_num, plot, chars)

            from backend.engine_narrative import PacingGraph
            pacing = PacingGraph.get_instruction(ep_num, book.target_eps or 50, is_light)
            villain_inst = self.engine.pm.get_villain_instruction(genre_str)

            is_important_ep = plot.is_catharsis or force_catharsis or ep_num == 1
            settings_ctx = json.dumps(bible_settings, ensure_ascii=False)

            prev_prose = ""
            if ep_num > 1:
                prev_ch = await self.engine.repo.get_chapter(book_id, ep_num - 1)
                if prev_ch and prev_ch.content:
                    prev_prose = prev_ch.content[-500:].strip()

            atmo_prompt = AtmosphereGenerator.get_prompt(
                season=(env_state or {}).get("season", "春"),
                weather=(env_state or {}).get("weather", "晴天"),
            )

            script_text = plot.script_content or ""
            p_dump      = plot.model_dump()

            if reporter:
                reporter.report(f"👑 第{ep_num}話 [ストレス:{current_stress_for_episode}]: 最新コンテキストで執筆開始", "info")

            # --- 改善案9: Style RAG による文体サンプル注入 ---
            style_rag = StyleRagManager(self.engine)
            # シーン設計図を元に、最も「質感」が近いサンプルを検索
            hegemony_sample_text = await style_rag.find_best_sample(
                plot.detailed_blueprint,
                phase=plot.current_chain_phase,
                tag_hint=plot.catharsis_type if plot.is_catharsis else None
            )
            hegemony_inst = style_rag.format_as_prompt(hegemony_sample_text)

            current_target_word_count = target_word_count
            if is_important_ep:
                current_target_word_count = int(target_word_count * 1.5)

            # 自己最適化パッチの読み込み
            from config import GlobalConfig
            optimized_patch = GlobalConfig().get("optimized_prompt_patch", "")
            if optimized_patch:
                plot.lite_model_director_notes = (plot.lite_model_director_notes or "") + f"\n【自己最適化指示】: {optimized_patch}"

            # システム指示（執筆エンジンの人格と制約）の構築
            # キャラクターの癖 (ExpansionHooks) を初回執筆から反映させる
            char_hooks_list = []
            for c in chars:
                try:
                    if hasattr(c, "registry_data"):
                        reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                    elif hasattr(c, "model_dump"):
                        reg = c.model_dump()
                    else:
                        reg = {}
                except Exception:
                    reg = {}
                hooks = reg.get("expansion_hooks", [])
                if hooks:
                    char_hooks_list.append(f"■ {c.name}の描写フック: {', '.join(hooks)}")
            hooks_inst = "\n".join(char_hooks_list)

            sys_inst = (
                f"{style_inst}\n{rule_set_content}\n{commercial_inst}\n"
                f"【作品設定・描写フック】: {settings_ctx}\n{hooks_inst}\n"
                "【AI定型句の禁止】: 蹂躙、驚愕、絶望、静寂、圧倒、歓喜を禁じ、具体的肉体反応で描写せよ。\n"
                "【説明語りの禁止】: 地の文や台詞での長々とした設定説明を避け、行動や情景を通じて情報を伝えること（Show, don't tell）。\n"
                "【可読性の向上】: スマホ閲覧を前提とし、1段落は1〜3文程度に抑えること。\n"
                "【会話の比率】: Web小説のテンポを維持するため、会話文の比率を40〜50%に保つこと。\n"
                "【凄さの間接描写】: 主人公の活躍は、周囲の具体的反応（声の震え、後ずさり等）を用いて間接的に伝えよ。\n"
                "【引きの美学】: 最後は短い倒置法や体言止めを用い、次を読みたくなる『引き』で締めること。"
            )

            fw_prompt = self.engine.pm.build_final_writing_prompt(
                ep_num=ep_num,
                plot_data=p_dump,
                script_text=script_text,
                target_word_count=current_target_word_count,
                plot_thought_process=plot.thought_process,
                prose_sample=prev_prose,
                settings_ctx=bible_settings, # Dict形式で渡す
                char_static_ctx=static_ctx, char_dynamic_ctx=dynamic_ctx, prev_ctx=prev_ctx,
                is_climax=is_important_ep,
                pacing_inst=pacing.get("instruction", ""),
                villain_inst=villain_inst,
                director_notes=(plot.lite_model_director_notes or "") + hegemony_inst,
            )
            fw_prompt += f"\n{atmo_prompt}"
            if plot.lite_model_director_notes:
                fw_prompt += f"\n【⚠️ プロット時の自己批判・修正指示】\n{plot.lite_model_director_notes}"
            if phase_instruction:
                fw_prompt += phase_instruction

            # --- 執筆・監視ループ (Regeneration Process) ---
            max_retries = 1 if is_easy_mode else 2
            final_content = ""
            final_meta = {}
            is_integrity_ok = True
            missing = []

            # 高速化微調整: ループ外で一度だけキーワードを抽出（CPUコスト削減）
            blueprint_keywords = integrity_monitor.extract_keywords(plot.detailed_blueprint)

            for attempt in range(max_retries):
                # 1回目は精度重視、2回目は多様性を上げて突破を図る
                temp = 0.7 + (passion - 0.5) * 0.2 + (attempt * 0.15)
                final_res = await self.engine._generate_json(MODEL_WRITING, fw_prompt, system_instruction=sys_inst, temp=temp)
                final_meta, raw_content = final_res.unwrap_or({}, "")
                # Ensure metadata is normalized to a dict-like structure
                final_meta = OutputSanitizer.normalize_metadata(final_meta)

                # 高速なRegExベースの整合性チェック
                is_integrity_ok, rate, missing = await integrity_monitor.check_integrity(blueprint_keywords, plot.detailed_blueprint, raw_content)

                if is_easy_mode:
                    # かんたんモード: リトライせず1回で確定させ、不備は後続の加筆ステップへ回す
                    final_content = self.engine.formatter.format_for_kakuyomu(raw_content)
                    break

                if is_integrity_ok:
                    # 通常回では論理検証をスキップし、重要回（Payoff/Climax）のみ追加検証
                    if is_important_ep and plot.misunderstanding_gap:
                        is_logic_ok, missing_steps = await logic_validator.validate_misunderstanding_flow(raw_content, plot.misunderstanding_gap)
                        if not is_logic_ok:
                            if reporter: reporter.report(f"🚨 論理矛盾検知 (Attempt {attempt+1}): {missing_steps}。再試行します。", "warning")
                            continue

                    final_content = self.engine.formatter.format_for_kakuyomu(raw_content)
                    break
                else:
                    reason = f"整合性率 {rate*100:.0f}% (欠落: {', '.join(missing[:3])})"
                    if reporter:
                        reporter.report(f"🚨 整合性エラーを検知 (Attempt {attempt+1}): {reason}。強制再生成を実行します。", "warning")
                    if attempt == max_retries - 1:
                        final_content = self.engine.formatter.format_for_kakuyomu(raw_content) # 最終リトライ失敗

            # 文字数不足または整合性不備時の自動肉付け・修正ロジック (かんたんモード統合)
            content_len = len(final_content)
            should_amplify = content_len > 100 and content_len < current_target_word_count * 0.85
            should_fix = is_easy_mode and not is_integrity_ok and content_len > 100

            if should_amplify or should_fix:
                if reporter:
                    msg = "⚠️ 描写不足・整合性を一括補正中..." if should_fix else "⚠️ 文字数不足。描写を拡張中..."
                    reporter.report(msg, "warning")

                # 改善: 欠落要素の補正と同時に、キャラクター固有の「癖(ExpansionHooks)」を反映
                char_hooks = []
                for c in chars:
                    try:
                        if hasattr(c, "registry_data"):
                            reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                        elif hasattr(c, "model_dump"):
                            reg = c.model_dump()
                        else:
                            reg = {}
                    except Exception:
                        reg = {}
                    hooks = reg.get("expansion_hooks", [])
                    if hooks:
                        char_hooks.append(f"■ {c.name}: {', '.join(hooks)}")
                hooks_inst = "\n【キャラクター固有の描写フック（必ず反映）】\n" + "\n".join(char_hooks) if char_hooks else ""

                fix_inst = f"\n【重要：以下の欠落要素を必ず含めて自然に加筆せよ】: {', '.join(missing)}" if should_fix and missing else ""
                amplify_prompt = self.engine.pm.build_amplify_prompt(final_content, current_target_word_count, fix_inst + hooks_inst)

                res_amp = await self.engine._generate_json(MODEL_WRITING, amplify_prompt, temp=0.85)
                _, amp_content = res_amp.unwrap_or({}, final_content)
                final_content = self.engine.formatter.format_for_kakuyomu(amp_content)

            # 有機的結合: DB設定に基づき、キャラクターの口調・人称を最終強制補正
            final_content = TonePerfector.enforce_tone(final_content, chars)

            if ep_num == 1:
                catharsis_errors = ContentValidator.check_catharsis_reservation(final_content, ep_num)
                for err in catharsis_errors:
                    if reporter:
                        reporter.report(err, "warning")
                    logger.warning(f"Catharsis check failed for Ep.1: {err}")

            rhythm_errors = ContentValidator.check_rhythm(final_content)
            if rhythm_errors:
                if reporter:
                    reporter.report("📏 リズム単調さを検知。自動補正を実行します...", "warning")
                original_before_rhythm = final_content
                final_content = ContentValidator.auto_correct_rhythm(final_content)
                tone_errors   = verify_character_tone(original_before_rhythm, final_content)
                for err in tone_errors:
                    if reporter:
                        reporter.report(err, "warning")

            # 改善案3: Payoffフェーズまたは重要回のみ厳密な監査を行う（それ以外はスキップして高速化）
            should_deep_audit = is_important_ep or plot.current_chain_phase == "Payoff"
            if reporter and should_deep_audit:
                reporter.report(f"🔍 第{ep_num}話 物語の整合性をチェック中...", "info")

            f_audit = await self.engine.auditor.audit_foreshadowing_payoff(book_id, ep_num, final_content) if should_deep_audit else ForeshadowingAudit(is_recovered=True)
            audit_log_data = {}

            if should_deep_audit:
                if not f_audit.is_recovered and f_audit.missing_items:
                    # 改善案3: 自動リトライ（書き直し）を廃止し、ユーザーへの警告のみにする
                    reporter.report(f"⚠️ 伏線未回収を検知しました。プロット設計図を確認してください: {', '.join(f_audit.missing_items)}", "warning")
                audit_log_data = f_audit.model_dump()
                audit_log_data = OutputSanitizer.normalize_metadata(audit_log_data)
            else:
                prev_chapter = await self.engine.repo.get_chapter(book_id, ep_num - 1)
                prev_ws = None
                if prev_chapter and prev_chapter.world_state:
                    try:
                        prev_ws_dict = prev_chapter.world_state if isinstance(prev_chapter.world_state, dict) else json.loads(prev_chapter.world_state)
                        prev_ws = WorldState.model_validate(prev_ws_dict)
                    except Exception as e:
                        logger.warning(f"Failed to parse previous world state for lightweight audit: {e}")

                current_ws_dict = final_meta.get("next_world_state", {})
                current_ws = WorldState.model_validate(current_ws_dict)

                light_audit = await self.engine.auditor.lightweight_audit_world_state(current_ws, prev_ws)
                if not light_audit.is_consistent:
                    for conflict in light_audit.conflict_points:
                        reporter.report(f"⚠️ 軽量監査警告: {conflict}", "warning")
                audit_log_data = light_audit.model_dump()
                audit_log_data = OutputSanitizer.normalize_metadata(audit_log_data)

            total_len += len(final_content)

            stress_delta = int(final_meta.get("stress_delta", 0) / 10)
            current_stress = max(0, current_stress_for_episode + stress_delta)
            await self.engine.repo.update_book_cumulative_stress(book_id, current_stress)

            if reporter:
                reporter.update_progress(
                    ep_num - start_ep + 1, end_ep - start_ep + 1,
                    f"第{ep_num}話 完了 ({len(final_content)}文字) [ストレス→{current_stress}]"
                )

            await self.engine.repo.create_chapter(
                book_id, ep_num,
                p_dump.get("title", f"第{ep_num}話"),
                final_content,
                final_meta.get("summary", ""),
                None,
                f"Completed [stress:{current_stress}]" + (f" [Audit:{audit_log_data.get('audit_type', 'L')}]" if not audit_log_data.get('is_consistent', True) else ""),
                final_meta.get("next_world_state", {}),
                {"note": "Ultimate Pipeline + StressLoop", "audit_log": audit_log_data},
                time.strftime('%Y-%m-%dT%H:%M:%S'),
            )
            await self.engine.repo.update_plot_status_stress_love(
                book_id, ep_num, current_stress, final_meta.get("love_delta", 0)
            )

        return total_len

    async def generate_episodes_pipeline(self, book_id: int, start_ep: int, end_ep: int, passion: float, target_word_count: int, reporter=None, is_easy_mode: bool = False) -> Tuple[int, List[Dict[str, Any]]]:
        # キューサイズを広げ、先行してプロットを作れるようにする
        plot_queue = asyncio.Queue() # Unbounded queue for maximum throughput
        from config import GlobalConfig
        cfg = GlobalConfig()
        configured_concurrency = cfg.get("max_concurrency", 0) # 0 means auto
        write_sem_value = configured_concurrency if configured_concurrency > 0 else (2 if is_easy_mode else 1)
        write_sem  = asyncio.Semaphore(write_sem_value)

        total_chars = [0] # Use a list to allow modification in nested async functions
        stop_event = asyncio.Event()
        bible = await self.engine.repo.get_latest_bible(book_id)
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") if bible else {}
        arcs = settings.get("arcs", [])

        async def plotter():
            failed_plot_generations = [] # Collect failures from plotter
            # プロットと執筆済みチャプターをスキャンして修復が必要なものを特定
            existing_plots = await self.engine.repo.get_plots_between(book_id, start_ep, end_ep)
            chapters = await self.engine.repo.get_all_non_anchor_chapters(book_id)
            chap_nums = {c.ep_num for c in chapters}

            plots_to_generate = []
            for ep in range(start_ep, end_ep + 1):
                if ep in chap_nums:
                    continue # 既に本文がある場合はスキップ

                # チャプターがない場合、既存プロットの有無を確認
                plot = next((p for p in existing_plots if p.ep_num == ep), None)
                if plot and plot.detailed_blueprint and len(plot.detailed_blueprint) > 100:
                    # プロットがあるなら即座に執筆キューへ
                    await plot_queue.put(plot)
                    if reporter: reporter.report(f"📂 既存プロットを利用: 第{ep}話", "info")
                else:
                    # プロットもないなら生成対象へ
                    plots_to_generate.append(ep)

            # プロット生成自体を並行タスクとして管理する
            plot_tasks = []
            try:
                async def _produce_plot(ep_num):
                    if stop_event.is_set(): return
                    if reporter: reporter.report(f"🗺️ プロット生成中: 第{ep_num}話", "info")
                    try:
                        p_res = await self.engine.planner.expand_plots(book_id, [ep_num], arcs, reporter=reporter, force=False)
                        if p_res:
                            if p_res[0].get("status") == "failed_plot_gen": # Check for failure indicator
                                failed_plot_generations.append(p_res[0])
                                if reporter: reporter.report(f"⚠️ プロット生成失敗: 第{ep_num}話 ({p_res[0]['error_message']})", "warning")
                            else:
                                await plot_queue.put(p_res[0])
                                if reporter: reporter.report(f"✅ プロット生成完了: 第{ep_num}話", "info")
                    except asyncio.CancelledError:
                        logger.info(f"Plot generation for ep {ep_num} was cancelled.")
                        failed_plot_generations.append({"ep_num": ep_num, "status": "cancelled", "error_message": "Plot generation cancelled."})
                    except Exception as e:
                        logger.error(f"Error producing plot for ep {ep_num}: {e}")
                        failed_plot_generations.append({"ep_num": ep_num, "status": "failed_plot_gen", "error_message": str(e)})

                # すべての話数のプロット生成を並行して開始（内部でSemaphore(4)が効く）
                tasks = [asyncio.create_task(_produce_plot(ep)) for ep in plots_to_generate]
                plot_tasks.extend(tasks)
                await asyncio.gather(*tasks)

                await plot_queue.put(None)
            except Exception as e:
                stop_event.set()
                await plot_queue.put(e)
                if reporter:
                    reporter.report(f"Plotter Error (Critical): {e}", "error")
            finally:
                # Add any remaining failed plot generations to the queue for the writer to process
                for failure in failed_plot_generations:
                    await plot_queue.put(failure)
                # Ensure the writer knows plotter is done
                await plot_queue.put(None)

        failed_episodes = [] # Collect all failed episodes (plot gen or writing)

        async def writer():
            try:
                while True:
                    item = await plot_queue.get()
                    if stop_event.is_set() or (reporter and reporter.state.should_stop()): break
                    if item is None: break

                    if isinstance(item, dict) and item.get("status") == "failed_plot_gen":
                        failed_episodes.append(item)
                        if reporter: reporter.report(f"⚠️ 第{item['ep_num']}話の執筆をスキップ (プロット生成失敗)", "warning")
                        plot_queue.task_done()
                        continue
                    elif isinstance(item, Exception): # If a raw exception somehow gets through
                        failed_episodes.append({"ep_num": "Unknown", "status": "critical_error", "error_message": str(item)})
                        if reporter: reporter.report(f"🚨 パイプラインで予期せぬエラーが発生: {item}", "error")
                        stop_event.set() # Stop the pipeline on critical unhandled exception
                        continue

                    # ep_num を確実に取得
                    ep = item.get("ep_num") if isinstance(item, dict) else getattr(item, 'ep_num', None)
                    if ep is None: continue # Should not happen with proper plotter failure handling

                    if reporter: reporter.report(f"✍️ 本文執筆中: 第{ep}話", "info")
                    async with write_sem:
                        chars_count = await self.generate_episodes(book_id, ep, ep, passion, target_word_count, True, reporter, is_easy_mode=is_easy_mode)
                        total_chars[0] += chars_count
                    plot_queue.task_done()
            except Exception as e:
                logger.error(f"Writer Error at ep {ep if 'ep' in locals() else 'unknown'}: {e}")
                failed_episodes.append({"ep_num": ep, "status": "failed_writing", "error_message": str(e)})
                if is_easy_mode:
                    if reporter: reporter.report(f"⚠️ 第{ep}話の執筆中にエラーが発生しましたが、続行します。", "warning")
                    # キューの状態を正常化して続行
                    try: plot_queue.task_done()
                    except: pass
                else:
                    stop_event.set()
                    if reporter: reporter.report(f"Writer Error: {e}", "error")
                    raise

        try:
            await asyncio.gather(plotter(), writer())
        except Exception as e:
            logger.error(f"Pipeline final error: {e}")

        return total_chars[0], failed_episodes

    async def analyze_and_import_chapter(self, book_id: int, ep_num: int, content: str, do_refine: bool = False) -> Dict[str, Any]:
        try:
            cleaned_content = self.engine.formatter.format_for_kakuyomu(content)
            book  = await self.engine.repo.get_book(book_id)
            if not book:
                return {"error": "作品が見つかりません"}
            plot  = await self.engine.repo.get_plot(book_id, ep_num)
            prompt = self.engine.pm.build_analyze_import_chapter_prompt(cleaned_content, EpisodeDraft)
            res = await self.engine._generate_json(MODEL_PLANNING, prompt, response_schema=EpisodeDraft)
            if res.success:
                data = res.metadata
                # 保存処理
                await self.engine.repo.create_chapter(
                    book_id, ep_num, data.get("title", f"第{ep_num}話"),
                    cleaned_content, data.get("summary", ""),
                    None, "Imported", data.get("next_world_state", {}),
                    {"note": "Imported via analyze_and_import_chapter"},
                    time.strftime('%Y-%m-%dT%H:%M:%S')
                )
                return data
            return {"error": "分析に失敗しました"}
        except Exception as e:
            return {"error": str(e)}

