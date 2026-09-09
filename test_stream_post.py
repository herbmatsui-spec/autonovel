from fastapi.testclient import TestClient
from src.backend import database
from src.backend.server import app
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import src.backend.database as db_module
import src.backend.database.core as db_core
from src.infrastructure.database.models.base_orm import Base

# Create a temporary SQLite database
tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
db_path = Path(tmp.name)
test_url = f"sqlite:///{db_path}"

# Override the database
test_engine = create_engine(test_url, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
db_module.engine = test_engine
db_module.SessionLocal = TestSessionLocal
db_core.DATABASE_URL = test_url
db_core._sync_engine = None
db_core._sync_session_factory = None

# Create tables
import src.backend.database.models  # noqa
import src.infrastructure.database.models  # noqa
Base.metadata.create_all(test_engine)

# Override the dependency
app.dependency_overrides[db_module.get_db] = lambda: TestSessionLocal()

client = TestClient(app)

# Test the POST endpoint
payload = {
    "current_chapter": "森の奥で主人公は剣を抜いた。",
    "chapter_history": [],
    "character_params": {},
    "content_length_limit": 2000,
}
resp = client.post("/easy_mode/generate/stream", json=payload)
print("Status code:", resp.status_code)
print("Headers:", resp.headers)
print("Text (first 500 chars):", resp.text[:500])

# Cleanup
app.dependency_overrides.clear()
test_engine.dispose()
os.unlink(db_path)