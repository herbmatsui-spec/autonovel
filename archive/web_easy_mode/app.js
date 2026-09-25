// Easy Mode フロントエンドロジック

document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generateBtn');
    const progressSection = document.getElementById('progressSection');
    const reviewSection = document.getElementById('reviewSection');
    const progressBar = document.getElementById('progress');
    const progressText = document.getElementById('progressText');
    const previewContent = document.getElementById('previewContent');
    const reviewContent = document.getElementById('reviewContent');
    const downloadTxtBtn = document.getElementById('downloadTxtBtn');
    const downloadZipBtn = document.getElementById('downloadZipBtn');
    const downloadEpubBtn = document.getElementById('downloadEpubBtn');
    const regenerateBtn = document.getElementById('regenerateBtn');

    let jobId = null;
    let pollingInterval = null;

    // フォームバリデーション
    function validateForm() {
        const genre = document.getElementById('genre').value;
        const length = document.getElementById('length').value;
        if (!genre) {
            alert('ジャンルを選択してください');
            return false;
        }
        if (!length || length < 100) {
            alert('目標長さは100文字以上で入力してください');
            return false;
        }
        return true;
    }

    // 生成開始
    generateBtn.addEventListener('click', async function() {
        if (!validateForm()) return;

        const genre = document.getElementById('genre').value;
        const length = document.getElementById('length').value;
        const keywords = document.getElementById('keywords').value;

        try {
            const response = await fetch('/api/easy_mode/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ genre, length, keywords })
            });

            if (!response.ok) {
                throw new Error(`生成開始に失敗しました: ${response.status}`);
            }

            const data = await response.json();
            jobId = data.job_id;
            console.log('ジョブID:', jobId);

            // UIを更新
            document.querySelector('.container').style.display = 'none';
            progressSection.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
            previewContent.innerHTML = '<p>生成を準備中...</p>';

            // ポーリング開始
            startPolling();
        } catch (error) {
            console.error('Error:', error);
            alert('エラーが発生しました: ' + error.message);
        }
    });

    // ポーリング関数
    function startPolling() {
        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/easy_mode/status/${jobId}`);
                if (!response.ok) {
                    throw new Error(`ステータス取得に失敗しました: ${response.status}`);
                }
                const data = await response.json();
                const progress = data.progress || 0;
                const preview = data.preview || '';

                // プログレスバーを更新
                progressBar.style.width = progress + '%';
                progressText.textContent = progress + '%';

                // プレビューを更新
                if (preview) {
                    previewContent.innerHTML = `<p>${preview.replace(/\n/g, '<br>')}</p>`;
                }

                // 完了チェック
                if (progress >= 100) {
                    clearInterval(pollingInterval);
                    await loadResult();
                }
            } catch (error) {
                console.error('Polling error:', error);
                clearInterval(pollingInterval);
                alert('ステータス取得中にエラーが発生しました: ' + error.message);
                // エラー時は初期画面に戻す
                resetUI();
            }
        }, 2000); // 2秒ごとにポーリング
    }

    // 結果を読み込む
    async function loadResult() {
        try {
            const response = await fetch(`/api/easy_mode/result/${jobId}`);
            if (!response.ok) {
                throw new Error(`結果取得に失敗しました: ${response.status}`);
            }
            const data = await response.json();
            const result = data.result || '';

            // レビュー画面を表示
            progressSection.classList.add('hidden');
            reviewSection.classList.remove('hidden');
            reviewContent.innerHTML = `<pre>${result}</pre>`;

            // ダウンロードボタンを有効化
            downloadTxtBtn.disabled = false;
            downloadZipBtn.disabled = false;
            downloadEpubBtn.disabled = false;
        } catch (error) {
            console.error('Error loading result:', error);
            alert('結果の読み込みに失敗しました: ' + error.message);
            resetUI();
        }
    }

    // ダウンロード機能
    downloadTxtBtn.addEventListener('click', function() {
        window.location.href = `/api/easy_mode/download/${jobId}?format=txt`;
    });

    downloadZipBtn.addEventListener('click', function() {
        window.location.href = `/api/easy_mode/download/${jobId}?format=zip`;
    });

    downloadEpubBtn.addEventListener('click', function() {
        window.location.href = `/api/easy_mode/download/${jobId}?format=epub`;
    });

    // 再生成ボタン
    regenerateBtn.addEventListener('click', function() {
        resetUI();
        // フォームをリセット
        document.getElementById('genre').value = '';
        document.getElementById('length').value = '';
        document.getElementById('keywords').value = '';
        document.querySelector('.container').style.display = 'block';
    });

    // UIをリセット
    function resetUI() {
        progressSection.classList.add('hidden');
        reviewSection.classList.add('hidden');
        document.querySelector('.container').style.display = 'block';
        jobId = null;
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }
});