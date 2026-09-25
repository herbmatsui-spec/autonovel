import unittest
from src.services.exporters.commercial_manuscript_exporter import CommercialManuscriptExporter

class TestCommercialManuscriptExporter(unittest.TestCase):
    def test_export(self):
        exporter = CommercialManuscriptExporter()
        episodes = [
            {"title": "第1話 タイトル1", "content": "本文1"},
            {"title": "第2話 タイトル2", "content": "本文2"},
        ]
        result = exporter.export(episodes)
        self.assertIn("目次", result)
        self.assertIn("第1話 タイトル1", result)
        self.assertIn("本文1", result)
        self.assertIn("あとがき", result)
        self.assertIn("登場人物紹介", result)

if __name__ == '__main__':
    unittest.main()