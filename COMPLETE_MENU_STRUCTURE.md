# Complete Menu Structure

## Main Menu (main.py)

```
┌────────────────────────────────────────────────┐
│  🚀 LlamaParse CLI  •  PDF Intelligence        │
└────────────────────────────────────────────────┘

Session Snapshot
┌─────────────────────────────┬────────┐
│ Metric                      │  Count │
├─────────────────────────────┼────────┤
│ Unparsed PDFs               │      0 │
│ Parsed Subjects             │     68 │
│ Years Covered               │      2 │
│ Subjects w/ parsed not      │      0 │
│   merged                    │        │
│ Merged not cleaned          │      0 │
└─────────────────────────────┴────────┘

┌────────────────────────────────────┐
│  1   PDF Parsing Utilities         │
│  2   Merging & Cleaning Markdown   │
│  3   CSV Quality Control           │
│  4   Database Management (NEW)     │
│  5   Full Statistics               │
│  6   Exit                          │
└────────────────────────────────────┘
```

### Option 1: PDF Parsing Utilities

Submenu for parsing PDFs with LlamaParse:
- Parse single PDF
- Parse multiple PDFs
- Parse all unparsed PDFs
- View parsed subjects
- Return to main menu

### Option 2: Merging & Cleaning Markdown

Submenu for markdown operations:
- Merge parsed files for specific subject
- Merge all unmerged subjects
- Clean markdown for specific subject
- Clean all uncleaned subjects
- Extract JSON data (AI extraction with Gemini)
- View markdown status
- Return to main menu

### Option 3: CSV Quality Control

```
┌─────────────────────────────────────────────┐
│  📊 CSV Quality Control Menu                │
│  BD_doentes.csv Quality Analysis            │
└─────────────────────────────────────────────┘

Individual Column Analysis:
 1   ID column (serial_id, year)
 2   processo column (patient process number)
 3   nome column (patient name)
 4   data_ent column (admission date)
 5   data_alta column (discharge date)
 6   destino column (discharge destination)
 7   sexo column (gender)
 8   data_nasc column (birth date)
 9   origem column (admission origin)

Comprehensive Options:
 10  Run all column checks
 11  Generate complete report
 12  Create clean dataset (BD_doentes_clean.csv)

 0   Return to main menu
```

### Option 4: Database Management (NEW)

```
┌────────────────────────────────────┐
│  🗄️  Database Management           │
│  MongoDB - UQ Database             │
└────────────────────────────────────┘

📊 Database Import Status
┌────────────────────────────┬────────┬────────────┐
│ Category                   │  Count │ Percentage │
├────────────────────────────┼────────┼────────────┤
│ Total Subjects             │     68 │    100.0%  │
│                            │        │            │
│ With Extracted JSON        │      1 │      1.5%  │
│ Without Extracted JSON     │     67 │     98.5%  │
│                            │        │            │
│ Imported to Database       │      1 │    100.0%  │
│ Not Yet Imported           │      0 │      0.0%  │
└────────────────────────────┴────────┴────────────┘

 1   Import all not-yet-imported subjects
 2   Import single subject by ID
 3   View database statistics
 4   Query database
 5   Refresh status
 0   Return to main menu
```

### Option 5: Full Statistics

Detailed project statistics:
- Total PDFs overview
- Parsed subjects count
- Year-based analysis with document counts
- Merge and clean status
- Comprehensive project metrics

### Option 6: Exit

Clean exit from application

## Complete Workflow

### Data Pipeline

```
1. PDF Files
   ↓ (Option 1: Parse with LlamaParse)
2. Parsed Markdown Files
   ↓ (Option 2: Merge & Clean)
3. Cleaned Markdown + Extracted JSON
   ↓ (Option 4: Import to Database)
4. MongoDB Database (UQ.internamentos)

Parallel:
CSV Data → (Option 3: Quality Control) → Clean CSV
```

### Typical Usage Pattern

