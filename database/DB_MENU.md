# Database Menu Documentation

## Overview

The Database Management menu provides comprehensive tools for managing the UQ MongoDB database, including:
- Automatic analysis of extraction and import status
- Batch and single-subject import functionality
- Database statistics and queries
- Real-time monitoring of the import pipeline

## File Structure

```
database/
├── db_menu.py              # Main database menu (NEW)
├── db_manager.py           # MongoDB connection manager
├── data_importer.py        # JSON import functionality
└── query_examples.py       # Query examples and patterns
```

## Database Menu Features

### 1. Automatic Status Analysis

When the database menu opens, it automatically:
- Scans all folders in `pdf/output/` for subject IDs
- Checks each folder for `{subject_id}_extracted.json` files
- Queries the MongoDB database to determine import status
- Displays comprehensive statistics

**Output:**
```
📊 Database Import Status
┌────────────────────────────┬────────┬────────────┐
│ Category                   │  Count │ Percentage │
├────────────────────────────┼────────┼────────────┤
│ Total Subjects             │     68 │    100.0%  │
│                            │        │            │
│ With Extracted JSON        │     45 │     66.2%  │
│ Without Extracted JSON     │     23 │     33.8%  │
│                            │        │            │
│ Imported to Database       │      1 │      2.2%  │
│ Not Yet Imported           │     44 │     97.8%  │
└────────────────────────────┴────────┴────────────┘
```

### 2. Menu Options

**Option 1: Import all not-yet-imported subjects**
- Imports all subjects that have extracted JSON but are not in database
- Shows progress bar during batch import
- Reports success/failure statistics
- Skips duplicates automatically

**Option 2: Import single subject by ID**
- Prompts for 4-digit subject ID
- Imports that specific subject
- Validates JSON file exists
- Reports success or error

**Option 3: View database statistics**
- Shows MongoDB connection status
- Lists all collections and document counts
- Displays database size and indexes
- Shows collection statistics

**Option 4: Query database**
- Launches interactive query examples
- Shows common query patterns with code
- Demonstrates aggregation pipelines
- Examples: list internamentos, search by patient, count by year

**Option 5: Refresh status**
- Re-scans pdf/output/ folders
- Re-queries database
- Updates statistics display
- Useful after external changes

### 3. Key Functions

**`analyze_extraction_status(base_output_dir)`**
- Scans all subject folders in pdf/output/
- Checks for extracted JSON files
- Queries database for existing imports
- Returns comprehensive statistics dict

**`display_extraction_statistics(results)`**
- Formats statistics in Rich tables
- Shows percentage calculations
- Optionally lists subjects (if not too many)
- Color-coded output (green=success, yellow=warning, red=error)

**`import_single_subject(subject_id, base_output_dir)`**
- Imports one subject's extracted JSON
- Connects to database
- Creates indexes if needed
- Handles duplicates gracefully

**`import_all_subjects(results, base_output_dir)`**
- Batch imports multiple subjects
- Shows progress with Rich progress bar
- Reports detailed results
- Requires user confirmation

## Integration with Main Menu

The database menu is integrated as **Option 4** in the main menu:

```python
elif choice == "4":
    # Launch Database Management menu
    from database.db_menu import menu_database
    if CONSOLE:
        CONSOLE.print("[cyan]Launching Database Management menu...[/cyan]")
    await menu_database(base_output_dir=base_output_dir)
    if CONSOLE:
        CONSOLE.print("[green]Returned from Database menu[/green]")
```

**Main menu structure:**
1. PDF Parsing Utilities
2. Merging & Cleaning Markdown
3. CSV Quality Control
4. **Database Management** (NEW)
5. Full Statistics
6. Exit

## MongoDB Structure

**Database:** UQ (Unidade de Queimados)

**Collection:** internamentos

**Document Structure:**
```json
{
  "doente": {
    "numero_processo": 23056175,
    "nome": "Patient Name",
    "data_nascimento": "1990-01-01",
    "sexo": "M"
  },
  "internamento": {
    "numero_internamento": 2401,
    "data_entrada": "2024-01-15",
    "data_alta": "2024-02-20",
    "dias_internamento": 36,
    "destino_alta": "Domicilio"
  },
  "queimaduras": [...],
  "procedimentos": [...],
  "infecoes": [...],
  "antibioticos": [...],
  "traumas": [...],
  "patologias": [...],
  "medicacoes": [...]
}
```

**Indexes:**
- `internamento.numero_internamento` (unique)
- `doente.numero_processo`
- `internamento.data_entrada`
- `doente.nome`
- Compound indexes for complex queries

## Usage Examples

### Running the Database Menu

**From main menu:**
```bash
uv run python main.py
# Select option 4: Database Management
```

**Standalone:**
```bash
uv run python database/db_menu.py
```

### Importing Subjects

**Import all pending:**
1. Open database menu (option 4)
2. Review statistics showing not-yet-imported subjects
3. Select option 1: "Import all not-yet-imported subjects"
4. Confirm import
5. Watch progress bar and results

**Import single subject:**
1. Open database menu (option 4)
2. Select option 2: "Import single subject by ID"
3. Enter subject ID (e.g., "2401")
4. View import result

## Error Handling

The database menu includes comprehensive error handling:

- **Missing directories:** Clear error messages if pdf/output/ not found
- **Database connection failures:** Graceful fallback, reports unavailable
- **Import errors:** Per-subject error reporting with details
- **Duplicate prevention:** Automatically skips already-imported subjects
- **Invalid JSON:** Catches and reports parsing errors

## Statistics Interpretation

**Total Subjects:** Count of all 4-digit folders in pdf/output/

**With Extracted JSON:** Folders containing `{id}_extracted.json` file

**Without Extracted JSON:** Folders missing extraction (need parsing + AI extraction)

**Imported to Database:** Extracted JSONs with matching `numero_internamento` in database

**Not Yet Imported:** Extracted JSONs ready to import but not yet in database

## Technical Details

**Technology Stack:**
- **Rich:** Terminal UI, tables, progress bars, panels
- **pymongo:** MongoDB Python driver (v4.15.3)
- **MongoDB:** v8.2.1, local instance at localhost:27017
- **Python:** 3.13 with type annotations
- **asyncio:** Async menu integration with main.py

**Performance:**
- Parallel checking during analysis (progress bar)
- Batch import with connection pooling
- Index optimization for fast queries
- Efficient JSON parsing with validation

## Future Enhancements

Potential additions:
- Export database to CSV for analysis
- Advanced query builder
- Data validation and quality checks
- Backup and restore functionality
- Migration tools for schema changes
- Analytics dashboard with charts

## Troubleshooting

**Menu won't open:**
- Check MongoDB is running: `systemctl status mongodb` or `brew services list`
- Verify connection: `mongosh --host localhost --port 27017`

**Import fails:**
- Check JSON file format matches expected structure
- Verify `numero_internamento` exists in JSON
- Ensure database has write permissions
- Check disk space

**Statistics show 0:**
- Verify pdf/output/ directory exists and has subject folders
- Check folder naming (must be 4-digit numbers)
- Confirm extracted JSON files have correct naming: `{id}_extracted.json`

## Related Documentation

- `database/README.md` - Database module overview
- `csv/README.md` - CSV quality control
- `MENU_FIX.md` - Main menu behavior fixes
- `csv/CHANGES.md` - CSV menu integration

## Change Log

**2025-10-10 - Initial Implementation**
- Created `db_menu.py` with 6 menu options
- Implemented extraction status analysis
- Added batch and single import functionality
- Integrated with main menu as option 4
- Created query examples integration
- Comprehensive error handling and Rich UI
