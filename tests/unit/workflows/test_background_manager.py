from src.backend.background import BackgroundTaskManager

def test_background_task_lifecycle():
    manager = BackgroundTaskManager()
    task_id = manager.create_task("generate_novel")
    assert task_id is not None

    manager.update_progress(task_id, 50, "半分完了")
    status = manager.get_status(task_id)
    assert status["progress"] == 50
    assert status["message"] == "半分完了"
