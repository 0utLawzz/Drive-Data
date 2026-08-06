# 🗂️ Drive Folders List (Drive-Data)

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API-green?logo=google-sheets&logoColor=white)
![Automation](https://img.shields.io/badge/Automation-Custom-blue)
![Status](https://img.shields.io/badge/Status-Active-success)

> **A smart Google Drive folder parser that extracts, categorizes, and exports trademark case data to Google Sheets or local Excel/CSV files.**

## Topics / Keywords
`google-drive` `google-sheets` `trademark` `ip-management` `folder-parser` `python` `automation` `pattern-matching` `pandas` `gspread` `cli-tool` `excel-export` `custom-automation`

---

## 🚀 Features

- **Multi-Mode Directory Scanning:** Process All Clients, Consultants, Both directories, or any custom path in a single run.
- **Regex-Based Pattern Classification:** 13 predefined trademark document categories automatically recognized without manual sorting.
- **Flexible Output Targets:** Single tool supports local (Excel/CSV) exports, cloud (Google Sheets) uploads, or both simultaneously.
- **Data Quality:** Unfiltered exports directly to Google Sheets and saved to CSV/Excel without any duplicate filtering, ensuring complete and exhaustive records.
- **Interactive CLI Menu & Quick Export:** Fast-path options that export raw directory listings or categorized listings efficiently.

---

## 🛠️ Architecture

**Drive-Data** is a single-script Python CLI application structured around three logical layers:

### 1. CLI Interface Layer
- An interactive, numbered text menu printed to the terminal.
- Handles user selection for directory scope (All Clients, Consultants, Both, Custom Path) and output destination (Local, Google Sheets, Both).

### 2. Directory Scanning & Pattern Matching Layer
- Recursively traverses the configured directory paths using `os.walk`.
- For each file found, applies a predefined set of regex patterns to classify the document into a trademark category (TM-1, TM-48, EXAM, ACK, etc.).
- Builds a structured list of dictionaries from the matched results.

### 3. Export Layer
- **Local:** Converts the list to a `pandas` DataFrame and exports via `openpyxl` to `.xlsx` and `.csv`.
- **Google Sheets:** Uses `gspread` with Google Service Account authentication to append all processed records directly to the sheet.

---

## 💻 Setup & Installation

### Requirements
- **Python 3.7+**
- **Google Cloud Service Account** with Google Sheets API and Google Drive API enabled.

### Step-by-Step Installation

1. **Clone/Download the Repository**
   ```bash
   git clone https://github.com/0utLawzz/Drive-Data.git
   cd Drive-Data
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
   Update the configuration in `main.py` if necessary:
   ```python
   SHEET_ID = "your_google_sheet_id"
   SHEET_NAME = "List"
   ```

5. **Run the Tool**
   ```bash
   python main.py
   ```

### Troubleshooting
- **`gspread.exceptions.SpreadsheetNotFound`** — Ensure the Sheet ID is correct and the sheet is shared with the service account email.
- **`FileNotFoundError: credentials.json`** — Ensure the JSON credentials file is in the project root directory.
- **Permission errors on export directory** — Ensure the local export directory path is writable.

---

## 👨‍💻 Credits

**By OutLawZ™ (Nadeem)**  
Custom Automation Specialist  

📧 Contact: [net2outlawzz@gmail.com](mailto:net2outlawzz@gmail.com) | [net2tara@gmail.com](mailto:net2tara@gmail.com)  
🌐 Website: [https://www.brandex.pk](https://www.brandex.pk)  
🔗 GitHub: [0utLawzz](https://github.com/0utLawzz)  

---
*Made with ❤️ by OutLawZ™*
