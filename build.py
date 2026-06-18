import subprocess
import sys
import os
import shutil

def build():
    # Construct PyInstaller command using python -m PyInstaller to bypass PATH issues
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--add-data", "index.html;.",
        "--add-data", "style.css;.",
        "--add-data", "script.js;.",
        "--add-data", "benchmark_logo.png;.",
        "--hidden-import", "qrcode",
        "--hidden-import", "qrcode.image.base",
        "--hidden-import", "qrcode.image.pil",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "PIL.ImageFont",
        "--name", "BenchmarkTestLogParser",
        "app.py"
    ]
    
    print("Building executable with PyInstaller...")
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Clean build artifacts if they exist
        for d in ["build", "dist"]:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d)
                except Exception as e:
                    print(f"Warning: Could not remove {d}: {e}. PyInstaller will try to overwrite it.")
        spec_file = "BenchmarkTestLogParser.spec"
        if os.path.exists(spec_file):
            try:
                os.remove(spec_file)
            except Exception as e:
                print(f"Warning: Could not remove {spec_file}: {e}")

        subprocess.run(cmd, check=True)
        print("="*60)
        print("Build completed successfully!")
        print("You can find the standalone executable at:")
        print(os.path.abspath(os.path.join("dist", "BenchmarkTestLogParser.exe")))
        print("="*60)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build()
