# Installation Guide

## Requirements

- **Python 3.7+**
- **Google Cloud Service Account** with Google Sheets API and Google Drive API enabled.

## Setup & Installation

1. **Clone/Download the Repository**
   ```bash
   cd path/to/Drive-Data
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Google Cloud Credentials**
   - Go to Google Cloud Console and create a service account.
   - Enable the **Google Sheets API** and **Google Drive API**.
   - Download the service account key as `credentials.json`.
   - Place `credentials.json` in the root of the `Drive-Data` directory.
   - Share your target Google Sheet with the service account email address (as Editor).

4. **Configure `main.py`**
   ```python
   SHEET_ID = "your_google_sheet_id"
   SHEET_NAME = "List"
   EXPORT_DIR = r"path\to\exports"
   ```

5. **Run the Tool**
   ```bash
   python main.py
   ```

## Troubleshooting

- **`gspread.exceptions.SpreadsheetNotFound`** — Ensure the Sheet ID is correct and the sheet is shared with the service account email.
- **`FileNotFoundError: credentials.json`** — Ensure the JSON credentials file is in the project root directory.
- **Permission errors on export directory** — Ensure the `EXPORT_DIR` path exists and is writable.

---

## 👨‍💻 Credits

**By OutLawZ™**

Website: https://www.brandex.pk

Contact:

📧 Email: net2tara@gmail.com
🌐 Website: https://www.brandex.pk

---
Made with ❤️ by OutLawZ™
