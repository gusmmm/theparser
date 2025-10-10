# Database Menu - Quick Start Guide

## Installation

No additional installation needed! The database menu is integrated into the main project.

## Prerequisites

1. **MongoDB running locally:**
   ```bash
   # Check if MongoDB is running
   systemctl status mongodb
   # or on macOS
   brew services list | grep mongodb
   ```

2. **Project environment:**
   ```bash
   cd /home/gusmmm/Desktop/theparser
   # Environment is automatically managed by uv
   ```

## Quick Start

### Method 1: Via Main Menu (Recommended)

```bash
uv run python main.py
```

Then select **Option 4: Database Management**

### Method 2: Standalone

```bash
uv run python database/db_menu.py
```

## What You'll See

When the database menu opens, you'll immediately see:

```
🗄️  Database Management
MongoDB - UQ Database

📊 Database Import Status
┌────────────────────────────────┬────────────┬──────────────┐
│ Category                       │      Count │   Percentage │
├────────────────────────────────┼────────────┼──────────────┤
│ Total Subjects                 │         68 │       100.0% │
│ With Extracted JSON            │          1 │         1.5% │
│ Without Extracted JSON         │         67 │        98.5% │
│ Imported to Database           │          1 │       100.0% │
│ Not Yet Imported               │          0 │         0.0% │
└────────────────────────────────┴────────────┴──────────────┘
```

## Common Tasks

### Import All Pending Subjects

1. Open database menu
2. Select option **1** (Import all not-yet-imported subjects)
3. Review the list
4. Confirm with **Y**
5. Watch the progress bar
6. See results summary

### Import Single Subject

1. Open database menu
2. Select option **2** (Import single subject by ID)
3. Enter subject ID (e.g., **2401**)
4. See import result

### Check Database Statistics

1. Open database menu
2. Select option **3** (View database statistics)
3. See:
   - Connection status
   - Collections list
   - Document counts
   - Database size
   - Indexes

### Run Query Examples

1. Open database menu
2. Select option **4** (Query database)
3. Interactive query examples launch:
   - List all internamentos
   - Search by patient process number
   - Count internamentos by year
   - Find patients with multiple burns

### Refresh Status

1. Open database menu
2. Select option **5** (Refresh status)
3. Re-scans folders and database
4. Updates statistics

## Understanding the Statistics

**Total Subjects:** All folders in `pdf/output/` (4-digit names)

**With Extracted JSON:** Folders containing `{id}_extracted.json`
- These are ready to import
- Already processed through AI extraction

**Without Extracted JSON:** Folders missing extraction file
- Need to run through extraction pipeline first
- Use option 2 in main menu: "Merging & Cleaning Markdown" → "Extract JSON data"

**Imported to Database:** Extracted JSONs successfully imported to MongoDB
- Safe in database
- Queryable
- Backed up

**Not Yet Imported:** Extracted JSONs not yet in database
- Ready to import
- Use option 1 to import all

## Typical Workflow

### First Time Setup

```bash
# 1. Start main menu
uv run python main.py

# 2. Parse PDFs (if needed) - Option 1
# 3. Merge and extract JSON - Option 2
# 4. Import to database - Option 4
```

### Regular Usage

```bash
# 1. Launch main menu
uv run python main.py

# 2. Check database status - Option 4
# 3. Import new subjects if any pending
# 4. Query database as needed
```

## Error Handling

### MongoDB Not Running

**Error:**
```
✗ Failed to connect to MongoDB
```

**Solution:**
```bash
# Start MongoDB
sudo systemctl start mongodb
# or on macOS
brew services start mongodb-community
```

### No Extracted JSON Files

**Status:**
```
Not Yet Imported: 0
(No subjects ready to import)
```

**Solution:**
Run the extraction pipeline first:
1. Main menu → Option 2: Merging & Cleaning Markdown
2. Select "Extract JSON data"
3. Choose subjects to extract
4. Return to database menu

### Subject Already Imported

**Message:**
```
⚠ Subject 2401 already in database
```

**This is normal!** The system prevents duplicates automatically.

## Tips

1. **Always check status first** - The menu shows you exactly what needs to be done

2. **Batch import is faster** - Use option 1 to import all at once

3. **Refresh after changes** - Press 5 to refresh if you made changes externally

4. **Query examples are your friend** - Option 4 shows you how to query the database

5. **Statistics tell the story** - Watch the percentages to track progress

## What Gets Imported

Each extracted JSON contains:
- **doente** (patient): processo, nome, data_nascimento, sexo
- **internamento** (admission): numero_internamento, data_entrada, data_alta, dias_internamento
- **queimaduras** (burns): array of burn records
- **procedimentos** (procedures): array of procedures
- **infecoes** (infections): array of infections
- **antibioticos** (antibiotics): array of medications
- **traumas** (traumas): array of trauma records
- **patologias** (pathologies): array of pathologies
- **medicacoes** (medications): array of medications

## Database Structure

**Database Name:** UQ (Unidade de Queimados)

**Collection:** internamentos

**Unique Key:** `internamento.numero_internamento`

**Indexes:**
- numero_internamento (unique)
- doente.numero_processo
- internamento.data_entrada
- doente.nome
- Compound indexes for complex queries

## Need Help?

**Check documentation:**
- `database/DB_MENU.md` - Full database menu documentation
- `database/IMPLEMENTATION_SUMMARY.md` - Implementation details
- `COMPLETE_MENU_STRUCTURE.md` - Complete menu hierarchy

**Common issues:**
1. MongoDB not running → Start MongoDB service
2. No extracted JSONs → Run extraction pipeline first
3. Import fails → Check JSON file format
4. Connection timeout → Check MongoDB configuration

## Summary

The database menu is your control center for managing imported medical records:
- ✅ Automatic status analysis
- ✅ Batch and single import
- ✅ Statistics and monitoring
- ✅ Query examples
- ✅ Real-time refresh
- ✅ Error handling
- ✅ Rich terminal UI

Just run `uv run python main.py` and select option 4!
