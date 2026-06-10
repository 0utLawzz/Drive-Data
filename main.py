import os
import re
import pandas as pd
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Base directory (wherever this script lives)
BASE_DIR = Path(__file__).parent.resolve()

# Export directory — lives next to the script
EXPORT_DIR = str(BASE_DIR / "export")
os.makedirs(EXPORT_DIR, exist_ok=True)

# Google Sheets configuration
SHEET_ID = "1Hiqcudjg-rqcm0kC-EvJv5vZeYjK3AngiS91lYmrbkY"
SHEET_NAME = "List"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def parse_client_folder(folder_name):
    """Parse client folder to extract client number and client name"""
    match = re.match(r'^([A-Z]-\d+)\s+(.+)$', folder_name)
    if match:
        return match.group(1), match.group(2)
    return "", folder_name

def parse_case_folder(folder_name):
    """Parse case folder to extract case #, case name, tm no, and class"""
    parts = folder_name.split()
    
    case_no = ""
    case_name = ""
    tm_no = ""
    class_code = ""
    
    for i, part in enumerate(parts):
        if re.match(r'^[A-Z]\d{3}-\d{3}$', part):
            case_no = part
        elif case_no and not case_name and re.match(r'^[A-Z][a-zA-Z]+$', part):
            case_name = part
        elif re.match(r'^\d{6}$', part):
            tm_no = part
        elif re.match(r'^[C]\d+$', part):
            class_code = part
    
    return case_no, case_name, tm_no, class_code

def extract_full_case_name(folder_name, tm_no):
    """Extract full case name using TM number as delimiter"""
    if not tm_no:
        return ""
    
    # Find TM number position and extract everything before it
    tm_pattern = rf'\b{tm_no}\b'
    match = re.search(tm_pattern, folder_name)
    
    if match:
        # Get everything after case number but before TM number
        parts = folder_name.split()
        case_name_parts = []
        found_case_no = False
        
        for part in parts:
            if re.match(r'^[A-Z]\d{3}-\d{3}$', part):
                found_case_no = True
                continue
            elif found_case_no and part != tm_no and not re.match(r'^[C]\d+$', part):
                case_name_parts.append(part)
            elif part == tm_no:
                break
        
        return " ".join(case_name_parts)
    
    return ""

