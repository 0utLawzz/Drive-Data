"""
main.py — Data-Shaper V2 CLI entry point.

All logic is now delegated to the scanner package:
  scanner.parser   — folder name parsing
  scanner.detector — document pattern detection
  scanner.scanner  — directory traversal & pipeline
  scanner.exporter — Excel, CSV, Google Sheets export

Configuration is read from config/settings.json.
Logs are written to logs/scan.log and logs/errors.log.
"""

from scanner.scanner import process_directory
from scanner.exporter import export_local, upload_to_sheets, quick_export_local
from utils.helpers import load_settings
from utils.logger import logger

# ---------------------------------------------------------------------------
# Load settings once at startup
# ---------------------------------------------------------------------------
_settings = load_settings()
_CONSULTANTS_PATH = _settings.get("consultants_path", r"F:\Brandex004\My Drive\2 CONSULTANTS")
_CLIENTS_PATH     = _settings.get("clients_path",     r"F:\Brandex004\My Drive\1 ALL CLIENTS")


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def show_menu() -> None:
    print("\n" + "=" * 60)
    print("    🗂️  DRIVE FOLDERS LIST — Pattern Matcher 🗂️")
    print("=" * 60)
    print("1. 📁 ALL CLIENTS")
    print("2. 📁 CONSULTANTS")
    print("3. 📁 BOTH Directories")
    print("4. 📁 Custom Path")
    print("5. 📁 Quick Export (Both, No Patterns)")
    print("6. ❌ Exit")
    print("=" * 60)


def get_upload_choice() -> str:
    while True:
        print("\n📤 Upload destination:")
        print("1. 💾 Local files only")
        print("2. 🌐 Google Sheets only")
        print("3. 💾🌐 Both local and Google Sheets")
        choice = input("Enter choice (1-3): ").strip()
        if choice in ("1", "2", "3"):
            return choice
        print("❌ Invalid choice! Please enter 1-3")


def get_amount_limit() -> int | None:
    while True:
        try:
            choice = input("Process all records? (y/n): ").strip().lower()
            if choice == "y":
                return None
            if choice == "n":
                amount = int(input("Enter max records to process: "))
                return amount
            print("Please enter 'y' or 'n'")
        except ValueError:
            print("Please enter a valid number")


def get_custom_path() -> str | None:
    import os
    path = input("Enter directory path: ").strip()
    if os.path.exists(path):
        return path
    print("❌ Path not found!")
    return None


def handle_upload(records: list, filename_prefix: str, upload_choice: str) -> None:
    """Route records to the correct export destination(s)."""
    if not records:
        logger.info("❌ No records to process!")
        return

    if upload_choice == "1":
        export_local(records, filename_prefix)
    elif upload_choice == "2":
        upload_to_sheets(records)
    elif upload_choice == "3":
        export_local(records, filename_prefix)
        upload_to_sheets(records)


# ---------------------------------------------------------------------------
# Quick export (option 5) — no pattern detection, minimal columns
# ---------------------------------------------------------------------------

def quick_export_both() -> None:
    """Scan both directories quickly without document pattern matching."""
    import os
    all_records = []

    logger.info("Processing CONSULTANTS (quick)...")
    if os.path.exists(_CONSULTANTS_PATH):
        records = process_directory(_CONSULTANTS_PATH, max_records=None)
        all_records.extend(records)
        logger.info("Found %d records in CONSULTANTS", len(records))
    else:
        logger.warning("Path not found: %s", _CONSULTANTS_PATH)

    logger.info("Processing ALL CLIENTS (quick)...")
    if os.path.exists(_CLIENTS_PATH):
        records = process_directory(_CLIENTS_PATH, max_records=None)
        all_records.extend(records)
        logger.info("Found %d records in ALL CLIENTS", len(records))
    else:
        logger.warning("Path not found: %s", _CLIENTS_PATH)

    quick_export_local(all_records, filename="drive_data_export")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    import os

    while True:
        show_menu()

        try:
            choice = input("Enter your choice (1-6): ").strip()

            if choice == "6":
                logger.info("👋 Goodbye!")
                break

            if choice == "5":
                quick_export_both()
                input("\n⏸️ Press Enter to continue...")
                continue

            max_records   = get_amount_limit()
            upload_choice = get_upload_choice()

            if choice == "1":
                logger.info("📁 Processing ALL CLIENTS...")
                if os.path.exists(_CLIENTS_PATH):
                    records = process_directory(_CLIENTS_PATH, max_records=max_records)
                    handle_upload(records, "clients_data", upload_choice)
                else:
                    logger.warning("❌ Path not found: %s", _CLIENTS_PATH)

            elif choice == "2":
                logger.info("📁 Processing CONSULTANTS...")
                if os.path.exists(_CONSULTANTS_PATH):
                    records = process_directory(_CONSULTANTS_PATH, max_records=max_records)
                    handle_upload(records, "consultants_data", upload_choice)
                else:
                    logger.warning("❌ Path not found: %s", _CONSULTANTS_PATH)

            elif choice == "3":
                logger.info("📁 Processing BOTH directories...")
                all_records: list = []

                if os.path.exists(_CLIENTS_PATH):
                    records = process_directory(_CLIENTS_PATH, max_records=max_records)
                    all_records.extend(records)
                    logger.info("Found %d records in ALL CLIENTS", len(records))
                else:
                    logger.warning("❌ Path not found: %s", _CLIENTS_PATH)

                # Adjust remaining limit for second directory
                if max_records is not None:
                    remaining = max_records - len(all_records)
                    max_records = None if remaining <= 0 else remaining

                if os.path.exists(_CONSULTANTS_PATH):
                    records = process_directory(_CONSULTANTS_PATH, max_records=max_records)
                    all_records.extend(records)
                    logger.info("Found %d records in CONSULTANTS", len(records))
                else:
                    logger.warning("❌ Path not found: %s", _CONSULTANTS_PATH)

                handle_upload(all_records, "all_data", upload_choice)

            elif choice == "4":
                logger.info("📁 Custom path option:")
                custom_path = get_custom_path()
                if custom_path:
                    records = process_directory(custom_path, max_records=max_records)
                    handle_upload(records, "custom_data", upload_choice)

            else:
                print("❌ Invalid choice! Please enter 1-6.")

        except KeyboardInterrupt:
            print("\n\n⚠️ Operation cancelled by user.")
            break
        except Exception as exc:
            logger.error("❌ Error: %s", exc)

        input("\n⏸️ Press Enter to continue...")


if __name__ == "__main__":
    main()
