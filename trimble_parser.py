import os
import re
import base64
import io
from concurrent.futures import ThreadPoolExecutor
from base_parser import BaseParser

class TrimbleParser(BaseParser):
    def scan_directory(self, parent_path, progress_callback=None, force_rescan=False):
        """Scans the directory tree for Trimble txt logs and returns a list of parsed runs."""
        if not parent_path or not os.path.exists(parent_path):
            return []
            
        from scan_cache import ScanCache
        cache = ScanCache(parent_path, "trimble", force_rescan)
        runs = []
        try:
            p1_items = os.listdir(parent_path)
        except Exception as e:
            print(f"Error reading parent path: {e}")
            return []

        # Find all log/txt files and extract metadata
        files_to_parse = []  # list of (meta, f_path) for FAIL runs
        all_candidate_paths = []
        
        for p1 in p1_items:
            p1_path = os.path.join(parent_path, p1)
            if not os.path.isdir(p1_path):
                continue
                
            # Scan all .txt and .log files directly inside the Level 1 directory
            try:
                files = os.listdir(p1_path)
            except Exception:
                continue

            for f in files:
                if not f.lower().endswith(('.txt', '.log')):
                    continue
                    
                f_path = os.path.join(p1_path, f)
                all_candidate_paths.append(f_path)

                # Check cache first
                cached_runs = cache.get_cached_runs(f_path)
                if cached_runs is not None:
                    runs.extend(cached_runs)
                    continue

                meta = self._parse_run_name(f)
                if not meta:
                    continue
                    
                # Part number and customer are hardcoded for Trimble runs
                meta["part_number"] = "105080-D"
                meta["part_num_3rd"] = "105080-D"
                meta["customer"] = "Trimble"
                meta["path"] = f_path
                meta["is_zip"] = False
                
                if meta["status"] == "FAIL":
                    files_to_parse.append((meta, f_path))
                else:
                    meta["steps"] = []
                    runs.append(meta)
                    cache.update_file(f_path, [meta])

        # Parse FAIL runs in parallel
        if files_to_parse:
            def parse_one(item):
                meta, f_path = item
                try:
                    with open(f_path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                        lines = file_obj.readlines()
                    steps = self._parse_log_lines(lines)
                except Exception as e:
                    print(f"Error parsing steps for {f_path}: {e}")
                    steps = []
                meta["steps"] = steps
                return meta, f_path

            completed = 0
            total = len(files_to_parse)
            with ThreadPoolExecutor() as executor:
                results = executor.map(parse_one, files_to_parse)
                for meta, f_path in results:
                    runs.append(meta)
                    cache.update_file(f_path, [meta])
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, f"Parsed failed log {completed}/{total}: {os.path.basename(f_path)}")

        # Save cache
        cache.clean_and_save(all_candidate_paths)
                
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
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                lines = file_obj.readlines()
            return self._parse_log_lines(lines)
        except Exception as e:
            print(f"Error parsing steps for {path}: {e}")
            return []

    def generate_barcode(self, path, is_zip, serial, date_time):
        """Reads the Trimble plain text log file, collects FAIL steps, and returns
        a formatted text block + base64-encoded QR code PNG."""
        try:
            import qrcode
            from PIL import Image
        except ImportError:
            return {"error": "qrcode/Pillow not installed. Run: pip install qrcode pillow"}

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            return {"error": f"Failed to read run file: {e}"}

        # Gather all rows where the word "FAIL" (case-insensitive) occurs,
        # excluding the "Extended Receiver ID" line, with multiple spaces collapsed.
        fail_steps = []
        for line in lines:
            line_stripped = line.strip()
            if re.search(r'fail', line_stripped, re.IGNORECASE):
                if "Extended Receiver ID" not in line_stripped:
                    # Collapse multiple consecutive spaces and/or tabs into a single space
                    cleaned_line = re.sub(r'[ \t]{2,}', ' ', line_stripped)
                    fail_steps.append(cleaned_line)

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

    def _parse_run_name(self, run_name):
        # Strip extension if any
        name, ext = os.path.splitext(run_name)
        
        # Regex to match [Serial]_[TestType]_[YYYY]_[MM]_[DD]_[HH]_[mm]_[Status]
        match = re.match(r"^([^_]+)_([^_]+)_(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(PASS|FAIL)$", name, re.IGNORECASE)
        if match:
            serial = match.group(1)
            test_type = match.group(2)
            year = match.group(3)
            month = match.group(4)
            day = match.group(5)
            hour = match.group(6)
            minute = match.group(7)
            status = match.group(8).upper()
            
            formatted_date = f"{year}-{month}-{day} {hour}:{minute}"
            
            return {
                "customer": "Trimble",
                "part_num_3rd": "105080-D",
                "serial": serial,
                "date_time": formatted_date,
                "status": status,
                "file_ext": ext,
                "test_type": test_type
            }
        return None

    def _parse_allowable(self, allowable_str):
        allowable_str = allowable_str.strip()
        if allowable_str.startswith('='):
            allowable_str = allowable_str[1:].strip()
        
        low_limit = "---N/A---"
        high_limit = "---N/A---"
        expected = "---N/A---"
        
        # Check for +/- format: e.g. "17.40 +/- 1.00" or "1.500 +/- 0.300"
        plus_minus_match = re.search(r"^([+-]?\d*\.?\d+)\s*\+/-\s*([+-]?\d*\.?\d+)(.*)$", allowable_str)
        if plus_minus_match:
            val_str = plus_minus_match.group(1)
            tol_str = plus_minus_match.group(2)
            unit = plus_minus_match.group(3).strip()
            
            expected = val_str + (f" {unit}" if unit else "")
            try:
                val = float(val_str)
                tol = float(tol_str)
                # Try to preserve decimal precision
                dec_places = 0
                if '.' in val_str:
                    dec_places = len(val_str.split('.')[1])
                elif '.' in tol_str:
                    dec_places = len(tol_str.split('.')[1])
                
                low = val - tol
                high = val + tol
                
                if dec_places > 0:
                    low_limit = f"{low:.{dec_places}f}"
                    high_limit = f"{high:.{dec_places}f}"
                else:
                    low_limit = str(int(low) if low.is_integer() else low)
                    high_limit = str(int(high) if high.is_integer() else high)
                    
                if unit:
                    low_limit += f" {unit}"
                    high_limit += f" {unit}"
            except Exception:
                low_limit = f"{val_str} - {tol_str}" + (f" {unit}" if unit else "")
                high_limit = f"{val_str} + {tol_str}" + (f" {unit}" if unit else "")
                
        # Check for > or >= format: e.g. "> 1.4V"
        elif allowable_str.startswith('>=') or allowable_str.startswith('>'):
            op = '>=' if allowable_str.startswith('>=') else '>'
            low_limit = allowable_str[len(op):].strip()
            
        # Check for < or <= format: e.g. "< 3.30"
        elif allowable_str.startswith('<=') or allowable_str.startswith('<'):
            op = '<=' if allowable_str.startswith('<=') else '<'
            high_limit = allowable_str[len(op):].strip()
            
        else:
            # Just expected discrete value: e.g. "On", "Off", "26201048"
            expected = allowable_str

        return low_limit, high_limit, expected

    def _parse_step_line(self, line):
        line = line.strip()
        if "Result =" not in line:
            return None
            
        # Split by Allowable and Result =
        match_allowable = re.search(r'\bAllowable\b\s*=?\s*', line, re.IGNORECASE)
        if not match_allowable:
            return None
            
        allowable_start = match_allowable.start()
        allowable_end = match_allowable.end()
        
        left_part = line[:allowable_start].strip()
        right_part = line[allowable_end:].strip()
        
        match_result = re.search(r'\bResult\b\s*=\s*', right_part, re.IGNORECASE)
        if not match_result:
            return None
            
        result_start = match_result.start()
        result_end = match_result.end()
        
        allowable_str = right_part[:result_start].strip()
        result_str = right_part[result_end:].strip()
        
        name = ""
        measured = ""
        
        match_value = re.search(r'\bValue\b\s*=\s*', left_part, re.IGNORECASE)
        if match_value:
            val_start = match_value.start()
            val_end = match_value.end()
            name = left_part[:val_start].strip()
            measured = left_part[val_end:].strip()
        else:
            if '=' in left_part:
                parts = left_part.split('=', 1)
                name = parts[0].strip()
                measured = parts[1].strip()
            else:
                name = left_part
                measured = ""
                
        if not name:
            name = "Value"
            
        result_upper = result_str.upper()
        if "PASS" in result_upper:
            result = "PASS"
        elif "FAIL" in result_upper:
            result = "FAIL"
        else:
            result = "PASS"

        # Suppress Extended Receiver ID failures as it is expected to mismatch on some units
        if name.strip() == "Extended Receiver ID":
            result = "PASS"
            
        low_limit, high_limit, expected = self._parse_allowable(allowable_str)
        
        return {
            "type": "step",
            "name": name,
            "low_limit": low_limit,
            "high_limit": high_limit,
            "expected": expected,
            "measured": measured,
            "result": result,
            "raw_result": result_str
        }

    def _parse_log_lines(self, lines):
        steps = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            # Check for section header: ends with : PASS, : FAIL, or : DISABLED (case insensitive)
            match_header = re.search(r':\s*(PASS|FAIL|DISABLED)$', line_str, re.IGNORECASE)
            if match_header:
                section_name = line_str[:match_header.start()].strip()
                steps.append({
                    "type": "section",
                    "name": section_name
                })
                continue
                
            # Check for test step
            if "Result =" in line_str or "result =" in line_str:
                parsed = self._parse_step_line(line_str)
                if parsed:
                    steps.append(parsed)
                    
        return steps
