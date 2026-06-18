from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def scan_directory(self, parent_path):
        """
        Scans the given directory tree for runs and returns a list of run dictionaries.
        Each run dictionary must contain:
        - customer (str)
        - part_number (str)
        - part_num_3rd (str)
        - serial (str)
        - date_time (str)
        - status (str: "PASS" or "FAIL")
        - path (str)
        - is_zip (bool)
        - steps (list of dicts)
        - file_ext (str)
        """
        pass

    @abstractmethod
    def get_run_steps(self, path):
        """
        Loads and returns steps for a run on demand.
        Returns a list of dictionaries with step details.
        """
        pass

    @abstractmethod
    def generate_barcode(self, path, is_zip, serial, date_time):
        """
        Generates QR code and text summary for failed steps of a run.
        Returns a dict with "text" and "qr_base64" (or "error").
        """
        pass
