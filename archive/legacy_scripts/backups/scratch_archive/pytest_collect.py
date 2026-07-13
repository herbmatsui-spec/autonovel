import pytest


class Collector:
    def pytest_collection_finish(self, session):
        for item in session.items:
            print(f"{item.nodeid} -> {item.fspath}")

pytest.main(['--collect-only'], plugins=[Collector()])

