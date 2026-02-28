# SWL View Quickstart (Windows 11)

1. Open PowerShell in the extracted folder.
2. Create and activate virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run:
   ```powershell
   .\run.bat
   ```
5. Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

Notes:
- `run.bat` activates `.venv`, runs scraper, then starts the Flask app.
- To skip scraping: `python run.py --skip-scrape`
