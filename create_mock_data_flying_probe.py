import os

def main():
    base_dir = "mock_data_flying_probe"
    os.makedirs(base_dir, exist_ok=True)

    # 1. Program 1: MOGCD34209_A_1.000 (uses .ngdx files)
    prog1_dir = os.path.join(base_dir, "MOGCD34209_A_1.000")
    os.makedirs(prog1_dir, exist_ok=True)

    ngdx_content = """@B
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
@E
@B
@
Model : MOGCD34209_A_1.000
Serial : BH1826MOG0008
Date : 5/26/2026 3:06:44 PM
Side: A
Tester: APT-1400F-SL
Operator: bakerlo
* PASS *
@
@E
@B
@
Model : MOGCD34209_A_1.000
Serial : BH1826MOG0008
Date : 5/26/2026 3:08:24 PM
Side: B
Tester: APT-1400F-SL
Operator: bakerlo
* PASS *
@
@E"""

    with open(os.path.join(prog1_dir, "BH1826MOG0008.ngdx"), "w") as f:
        f.write(ngdx_content)

    # 2. Program 2: MOGCA66178_A_1.002.SWX (uses .NGD files)
    prog2_dir = os.path.join(base_dir, "MOGCA66178_A_1.002.SWX")
    os.makedirs(prog2_dir, exist_ok=True)

    ngd_content_1 = """@
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
* FAIL *

Model:MOGCA66178_A_1.002.SWX (B)
DATE 02/12/26 07:42:33

Test time:103 s
Test ID :TAKAYA-B
User name :Administrator
@

* GROUP No.1   *
* FAIL *
Serial No.:BH5125MOG1098

000139 "R101*      " "5O         " "MOGM55342K09B10D0R  " "40.95 O  " "409.5 KO " "OPEN   " "1.0 ms" "( +, -, N, N) "   103
000323 "R102       " "3.32KO     " "MOGD55342K07B3E32R  " "4.095 KO " "10.40 MO " "OPEN   " "200.0 ms" "( -,G1, N, +) "   103
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

    with open(os.path.join(prog2_dir, "BH5125MOG1098(B).NGD"), "w") as f:
        f.write(ngd_content_1)

    print("Successfully created mock folder structure and test data in 'mock_data_flying_probe/'")

if __name__ == "__main__":
    main()
