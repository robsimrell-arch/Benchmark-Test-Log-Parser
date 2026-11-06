import os
import json
import hashlib

CACHE_DIR = '.cache'

def get_cache_path(parent_path, parser_name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = f"{parent_path}_{parser_name}"
    h = hashlib.sha256(key.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")

class ScanCache:
    def __init__(self, parent_path, parser_name, force_rescan=False):
        self.parent_path = parent_path
        self.parser_name = parser_name
        self.force_rescan = force_rescan
        self.cache_path = get_cache_path(parent_path, parser_name)
        self.data = {"parser": parser_name, "files": {}}
        self._dirty = False
        if not force_rescan and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")

    def get_cached_runs(self, file_path):
        """Returns cached runs if mtime matches, else None."""
        if self.force_rescan:
            return None
        if not os.path.exists(file_path):
            return None
        
        file_entry = self.data.get("files", {}).get(file_path)
        if not file_entry:
            return None
            
        try:
            current_mtime = os.path.getmtime(file_path)
            if current_mtime == file_entry.get("mtime"):
                return file_entry.get("runs")
        except Exception:
            pass
        return None

    def update_file(self, file_path, runs):
        """Updates the cache entry for a file."""
        try:
            mtime = os.path.getmtime(file_path)
            if "files" not in self.data:
                self.data["files"] = {}
            self.data["files"][file_path] = {
                "mtime": mtime,
                "runs": runs
            }
            self._dirty = True
        except Exception:
            pass

    def clean_and_save(self, active_file_paths):
        """Removes entries no longer present in listed files, and saves cache."""
        cached_paths = list(self.data.get("files", {}).keys())
        active_set = set(active_file_paths)
        for path in cached_paths:
            if path not in active_set:
                self.data["files"].pop(path, None)
                self._dirty = True
                
        if self._dirty:
            try:
                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f)
                self._dirty = False
            except Exception as e:
                print(f"Error saving cache: {e}")
