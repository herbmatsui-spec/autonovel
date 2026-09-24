"""
Easy Mode バックエンドAPI
"""

import uuid
import threading
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file, make_response
import os
import json

# ブループrintを作成
easy_mode_bp = Blueprint('easy_mode', __name__)

# ジョブの状態を保存する辞書（実際のアプリケーションではデータベースやRedisを使用）
jobs = {}
jobs_lock = threading.Lock()

# ジョブの有効期限（例: 1時間）
JOB_EXPIRY_HOURS = 1

def cleanup_expired_jobs():
    """期限切れのジョブを削除"""
    now = datetime.now()
    expired_ids = []
    with jobs_lock:
        for job_id, job in jobs.items():
            if now - job['created_at'] > timedelta(hours=JOB_EXPIRY_HOURS):
                expired_ids.append(job_id)
        for job_id in expired_ids:
            del jobs[job_id]

def generate_story_job(job_id, genre, length, keywords):
    """
    バックグラウンドでストーリーを生成する関数
    実際の生成ロジックはここで実装する（プレースホルダー）
    """
    try:
        # ステージ1: 開始
        update_job_status(job_id, 10, "生成を開始しています...")
        time.sleep(1)  # プレースホルダー
        
        # ステージ2: プロット作成
        update_job_status(job_id, 20, "プロットを作成中...")
        time.sleep(2)
        
        # ステージ3: 章ごとに生成（シミュレーション）
        for i in range(1, 6):  # 5章としてシミュレーション
            progress = 20 + (i * 15)  # 20%から95%まで
            update_job_status(job_id, progress, f"章 {i}/5 を生成中...")
            time.sleep(2)  # 各章の生成をシミュレート
            
            # 中間プレビューを更新（実際のアプリケーションではここでプレビューを保存）
            preview = f"これは章 {i} のプレビューです。ジャンル: {genre}, キーワード: {keywords}..."
            with jobs_lock:
                if job_id in jobs:
                    jobs[job_id]['preview'] = preview
        
        # ステージ4: 仕上げ
        update_job_status(job_id, 95, "仕上げ中...")
        time.sleep(1)
        
        # 最終結果を生成（プレースホルダー）
        result = f"""# 生成された小説

**ジャンル**: {genre}
**目標長さ**: {length}文字
**キーワード**: {keywords}

---

これはプレースホルダーの小説です。
実際のアプリケーションでは、ここでLLMを使ってストーリーを生成します。

## 第1章
物語の始まりです。主人公が冒険の旅に出ます。

## 第2章
主人公は仲間と出会い、困難に直面します。

## 第3章
クライマックス：主人公は最大の試練に立ち向かいます。

## 第4章
解決：主人公は目標を達成し、平和を取り戻します。

## 第5章
エピローグ：新たな始まりの予感。

*この小説は {datetime.now().strftime('%Y年%m月%d日')} に生成されました。*
"""
        
        # ジョブを完了状態に更新
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'completed'
                jobs[job_id]['progress'] = 100
                jobs[job_id]['result'] = result
                jobs[job_id]['message'] = '生成が完了しました'
    except Exception as e:
        # エラーが発生した場合
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['error'] = str(e)
                jobs[job_id]['message'] = f'エラーが発生しました: {str(e)}'

def update_job_status(job_id, progress, message):
    """ジョブのステータスを更新"""
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]['progress'] = progress
            jobs[job_id]['message'] = message
            jobs[job_id]['updated_at'] = datetime.now()

# エンドポイント定義

@easy_mode_bp.route('/generate', methods=['POST'])
def generate():
    """生成リクエストを受け付けてジョブIDを返却"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '無効なリクエスト'}), 400
        
        genre = data.get('genre')
        length = data.get('length')
        keywords = data.get('keywords', '')
        
        # バリデーション
        if not genre:
            return jsonify({'error': 'ジャンルは必須です'}), 400
        if not length or length < 100:
            return jsonify({'error': '目標長さは100文字以上でなければなりません'}), 400
        
        # ジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # ジョブを初期化
        with jobs_lock:
            jobs[job_id] = {
                'id': job_id,
                'genre': genre,
                'length': length,
                'keywords': keywords,
                'status': 'processing',
                'progress': 0,
                'message': 'ジョブが作成されました',
                'result': None,
                'preview': '',
                'error': None,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        
        # バックグラウンドで生成を開始
        thread = threading.Thread(target=generate_story_job, args=(job_id, genre, length, keywords))
        thread.daemon = True
        thread.start()
        
        # 期限切れジョブのクリーンアップ（定期的に実行）
        cleanup_expired_jobs()
        
        return jsonify({'job_id': job_id}), 202
    
    except Exception as e:
        return jsonify({'error': f'サーバーエラー: {str(e)}'}), 500

@easy_mode_bp.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    """ジョブの進行状況を取得"""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'error': 'ジョブが見つかりません'}), 404
        
        # 必要なフィールドのみを返す
        return jsonify({
            'job_id': job['id'],
            'status': job['status'],
            'progress': job['progress'],
            'message': job['message'],
            'preview': job.get('preview', '')
        })

@easy_mode_bp.route('/result/<job_id>', methods=['GET'])
def result(job_id):
    """生成結果を取得"""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'error': 'ジョブが見つかりません'}), 404
        
        if job['status'] != 'completed':
            return jsonify({'error': 'ジョブはまだ完了していません', 'status': job['status']}), 400
        
        return jsonify({
            'job_id': job['id'],
            'result': job['result']
        })

@easy_mode_bp.route('/download/<job_id>', methods=['GET'])
def download(job_id):
    """指定された形式でファイルをダウンロード"""
    format_param = request.args.get('format', 'txt').lower()
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'error': 'ジョブが見つかりません'}), 404
        
        if job['status'] != 'completed':
            return jsonify({'error': 'ジョブはまだ完了していません', 'status': job['status']}), 400
        
        result = job['result']
        if not result:
            return jsonify({'error': '結果が見つかりません'}), 404
        
        # 形式に応じてファイルを生成
        if format_param == 'txt':
            # テキストファイル
            response = make_response(result)
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=story_{job_id}.txt'
            return response
        elif format_param == 'zip':
            # ZIPファイル（簡易実装：実際にはzipfileモジュールを使う）
            # ここではプレースホルダーとしてテキストを返すが、実際はZIPを生成すべき
            response = make_response(result)
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = f'attachment; filename=story_{job_id}.zip'
            return response
        elif format_param == 'epub':
            # EPUBファイル（簡易実装）
            response = make_response(result)
            response.headers['Content-Type'] = 'application/epub+zip'
            response.headers['Content-Disposition'] = f'attachment; filename=story_{job_id}.epub'
            return response
        else:
            return jsonify({'error': 'サポートされていない形式です'}), 400

# ブループrintを登録するための関数（アプリケーションファクトリーで使用）
def init_app(app):
    app.register_blueprint(easy_mode_bp, url_prefix='/api/easy_mode')