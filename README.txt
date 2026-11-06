================================================================================
                         BENCHMARK TEST LOG PARSER
================================================================================

Official GitHub Repository:
https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser


--------------------------------------------------------------------------------
1. OVERVIEW
--------------------------------------------------------------------------------
Benchmark Test Log Parser is an automated desktop tool that scans, indexes,
and normalizes test execution logs produced by electronics manufacturing test
fixtures.

Key Features:
- Multi-Fixture Support: Built-in parsers for Trimble, Siemens, and Flying Probe.
- Fast File System Scanning: High-speed caching (scan_cache.py) for large logs.
- Visual Analytics UI: Dark-themed interface (PyWebView, HTML5, CSS3, JS).
- Interactive Failure Drilldown: Pinpoint failing steps, limits, and deltas.
- Traceability: 2D barcode generation for board serials and timestamps.
- Standalone Portable Executable: Single-file Windows .exe with custom icon.


--------------------------------------------------------------------------------
2. QUICKSTART & SETUP
--------------------------------------------------------------------------------
Prerequisites:
- Git: https://git-scm.com/
- Python 3.10+ (64-bit recommended): https://www.python.org/
- Google Antigravity IDE: https://antigravity.google (for AI development)

Step 1: Clone the repository
    git clone https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser.git
    cd Benchmark-Test-Log-Parser

Step 2: Create and activate a Python virtual environment
    python -m venv .venv
    .venv\Scripts\activate

Step 3: Install dependencies
    pip install -r requirements.txt

Step 4: Run the app locally
    python app.py

Step 5: Build the standalone Windows .exe
    python build.py
    (Executable will be placed in dist\BenchmarkTestLogParser.exe)


--------------------------------------------------------------------------------
3. DEVELOPING & MAKING ALTERATIONS WITH GOOGLE ANTIGRAVITY
--------------------------------------------------------------------------------
This codebase is designed for pair programming using Google Antigravity (AGY).

How to Get Started:
1. Launch Google Antigravity IDE (https://antigravity.google).
2. Open the project folder: File > Open Folder... > select Benchmark-Test-Log-Parser.
3. Open the Antigravity Agent sidebar (Ctrl + L or click the sidebar icon).

Codebase Map:
- app.py               : PyWebView window host & JS-to-Python bridge API.
- base_parser.py       : Abstract base class BaseParser for all test formats.
- siemens_parser.py    : Siemens fixture log parser (.csv, .zip archives).
- trimble_parser.py    : Trimble fixture log parser.
- flying_probe_parser.py: Flying probe fixture log parser (.NGD / .ngdx).
- scan_cache.py        : Fast directory cache to avoid slow repeat scans.
- index.html, style.css, script.js: Dashboard UI, tables, modals, and styling.
- build.py             : PyInstaller one-file packaging script with embedded icon.
- app_icon.ico / .png  : Custom high-res application artwork icon.

Example Antigravity Modification Prompts:

  [Add a New Tester Log Parser]
  Prompt:
    /plan I need to add support for a new test log format: [Tester Name].
    1. Create tester_parser.py inheriting from BaseParser in base_parser.py.
    2. Implement parse_directory(), get_failure_data(), and generate_barcode().
    3. Register the new parser in app.py's self._parsers map.
    4. Add the new option to the #parser-select dropdown in index.html.

  [Customize Dashboard UI / Analytics]
  Prompt:
    In index.html and script.js, let's add a new KPI card for "Average Cycle Time":
    1. Calculate average test duration across the active filtered dataset in script.js.
    2. Add the card to index.html matching style.css.
    3. Add a button to export failure data to CSV.

  [Verify and Rebuild Release Binary]
  Prompt:
    Please run test_parser.py to verify all parsers handle the mock test data,
    then run build.py to compile the updated standalone Windows executable.

Recommended Antigravity Slash Commands:
- /plan     : Step-by-step feature and architecture planning before execution.
- /grill-me : Interactive requirement interview to align on design decisions.
- /goal     : Autonomous long-running implementation and verification.
- /boost    : Deep reasoning for complex parsing logic and regex algorithms.


--------------------------------------------------------------------------------
4. LICENSE & CREDITS
--------------------------------------------------------------------------------
- Repository: https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser
- Maintained by: robsimrell-arch
- Created for Benchmark electronics manufacturing test engineering workflows.