def check_file_patterns(file_names):
    """Check file names for all patterns and return tickmarks for each category"""
    file_list = file_names.split('\n') if file_names else []
    
    # Pattern definitions for each category
    patterns = {
        'TM-1': [
            r'\bTM-1\b', r'\bTM1\b', r'\(TM-1\)', r'\[TM-1\]'
        ],
        'TM-48': [
            r'\bTM-48\b', r'\bTM48\b', r'\(TM-48\)', r'\[TM-48\]',
            r'UPDATED\s*\[TM-48\]', r'UPDATED\s*X\s*\[TM-48\]',
            r'TM-48\s*-\s*COPY', r'TM-48\s*-\s*COPY\s*-\s*COPY'
        ],
        'EXAM': [
            r'\bTM-48\b', r'\bTM48\b', r'\bEXAMINATION\b', r'\bSHOWCASE\b',
            r'SHOWCASE\s*NOTICE', r'17\(2\)\(B\)', r'14\(3\)\(A\)', r'14\(1\)\(b\)',
            r'\bREPLY\b', r'REPLY\s*OF\s*NOTICE', r'MULTIPAL\s*REPLIES',
            r'17\(2\)\(B\),\s*14\(3\)\(A\)\s*&\s*14\(1\)\(B\)',
            r'17\(2\)\(B\),\s*14\(3\)\(A\),\s*14\s*\(1\)\s*\(B\).*AND\s*14\(1\)\(C\)',
            r'REPLY\s*\[.*?\]\s*\(\d{2}-\d{2}-\d{4}\)'
        ],
        'ACK': [
            r'\bACK\b', r'ACKNOWLEDGMENT', r'ACKNOLDGEMENT',
            r'ACK\s*-\s*A\d{3}-\d{3}.*?C\d{2}.*?\d{2}-\w{3}-\d{4}'
        ],
        'ACCEPTANCE': [
            r'\bACCEPTANCE\b', r'ACCEPTANCE\s*DONE', r'COMPLETE\s*FILE'
        ],
        'D-NOTE': [
            r'\bTM-11\b', r'\bTM11\b', r'IPO-PAKISTAN\s*__\s*TM\s*11', r'TM\s*11',
            r'DEMAND\s*NOTE'
        ],
        'TM-16': [
            r'\bTM-16\b', r'\bTM16\b', r'IPO-PAKISTAN\s*__\s*TM\s*16', r'TM\s*16'
        ],
        'TM-50': [
            r'\bTM-50\b', r'\bTM50\b', r'IPO-PAKISTAN\s*__\s*TM\s*50', r'TM\s*50'
        ],
        'TM-06': [
            r'IPO-PAKISTAN\s*__\s*TM\s*06', r'IPO-PAKISTAN\s*__\s*TM\s*\d{2}'
        ],
        'COMPANY': [
            r'BOARD\s*OF\s*RESULOTION', r'BOARD\s*OF\s*RESOLUTION'
        ],
        'OPPO': [
            r'WITHDRAWN\s*LETTER'
        ],
        'PUB': [
            r'\bPublication\b', r'\bPUBLICATION\b'
        ],
        'CERTIFICATE': [
            r'\bCERTIFICATE\b', r'CERTIFICATE\s*WITH\s*SIGN', 
            r'ORIGINAL\s*CERTIFICATE', r'TRADE\s*MARK\s*CERTIFICATE',
            r'RENEWAL\s*CERTIFICATE'
        ]
    }
    
    # Function to check if any pattern matches
    def check_pattern(text, pattern_list):
        if not text:
            return False
        text = str(text).upper()
        for pattern in pattern_list:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    # Check all patterns and return results
    results = {}
    all_files_text = " ".join(file_list)
    
    for category, pattern_list in patterns.items():
        results[category] = "✓" if check_pattern(all_files_text, pattern_list) else ""
    
    return results

