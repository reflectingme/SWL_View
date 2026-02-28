# SWL View Quickstart (macOS / Linux)

1. Open Terminal in the extracted folder.
2. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   ./run.sh
   ```
5. Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

Notes:
- `run.sh` activates `.venv`, runs scraper, then starts the Flask app.
- To skip scraping: `python run.py --skip-scrape`
