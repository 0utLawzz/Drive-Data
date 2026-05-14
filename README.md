# Drive Data Parser

A Python tool for parsing Google Drive folder structures and extracting trademark case information with pattern matching capabilities.

## Features

- **Directory Parsing**: Parse client and case folder structures from Google Drive
- **Pattern Matching**: Automatically detect and categorize trademark documents (TM-1, TM-48, EXAM, ACK, etc.)
- **Google Sheets Integration**: Upload parsed data directly to Google Sheets with duplicate control
- **Local Export**: Export data to Excel and CSV files
- **Quick Export**: Fast export without pattern matching for both directories
- **Batch Processing**: Process specific number of records for testing

## Requirements

```bash
pip install pandas gspread openpyxl google-auth
```

## Setup

1. Create a Google Cloud project and enable Google Sheets API and Google Drive API
2. Create a service account and download credentials.json
3. Place `credentials.json` in the project directory
4. Update the `SHEET_ID` in `main.py` with your Google Sheet ID

## Usage

Run the main script:

```bash
python main.py
```

### Menu Options

1. **ALL CLIENTS** - Process all client directories
2. **CONSULTANTS** - Process consultant directories
3. **BOTH Directories** - Process both client and consultant directories
4. **Custom Path** - Process a custom directory path
5. **Quick Export** - Export both directories without pattern matching
6. **Exit** - Exit the program

### Upload Options

- Local files only (Excel/CSV)
- Google Sheets only
- Both local and Google Sheets

## Pattern Categories

The tool automatically detects the following document patterns:

- **TM-1**: Trademark application forms
- **TM-48**: Trademark registration certificates
- **EXAM**: Examination reports and showcase notices
- **ACK**: Acknowledgment receipts
- **ACCEPTANCE**: Acceptance documents
- **D-NOTE**: Demand notes (TM-11)
- **TM-16**: Trademark renewal documents
- **TM-50**: Trademark opposition documents
- **TM-06**: Other trademark forms
- **COMPANY**: Board resolutions
- **OPPO**: Withdrawn letters
- **PUB**: Publication documents
- **CERTIFICATE**: Trademark certificates

## File Structure

```
TMAuto/
├── main.py              # Main application script
├── credentials.json    # Google Sheets credentials (not in repo)
├── exports/            # Exported Excel/CSV files (gitignored)
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Configuration

Edit the following constants in `main.py`:

```python
SHEET_ID = "your_google_sheet_id"
SHEET_NAME = "List"
EXPORT_DIR = r"g:\TMAuto\exports"
```

## License

MIT License
