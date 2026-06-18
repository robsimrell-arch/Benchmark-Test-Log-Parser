import os
import unittest
import shutil
import tempfile
import zipfile
from trimble_parser import TrimbleParser
from siemens_parser import SiemensParser

class TestTrimbleParser(unittest.TestCase):
    def setUp(self):
        self.parser = TrimbleParser()

    def test_run_name_parsing(self):
        filename = "26201048_RFPERF_2026_06_17_10_19_FAIL.log"
        res = self.parser._parse_run_name(filename)
        self.assertIsNotNone(res)
        self.assertEqual(res["customer"], "Trimble")
        self.assertEqual(res["part_num_3rd"], "105080-D")
        self.assertEqual(res["serial"], "26201048")
        self.assertEqual(res["date_time"], "2026-06-17 10:19")
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(res["test_type"], "RFPERF")

    def test_parse_allowable(self):
        # Format 1: +/-
        low, high, exp = self.parser._parse_allowable("= 17.40 +/-  1.00")
        self.assertEqual(low, "16.40")
        self.assertEqual(high, "18.40")
        self.assertEqual(exp, "17.40")

        # Format 2: > or >=
        low, high, exp = self.parser._parse_allowable("> 1.4V")
        self.assertEqual(low, "1.4V")
        self.assertEqual(high, "---N/A---")
        self.assertEqual(exp, "---N/A---")

        # Format 3: discrete value
        low, high, exp = self.parser._parse_allowable("On")
        self.assertEqual(low, "---N/A---")
        self.assertEqual(high, "---N/A---")
        self.assertEqual(exp, "On")

    def test_scan_directory_trimble(self):
        # Create a temp dir structure simulating Trimble logs
        tmp_dir = tempfile.mkdtemp()
        try:
            sub_dir = os.path.join(tmp_dir, "Run1")
            os.makedirs(sub_dir)
            log_content = """Fail
Serial Number: 26201048
PCB Number: K2526000000000115A
Part Number: 000000-00
Load serial number: PASS
     Value =        26201048     Allowable =        26201048     Result = PASS
LE5     JAMDET: FAIL
     LE5     JAMDET     Value =         0.023       Allowable = > 1.4V              Result = FAIL
"""
            log_path = os.path.join(sub_dir, "26201048_RFPERF_2026_06_17_10_19_FAIL.log")
            with open(log_path, "w") as f:
                f.write(log_content)

            runs = self.parser.scan_directory(tmp_dir)
            self.assertEqual(len(runs), 1)
            run = runs[0]
            self.assertEqual(run["serial"], "26201048")
            self.assertEqual(run["status"], "FAIL")
            self.assertEqual(run["customer"], "Trimble")
            self.assertEqual(run["part_number"], "105080-D")
            self.assertEqual(len(run["steps"]), 4)
            
            # Verify details (index 3 should be the LE5 JAMDET step)
            step = run["steps"][3]
            self.assertEqual(step["name"], "LE5     JAMDET")
            self.assertEqual(step["result"], "FAIL")
            self.assertEqual(step["measured"], "0.023")
            self.assertEqual(step["low_limit"], "1.4V")
        finally:
            shutil.rmtree(tmp_dir)


class TestSiemensParser(unittest.TestCase):
    def setUp(self):
        self.parser = SiemensParser()

    def test_run_name_parsing_format_a(self):
        filename = "Siemens_TF80418_26200213_06152026_1110_PASS.csv"
        res = self.parser._parse_run_name(filename)
        self.assertIsNotNone(res)
        self.assertEqual(res["customer"], "Siemens")
        self.assertEqual(res["part_num_3rd"], "TF80418")
        self.assertEqual(res["serial"], "26200213")
        self.assertEqual(res["date_time"], "2026-06-15 11:10")
        self.assertEqual(res["status"], "PASS")

    def test_run_name_parsing_format_b(self):
        filename = "Siemens_TF80418_26200213__061520261110_PASS_pg1.csv"
        res = self.parser._parse_run_name(filename)
        self.assertIsNotNone(res)
        self.assertEqual(res["customer"], "Siemens")
        self.assertEqual(res["part_num_3rd"], "TF80418")
        self.assertEqual(res["serial"], "26200213")
        self.assertEqual(res["date_time"], "2026-06-15 11:10")
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["suffix"], "_pg1")

    def test_parse_single_row(self):
        # Step row (pg3/pg4 style)
        row = ["Analog Input Test", "4.8", "5.2", "5.0", "5.01", "PASS"]
        res = self.parser._parse_single_row(row)
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "step")
        self.assertEqual(res["name"], "Analog Input Test")
        self.assertEqual(res["low_limit"], "4.8")
        self.assertEqual(res["high_limit"], "5.2")
        self.assertEqual(res["expected"], "5.0")
        self.assertEqual(res["measured"], "5.01")
        self.assertEqual(res["result"], "PASS")

        # Step row (pg2 style)
        row = ["Power Draw", "150 mA", "FAIL"]
        res = self.parser._parse_single_row(row)
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "step")
        self.assertEqual(res["name"], "Power Draw")
        self.assertEqual(res["measured"], "150 mA")
        self.assertEqual(res["result"], "FAIL")

        # Section header row
        row = ["..Power Rails Verification.."]
        res = self.parser._parse_single_row(row)
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "section")
        self.assertEqual(res["name"], "Power Rails Verification")

    def test_scan_directory_siemens(self):
        # Create a temp dir structure simulating Siemens logs
        tmp_dir = tempfile.mkdtemp()
        try:
            # Level 1: Part Number
            part_dir = os.path.join(tmp_dir, "TF80418")
            # Level 2: Date
            date_dir = os.path.join(part_dir, "Tuesday_June 15_2026")
            os.makedirs(date_dir)

            # Create loose CSV files for pg1 and pg2
            pg1_content = "Analog Input Test,4.8,5.2,5.0,5.01,PASS\n"
            pg2_content = "Power Draw,150 mA,FAIL\n"
            
            pg1_path = os.path.join(date_dir, "Siemens_TF80418_26200213__061520261110_FAIL_pg1.csv")
            pg2_path = os.path.join(date_dir, "Siemens_TF80418_26200213__061520261110_FAIL_pg2.csv")

            with open(pg1_path, "w") as f:
                f.write(pg1_content)
            with open(pg2_path, "w") as f:
                f.write(pg2_content)

            runs = self.parser.scan_directory(tmp_dir)
            # The loose CSVs should be consolidated into 1 merged run
            self.assertEqual(len(runs), 1)
            run = runs[0]
            self.assertEqual(run["serial"], "26200213")
            self.assertEqual(run["part_number"], "TF80418")
            self.assertEqual(run["customer"], "Siemens")
            self.assertEqual(run["status"], "FAIL")
            self.assertEqual(len(run["steps"]), 2)
            
            # Step 1
            self.assertEqual(run["steps"][0]["name"], "Analog Input Test")
            self.assertEqual(run["steps"][0]["result"], "PASS")
            # Step 2
            self.assertEqual(run["steps"][1]["name"], "Power Draw")
            self.assertEqual(run["steps"][1]["result"], "FAIL")
        finally:
            shutil.rmtree(tmp_dir)

if __name__ == '__main__':
    unittest.main()
