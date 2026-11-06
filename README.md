# Benchmark Test Log Parser

<div align="center">
  <img src="app_icon.png" alt="Benchmark Test Log Parser Icon" width="128" height="128" style="border-radius: 28px; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);" />
  <br />
  <p><strong>A high-performance desktop analytics and log parsing tool for electronics manufacturing test systems.</strong></p>
  <p>
    <a href="https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser"><img src="https://img.shields.io/badge/GitHub-Repository-blue?logo=github" alt="GitHub Repository" /></a>
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows" alt="Platform Windows" />
    <img src="https://img.shields.io/badge/AI--Assisted-Google%20Antigravity-4285F4?logo=google" alt="Google Antigravity" />
  </p>
</div>

---

## 📌 Repository & Overview

- **Official GitHub Repository**: [https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser](https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser)

**Benchmark Test Log Parser** is an automated desktop tool that scans, indexes, and normalizes test execution logs produced by electronics manufacturing test fixtures. It features:
- **Multi-Fixture Support**: Built-in extensible parsers for **Trimble**, **Siemens**, and **Flying Probe** test fixtures.
- **Fast File System Scanning**: Cached scanning mechanism (`scan_cache.py`) for processing large test log archives.
- **Visual Analytics UI**: Dark-themed UI built with PyWebView, HTML5, CSS3, and vanilla JavaScript.
- **Interactive Failure Drilldown**: Pinpoints failing test steps, limits, and measurement deltas.
- **Traceability & QR/Barcode Generation**: Generates 2D barcodes for boards, serials, and test timestamps.
- **Self-Contained Standalone Executable**: Packaged into a portable Windows `.exe` with embedded artwork icon using PyInstaller.

---

## 🚀 Quickstart & Setup

### Prerequisites
- **Git**: [git-scm.com](https://git-scm.com/)
- **Python 3.10+** (64-bit recommended): [python.org](https://www.python.org/)
- **Google Antigravity IDE**: [antigravity.google](https://antigravity.google) (for AI-assisted development and modifications)

### 1. Clone the Repository
```bash
git clone https://github.com/robsimrell-arch/Benchmark-Test-Log-Parser.git
cd Benchmark-Test-Log-Parser
```

### 2. Set Up a Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Or Command Prompt (cmd.exe):
# .venv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application Locally
```bash
python app.py
```

### 5. Build the Standalone Windows Executable
To package the app into `dist/BenchmarkTestLogParser.exe` with the custom icon and assets embedded:
```bash
python build.py
```

---

## 🤖 Developing & Modifying with Google Antigravity

This codebase is optimized for AI-first pair programming using **Google Antigravity (AGY)**. Antigravity understands the application architecture, file dependencies, and build pipelines out-of-the-box.

### Step 1: Open the Project in Antigravity IDE
1. Launch **Google Antigravity**.
2. Select **File > Open Folder...** and select the cloned `Benchmark-Test-Log-Parser` directory.
3. Open the **Antigravity Agent** sidebar (press `Ctrl + L` or click the Antigravity icon in the side rail).

---

### Step 2: Understand the Codebase Architecture
When prompting Antigravity, reference these core components for immediate context:

| Component | Key Files | Responsibility |
| :--- | :--- | :--- |
| **Window Host & API Bridge** | [`app.py`](app.py) | Manages the native PyWebView window and exposes Python APIs to the frontend via the `Api` class. |
| **Parser Architecture** | [`base_parser.py`](base_parser.py) | Abstract base class defining `BaseParser` interface (`parse_directory()`, `generate_barcode()`, `get_failure_data()`). |
| **Fixture Parsers** | [`trimble_parser.py`](trimble_parser.py)<br>[`siemens_parser.py`](siemens_parser.py)<br>[`flying_probe_parser.py`](flying_probe_parser.py) | Parser implementations tailored to specific tester log formats and folder structures. |
| **Scan Caching** | [`scan_cache.py`](scan_cache.py) | High-speed cache serialization avoiding redundant directory walking on rescans. |
| **Frontend UI** | [`index.html`](index.html)<br>[`style.css`](style.css)<br>[`script.js`](script.js) | Modern dashboard, dynamic data table, filtering controls, and modal dialogues. |
| **Build Automation** | [`build.py`](build.py)<br>[`app_icon.ico`](app_icon.ico) | PyInstaller compilation script that bundles HTML/CSS/JS, logos, and the native `.ico`. |

---

### Step 3: Practical Modification Workflows & Prompt Templates

Here are ready-to-use prompt templates you can copy and paste into the Antigravity Agent chat to make common alterations:

#### 🧪 Workflow A: Adding a New Test Log Parser
To add support for a new manufacturing test format (e.g., Teradyne, Keysight, or an in-house tester):

> **Antigravity Prompt:**
> ```text
> /plan I need to add support for a new test log format: [Tester Name, e.g. Keysight 3070].
> 1. Create keysight_parser.py inheriting from BaseParser in base_parser.py.
> 2. Implement parse_directory(), get_failure_data(), and generate_barcode().
> 3. Register the new parser in app.py's self._parsers map.
> 4. Add the new option to the #parser-select dropdown in index.html.
> 5. Create a mock data generator create_mock_data_keysight.py for testing.
> ```

#### 🎨 Workflow B: Customizing the UI, Metrics, or Data Tables
To introduce new visual metrics, filter columns, or export options:

> **Antigravity Prompt:**
> ```text
> In index.html and script.js, let's add a new filter and metric card for "Average Test Duration (seconds)":
> 1. Calculate the mean test cycle duration across the active filtered dataset in script.js.
> 2. Add a KPI card in index.html matching the existing dark theme in style.css.
> 3. Add an export option to download failure details as a separate CSV file.
> ```

#### 📦 Workflow C: Rebuilding & Validating the Binary
After making alterations, ask Antigravity to run automated validation and produce a new release:

> **Antigravity Prompt:**
> ```text
> Please run test_parser.py to verify that all parsers handle the mock test data correctly, then run build.py to generate the updated standalone Windows executable in dist/BenchmarkTestLogParser.exe.
> ```

---

### Step 4: Recommended Antigravity Slash Commands

Make full use of Antigravity's built-in slash commands during development:

- **/plan**: Use when planning a multi-file feature (like a new parser or UI overhaul) before changing files.
- **/grill-me**: Interview mode where Antigravity asks targeted questions one-by-one to resolve design decisions before writing code.
- **/goal**: Runs comprehensive tasks autonomously and verifies everything is working before completing.
- **/boost**: Activates deep reasoning for complex parsing logic, regex optimization, or binary reverse-engineering.

---

## 📄 License & Credits

- Maintained by [robsimrell-arch](https://github.com/robsimrell-arch).
- Created for Benchmark electronics manufacturing log analytics and test engineering workflows.
