import unittest

from parser_pipeline.dom_mapper import _classify


class DomMapperTests(unittest.TestCase):
    def test_layer_classification(self):
        self.assertEqual(_classify("Beam Line", "B-1")[0], "beam")
        self.assertEqual(_classify("Column Label", "C-1")[0], "column")

    def test_unknown_is_reviewable(self):
        kind, confidence = _classify("ANNO", "")
        self.assertEqual(kind, "other")
        self.assertLess(confidence, 0.5)


if __name__ == "__main__":
    unittest.main()
