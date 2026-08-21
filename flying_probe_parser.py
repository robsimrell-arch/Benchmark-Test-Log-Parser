import os
import re
import base64
import io
from datetime import datetime
from base_parser import BaseParser

class FlyingProbeParser(BaseParser):
    def scan_directory(self, parent_path, progress_callback=None, force_rescan=False):
        """Scans the directory tree for Flying Probe logs and returns a list of parsed runs."""
        if not parent_path or not os.path.exists(parent_path):
            return []

        from scan_cache import ScanCache
        cache = ScanCache(parent_path, "flying_probe", force_rescan)
        runs = []
        try:
            # Level 1: Program Name folders
            p1_items = os.listdir(parent_path)
        except Exception as e:
            print(f"Error reading parent path: {e}")
            return []

        # Collect all files to parse
        files_to_parse = []
        all_candidate_paths = []
        for p1 in p1_items:
            p1_path = os.path.join(parent_path, p1)
            if not os.path.isdir(p1_path):
                continue

            try:
                files = os.listdir(p1_path)
            except Exception:
                continue

            for f in files:
                f_ext = os.path.splitext(f)[1].lower()
                if f_ext in ('.ngd', '.ngdx'):
                    f_path = os.path.join(p1_path, f)
                    all_candidate_paths.append(f_path)
                    
                    # Check cache first
                    cached_runs = cache.get_cached_runs(f_path)
                    if cached_runs is not None:
                        runs.extend(cached_runs)
                        continue
                        
                    files_to_parse.append((f_path, f, p1, f_ext))

        total_files = len(files_to_parse)
        if total_files == 0:
            # Still save cache to clean up deleted files
            cache.clean_and_save(all_candidate_paths)
            
            # Calculate cumulative tests per serial number
            serial_counts = {}
            for r in runs:
                s = r["serial"]
                serial_counts[s] = serial_counts.get(s, 0) + 1
            for r in runs:
                r["cumulative_tests"] = serial_counts[r["serial"]]
            runs.sort(key=lambda x: x["date_time"], reverse=True)
            return runs

        # Concurrently parse files using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def parse_file(item):
            f_path, f, program_name, f_ext = item
            try:
                mtime_val = os.path.getmtime(f_path)
                mtime_str = datetime.fromtimestamp(mtime_val).strftime("%Y-%m-%d %H:%M:%S")
                with open(f_path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                    content = file_obj.read()
                file_runs = self._parse_file_content(content, f, program_name, f_path, f_ext, file_mtime_str=mtime_str)
                return file_runs, f_path, f
            except Exception as e:
                print(f"Error reading file {f_path}: {e}")
                return [], f_path, f

        completed = 0
        if progress_callback:
            progress_callback(0, total_files, f"Starting scanning of {total_files} files...")

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(parse_file, item): item for item in files_to_parse}
            for future in as_completed(futures):
                file_runs, file_path, filename = future.result()
                runs.extend(file_runs)
                cache.update_file(file_path, file_runs)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_files, f"Parsed {completed}/{total_files} files: {filename}")

        # Save cache
        cache.clean_and_save(all_candidate_paths)

        # Calculate cumulative tests per serial number
        serial_counts = {}
        for r in runs:
            s = r["serial"]
            serial_counts[s] = serial_counts.get(s, 0) + 1

        for r in runs:
            r["cumulative_tests"] = serial_counts[r["serial"]]

        # Sort runs by date descending
        runs.sort(key=lambda x: x["date_time"], reverse=True)
        return runs

    def get_run_steps(self, path, serial=None, date_time=None):
        """Reads and parses the steps of a specific run on-demand."""
        if not path or not os.path.exists(path):
            return []

        try:
            mtime_val = os.path.getmtime(path)
            mtime_str = datetime.fromtimestamp(mtime_val).strftime("%Y-%m-%d %H:%M:%S")
            with open(path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                content = file_obj.read()
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            return []

        f_ext = os.path.splitext(path)[1].lower()
        filename = os.path.basename(path)
        # Parse all runs in this file
        runs = self._parse_file_content(content, filename, "", path, f_ext, file_mtime_str=mtime_str)

        # Find the matching run
        for r in runs:
            # If serial and date_time are provided, match them
            match_serial = serial is None or r["serial"] == serial
            match_date = date_time is None or r["date_time"] == date_time
            if match_serial and match_date:
                return r["steps"]

        # Fallback to returning the first run's steps if no exact match found
        if runs:
            return runs[0]["steps"]
        return []

    def generate_barcode(self, path, is_zip, serial, date_time):
        """Reads the Flying Probe log, collects FAIL steps for the matching run,
        and returns a formatted text block + base64-encoded QR code PNG."""
        try:
            import qrcode
            from PIL import Image
        except ImportError:
            return {"error": "qrcode/Pillow not installed. Run: pip install qrcode pillow"}

        steps = self.get_run_steps(path, serial, date_time)
        fail_steps = []
        for step in steps:
            if step["result"] == "FAIL":
                step_name = step["name"]
                measured = step["measured"]
                low = step["low_limit"]
                high = step["high_limit"]
                expected = step["expected"]

                limits_str = ""
                if low != "---N/A---" or high != "---N/A---":
                    limits_str = f"[{low}-{high}]"

                exp_str = ""
                if expected != "---N/A---" and expected != "":
                    exp_str = f" Expected:{expected}"

                fail_steps.append(f"{step_name}={measured}{limits_str}{exp_str} FAIL")

        header = f"SN:{serial} {date_time}"
        if fail_steps:
            text_block = header + "\n" + "\n".join(fail_steps)
        else:
            text_block = header + "\nNo failed steps found."

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

    def _parse_file_content(self, content, filename, program_name, file_path, file_ext, file_mtime_str=None):
        """Parses the content of a file and returns a list of run dictionaries."""
        from datetime import datetime, timedelta
        
        current_dt = None
        if file_mtime_str:
            try:
                current_dt = datetime.strptime(file_mtime_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        runs = []
        if file_ext == '.ngdx':
            # Split by @B and @E
            blocks = re.findall(r'@B(.*?)@E', content, re.DOTALL | re.IGNORECASE)
            for block in blocks:
                run_dict = self._parse_ngdx_run(block, filename, program_name, file_path, file_ext)
                if run_dict:
                    if current_dt:
                        run_dict["date_time"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
                        current_dt += timedelta(seconds=1)
                    runs.append(run_dict)
        elif file_ext == '.ngd':
            # Split by @ and keep non-empty segments
            segments = [s.strip() for s in content.split('@') if s.strip()]
            # Pairs of (Header, Body)
            for i in range(0, len(segments) - 1, 2):
                header_text = segments[i]
                body_text = segments[i+1]
                run_dict = self._parse_ngd_run(header_text, body_text, filename, program_name, file_path, file_ext)
                if run_dict:
                    if current_dt:
                        run_dict["date_time"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
                        current_dt += timedelta(seconds=1)
                    runs.append(run_dict)
        return runs

    def _parse_ngdx_run(self, block, filename, program_name, file_path, file_ext):
        """Parses a single run block from a .ngdx file."""
        # Split block by @ and keep non-empty
        parts = [p.strip() for p in block.split('@') if p.strip()]
        if not parts:
            return None

        header_text = parts[0]
        body_text = parts[1] if len(parts) > 1 else ""

        # Parse header
        lines = [line.strip() for line in header_text.splitlines() if line.strip()]
        model = ""
        serial = ""
        date_str = ""
        board_side = ""
        tester = ""
        status = "PASS"

        for line in lines:
            if line.startswith('*'):
                if "PASS" in line.upper():
                    status = "PASS"
                elif "FAIL" in line.upper():
                    status = "FAIL"
                continue

            match = re.match(r'^([^:]+)\s*:\s*(.*)$', line)
            if match:
                key = match.group(1).strip().lower()
                val = match.group(2).strip()
                if key == "model":
                    model = val
                elif key == "serial":
                    serial = val
                elif key == "date":
                    date_str = val
                elif key == "side":
                    board_side = val
                elif key == "tester":
                    tester = val

        # Clean serial number and model
        serial = self._clean_serial(serial, filename)
        part_number = self._clean_model(model)
        board_side = self._resolve_board_side(filename, model, board_side)
        date_time = self._parse_and_format_date(date_str)

        # Parse steps from body_text
        steps = []
        if body_text:
            body_lines = [l.strip() for l in body_text.splitlines() if l.strip()]
            for line in body_lines:
                step = self._parse_ngdx_step_line(line)
                if step:
                    steps.append(step)

        return {
            "customer": "Flying Probe",
            "part_number": part_number,
            "part_num_3rd": model,
            "program_name": program_name,
            "serial": serial,
            "date_time": date_time,
            "board_side": board_side,
            "tester": tester,
            "status": status,
            "path": file_path,
            "is_zip": False,
            "file_ext": file_ext,
            "steps": steps
        }

    def _parse_ngd_run(self, header_text, body_text, filename, program_name, file_path, file_ext):
        """Parses a single run from a .ngd file."""
        lines = [line.strip() for line in header_text.splitlines() if line.strip()]
        model = ""
        date_str = ""
        tester = ""
        status = "PASS"

        for line in lines:
            if line.startswith('*'):
                if "PASS" in line.upper():
                    status = "PASS"
                elif "FAIL" in line.upper():
                    status = "FAIL"
                continue

            if line.lower().startswith("model"):
                match = re.match(r'^model\s*:\s*(.*)$', line, re.IGNORECASE)
                if match:
                    model = match.group(1).strip()
            elif line.lower().startswith("date"):
                match = re.match(r'^date\s+(.*)$', line, re.IGNORECASE)
                if match:
                    date_str = match.group(1).strip()
            elif line.lower().startswith("test id"):
                match = re.match(r'^test id\s*:\s*(.*)$', line, re.IGNORECASE)
                if match:
                    tester = match.group(1).strip()

        # Parse serial from body
        serial = ""
        body_lines = [l.strip() for l in body_text.splitlines() if l.strip()]
        for line in body_lines:
            if line.lower().startswith("serial no."):
                match = re.match(r'^serial no\s*:\s*(.*)$', line, re.IGNORECASE)
                if match:
                    serial = match.group(1).strip()
                break

        # Clean serial number and model
        serial = self._clean_serial(serial, filename)
        part_number = self._clean_model(model)
        board_side = self._resolve_board_side(filename, model, "")
        date_time = self._parse_and_format_date(date_str)

        # Parse steps from body
        steps = []
        for line in body_lines:
            if line.count('"') >= 10:
                step = self._parse_ngd_step_line(line)
                if step:
                    steps.append(step)

        return {
            "customer": "Flying Probe",
            "part_number": part_number,
            "part_num_3rd": model,
            "program_name": program_name,
            "serial": serial,
            "date_time": date_time,
            "board_side": board_side,
            "tester": tester,
            "status": status,
            "path": file_path,
            "is_zip": False,
            "file_ext": file_ext,
            "steps": steps
        }

    def _parse_ngdx_step_line(self, line):
        """Parses a failed step line in .ngdx file format."""
        tokens = line.split()
        if len(tokens) < 7:
            return None

        # Locate UPPER or LOWER dynamically
        limit_idx = -1
        limit_type = ""
        for idx, token in enumerate(tokens):
            t_upper = token.upper()
            if t_upper in ("UPPER", "LOWER"):
                limit_idx = idx
                limit_type = t_upper
                break

        if limit_idx == -1 or limit_idx + 2 >= len(tokens):
            return None

        name = tokens[1]
        expected = tokens[2] if tokens[2] != '*' else "---N/A---"
        limit_1 = tokens[5]

        num_1_str = tokens[limit_idx + 1]
        num_2_str = tokens[limit_idx + 2]

        try:
            num_1_val = float(re.sub(r'[^\d.-]', '', num_1_str))
            num_2_val = float(re.sub(r'[^\d.-]', '', num_2_str))
        except ValueError:
            num_1_val = 0.0
            num_2_val = 0.0

        if limit_type == "UPPER":
            if num_1_val >= num_2_val:
                measured = num_1_str
                high_limit = num_2_str
            else:
                measured = num_2_str
                high_limit = num_1_str
            low_limit = limit_1
        else:  # LOWER
            if num_1_val <= num_2_val:
                measured = num_1_str
                low_limit = num_2_str
            else:
                measured = num_2_str
                low_limit = num_1_str
            high_limit = limit_1

        return {
            "name": name,
            "low_limit": low_limit,
            "high_limit": high_limit,
            "expected": expected,
            "measured": measured,
            "result": "FAIL"
        }

    def _parse_ngd_step_line(self, line):
        """Parses a failed step line in .ngd file format."""
        parts = line.split('"')
        if len(parts) >= 12:
            name = parts[1].strip()
            expected = parts[3].strip()
            high_limit = parts[7].strip()
            measured = parts[9].strip()
            return {
                "name": name,
                "low_limit": "---N/A---",
                "high_limit": high_limit if high_limit else "---N/A---",
                "expected": expected if expected else "---N/A---",
                "measured": measured if measured else "---N/A---",
                "result": "FAIL"
            }
        return None

    def _clean_serial(self, serial, filename):
        """Cleans the serial number, falling back to the filename if necessary."""
        serial = serial.strip()
        if not serial:
            name, _ = os.path.splitext(filename)
            serial = name
        
        serial = re.sub(r'\s*\([AB]\)\s*$', '', serial, flags=re.IGNORECASE)
        serial = re.sub(r'\s*\(Top\)\s*$', '', serial, flags=re.IGNORECASE)
        serial = re.sub(r'\s*\(Bottom\)\s*$', '', serial, flags=re.IGNORECASE)
        return serial.strip()

    def _clean_model(self, model):
        """Cleans the model name by removing board side indicators."""
        clean_model = model.strip()
        clean_model = re.sub(r'\s*\([AB]\)\s*$', '', clean_model, flags=re.IGNORECASE)
        clean_model = re.sub(r'\s*\(Top\)\s*$', '', clean_model, flags=re.IGNORECASE)
        clean_model = re.sub(r'\s*\(Bottom\)\s*$', '', clean_model, flags=re.IGNORECASE)
        return clean_model.strip()

    def _resolve_board_side(self, filename, model, parsed_side):
        """Resolves board side from parsed side, model name, or filename."""
        side = parsed_side.strip().upper()
        if side in ("A", "B"):
            return side

        if "(B)" in model or "Bottom" in model or "BOTTOM" in model:
            return "B"
        if "(A)" in model or "Top" in model or "TOP" in model:
            return "A"

        if "(B)" in filename or "Bottom" in filename or "BOTTOM" in filename:
            return "B"
        if "(A)" in filename or "Top" in filename or "TOP" in filename:
            return "A"

        return ""

    def _parse_and_format_date(self, date_str):
        """Parses date string using multiple patterns and returns format YYYY-MM-DD HH:MM:SS."""
        date_str = date_str.strip()
        if not date_str:
            return ""

        first_token = date_str.split('/')[0] if '/' in date_str else ""
        date_part = date_str.split()[0] if date_str.split() else ""
        last_token = date_part.split('/')[-1] if '/' in date_part else ""

        formats = []
        formats.append("%m/%d/%Y %I:%M:%S %p")
        formats.append("%m/%d/%Y %H:%M:%S")
        formats.append("%Y/%m/%d %H:%M:%S")

        if last_token == "26":
            formats.extend([
                "%m/%d/%y %H:%M:%S",
                "%d/%m/%y %H:%M:%S",
                "%y/%m/%d %H:%M:%S"
            ])
        elif first_token == "26":
            formats.extend([
                "%y/%m/%d %H:%M:%S",
                "%m/%d/%y %H:%M:%S",
                "%d/%m/%y %H:%M:%S"
            ])
        else:
            formats.extend([
                "%m/%d/%y %H:%M:%S",
                "%d/%m/%y %H:%M:%S",
                "%y/%m/%d %H:%M:%S"
            ])

        formats.append("%Y-%m-%d %H:%M:%S")

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        return date_str
