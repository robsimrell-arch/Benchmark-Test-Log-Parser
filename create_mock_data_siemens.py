import os
import zipfile
import csv

def create_csv_content(is_fail=False):
    # R88 will fail if is_fail is True
    r88_result = "   FAIL   " if is_fail else "   PASS   "
    r88_measured = "20.50 Ohms" if is_fail else "44.62 Ohms"
    
    lines = [
        ["", "Low Limit", "High Limit", "Expected", "Measured", "Result", ""],
        [".... Verify Critical Components ....", "", "", "", "", "", ""],
        ["R58", "812.625 Ohms", "837.375 Ohms", "825.00 Ohms", "826.52 Ohms", "   PASS   ", ""],
        ["R59", "812.625 Ohms", "837.375 Ohms", "825.00 Ohms", "823.67 Ohms", "   PASS   ", ""],
        ["R88", "43.200 Ohms", "47.200 Ohms", "45.20 Ohms", r88_measured, r88_result, ""],
        ["R60", "43.200 Ohms", "47.200 Ohms", "45.20 Ohms", "44.66 Ohms", "   PASS   ", ""],
        ["R87", "43.200 Ohms", "47.200 Ohms", "47.00 Ohms", "45.45 Ohms", "   PASS   ", ""],
        ["R173", "24.444 Ohms", "25.956 Ohms", "25.20 Ohms", "25.17 Ohms", "   PASS   ", ""],
        ["", "", "", "", "", "", ""],
        [".... Hardware Voltage Regulation Test ....", "", "", "", "", "", ""],
        ["VI Isolated (TP20(+) to TP11(-))", "6.00 Volts", "7.00 Volts", "6.50 Volts", "6.50 Volts", "   PASS   ", ""],
        ["VCC1.2 (TP8(+) to TP11(-))", "1.10 Volts", "1.30 Volts", "1.20 Volts", "1.19 Volts", "   PASS   ", ""],
        ["3.3V Isolated (TP19(+) to TP11(-))", "3.10 Volts", "3.50 Volts", "3.30 Volts", "3.26 Volts", "   PASS   ", ""],
        ["VCC Isolated (TP17(+) to TP11(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "4.96 Volts", "   PASS   ", ""],
        ["VCC1 (TP21 to J7 pin 7(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "5.07 Volts", "   PASS   ", ""],
        ["", "", "", "", "", "", ""],
        [".... Firmware Voltage Regulation Test ....", "", "", "", "", "", ""],
        ["+5S (TP1(+) to TP2(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "5.00 Volts", "   PASS   ", ""],
        ["+5P (TP3(+) to TP4(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "5.00 Volts", "   PASS   ", ""],
        ["+5C (TP6(+) to TP5(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "4.99 Volts", "   PASS   ", ""],
        ["+5VD (TP13(+) to TP14(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "4.99 Volts", "   PASS   ", ""],
        ["V5X (TP10(+) to TP14(-))", "4.80 Volts", "5.20 Volts", "5.00 Volts", "5.01 Volts", "   PASS   ", ""],
        ["VX (TP15(+) to TP14(-))", "14.72 Volts", "17.28 Volts", "16.00 Volts", "16.42 Volts", "   PASS   ", ""],
        ["3.3VD (TP12(+) to TP14(-))", "3.20 Volts", "3.40 Volts", "3.30 Volts", "3.31 Volts", "   PASS   ", ""],
        ["", "", "", "", "", "", ""],
        [".... Calibration Test ....", "", "", "", "", "", ""],
        ["GCP Calibration", "---N/A---", "---N/A---", "PASS ", "PASS ", "   PASS   ", ""],
        ["GCP Calibration Required", "---N/A---", "---N/A---", "Not Required ", "Not Required ", "   PASS   ", ""],
        ["Island Calibration", "---N/A---", "---N/A---", "PASS ", "PASS ", "   PASS   ", ""],
        ["Island Calibration Required", "---N/A---", "---N/A---", "Not Required ", "Not Required ", "   PASS   ", ""],
        ["EZ", "95.00 EZ", "105.00 EZ", "100.00 EZ", "100 EZ", "   PASS   ", ""],
        ["EX", "90.00 EX", "100.00 EX", "95.00 EX", "96 EX", "   PASS   ", ""],
        ["ISLAND LED (DS112) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["OUT 1 LED(DS13) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["OUT 2 LED(DS14) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["", "", "", "", "", "", ""],
        [".... Prempt Logic Test ....", "", "", "", "", "", ""],
        ["Prime LED(DS2) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX A LED(DS3) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX B LED(DS4) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX C LED(DS5) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX D LED(DS6) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX E LED(DS7) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX F LED(DS8) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["DAX G LED(DS9) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""],
        ["PRE-EMPT LED(DS10) Energized", "---N/A---", "---N/A---", "Energized ", "Energized ", "   PASS   ", ""]
    ]
    return lines

def create_pg2_content(is_fail=False):
    result = "   ***FAIL***   " if is_fail else "   PASS   "
    time_val = "4:19" if is_fail else "2:30"
    lines = [
        ["TF80418 Test", f" Time: {time_val}", result, ""],
        ["", "", "", ""],
        ["Test Cases Run", "Result", ""],
        [".... Verify Critical Components ...", "  Time: 0:34 ", "   PASS   ", ""],
        [".... Hardware Voltage Regulation Test ...", "  Time: 1:18 ", "   PASS   ", ""],
        [".... Firmware Voltage Regulation Test ...", f"  Time: {time_val} ", result, ""],
        ["", "", "", ""],
        ["Test Report File Path:", "", ""],
        [r"C:\Automated Test Records\TF80418\Wednesday_June 03_2026\Siemens_80418_099301_06032026_0100_FAIL.xls", "", ""]
    ]
    return lines

def create_pg4_content(is_fail=False):
    vpi1_off_result = "   ***FAIL***   " if is_fail else "   PASS   "
    vpi1_off_measured = "Energized" if is_fail else "De-Energized"
    
    lines = [
        ["", "Low Limit", "High Limit", "Expected", "Measured", "Result", ""],
        ["MOTION LED(DS11) Energized", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["ISLAND LED(12) Energized", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["IN 1 LED(DS15) Energized", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["IN 2 LED(DS16) Energized", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["HEALTH LED(DS19) FLASHING", "---N/A---", "---N/A---", "Flashing", "Flashing", "   PASS   ", ""],
        ["POWER LED(DS20) Energized", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["Preempt OFF", "---N/A---", "---N/A---", "De-Energized", "De-Energized", "   PASS   ", ""],
        ["", "", "", "", "", "", ""],
        [".... Vital Input Circuit Test ....", "", "", "", "", "", ""],
        ["VPI 1 ON", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["VPI 2 ON", "---N/A---", "---N/A---", "Energized", "Energized", "   PASS   ", ""],
        ["VPI 1 OFF", "---N/A---", "---N/A---", "De-Energized", vpi1_off_measured, vpi1_off_result, ""],
        ["VPI 2 OFF", "---N/A---", "---N/A---", "De-Energized", "De-Energized", "   PASS   ", ""],
        ["VPI 1 ON Voltage", "7.00 Volts", "8.00 Volts", "8.00 Volts", "7.00 Volts", "   PASS   ", ""],
        ["VPI 2 ON Voltage", "7.00 Volts", "8.00 Volts", "8.00 Volts", "7.00 Volts", "   PASS   ", ""],
    ]
    return lines

def write_csv(filepath, lines):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(lines)

def build_zip(zip_path, folder_name, is_fail=False):
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    # create temporary CSV files
    temp_dir = "temp_mock"
    os.makedirs(temp_dir, exist_ok=True)
    
    csv_paths = {}
    for pg in [1, 2, 3, 4]:
        csv_name = f"{folder_name}_pg{pg}.csv"
        csv_path = os.path.join(temp_dir, csv_name)
        # We write test steps in pg3 and pg4, others are empty or simple dummy content
        if pg == 2:
            write_csv(csv_path, create_pg2_content(is_fail))
        elif pg == 3:
            write_csv(csv_path, create_csv_content(is_fail))
        elif pg == 4:
            write_csv(csv_path, create_pg4_content(is_fail))
        else:
            write_csv(csv_path, [["Dummy Page", str(pg)], ["Status", "OK"]])
        csv_paths[csv_name] = csv_path
        
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for csv_name, csv_path in csv_paths.items():
            z.write(csv_path, csv_name)
            os.remove(csv_path)
            
    os.rmdir(temp_dir)

def main():
    base_dir = "mock_data_siemens"
    
    # 1. TF80418 -> Tuesday_June 09_2026 -> Siemens_80418_099257_06092026_0535_PASS.zip
    run1_dir_name = "Siemens_80418_099257_06092026_0535_PASS"
    run1_path = os.path.join(base_dir, "TF80418", "Tuesday_June 09_2026", f"{run1_dir_name}.zip")
    build_zip(run1_path, run1_dir_name, is_fail=False)
    
    # 2. TF80418 -> Tuesday_June 09_2026 -> Siemens_80418_099257_06092026_0600_FAIL (As a standard folder!)
    run2_dir_name = "Siemens_80418_099257_06092026_0600_FAIL"
    run2_path = os.path.join(base_dir, "TF80418", "Tuesday_June 09_2026", run2_dir_name)
    os.makedirs(run2_path, exist_ok=True)
    for pg in [1, 2, 3, 4]:
        csv_name = f"{run2_dir_name}_pg{pg}.csv"
        csv_path = os.path.join(run2_path, csv_name)
        if pg == 2:
            write_csv(csv_path, create_pg2_content(is_fail=True))
        elif pg == 3:
            write_csv(csv_path, create_csv_content(is_fail=True))
        elif pg == 4:
            write_csv(csv_path, create_pg4_content(is_fail=True))
        else:
            write_csv(csv_path, [["Dummy Page", str(pg)], ["Status", "OK"]])
            
    # 3. TF80418 -> Wednesday_June 10_2026 -> Siemens_80418_099257_06102026_0800_PASS.zip
    run3_dir_name = "Siemens_80418_099257_06102026_0800_PASS"
    run3_path = os.path.join(base_dir, "TF80418", "Wednesday_June 10_2026", f"{run3_dir_name}.zip")
    build_zip(run3_path, run3_dir_name, is_fail=False)
    
    # 4. TF55555 -> Wednesday_June 10_2026 -> GE_55555_123456_06102026_0930_FAIL.zip
    run4_dir_name = "GE_55555_123456_06102026_0930_FAIL"
    run4_path = os.path.join(base_dir, "TF55555", "Wednesday_June 10_2026", f"{run4_dir_name}.zip")
    build_zip(run4_path, run4_dir_name, is_fail=True)
    
    print("Successfully created mock folder structure and test data in 'mock_data_siemens/'")

if __name__ == "__main__":
    main()
