"""システム健全性全機能診断スクリプト (Step 66)。"""
import sys

def check_all_modules():
    print("[1/5] Checking Phase 1 Commercial & UX modules...")
    from src.backend.routers.commercial import PublicationScheduleCreate
    from src.services.conflict_report_service import ConflictReportService
    from src.services.book_score_service import BookScoreService
    print("      -> OK")

    print("[2/5] Checking Phase 2 Image & Audio & EPUB modules...")
    from src.services.illustration.factory import get_image_client
    from src.services.audio.factory import get_audio_client
    from src.services.audio.dialogue_extractor import DialogueExtractor
    from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder
    print("      -> OK")

    print("[3/5] Checking Phase 3 Resilience & Autonomy modules...")
    from src.llm.resilient_gateway import ResilientLLMGateway
    from src.llm.circuit_breaker import LLMCircuitBreaker
    from src.services.graph.networkx_store import NetworkXGraphStore
    from src.services.cost_budget_guard import CostBudgetGuard
    print("      -> OK")

    print("[4/5] Checking Storage & Pure EPUB Packer...")
    from src.services.exporters.pure_epub_packer import PureEpubPacker
    packer = PureEpubPacker()
    b = packer.build_epub_bytes()
    assert b.startswith(b"PK")
    print("      -> OK")

    print("[5/5] Checking Server & Routers wiring...")
    from src.backend.server import app
    assert app is not None
    print("      -> OK")

    print("\n==========================================")
    print("[SUCCESS] ALL SYSTEM HEALTH CHECKS PASSED (100%)")
    print("==========================================")

if __name__ == "__main__":
    check_all_modules()
