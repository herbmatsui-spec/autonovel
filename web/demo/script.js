// AutoNovel かんたんモード デモ メインロジック

document.addEventListener('DOMContentLoaded', () => {
  // DOM要素の取得
  const tutorialBtn = document.getElementById('tutorialBtn');
  const tutorialStatus = document.getElementById('tutorialStatus');
  const mainContent = document.getElementById('mainContent');
  const stepElements = document.querySelectorAll('.step');
  const stepIndicators = document.querySelectorAll('.step-step');
  
  // ボタン要素
  const gachaBtn = document.getElementById('gachaBtn');
  const selectGachaBtn = document.getElementById('selectGachaBtn');
  const gachaResult = document.getElementById('gachaResult');
  const gachaCard = document.getElementById('gachaCard');
  
  const reversePlotForm = document.getElementById('reversePlotForm');
  const plotBtn = document.getElementById('plotBtn');
  const plotResult = document.getElementById('plotResult');
  const episodesContainer = document.getElementById('episodesContainer');
  const nextToCharBtn = document.getElementById('nextToCharBtn');
  
  const streamingBtn = document.getElementById('streamingBtn');
  const generationBtn = document.getElementById('generationBtn');
  const stopStreamingBtn = document.getElementById('stopStreamingBtn');
  const streamingPreview = document.getElementById('streamingPreview');
  const streamingContent = document.getElementById('streamingContent');
  const charCount = document.getElementById('charCount');
  
  const exportBtn = document.getElementById('exportBtn');
  const promoteBtn = document.getElementById('promoteBtn');
  const restartBtn = document.getElementById('restartBtn');
  const studioBtn = document.getElementById('studioBtn');
  
  const resultTabs = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  const generatedContent = document.getElementById('generatedContent');
  const suggestionsContent = document.getElementById('suggestionsContent');
  
  // キャラ設定フォーム要素
  const charName = document.getElementById('charName');
  const charPersonality = document.getElementById('charPersonality');
  const charAbility = document.getElementById('charAbility');
  const charGenre = document.getElementById('charGenre');
  const openingText = document.getElementById('openingText');
  
  // チュートリアルモードのトグル
  tutorialBtn.addEventListener('click', () => {
    DEMO_STATE.tutorialMode = !DEMO_STATE.tutorialMode;
    tutorialStatus.textContent = DEMO_STATE.tutorialMode ? 'ON' : 'OFF';
    tutorialBtn.classList.toggle('active', DEMO_STATE.tutorialMode);
    
    // Bodyにチュートリアルモードクラスを追加/削除
    document.body.classList.toggle('tutorial-mode', DEMO_STATE.tutorialMode);
    
    if (DEMO_STATE.tutorialMode) {
      Utils.showToast('チュートリアルモードが有効になりました。各ステップで詳細な説明が表示されます。', 'info');
    } else {
      Utils.showToast('チュートリアルモードが無効になりました。', 'info');
    }
  });
  
  // ステップナビゲーション
  const showStep = (stepNumber) => {
    // すべてのステップを非表示
    stepElements.forEach(step => {
      step.classList.remove('active', 'fade-in');
      step.classList.add('hidden');
    });
    
    // すべてのインジケーターをリセット
    stepIndicators.forEach((indicator, index) => {
      indicator.classList.remove('active', 'completed');
      if (index < stepNumber - 1) {
        indicator.classList.add('completed');
      } else if (index === stepNumber - 1) {
        indicator.classList.add('active');
      }
    });
    
    // 指定されたステップを表示
    const targetStep = document.getElementById(`step${stepNumber}`);
    if (targetStep) {
      targetStep.classList.remove('hidden');
      targetStep.classList.add('active', 'fade-in');
      DEMO_STATE.currentStep = stepNumber;
    }
  };
  
  // 次のステップに進む
  const nextStep = () => {
    if (DEMO_STATE.currentStep < 5) {
      showStep(DEMO_STATE.currentStep + 1);
    }
  };
  
  // 前のステップに戻る
  const prevStep = () => {
    if (DEMO_STATE.currentStep > 1) {
      showStep(DEMO_STATE.currentStep - 1);
    }
  };
  
  // 企画ガチャ機能
  gachaBtn.addEventListener('click', async () => {
    gachaBtn.disabled = true;
    gachaBtn.innerHTML = '<span class="loading"></span> ガチャを引いています...';
    
    // ランダムにジャンルを選択
    const genres = Object.keys(GACHA_RESULTS);
    const selectedGenre = Utils.randomItem(genres);
    const plans = GACHA_RESULTS[selectedGenre];
    const selectedPlan = Utils.randomItem(plans);
    
    // ローディングシミュレーション
    await Utils.delay(1500);
    
    // 結果表示
    gachaCard.innerHTML = `
      <h4>${selectedPlan.title}</h4>
      <p><strong>概要:</strong> ${selectedPlan.logline}</p>
      <p><strong>主人公:</strong> ${selectedPlan.protagonist_summary}</p>
      <p><strong>魅力点:</strong> <span class="charm-point">${selectedPlan.charm_point}</span></p>
    `;
    
    gachaResult.classList.remove('hidden');
    gachaResult.classList.add('fade-in');
    selectGachaBtn.dataset.planId = selectedPlan.plan_id;
    selectGachaBtn.dataset.planData = JSON.stringify(selectedPlan);
    
    gachaBtn.disabled = false;
    gachaBtn.textContent = '🎲 企画ガチャを引く';
    
    if (DEMO_STATE.tutorialMode) {
      Utils.showToast('ガチャの結果が表示されました。この案を選択するか、もう一度引き直すことができます。', 'info', 4000);
    }
  });
  
  selectGachaBtn.addEventListener('click', () => {
    const planData = JSON.parse(selectGachaBtn.dataset.planData);
    DEMO_STATE.selectedGachaPlan = planData;
    
    // キャラ設定に反映（ガチャ結果から）
    charName.value = planData.protagonist_summary.split(' - ')[0] || 'アルト';
    charPersonality.value = planData.protagonist_summary.split(' - ')[1] || '熱血・仲間思い・冷静な判断力';
    charAbility.value = '古代魔導剣術・時空間把握'; // デフォルト
    charGenre.value = 'ファンタジー'; // デフォルト、実際はガチャ結果から推測すべきだが簡略化
    
    // 冒頭テキストにシードを挿入
    const seedText = `【プラン: ${planData.title}】\n概要: ${planData.logline}\n魅力点: ${planData.charm_point}`;
    openingText.value = seedText;
    
    Utils.showToast('ガチャ結果をキャラクター設定に反映しました。', 'success');
    nextStep(); // 次のステップ（プロット作成）に進む
  });
  
  // 逆算プロットビルダー
  reversePlotForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const genre = document.getElementById('genreSelect').value;
    const protagonist = document.getElementById('protagonistInput').value;
    const goal = document.getElementById('goalInput').value;
    const obstacle = document.getElementById('obstacleInput').value;
    
    if (!genre || !protagonist || !goal || !obstacle) {
      Utils.showToast('すべての項目を入力してください。', 'error');
      return;
    }
    
    plotBtn.disabled = true;
    plotBtn.innerHTML = '<span class="loading"></span> プロットを生成しています...';
    
    // ローディングシミュレーション
    await Utils.delay(2000);
    
    // サンプルプロットデータを使用（実際は入力に基づいて生成）
    episodesContainer.innerHTML = '';
    SAMPLE_PLOT_DATA.episodes.forEach((episode, index) => {
      const episodeElement = document.createElement('div');
      episodeElement.className = 'episode-card';
      episodeElement.innerHTML = `
        <h4>
          <span class="episode-number">第${episode.ep_num}話</span>
          <span class="episode-title">${episode.title}</span>
          ${episode.is_catharsis ? '<span class="is-catharsis">クライマックス</span>' : ''}
        </h4>
        <p class="episode-summary">${episode.one_line_summary}</p>
      `;
      episodesContainer.appendChild(episodeElement);
    });
    
    plotResult.classList.remove('hidden');
    plotResult.classList.add('fade-in');
    
    plotBtn.disabled = false;
    plotBtn.textContent = '🔮 プロット構造を生成';
    
    // キャラ設定に反映
    charGenre.value = genre;
    charName.value = protagonist.split('、')[0] || protagonist.split(' ')[0] || '主人公';
    charPersonality.value = protagonist.includes('、') ? protagonist.split('、')[1] : protagonist;
    charAbility.value = '特殊能力'; // デフォルト
    
    if (DEMO_STATE.tutorialMode) {
      Utils.showToast('プロット構造が生成されました。次のステップでキャラ設定を確認しましょう。', 'info', 4000);
    }
    
    nextStep(); // 次のステップ（キャラ設定）に進む
  });
  
  // リアルタイム速筆（ストリーミング）
  let streamingInterval = null;
  let streamedText = '';
  
  streamingBtn.addEventListener('click', async () => {
    if (DEMO_STATE.isStreaming) {
      // ストリーミングを停止
      clearInterval(streamingInterval);
      DEMO_STATE.isStreaming = false;
      streamingBtn.textContent = '⚡ リアルタイム速筆 (SSE)';
      stopStreamingBtn.disabled = true;
      
      if (DEMO_STATE.tutorialMode) {
        Utils.showToast('ストリーミングを停止しました。', 'info');
      }
      return;
    }
    
    // 入力チェック
    if (!charName.value.trim() || !openingText.value.trim()) {
      Utils.showToast('キャラクター名と冒頭テキストを入力してください。', 'error');
      return;
    }
    
    DEMO_STATE.isStreaming = true;
    streamingBtn.textContent = '⚡ ストリーミング執筆中...';
    stopStreamingBtn.disabled = false;
    streamedText = openingText.value || ''; // 現在のテキストから開始
    
    // キャラクター情報を取得
    const charInfo = {
      name: charName.value,
      personality: charPersonality.value,
      ability: charAbility.value,
      genre: charGenre.value
    };
    
    // ストリーミングシミュレーション開始
    streamingInterval = setInterval(async () => {
      // ランダムなテキストを追加（実際はAPI呼び出しのシミュレーション）
      const additions = [
        " 今日も冒険は続く。",
        " アルトは剣を構え、先へと進んだ。",
        " 前方から微かな光が見えてくる。",
        " 「さあ、行くぞ！」リナが叫んだ。",
        " 古代の遺跡の入り口が見えてきた。",
        " 二人はゆっくりとその中へと足を踏み入れた。",
        " 壁に刻まれた謎の記号が、ほんのりと光っている。",
        " これは一体何を意味するのだろうか？",
        " アルトは直感的に、これが重要だと感じた。",
        " ここで休憩を取って、明日に備えよう。"
      ];
      
      const addition = Utils.randomItem(additions);
      streamedText += addition;
      
      // 表示を更新
      streamingContent.textContent = streamedText;
      charCount.textContent = `${streamedText.length.toLocaleString()} 文字`;
      
      // スクロールを最新位置に
      streamingContent.scrollTop = streamingContent.scrollHeight;
      
      // 一定長に達したら停止（デモなので適切な長さで停止）
      if (streamedText.length > 800) {
        clearInterval(streamingInterval);
        DEMO_STATE.isStreaming = false;
        streamingBtn.textContent = '⚡ リアルタイム速筆 (SSE)';
        stopStreamingBtn.disabled = true;
        
        if (DEMO_STATE.tutorialMode) {
          Utils.showToast('ストリーミングが完了しました。かんたん執筆開始で本格的な生成を試してみてください。', 'success');
        }
      }
    }, 800); // 0.8秒ごとに更新
  });
  
  stopStreamingBtn.addEventListener('click', () => {
    clearInterval(streamingInterval);
    DEMO_STATE.isStreaming = false;
    streamingBtn.textContent = '⚡ リアルタイム速筆 (SSE)';
    stopStreamingBtn.disabled = true;
    streamingContent.textContent = streamedText; // 最終状態を保持
    
    if (DEMO_STATE.tutorialMode) {
      Utils.showToast('ストリーミングを停止しました。', 'info');
    }
  });
  
  // かんたん執筆開始
  generationBtn.addEventListener('click', async () => {
    // 入力チェック
    if (!charName.value.trim()) {
      Utils.showToast('キャラクター名を入力してください。', 'error');
      return;
    }
    
    // 状態を更新
    DEMO_STATE.isGenerating = true;
    generationBtn.disabled = true;
    generationBtn.innerHTML = '<span class="loading"></span> 執筆中...';
    
    // キャラ設定オブジェクトを作成
    DEMO_STATE.character = {
      name: charName.value,
      personality: charPersonality.value,
      ability: charAbility.value,
      genre: charGenre.value
    };
    
    DEMO_STATE.openingText = openingText.value;
    
    // ローディングシミュレーション
    await Utils.delay(3000); // 3秒かけて「生成」
    
    // 生成結果を設定
    DEMO_STATE.generatedText = SAMPLE_GENERATED_TEXT;
    DEMO_STATE.suggestions = SAMPLE_SUGGESTIONS;
    
    // 結果表示
    await Utils.typeWriter(generatedContent, DEMO_STATE.generatedText, 30);
    
    // サジェスト表示
    suggestionsContent.innerHTML = '';
    DEMO_STATE.suggestions.forEach((suggestion, index) => {
      const suggestionElement = document.createElement('div');
      suggestionElement.className = 'suggestion-item';
      suggestionElement.innerHTML = `
        <h4>
          <span class="suggestion-number">${index + 1}</span>
          <span class="suggestion-text">${suggestion}</span>
        </h4>
      `;
      suggestionsContent.appendChild(suggestionElement);
    });
    
    // 生成結果ステップに進む
    generationBtn.disabled = false;
    generationBtn.textContent = '🪄 かんたん執筆開始';
    DEMO_STATE.isGenerating = false;
    
    Utils.showToast('本文の生成が完了しました！次話へのAI提案を確認してください。', 'success');
    
    // 自動的に結果ステップに進む（タブは手動で切り替える）
    showStep(4);
  });
  
  // 結果タブ切り替え
  resultTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // すべてのタブをリセット
      resultTabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      // クリックされたタブをアクティベート
      tab.classList.add('active');
      const targetTab = tab.dataset.tab;
      document.querySelector(`.tab-content[data-tab="${targetTab}"]`).classList.add('active');
    });
  });
  
  // エクスポート機能
  exportBtn.addEventListener('click', () => {
    if (!DEMO_STATE.generatedText) {
      Utils.showToast('まずは本文を生成してください。', 'error');
      return;
    }
    
    exportBtn.disabled = true;
    exportBtn.innerHTML = '<span class="loading"></span> パッケージを生成しています...';
    
    // ZIP生成シミュレーション
    Utils.delay(1500).then(() => {
      // ダミーのZIPデータを作成（実際はBlobを生成）
      const zipData = `AutoNovel デモ エクスポート\n\n生成日時: ${new Date().toLocaleString()}\n\n=== 生成本文 ===\n${DEMO_STATE.generatedText}\n\n=== 次話提案 ===\n${DEMO_STATE.suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n=== キャラクター設定 ===\n名前: ${DEMO_STATE.character.name}\n性格: ${DEMO_STATE.character.personality}\n能力: ${DEMO_STATE.character.ability}\nジャンル: ${DEMO_STATE.character.genre}\n\n=== ご利用ありがとう ===\nこのデモはAutoNovelのかんたんモードを体験するためのものです。\n本物のAutoNovelでは、より高品質なAI生成と多機能が利用できます。`;
      
      // Blobを作成してダウンロード
      const blob = new Blob([zipData], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `autonovel-demo-export_${Date.now()}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      exportBtn.disabled = false;
      exportBtn.textContent = '📦 納品パッケージ (ZIP) ダウンロード';
      
      Utils.showToast('エクスポートが完了しました！テキストファイルとしてダウンロードされました。', 'success');
      
      if (DEMO_STATE.tutorialMode) {
        Utils.showToast('エクスポート機能の説明：実際のAutoNovelではZIP形式で本文・設定・プロット・JSONデータがパッケージされます。', 'info', 5000);
      }
    });
  });
  
  // 上級者Studioへ昇格
  promoteBtn.addEventListener('click', () => {
    if (!DEMO_STATE.generatedText) {
      Utils.showToast('まずは本文を生成してください。', 'error');
      return;
    }
    
    promoteBtn.disabled = true;
    promoteBtn.innerHTML = '<span class="loading"></span> 昇格処理中...';
    
    Utils.delay(1000).then(() => {
      promoteBtn.disabled = false;
      promoteBtn.textContent = '🚀 上級者Studioへ昇格';
      
      Utils.showToast('上級者Studioへの昇格が完了しました！（デモでは実際の遷移は行われません）', 'success');
      
      // 完了ステップに進む
      showStep(5);
      
      if (DEMO_STATE.tutorialMode) {
        Utils.showToast('上級者Studioでは、詳細なプロット編集、キャラクター管理、マルチメディア機能などが利用できます。', 'info', 5000);
      }
    });
  });
  
  // 最初からやり直す
  restartBtn.addEventListener('click', () => {
    // 状態をリセット
    DEMO_STATE.currentStep = 1;
    DEMO_STATE.selectedGachaPlan = null;
    DEMO_STATE.character = { name: "", personality: "", ability: "", genre: "" };
    DEMO_STATE.openingText = "";
    DEMO_STATE.generatedText = "";
    DEMO_STATE.suggestions = [];
    DEMO_STATE.isGenerating = false;
    DEMO_STATE.isStreaming = false;
    
    // フォームをリセット
    charName.value = '';
    charPersonality.value = '';
    charAbility.value = '';
    charGenre.value = 'ファンタジー';
    openingText.value = '';
    
    // UIをリセット
    document.getElementById('step1').classList.remove('hidden');
    document.getElementById('step1').classList.add('active', 'fade-in');
    stepElements.forEach((step, index) => {
      if (index > 0) {
        step.classList.remove('active', 'fade-in');
        step.classList.add('hidden');
      }
    });
    
    stepIndicators.forEach((indicator, index) => {
      indicator.classList.remove('active', 'completed');
      if (index === 0) {
        indicator.classList.add('active');
      }
    });
    
    // 結果エリアをクリア
    gachaResult.classList.add('hidden');
    plotResult.classList.add('hidden');
    streamingPreview.classList.add('hidden');
    generatedContent.textContent = '';
    suggestionsContent.innerHTML = '';
    resultTabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    document.querySelector('.tab-content[data-tab="generated"]').classList.add('active');
    resultTabs[0].classList.add('active');
    
    // ボタン状態をリセット
    gachaBtn.disabled = false;
    gachaBtn.textContent = '🎲 企画ガチャを引く';
    plotBtn.disabled = false;
    plotBtn.textContent = '🔮 プロット構造を生成';
    streamingBtn.textContent = '⚡ リアルタイム速筆 (SSE)';
    generationBtn.disabled = false;
    generationBtn.textContent = '🪄 かんたん執筆開始';
    exportBtn.disabled = false;
    exportBtn.textContent = '📦 納品パッケージ (ZIP) ダウンロード';
    promoteBtn.disabled = false;
    promoteBtn.textContent = '🚀 上級者Studioへ昇格';
    if (streamingInterval) {
      clearInterval(streamingInterval);
      streamingInterval = null;
    }
    stopStreamingBtn.disabled = true;
    
    Utils.showToast('最初からやり直しました。新しい物語を始めましょう！', 'success');
    
    if (DEMO_STATE.tutorialMode) {
      Utils.showToast('チュートリアルモードが有効です。各ステップで詳細なガイドが表示されます。', 'info');
    }
  });
  
  // 上級者Studio体験ボタン（実際のリンクへ）
  studioBtn.addEventListener('click', () => {
    Utils.showToast('実際のAutoNovel上級者Studioは、https://herbmatsui-spec.github.io/autonovel/ で体験できます。', 'info');
    // 実際のプロダクトサイトへリンク（デモなのでアラートで代替）
    // window.open('https://herbmatsui-spec.github.io/autonovel/', '_blank');
  });
  
  // 初期化：最初のステップを表示
  showStep(1);
  
  // キーボードショートカット
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      // エスケープキーでモーダル閉じたり操作をキャンセル
      const modalOverlay = document.querySelector('.modal-overlay');
      if (modalOverlay) {
        modalOverlay.remove();
      }
    }
    
    if (e.key === 'Enter' && e.ctrlKey) {
      // Ctrl+Enterで執筆開始
      if (!DEMO_STATE.isGenerating && !DEMO_STATE.isStreaming) {
        generationBtn.click();
      }
    }
  });
  
  // 初期トースト
  if (!DEMO_STATE.tutorialMode) {
    Utils.showToast('AutoNovel かんたんモード デモへようこそ！「チュートリアルモード」ボタンでステップバイステップのガイドを有効にできます。', 'info', 5000);
  }
});

// デモ状態オブジェクト（グローバルスコープに公開）
window.DEMO_STATE = window.DEMO_STATE || {};