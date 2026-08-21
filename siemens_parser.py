import os
import re
import csv
import zipfile
import base64
import io
from base_parser import BaseParser

class SiemensParser(BaseParser):
    def scan_directory(self, parent_path, progress_callback=None, force_rescan=False):
        """Scans the directory tree for test logs and returns a list of parsed runs."""
        if not parent_path or not os.path.exists(parent_path):
            return []
            
        from scan_cache import ScanCache
        cache = ScanCache(parent_path, "siemens", force_rescan)
        runs = []
        # Level 1: Part Number (e.g. TF80418)
        try:
            p1_items = os.listdir(parent_path)
        except Exception as e:
            print(f"Error reading parent path: {e}")
            return []

        # Collect all candidates first to support progress reporting
        candidates = []
        for p1 in p1_items:
            p1_path = os.path.join(parent_path, p1)
            if not os.path.isdir(p1_path):
                continue
            # Level 2: Date (e.g. Tuesday_June 09_2026)
            try:
                p2_items = os.listdir(p1_path)
            except Exception:
                continue
            for p2 in p2_items:
                p2_path = os.path.join(p1_path, p2)
                if not os.path.isdir(p2_path):
                    continue
                # Level 3: Zip files, folders, or loose CSV files
                try:
                    p3_items = os.listdir(p2_path)
                except Exception:
                    continue
                for p3 in p3_items:
                    p3_path = os.path.join(p2_path, p3)
                    is_zip = zipfile.is_zipfile(p3_path)
                    is_dir = os.path.isdir(p3_path)
                    is_csv = p3_path.lower().endswith('.csv')
                    if is_zip or is_dir or is_csv:
                        candidates.append((p3_path, p1, is_zip, is_dir, is_csv, p3))

        total = len(candidates)
        all_candidate_paths = [c[0] for c in candidates]
        
        completed = 0
        if progress_callback and total > 0:
            progress_callback(0, total, f"Starting scanning of {total} items...")

        for p3_path, p1, is_zip, is_dir, is_csv, p3 in candidates:
            # Check cache first
            cached_runs = cache.get_cached_runs(p3_path)
            if cached_runs is not None:
                runs.extend(cached_runs)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, f"Loaded from cache: {p3}")
                continue

            meta = self._parse_run_name(p3)
            if not meta:
                completed += 1
                continue

            # Add part number from Level 1 folder
            meta["part_number"] = p1
            meta["path"] = p3_path
            meta["is_zip"] = is_zip

            # Read steps eagerly
            steps = []
            try:
                all_lines = []
                if is_zip:
                    all_lines = self._read_all_csvs_from_zip(p3_path)
                elif is_dir:
                    all_lines = self._read_all_csvs_from_folder(p3_path)
                elif is_csv:
                    all_lines = self._read_all_loose_csvs(p3_path)
                    
                if all_lines:
                    for line_set in all_lines:
                        steps.extend(self._parse_csv_rows(line_set))
            except Exception as e:
                print(f"Error parsing steps for {p3}: {e}")

            meta["steps"] = steps
            runs.append(meta)
            cache.update_file(p3_path, [meta])
            
            completed += 1
            if progress_callback:
                progress_callback(completed, total, f"Parsed {completed}/{total} items: {p3}")

        # Save cache
        cache.clean_and_save(all_candidate_paths)
                    
        # Consolidate/merge duplicate runs (e.g. from loose page CSV files)
        merged_runs = {}
        for r in runs:
            key = (r["customer"], r["part_num_3rd"], r["serial"], r["date_time"], r["status"])
            if key not in merged_runs:
                merged_runs[key] = r
            else:
                existing = merged_runs[key]
                if len(r["steps"]) > len(existing["steps"]):
                    existing["steps"] = r["steps"]
                    existing["path"] = r["path"]
                    existing["is_zip"] = r["is_zip"]
                    existing["file_ext"] = r["file_ext"]
                    if "suffix" in r:
                        existing["suffix"] = r["suffix"]
                        
        runs = list(merged_runs.values())
                    
        # Calculate cumulative tests per serial number
        serial_counts = {}
        for r in runs:
            s = r["serial"]
            serial_counts[s] = serial_counts.get(s, 0) + 1
            
        for r in runs:
            r["cumulative_tests"] = serial_counts[r["serial"]]
            
        # Sort runs by date descending as default
        runs.sort(key=lambda x: x["date_time"], reverse=True)
        return runs

    def get_run_steps(self, path):
        """Reads and parses the steps of a specific log file on-demand."""
        if not path or not os.path.exists(path):
            return []
        steps = []
        try:
            is_zip = zipfile.is_zipfile(path)
            is_dir = os.path.isdir(path)
            is_csv = path.lower().endswith('.csv')
            
            all_lines = []
            if is_zip:
                all_lines = self._read_all_csvs_from_zip(path)
            elif is_dir:
                all_lines = self._read_all_csvs_from_folder(path)
            elif is_csv:
                all_lines = self._read_all_loose_csvs(path)
                
            if all_lines:
                for line_set in all_lines:
                    steps.extend(self._parse_csv_rows(line_set))
        except Exception as e:
            print(f"Error parsing steps for {path}: {e}")
        return steps

    def generate_barcode(self, path, is_zip, serial, date_time):
        """Reads all page CSVs from a run, collects FAIL steps, and returns
        a formatted text block + base64-encoded QR code PNG."""
        try:
            import qrcode
            from PIL import Image
        except ImportError:
            return {"error": "qrcode/Pillow not installed. Run: pip install qrcode pillow"}

        # Gather lines from all page CSVs
        all_lines = []
        try:
            if is_zip:
                all_lines = self._read_all_csvs_from_zip(path)
            elif os.path.isdir(path):
                all_lines = self._read_all_csvs_from_folder(path)
            else:
                # Find all loose CSV pages in the same directory belonging to the same run
                all_lines = self._read_all_loose_csvs(path)
        except Exception as e:
            return {"error": f"Failed to read run files: {e}"}

        # Parse all FAIL steps from collected lines
        fail_steps = []
        seen_steps = set()
        for line_set in all_lines:
            reader = csv.reader(line_set)
            for row in reader:
                parsed = self._parse_single_row(row)
                if parsed and parsed["type"] == "step" and parsed["result"] == "FAIL":
                    step_name = parsed["name"]
                    # De-duplicate by step name
                    if step_name in seen_steps:
                        continue
                    seen_steps.add(step_name)
                    
                    low_limit = parsed["low_limit"]
                    high_limit = parsed["high_limit"]
                    # Clean limits for pg2 where they are "---N/A---" or empty
                    has_limits = (low_limit and "N/A" not in low_limit and low_limit != "") or (high_limit and "N/A" not in high_limit and high_limit != "")
                    limits = f"[{low_limit}-{high_limit}]" if has_limits else ""
                    
                    expected = parsed["expected"]
                    # Clean expected: if it is empty or "---N/A---", do not output "Expected:..."
                    has_expected = expected and expected != "---N/A---" and expected != ""
                    expected_str = f" Expected:{expected}" if has_expected else ""
                    
                    measured = parsed["measured"]
                    raw_result = parsed["raw_result"]
                    
                    fail_steps.append(f"{step_name}={measured}{limits}{expected_str} {raw_result}")

        # Build text block
        header = f"SN:{serial} {date_time}"
        if fail_steps:
            text_block = header + "\n" + "\n".join(fail_steps)
        else:
            text_block = header + "\nNo failed steps found."

        # Generate QR code
        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=4,
            )
            qr.add_data(text_block)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            return {"error": f"QR generation failed: {e}"}

        return {"text": text_block, "qr_base64": qr_b64}

    def _page_sort_key(self, filename):
        match = re.search(r'_pg(\d+)', filename, re.IGNORECASE)
        if match:
            return (0, int(match.group(1)), filename)
        return (1, 0, filename)

    def _read_all_csvs_from_zip(self, zip_path):
        """Returns a list of line-lists, one per CSV file in the zip."""
        results = []
        with zipfile.ZipFile(zip_path, 'r') as z:
            names = sorted(z.namelist(), key=self._page_sort_key)
            for name in names:
                if name.lower().endswith('.csv'):
                    content = z.read(name).decode('utf-8-sig', errors='ignore')
                    results.append(content.splitlines())
        return results

    def _read_all_csvs_from_folder(self, folder_path):
        """Returns a list of line-lists, one per CSV file in the folder."""
        results = []
        try:
            names = os.listdir(folder_path)
        except Exception:
            return results
        names = sorted(names, key=self._page_sort_key)
        for name in names:
            if name.lower().endswith('.csv'):
                filepath = os.path.join(folder_path, name)
                try:
                    with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
                        results.append(f.readlines())
                except Exception:
                    pass
        return results

    def _read_all_loose_csvs(self, path):
        """Finds all loose CSV pages in the same directory that belong to the same run and returns their line-lists."""
        results = []
        parent_dir = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        
        meta = self._parse_run_name(filename)
        if meta and meta.get("suffix"):
            suffix = meta["suffix"]
            base_name = name[:-len(suffix)]
        else:
            base_name = re.sub(r'_pg\d+$', '', name, flags=re.IGNORECASE)
            
        try:
            siblings = os.listdir(parent_dir)
        except Exception:
            siblings = [filename]
            
        matched_files = []
        for s in siblings:
            if s.lower().endswith('.csv'):
                s_name, _ = os.path.splitext(s)
                s_meta = self._parse_run_name(s)
                if s_meta and s_meta.get("suffix"):
                    s_base = s_name[:-len(s_meta["suffix"])]
                else:
                    s_base = re.sub(r'_pg\d+$', '', s_name, flags=re.IGNORECASE)
                    
                if s_base.lower() == base_name.lower():
                    matched_files.append(s)
                    
        matched_files = sorted(matched_files, key=self._page_sort_key)
        
        for f in matched_files:
            filepath = os.path.join(parent_dir, f)
            try:
                with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as file:
                    results.append(file.readlines())
            except Exception:
                pass
        return results

    def _parse_run_name(self, run_name):
        # Strip extension if any
        name, ext = os.path.splitext(run_name)
        
        # Try Format B first (since it is more specific with double underscore and 12-digit datetime)
        match_b = re.match(r"^(.+)_([^_]+)_([^_]+)__(\d{12})_(PASS|FAIL)(.*)$", name, re.IGNORECASE)
        if match_b:
            customer = match_b.group(1)
            part_num_3rd = match_b.group(2)
            serial = match_b.group(3)
            datetime_str = match_b.group(4)
            status = match_b.group(5).upper()
            suffix = match_b.group(6)
            
            # Format date: MMDDYYYYHHMM -> YYYY-MM-DD HH:MM
            month = datetime_str[0:2]
            day = datetime_str[2:4]
            year = datetime_str[4:8]
            hour = datetime_str[8:10]
            minute = datetime_str[10:12]
            formatted_date = f"{year}-{month}-{day} {hour}:{minute}"
            
            return {
                "customer": customer,
                "part_num_3rd": part_num_3rd,
                "serial": serial,
                "date_time": formatted_date,
                "raw_date": datetime_str[0:8],
                "raw_time": datetime_str[8:12],
                "status": status,
                "file_ext": ext,
                "suffix": suffix
            }
            
        # Try Format A
        match_a = re.match(r"^(.+)_([^_]+)_([^_]+)_(\d{8})_(\d{4})_(PASS|FAIL)(.*)$", name, re.IGNORECASE)
        if match_a:
            customer = match_a.group(1)
            part_num_3rd = match_a.group(2)
            serial = match_a.group(3)
            date_str = match_a.group(4)
            time_str = match_a.group(5)
            status = match_a.group(6).upper()
            suffix = match_a.group(7)
            
            # Format date: MMDDYYYY -> YYYY-MM-DD
            # Time: HHMM -> HH:MM
            month = date_str[0:2]
            day = date_str[2:4]
            year = date_str[4:]
            hour = time_str[0:2]
            minute = time_str[2:4]
            formatted_date = f"{year}-{month}-{day} {hour}:{minute}"
            
            return {
                "customer": customer,
                "part_num_3rd": part_num_3rd,
                "serial": serial,
                "date_time": formatted_date,
                "raw_date": date_str,
                "raw_time": time_str,
                "status": status,
                "file_ext": ext,
                "suffix": suffix
            }
            
        # Fallback to split-based parsing for backward compatibility
        parts = name.split('_')
        if len(parts) >= 6:
            pass_fail = parts[-1].upper()
            if pass_fail in ("PASS", "FAIL"):
                time_str = parts[-2]
                date_str = parts[-3]
                serial = parts[-4]
                part_num_3rd = parts[-5]
                customer = "_".join(parts[:-5])
                
                if len(date_str) == 8 and len(time_str) == 4:
                    month = date_str[0:2]
                    day = date_str[2:4]
                    year = date_str[4:]
                    hour = time_str[0:2]
                    minute = time_str[2:4]
                    formatted_date = f"{year}-{month}-{day} {hour}:{minute}"
                else:
                    formatted_date = f"Unknown ({date_str} {time_str})"
                    
                return {
                    "customer": customer,
                    "part_num_3rd": part_num_3rd,
                    "serial": serial,
                    "date_time": formatted_date,
                    "raw_date": date_str,
                    "raw_time": time_str,
                    "status": pass_fail,
                    "file_ext": ext,
                    "suffix": ""
                }
                
        return None

    def _parse_single_row(self, row):
        if not row:
            return None
        first_col = row[0].strip()
        if not first_col:
            return None
            
        # Check if it is a pg2 step row (lengths between 3 and 5, with result in row[2])
        if len(row) >= 3 and len(row) < 6:
            result_col = row[2].strip().upper()
            if "PASS" in result_col:
                result = "PASS"
            elif "FAIL" in result_col:
                result = "FAIL"
            else:
                return None
                
            return {
                "type": "step",
                "name": first_col.strip(".").strip(),
                "low_limit": "---N/A---",
                "high_limit": "---N/A---",
                "expected": "---N/A---",
                "measured": row[1].strip(),
                "result": result,
                "raw_result": row[2].strip()
            }
            
        # Check if it is a section header (starts and ends with "..")
        is_section = first_col.startswith("..") and first_col.endswith("..")
        if is_section:
            section_name = first_col.strip(".").strip()
            return {
                "type": "section",
                "name": section_name
            }
            
        # Check if it is a pg3/pg4 step row (len(row) >= 6)
        if len(row) >= 6:
            raw_result = row[5].strip().upper()
            if "PASS" in raw_result:
                result = "PASS"
            elif "FAIL" in raw_result:
                result = "FAIL"
            else:
                return None
                
            return {
                "type": "step",
                "name": first_col,
                "low_limit": row[1].strip(),
                "high_limit": row[2].strip(),
                "expected": row[3].strip(),
                "measured": row[4].strip(),
                "result": result,
                "raw_result": row[5].strip()
            }
            
        return None

    def _parse_csv_rows(self, csv_lines):
        steps = []
        reader = csv.reader(csv_lines)
        for row in reader:
            parsed = self._parse_single_row(row)
            if parsed:
                steps.append(parsed)
        return steps