**Initial Setup:**
1. Run main menu: `uv run python main.py`
2. Option 1: Parse PDFs (if any unparsed)
3. Option 2: Merge and clean markdown
4. Option 2: Extract JSON data with AI
5. Option 4: Import extracted data to database
6. Option 3: Quality control CSV data

**Regular Usage:**
1. Option 4: Check database import status
2. Option 4: Import new subjects
3. Option 3: Verify CSV data quality
4. Option 5: View project statistics

## Menu Integration Pattern

All menus follow consistent pattern:
- Rich terminal UI with colored output
- Progress bars for long operations
- Confirmation prompts for destructive actions
- Clear error messages
- Easy navigation (number selection)
- Breadcrumb trail (where you are)

## Technology Stack

**Terminal UI:**
- Rich library for all menus
- Tables, panels, progress bars
- Color-coded output
- Box drawing characters

**Data Processing:**
- LlamaParse for PDF parsing
- Markdown processing utilities
- pandas for CSV analysis
- Google Gemini for AI extraction

**Database:**
- MongoDB with pymongo
- Embedded document structure
- Indexed collections
- Connection pooling

**Package Management:**
- uv for dependency management
- Python 3.13
- Virtual environment isolation

## Documentation Structure

```
theparser/
├── main.py                          # Main menu entry point
├── README.md                        # Project overview
├── MENU_FIX.md                      # Main menu behavior fixes
│
├── csv/
│   ├── csv_menu.py                  # CSV quality control menu
│   ├── README.md                    # CSV module documentation
│   ├── IMPLEMENTATION.md            # CSV implementation details
│   └── CHANGES.md                   # CSV changes log
│
└── database/
    ├── db_menu.py                   # Database management menu (NEW)
    ├── db_manager.py                # MongoDB connection manager
    ├── data_importer.py             # JSON import functionality
    ├── query_examples.py            # Query examples
    ├── DB_MENU.md                   # Database menu docs (NEW)
    ├── IMPLEMENTATION_SUMMARY.md    # Implementation summary (NEW)
    └── README.md                    # Database module overview
```

## Quick Reference

**Launch main menu:**
```bash
uv run python main.py
```

**Standalone menus:**
```bash
uv run python csv/csv_menu.py
uv run python database/db_menu.py
```

**Direct operations:**
```bash
# Parse single PDF
uv run python main.py --parse-only

# Full pipeline
uv run python main.py --full

# Merge only
uv run python main.py --merge-only

# Clean only
uv run python main.py --clean-only
```

## Menu Hierarchy

```
Main Menu (main.py)
│
├── 1. PDF Parsing (menu_llamaparse)
│   ├── Parse single PDF
│   ├── Parse multiple PDFs
│   ├── Parse all unparsed
│   └── View parsed subjects
│
├── 2. Markdown Utils (menu_markdown_utils)
│   ├── Merge parsed files
│   ├── Merge all unmerged
│   ├── Clean markdown
│   ├── Clean all uncleaned
│   ├── Extract JSON data
│   └── View status
│
├── 3. CSV Quality Control (csv/csv_menu.py) ← subprocess
│   ├── 9 individual column analyses
│   ├── Run all checks
│   ├── Generate report
│   └── Create clean dataset
│
├── 4. Database Management (database/db_menu.py) ← NEW
│   ├── Import all pending
│   ├── Import single subject
│   ├── View statistics
│   ├── Query examples
│   └── Refresh status
│
├── 5. Full Statistics
│   └── Comprehensive project metrics
│
└── 6. Exit
```

## Summary

The system now provides a complete, menu-driven workflow for:
1. **PDF Processing** - Parse with LlamaParse
2. **Markdown Processing** - Merge and clean
3. **CSV Quality Control** - Analyze and clean CSV data
4. **Database Management** - Import and query MongoDB (NEW)
5. **Statistics** - Monitor project status

All menus are:
- Interactive with Rich UI
- Well-documented
- Error-handled
- User-friendly
- Consistent in design
