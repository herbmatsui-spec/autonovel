# AutoNovel

小説生成エンジンのリポジトリ。

## 構成
- `src/`      : FastAPI バックエンド
- `frontend/` : Vite + React フロントエンド
- `tests/`    : pytest
- `scripts/`  : 検証スクリプト

## 開発
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
cd frontend; npm install; cd ..
.\scripts\verify_all.ps1
```

## 実行
`アプリ起動.bat` または `docker compose up --build`
