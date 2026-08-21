import os
import csv
import webview
import json
import subprocess
from trimble_parser import TrimbleParser
from siemens_parser import SiemensParser
from flying_probe_parser import FlyingProbeParser

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")

class Api:
    def __init__(self):
        self._window = None
        self._parsers = {
            "trimble": TrimbleParser(),
            "siemens": SiemensParser(),
            "flying_probe": FlyingProbeParser()
        }
        # Load from config or default to trimble
        config = load_config()
        self._active_parser_name = config.get("last_parser", "trimble")
        if self._active_parser_name not in self._parsers:
            self._active_parser_name = "trimble"

    def set_window(self, window):
        self._window = window

    def select_directory(self):
        """Opens a native folder selection dialog and returns the selected path."""
        if not self._window:
            return None
        
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            path = result[0]
            self.save_last_directory(path)
            return path
        return None

    def get_last_directory(self):
        """Loads and returns the last selected directory from config.json if it exists."""
        config = load_config()
        path = config.get("last_directory", "")
        if path and os.path.exists(path):
            return path
        return ""

    def save_last_directory(self, path):
        """Saves the last selected directory to config.json."""
        if path:
            config = load_config()
            config["last_directory"] = path
            save_config(config)

    def get_last_parser(self):
        """Loads and returns the last selected parser from config.json."""
        return self._active_parser_name

    def set_active_parser(self, parser_name):
        """Sets the active parser and saves it to config.json."""
        parser_name = parser_name.lower().strip()
        if parser_name in self._parsers:
            self._active_parser_name = parser_name
            config = load_config()
            config["last_parser"] = parser_name
            save_config(config)
            return True
        return False

    def scan_directory(self, parent_path, force_rescan=False):
        """Delegates directory scanning to the active parser."""
        parser = self._parsers.get(self._active_parser_name)
        if not parser:
            return []

        def progress_callback(current, total, message):
            if self._window:
                escaped_msg = message.replace("'", "\\'").replace("\n", " ")
                self._window.evaluate_js(f"if (window.updateScanProgress) window.updateScanProgress({current}, {total}, '{escaped_msg}');")

        return parser.scan_directory(parent_path, progress_callback=progress_callback, force_rescan=force_rescan)

    def get_run_steps(self, path, serial=None, date_time=None):
        """Delegates step loading to the active parser."""
        parser = self._parsers.get(self._active_parser_name)
        if not parser:
            return []
        if self._active_parser_name == 'flying_probe':
            return parser.get_run_steps(path, serial, date_time)
        return parser.get_run_steps(path)

    def export_csv(self, export_list):
        """Opens a save file dialog and saves the table view data to a CSV file."""
        if not self._window or not export_list:
            return None

        if self._active_parser_name == 'trimble':
            default_filename = 'Trimble_Extracted_Logs.csv'
        elif self._active_parser_name == 'siemens':
            default_filename = 'Siemens_Extracted_Logs.csv'
        else:
            default_filename = 'FlyingProbe_Extracted_Logs.csv'

        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, 
            save_filename=default_filename, 
            file_types=('CSV Files (*.csv)', 'All Files (*.*)')
        )
        if not result:
            return None

        save_path = result[0]
        if not save_path.lower().endswith('.csv'):
            save_path += '.csv'

        try:
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Headers
                if self._active_parser_name == 'flying_probe':
                    writer.writerow(['Date/Time', 'Part Number', 'Program Name', 'Serial Number', 'Board Side', 'Tester/Test ID', 'Pass/Fail', 'Cumulative Tests', 'Customer'])
                    for item in export_list:
                        writer.writerow([
                            item.get('date_time', ''),
                            item.get('part_number', ''),
                            item.get('program_name', ''),
                            item.get('serial', ''),
                            item.get('board_side', ''),
                            item.get('tester', ''),
                            item.get('status', ''),
                            item.get('cumulative_tests', ''),
                            item.get('customer', '')
                        ])
                else:
                    writer.writerow(['Date/Time', 'Part Number (L1)', 'Serial Number', 'Pass/Fail', 'Cumulative Tests', 'Customer', 'Part Number (L3)'])
                    for item in export_list:
                        writer.writerow([
                            item.get('date_time', ''),
                            item.get('part_number', ''),
                            item.get('serial', ''),
                            item.get('status', ''),
                            item.get('cumulative_tests', ''),
                            item.get('customer', ''),
                            item.get('part_num_3rd', '')
                        ])
            return save_path
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            raise Exception(f"Failed to write file: {str(e)}")

    def open_explorer(self, path):
        """Opens the file explorer pointing to the given path or its parent directory."""
        if not path or not os.path.exists(path):
            return False
            
        try:
            path = os.path.abspath(path)
            if os.path.isfile(path):
                subprocess.Popen(f'explorer /select,"{path}"')
            else:
                os.startfile(path)
            return True
        except Exception as e:
            print(f"Error opening explorer for path {path}: {e}")
            return False

    def generate_barcode(self, path, is_zip, serial, date_time):
        """Delegates barcode generation to the active parser."""
        parser = self._parsers.get(self._active_parser_name)
        if not parser:
            return {"error": "No active parser selected"}
        return parser.generate_barcode(path, is_zip, serial, date_time)

def main():
    api = Api()
    # Create webview window loading local index.html file
    window = webview.create_window(
        title='Benchmark Test Log Parser',
        url='index.html',
        js_api=api,
        width=1280,
        height=850,
        min_size=(900, 600)
    )
    api.set_window(window)
    # Start the webview loop
    webview.start()

if __name__ == '__main__':
    main()
