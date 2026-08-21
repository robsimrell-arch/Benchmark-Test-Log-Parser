import os
import unittest
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
import time
from trimble_parser import TrimbleParser
from siemens_parser import SiemensParser
from flying_probe_parser import FlyingProbeParser

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

class TestFlyingProbeParser(unittest.TestCase):
    def setUp(self):
        self.parser = FlyingProbeParser()
        self.ngdx_content = """@B
@
Model : MOGCD34209_A_1.000
Serial : BH1826MOG0008
Date : 5/26/2026 2:27:50 PM
Side: A
Tester: APT-1400F-SL
Operator: Administrator
* PASS *
@
@E
@B
@
Model : MOGCD34209_A_1.000
Serial : BH1826MOG0008
Date : 5/26/2026 2:29:29 PM
Side: B
Tester: APT-1400F-SL
Operator: Administrator
* FAIL *
@
3 R202* 50mO MOGCA44611-000 * 0.2807[O] R 14  11  UPPER 464.3800[O] 10.2291[O]
5 R201* 50mO MOGCA44611-000 * 0.2789[O] R 14   3 UPPER 471.8499[O] 10.1470[O]
1429 R193 50mO MOGCA44611-000 * 0.6986[O] R 14   22 UPPER 2.5225[O] 2.1606[O]
@E"""

        self.ngd_content = """@
* FAIL *

Model:MOGCA66178_A_1.002.SWX (B)
DATE 02/11/26 19:08:21

Test time:56 s
Test ID :TAKAYA-B
User name :bakerlo
@

* GROUP No.1   *
* FAIL *
Serial No.:BH5125MOG1098

000139 "R101*      " "5O         " "MOGM55342K09B10D0R  " "40.95 O  " "409.5 KO " "OPEN   " "1.0 ms" "( +, -, N, N) "    56
000323 "R102       " "3.32KO     " "MOGD55342K07B3E32R  " "4.095 KO " "10.27 MO " "OPEN   " "200.0 ms" "( -,G1, N, +) "    56
@
@
* PASS *

Model:MOGCA66178_A_1.002.SWX2 (B)
DATE 26/03/07 08:49:29

Version No. :V3.0-4e
Test ID :Takaya D
User name :bakerlo
Index :CA66177.D CA9 Format (Bottom Sid
@

* GROUP No.1   *
* PASS *
Serial No.:BH5125MOG1098

@"""

    def test_parse_ngdx_runs(self):
        runs = self.parser._parse_file_content(self.ngdx_content, "BH1826MOG0008.ngdx", "MyProgram", "/dummy/path/BH1826MOG0008.ngdx", ".ngdx")
        self.assertEqual(len(runs), 2)
        
        # Check first run (PASS)
        run1 = runs[0]
        self.assertEqual(run1["serial"], "BH1826MOG0008")
        self.assertEqual(run1["part_number"], "MOGCD34209_A_1.000")
        self.assertEqual(run1["program_name"], "MyProgram")
        self.assertEqual(run1["status"], "PASS")
        self.assertEqual(run1["board_side"], "A")
        self.assertEqual(run1["tester"], "APT-1400F-SL")
        self.assertEqual(run1["date_time"], "2026-05-26 14:27:50")
        self.assertEqual(len(run1["steps"]), 0)

        # Check second run (FAIL)
        run2 = runs[1]
        self.assertEqual(run2["serial"], "BH1826MOG0008")
        self.assertEqual(run2["status"], "FAIL")
        self.assertEqual(run2["board_side"], "B")
        self.assertEqual(run2["date_time"], "2026-05-26 14:29:29")
        self.assertEqual(len(run2["steps"]), 3)

        # Step 1
        s1 = run2["steps"][0]
        self.assertEqual(s1["name"], "R202*")
        self.assertEqual(s1["low_limit"], "0.2807[O]")
        self.assertEqual(s1["high_limit"], "10.2291[O]")
        self.assertEqual(s1["expected"], "50mO")
        self.assertEqual(s1["measured"], "464.3800[O]")
        self.assertEqual(s1["result"], "FAIL")

    def test_parse_ngd_runs(self):
        runs = self.parser._parse_file_content(self.ngd_content, "BH5125MOG1098(B).NGD", "ProgB", "/dummy/path/BH5125MOG1098(B).NGD", ".ngd")
        self.assertEqual(len(runs), 2)

        # Check first run (FAIL)
        run1 = runs[0]
        self.assertEqual(run1["serial"], "BH5125MOG1098")
        self.assertEqual(run1["part_number"], "MOGCA66178_A_1.002.SWX")
        self.assertEqual(run1["program_name"], "ProgB")
        self.assertEqual(run1["status"], "FAIL")
        self.assertEqual(run1["board_side"], "B")
        self.assertEqual(run1["tester"], "TAKAYA-B")
        self.assertEqual(run1["date_time"], "2026-02-11 19:08:21")
        self.assertEqual(len(run1["steps"]), 2)

        # Step 1
        s1 = run1["steps"][0]
        self.assertEqual(s1["name"], "R101*")
        self.assertEqual(s1["low_limit"], "---N/A---")
        self.assertEqual(s1["high_limit"], "40.95 O")
        self.assertEqual(s1["expected"], "5O")
        self.assertEqual(s1["measured"], "409.5 KO")
        self.assertEqual(s1["result"], "FAIL")

        # Check second run (PASS)
        run2 = runs[1]
        self.assertEqual(run2["serial"], "BH5125MOG1098")
        self.assertEqual(run2["part_number"], "MOGCA66178_A_1.002.SWX2")
        self.assertEqual(run2["status"], "PASS")
        self.assertEqual(run2["board_side"], "B")
        self.assertEqual(run2["tester"], "Takaya D")
        self.assertEqual(run2["date_time"], "2026-03-07 08:49:29")
        self.assertEqual(len(run2["steps"]), 0)

    def test_scan_directory_flying_probe(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            sub_dir = os.path.join(tmp_dir, "MOG_PROG")
            os.makedirs(sub_dir)
            
            # Write .ngdx file
            ngdx_path = os.path.join(sub_dir, "BH1826MOG0008.ngdx")
            with open(ngdx_path, "w") as f:
                f.write(self.ngdx_content)

            runs = self.parser.scan_directory(tmp_dir)
            self.assertEqual(len(runs), 2)
            
            # Runs should be sorted by date descending:
            # 5/26/2026 2:29:29 PM (FAIL) is first, 5/26/2026 2:27:50 PM (PASS) is second
            self.assertEqual(runs[0]["status"], "FAIL")
            self.assertEqual(runs[0]["program_name"], "MOG_PROG")
            self.assertEqual(runs[0]["cumulative_tests"], 2)
            
            self.assertEqual(runs[1]["status"], "PASS")
            self.assertEqual(runs[1]["cumulative_tests"], 2)
        finally:
            shutil.rmtree(tmp_dir)

    def test_get_run_steps_flying_probe(self):
        tmp_file = tempfile.mktemp(suffix=".ngdx")
        try:
            with open(tmp_file, "w") as f:
                f.write(self.ngdx_content)

            mtime_val = os.path.getmtime(tmp_file)
            mtime_str = datetime.fromtimestamp(mtime_val).strftime("%Y-%m-%d %H:%M:%S")
            dt = datetime.strptime(mtime_str, "%Y-%m-%d %H:%M:%S")
            date_time_pass = mtime_str
            date_time_fail = (dt + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")

            # Get steps for the PASS run
            steps1 = self.parser.get_run_steps(tmp_file, "BH1826MOG0008", date_time_pass)
            self.assertEqual(len(steps1), 0)

            # Get steps for the FAIL run
            steps2 = self.parser.get_run_steps(tmp_file, "BH1826MOG0008", date_time_fail)
            self.assertEqual(len(steps2), 3)
            self.assertEqual(steps2[0]["name"], "R202*")
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_generate_barcode_flying_probe(self):
        tmp_file = tempfile.mktemp(suffix=".ngdx")
        try:
            with open(tmp_file, "w") as f:
                f.write(self.ngdx_content)

            mtime_val = os.path.getmtime(tmp_file)
            mtime_str = datetime.fromtimestamp(mtime_val).strftime("%Y-%m-%d %H:%M:%S")
            dt = datetime.strptime(mtime_str, "%Y-%m-%d %H:%M:%S")
            date_time_fail = (dt + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")

            res = self.parser.generate_barcode(tmp_file, False, "BH1826MOG0008", date_time_fail)
            self.assertNotIn("error", res)
            self.assertIn("text", res)
            self.assertIn("qr_base64", res)
            
            self.assertIn(f"SN:BH1826MOG0008 {date_time_fail}", res["text"])
            self.assertIn("R202*=464.3800[O][0.2807[O]-10.2291[O]] Expected:50mO FAIL", res["text"])
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

class TestScanCache(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.tmp_dir, "test.ngdx")
        with open(self.file_path, "w") as f:
            f.write("dummy")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)
        cache_dir = ".cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

    def test_cache_save_load(self):
        from scan_cache import ScanCache
        # 1. Save runs to cache
        cache1 = ScanCache(self.tmp_dir, "flying_probe", force_rescan=True)
        dummy_runs = [{"serial": "123", "date_time": "2026-01-01 12:00:00", "path": self.file_path}]
        cache1.update_file(self.file_path, dummy_runs)
        cache1.clean_and_save([self.file_path])

        # 2. Load from cache (incremental scan)
        cache2 = ScanCache(self.tmp_dir, "flying_probe", force_rescan=False)
        cached_runs = cache2.get_cached_runs(self.file_path)
        self.assertIsNotNone(cached_runs)
        self.assertEqual(cached_runs[0]["serial"], "123")

        # 3. Load with force_rescan should bypass
        cache3 = ScanCache(self.tmp_dir, "flying_probe", force_rescan=True)
        cached_runs_force = cache3.get_cached_runs(self.file_path)
        self.assertIsNone(cached_runs_force)

        # 4. Modify file mtime, should return None
        os.utime(self.file_path, (time.time() + 100, time.time() + 100))
        cache4 = ScanCache(self.tmp_dir, "flying_probe", force_rescan=False)
        cached_runs_mod = cache4.get_cached_runs(self.file_path)
        self.assertIsNone(cached_runs_mod)

if __name__ == '__main__':
    # Import time for utime modification in test
    import time
    unittest.main()
