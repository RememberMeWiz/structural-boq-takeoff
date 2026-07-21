import unittest

from member_size_extractor import parse_size, parse_tag


class MemberSizeParsingTests(unittest.TestCase):
    def test_dimension_formats(self):
        self.assertEqual(parse_size("400 x 900"), {
            "size_text": "400x900", "width_mm": 400.0, "depth_mm": 900.0
        })
        self.assertEqual(parse_size("2B-1 350×750"), {
            "size_text": "350×750", "width_mm": 350.0, "depth_mm": 750.0
        })

    def test_tags_exclude_dimension_components(self):
        self.assertEqual(parse_tag("2B-1 400x900", "beam"), "2B-1")
        self.assertEqual(parse_tag("C-28", "column"), "C-28")
        self.assertEqual(parse_tag("1B137 350x750", "beam"), "1B137")
        self.assertEqual(parse_tag("2C61", "column"), "2C61")


if __name__ == "__main__":
    unittest.main()
