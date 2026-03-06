# SWL View Quickstart (Windows 11)

1. Install Python 3 (if needed):
   ```powershell
   winget install Python.Python.3.12
   ```
   Or install from python.org and enable `Add python.exe to PATH`.
2. Open a new PowerShell window in the extracted folder.
3. Verify Python:
   ```powershell
   python --version
   ```
4. Create and activate virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
5. If activation is blocked:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```
6. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
7. Run:
   ```powershell
   .\run.bat
   ```
8. Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

Notes:
- `run.bat` activates `.venv`, runs scraper, then starts the Flask app.
- To skip scraping: `python run.py --skip-scrape`
