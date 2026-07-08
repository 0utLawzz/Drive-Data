"""
tests/test_parser.py — Parser unit tests for Data-Shaper V2.

Run with:  python -m pytest tests/test_parser.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scanner.parser import parse_case_folder, parse_client_folder, validate_client_folder

# ---------------------------------------------------------------------------
# Case folder parsing tests
# ---------------------------------------------------------------------------

class TestParseCaseFolder:

    def test_full_format_c_suffix(self):
        """A020-003 Trendy Toys 747478 C32"""
        case_no, case_name, tm_no, class_code = parse_case_folder("A020-003 Trendy Toys 747478 C32")
        assert case_no    == "A020-003"
        assert case_name  == "Trendy Toys"
        assert tm_no      == "747478"
        assert class_code == "C32"

    def test_full_format_class_word(self):
        """A020-003 Trendy Toys 747478 Class 32"""
        case_no, case_name, tm_no, class_code = parse_case_folder("A020-003 Trendy Toys 747478 Class 32")
        assert case_no    == "A020-003"
        assert case_name  == "Trendy Toys"
        assert tm_no      == "747478"
        assert class_code == "C32"

    def test_no_tm_no(self):
        """A020-003 Trendy-Toys — no TM number"""
        case_no, case_name, tm_no, class_code = parse_case_folder("A020-003 Trendy-Toys")
        assert case_no    == "A020-003"
        assert case_name  == "Trendy-Toys"
        assert tm_no      == ""
        assert class_code == ""

    def test_case_no_only(self):
        """A020-003 — bare case number only"""
        case_no, case_name, tm_no, class_code = parse_case_folder("A020-003")
        assert case_no    == "A020-003"
        assert case_name  == ""
        assert tm_no      == ""
        assert class_code == ""

    def test_hyphenated_case_no(self):
        """A-020-003 Trendy Toys"""
        case_no, case_name, tm_no, class_code = parse_case_folder("A-020-003 Trendy Toys")
        assert case_no   == "A-020-003"
        assert case_name == "Trendy Toys"
        assert tm_no     == ""

    def test_x_prefix(self):
        """X015-001 My Brand 555555 C5"""
        case_no, case_name, tm_no, class_code = parse_case_folder("X015-001 My Brand 555555 C5")
        assert case_no    == "X015-001"
        assert case_name  == "My Brand"
        assert tm_no      == "555555"
        assert class_code == "C5"

    def test_multiword_brand(self):
        """B030-007 Cool Brand Name 123456 C10"""
        case_no, case_name, tm_no, class_code = parse_case_folder("B030-007 Cool Brand Name 123456 C10")
        assert case_no    == "B030-007"
        assert case_name  == "Cool Brand Name"
        assert tm_no      == "123456"
        assert class_code == "C10"

    def test_empty_string(self):
        """Empty folder name — should return all empty, not crash."""
        case_no, case_name, tm_no, class_code = parse_case_folder("")
        assert case_no == case_name == tm_no == class_code == ""

    def test_completely_malformed(self):
        """Garbage input — should return all empty, not crash."""
        case_no, case_name, tm_no, class_code = parse_case_folder("??? @@@@ ###")
        assert case_no == case_name == tm_no == class_code == ""

    def test_class_uppercase_normalised(self):
        """c32 (lowercase) should normalise to C32."""
        _, _, _, class_code = parse_case_folder("A001-001 Brand 111111 c32")
        assert class_code == "C32"

    def test_class_without_tm_no(self):
        """Class code should be extracted even when TM number is absent."""
        case_no, case_name, tm_no, class_code = parse_case_folder("A020-003 Trendy Toys C32")
        assert case_no    == "A020-003"
        assert tm_no      == ""
        assert class_code == "C32"
        # case_name should NOT include the class token
        assert "C32" not in case_name

    def test_class_word_format_without_tm_no(self):
        """'Class 32' format should work even when TM number is absent."""
        _, _, tm_no, class_code = parse_case_folder("A020-003 Brand Class 32")
        assert tm_no      == ""
        assert class_code == "C32"


# ---------------------------------------------------------------------------
# Client folder parsing tests
# ---------------------------------------------------------------------------

class TestParseClientFolder:

    def test_standard_format(self):
        """A-020 Brandex International"""
        num, name = parse_client_folder("A-020 Brandex International")
        assert num  == "A-020"
        assert name == "Brandex International"

    def test_code_only(self):
        """B-005 — no client name"""
        num, name = parse_client_folder("B-005")
        assert num  == "B-005"
        assert name == ""

    def test_no_code(self):
        """random folder — no recognisable code"""
        num, name = parse_client_folder("random folder")
        assert num  == ""
        assert name == "random folder"

    def test_empty(self):
        num, name = parse_client_folder("")
        assert num  == ""
        assert name == ""


# ---------------------------------------------------------------------------
# Validation warnings tests
# ---------------------------------------------------------------------------

class TestValidateClientFolder:

    def test_valid_folder_no_warnings(self):
        result = validate_client_folder("A-020 Brandex")
        assert result["warnings"] == []

    def test_missing_code_generates_warning(self):
        result = validate_client_folder("just a name folder")
        assert any("client code" in w.lower() for w in result["warnings"])

    def test_missing_name_generates_warning(self):
        result = validate_client_folder("A-020")
        assert any("empty" in w.lower() for w in result["warnings"])
