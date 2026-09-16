from src.backend.database.uow import UnitOfWork

def test_unit_of_work_initialization():
    uow = UnitOfWork()
    assert uow.session is None
    assert hasattr(uow, 'outbox_service')