def process_directory(base_path, prefix_to_remove, max_records=None):
    """Process directory and return list of records"""
    records = []
    case_groups = {}
    processed_count = 0
    
    for client_folder in os.listdir(base_path):
        if max_records and processed_count >= max_records:
            break
            
        client_path = os.path.join(base_path, client_folder)
        if not os.path.isdir(client_path):
            continue
        
        client_number, client_name = parse_client_folder(client_folder)
        
        for case_folder in os.listdir(client_path):
            if max_records and processed_count >= max_records:
                break
                
            case_path = os.path.join(client_path, case_folder)
            if not os.path.isdir(case_path):
                continue
            
            case_no, case_name, tm_no, class_code = parse_case_folder(case_folder)
            
            # Extract full case name using TM number
            full_case_name = extract_full_case_name(case_folder, tm_no)
            if full_case_name:
                case_name = full_case_name
            
            case_key = (client_number, client_name, case_no, case_name, tm_no, class_code)
            
            files = []
            for file in os.listdir(case_path):
                file_path = os.path.join(case_path, file)
                if os.path.isfile(file_path):
                    # Skip desktop.ini files
                    if file.lower() == 'desktop.ini':
                        continue
                    
                    file_name, file_ext = os.path.splitext(file)
                    # Remove .ini extension from any file
                    if file_ext.lower() == '.ini':
                        file_ext = ''
                    files.append(f"{file_name}|{file_ext.lstrip('.')}")
            
            if case_key not in case_groups:
                case_groups[case_key] = []
            case_groups[case_key].extend(files)
            processed_count += 1
    
    for (client_number, client_name, case_no, case_name, tm_no, class_code), files in case_groups.items():
        file_names = "\n".join([f.split("|")[0] for f in files if f.split("|")[0]])
        file_exts = "\n".join([f.split("|")[1] for f in files if f.split("|")[1]])
        
        # Check file patterns for tickmarks
        pattern_results = check_file_patterns(file_names)
        
        record = {
            "CLIENT NUMBER": client_number,
            "CLIENT NAME": client_name,
            "CASE #": case_no,
            "CASE NAME": case_name,
            "TM NO": tm_no,
            "CLASS": class_code,
            "FILES": file_names,
            "EXT": file_exts,
            "DATE ADDED": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add all pattern columns
        record.update(pattern_results)
        
        records.append(record)
    
    return records

def get_google_sheets_client():
    """Initialize Google Sheets client using credentials.json next to this script"""
    try:
        creds_path = str(BASE_DIR / "credentials.json")
        if not os.path.exists(creds_path):
            print(f"❌ credentials.json not found at: {creds_path}")
            return None
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

def get_existing_tm_numbers(sheet):
    """Get existing TM numbers from sheet to avoid duplicates"""
    try:
        worksheet = sheet.worksheet(SHEET_NAME)
        records = worksheet.get_all_records()
        tm_numbers = set()
        
        for record in records:
            tm_col = record.get('TM NO', '')
            if tm_col and tm_col.strip():
                tm_numbers.add(tm_col.strip())
        
        return tm_numbers
    except Exception as e:
        print(f"Error getting existing TM numbers: {e}")
        return set()

def setup_sheet_headers(sheet):
    """Setup headers with emojis"""
    try:
        # Check if worksheet exists, if not create it
        try:
            worksheet = sheet.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Create the worksheet if it doesn't exist
            worksheet = sheet.add_worksheet(title=SHEET_NAME, rows="1000", cols="22")
            print(f"✅ Created new worksheet: {SHEET_NAME}")
        
        headers = [
            "📋 CLIENT NUMBER",
            "👤 CLIENT NAME", 
            "📁 CASE #",
            "📝 CASE NAME",
            "🔢 TM NO",
            "📚 CLASS",
            "📎 FILES",
            "📄 EXT",
            "📄 TM-1",
            "📄 TM-48", 
            "📝 EXAM",
            "✅ ACK",
            "✅ ACCEPTANCE",
            "📋 D-NOTE",
            "📄 TM-16",
            "📄 TM-50",
            "📄 TM-06",
            "🏢 COMPANY",
            "❌ OPPO",
            "📰 PUB",
            "📜 CERTIFICATE",
            "📅 DATE ADDED"
        ]
        worksheet.update(values=[headers], range_name='A1:V1')
        return worksheet
    except Exception as e:
        print(f"Error setting up headers: {e}")
        return None

def upload_to_sheets(records, sheet_id=SHEET_ID):
    """Upload records to Google Sheets with duplicate control"""
    client = get_google_sheets_client()
    if not client:
        return False
    
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = setup_sheet_headers(sheet)
        if not worksheet:
            return False
        
        # Get existing TM numbers
        existing_tm_numbers = get_existing_tm_numbers(sheet)
        
        # Filter out duplicates
        new_records = []
        for record in records:
            tm_no = record.get('TM NO', '').strip()
            if tm_no and tm_no not in existing_tm_numbers:
                new_records.append(record)
                existing_tm_numbers.add(tm_no)
        
        if not new_records:
            print("No new records to upload (all duplicates filtered)")
            return True
        
        # Prepare data for upload
        data = []
        for record in new_records:
            row = [
                record.get('CLIENT NUMBER', ''),
                record.get('CLIENT NAME', ''),
                record.get('CASE #', ''),
                record.get('CASE NAME', ''),
                record.get('TM NO', ''),
                record.get('CLASS', ''),
                record.get('FILES', ''),
                record.get('EXT', ''),
                record.get('TM-1', ''),
                record.get('TM-48', ''),
                record.get('EXAM', ''),
                record.get('ACK', ''),
                record.get('ACCEPTANCE', ''),
                record.get('D-NOTE', ''),
                record.get('TM-16', ''),
                record.get('TM-50', ''),
                record.get('TM-06', ''),
                record.get('COMPANY', ''),
                record.get('OPPO', ''),
                record.get('PUB', ''),
                record.get('CERTIFICATE', ''),
                record.get('DATE ADDED', '')
            ]
            data.append(row)
        
        # Append new records
        worksheet.append_rows(data)
        print(f"✅ Uploaded {len(new_records)} new records to Google Sheets")
        print(f"📊 Filtered out {len(records) - len(new_records)} duplicates")
        return True
        
    except Exception as e:
        print(f"Error uploading to Google Sheets: {e}")
        return False

def export_local(records, filename_prefix):
    """Export data to local Excel and CSV files"""
    if not records:
        print("No records to export!")
        return
    
    df = pd.DataFrame(records)
    columns = [
        "CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS", 
        "FILES", "EXT", "TM-1", "TM-48", "EXAM", "ACK", "ACCEPTANCE", "D-NOTE", 
        "TM-16", "TM-50", "TM-06", "COMPANY", "OPPO", "PUB", "CERTIFICATE", "DATE ADDED"
    ]
    df = df[columns]
    
    # Short file names
    short_names = {
        "consultants_data": "cons_patterns",
        "clients_data": "clients_patterns", 
        "all_data": "all_patterns",
        "custom_data": "custom_patterns"
    }
    
    short_name = short_names.get(filename_prefix, filename_prefix)
    
    # Export to Excel
    excel_file = os.path.join(EXPORT_DIR, f"{short_name}.xlsx")
    df.to_excel(excel_file, index=False, engine='openpyxl')
    
    # Export to CSV
    csv_file = os.path.join(EXPORT_DIR, f"{short_name}.csv")
    df.to_csv(csv_file, index=False)
    
    print(f"💾 Exported {len(records)} records locally:")
    print(f"   📊 Excel: {excel_file}")
    print(f"   📄 CSV: {csv_file}")

def show_menu():
    """Display menu options"""
    print("\n" + "="*60)
    print("    🗂️  DRIVE FOLDERS LIST — Pattern Matcher 🗂️")
    print("="*60)
    print("1. 📁 ALL CLIENTS")
    print("2. 📁 CONSULTANTS")
    print("3. 📁 BOTH Directories")
    print("4. 📁 Custom Path")
    print("5. 📁 Quick Export (Both, No Patterns)")
    print("6. ❌ Exit")
    print("="*60)

def get_upload_choice():
    """Get upload destination choice"""
    while True:
        print("\n📤 Upload destination:")
        print("1. 💾 Local files only")
        print("2. 🌐 Google Sheets only")
        print("3. 💾🌐 Both local and Google Sheets")
        
        choice = input("Enter choice (1-3): ").strip()
        if choice in ['1', '2', '3']:
            return choice
        else:
            print("❌ Invalid choice! Please enter 1-3")

def get_amount_limit():
    """Get amount limit from user"""
    while True:
        try:
            choice = input("Process all records? (y/n): ").lower()
            if choice == 'y':
                return None
            elif choice == 'n':
                amount = int(input("Enter max records to process: "))
                return amount
            else:
                print("Please enter 'y' or 'n'")
        except ValueError:
            print("Please enter a valid number")

def get_custom_path():
    """Get custom path from user"""
    path = input("Enter directory path: ").strip()
    if os.path.exists(path):
        return path
    else:
        print("❌ Path not found!")
        return None

def main():
    consultants_path = r"F:\Brandex004\My Drive\2 CONSULTANTS"
    clients_path = r"F:\Brandex004\My Drive\1 ALL CLIENTS"
    
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-6): ").strip()
            
            if choice == '6':
                print("👋 Goodbye!")
                break
            
            if choice == '5':
                quick_export_both()
                input("\n⏸️ Press Enter to continue...")
                continue
            
            max_records = get_amount_limit()
            upload_choice = get_upload_choice()
            
            if choice == '2':  # Consultant
                print("\n📁 Processing CONSULTANTS...")
                if os.path.exists(consultants_path):
                    records = process_directory(consultants_path, consultants_path + "\\", max_records)
                    handle_upload(records, "consultants_data", upload_choice)
                else:
                    print(f"❌ Path not found: {consultants_path}")
                    
            elif choice == '1':  # All Clients
                print("\n📁 Processing ALL CLIENTS...")
                if os.path.exists(clients_path):
                    records = process_directory(clients_path, clients_path + "\\", max_records)
                    handle_upload(records, "clients_data", upload_choice)
                else:
                    print(f"❌ Path not found: {clients_path}")
                    
            elif choice == '3':
                print("\n📁 Processing BOTH directories...")
                all_records = []
                
                if os.path.exists(clients_path):
                    print("Processing ALL CLIENTS...")
                    records = process_directory(clients_path, clients_path + "\\", max_records)
                    all_records.extend(records)
                    print(f"Found {len(records)} records")
                else:
                    print(f"❌ Path not found: {clients_path}")
                
                if max_records:
                    remaining = max_records - len(all_records)
                    if remaining <= 0:
                        max_records = None
                    else:
                        max_records = remaining
                
                if os.path.exists(consultants_path):
                    print("Processing CONSULTANTS...")
                    records = process_directory(consultants_path, consultants_path + "\\", max_records)
                    all_records.extend(records)
                    print(f"Found {len(records)} records")
                else:
                    print(f"❌ Path not found: {consultants_path}")
                
                handle_upload(all_records, "all_data", upload_choice)
                
            elif choice == '4':
                print("\n📁 Custom path option:")
                custom_path = get_custom_path()
                if custom_path:
                    records = process_directory(custom_path, custom_path + "\\", max_records)
                    handle_upload(records, "custom_data", upload_choice)
                    
            else:
                print("❌ Invalid choice! Please enter 1-6.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Operation cancelled by user.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\n⏸️ Press Enter to continue...")

def handle_upload(records, filename_prefix, upload_choice):
    """Handle upload based on user choice"""
    if not records:
        print("❌ No records to process!")
        return
    
    if upload_choice == '1':
        export_local(records, filename_prefix)
    elif upload_choice == '2':
        upload_to_sheets(records)
    elif upload_choice == '3':
        export_local(records, filename_prefix)
        upload_to_sheets(records)

def quick_export_both():
    """Quick export both directories without pattern matching"""
    consultants_path = r"F:\Brandex004\My Drive\2 CONSULTANTS"
    clients_path = r"F:\Brandex004\My Drive\1 ALL CLIENTS"
    
    all_records = []
    
    # Process 2 CONSULTANTS
    print("Processing 2 CONSULTANTS...")
    if os.path.exists(consultants_path):
        consultants_records = process_directory(consultants_path, consultants_path + "\\", None)
        all_records.extend(consultants_records)
        print(f"Found {len(consultants_records)} records in 2 CONSULTANTS")
    else:
        print(f"Path not found: {consultants_path}")

    # Process 1 ALL CLIENTS
    print("\nProcessing 1 ALL CLIENTS...")
    if os.path.exists(clients_path):
        clients_records = process_directory(clients_path, clients_path + "\\", None)
        all_records.extend(clients_records)
        print(f"Found {len(clients_records)} records in 1 ALL CLIENTS")
    else:
        print(f"Path not found: {clients_path}")
    
    # Export to files
    if all_records:
        df = pd.DataFrame(all_records)
        columns = ["CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS", "FILES", "EXT", "DATE ADDED"]
        df = df[columns]
        
        excel_file = os.path.join(EXPORT_DIR, "drive_data_export.xlsx")
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"\nExported {len(all_records)} records to {excel_file}")
        
        csv_file = os.path.join(EXPORT_DIR, "drive_data_export.csv")
        df.to_csv(csv_file, index=False)
        print(f"Also exported to {csv_file}")
    else:
        print("\nNo records found.")

if __name__ == "__main__":
    main()
