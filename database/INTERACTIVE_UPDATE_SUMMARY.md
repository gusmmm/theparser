# Interactive Update Implementation - Summary

**Date:** 2025-10-10
**Feature:** Interactive database updater with field selection

## Changes Made

### 1. Fixed `ano_internamento` Lookup

**Problem:** The validator and updater were looking for `ano_internamento` in the wrong location.
- **Before:** `internamento.ano_internamento` (nested, doesn't exist)
- **After:** `ano_internamento` (root level of document)

**Files Modified:**
- `database/data_validator.py` - Now checks root level first, falls back to calculation
- `database/data_updater.py` - Changed path from `internamento.ano_internamento` to `ano_internamento`

**Result:** Now correctly detects the discrepancy:
- Database: `ano_internamento: 2023`
- CSV: `year: 2024`
- Status: ✗ (mismatch detected)

### 2. Created Interactive Updater

**New File:** `database/interactive_updater.py` (372 lines)

**Features:**
- **Numbered field display** - Each discrepancy gets a row number (1, 2, 3, ...)
- **Per-record review** - See all discrepancies for each internamento
- **Four action options:**
  - `a` - Update all fields for this record
  - `s` - Select specific fields by number (e.g., "1,3,4")
  - `n` - Skip this record
  - `q` - Quit and save selections so far
- **Field selection** - Enter comma-separated numbers or "all"
- **Update summary** - Shows what will be updated before execution
- **Final confirmation** - Must confirm before database modification
- **Progress tracking** - Rich progress bar during updates
- **Result reporting** - Detailed success/failure statistics

**Key Functions:**
- `display_discrepancies_interactive()` - Interactive field selection
- `get_mongo_path()` - Maps field names to MongoDB paths
- `display_update_summary()` - Shows selection summary
- `execute_selected_updates()` - Performs the updates
- `interactive_update_main()` - Main orchestration

### 3. Updated Database Menu

**Modified:** `database/db_menu.py`

**Changes:**
- **Option 7 label:** "Update database from CSV (LIVE)" → "Update database from CSV (interactive)"
- **Option 7 behavior:** Now launches `interactive_updater.py` instead of `data_updater.py --live`
- **User experience:** More intuitive - review and select instead of all-or-nothing

### 4. Created Documentation

**New File:** `database/INTERACTIVE_UPDATER.md`

Complete user guide covering:
- Overview and features
- Usage instructions
- Interactive workflow steps
- Example sessions
- Field selection tips
- Safety features
- Troubleshooting
- Best practices

## Test Results

### Validation Test

With the `ano_internamento` fix, the validator now correctly shows 4 discrepancies for record 2401:

```
Field Discrepancies
Field              Database              CSV             Match
ano_internamento   2023                  2024            ✗
data_entrada       2023-12-31            2024-01-04      ✗
data_alta          2024-01-26            2024-01-22      ✗
destino_alta       consulta externa...   enfcp           ✗
```

### Interactive Updater Test

The interactive updater displays:

```
                    Field Discrepancies
╭──────┬──────────────────────┬─────────────────┬───────────────╮
│   No │ Field                │ Database Value  │ CSV Value     │
├──────┼──────────────────────┼─────────────────┼───────────────┤
│    1 │ ano_internamento     │ 2023            │ 2024          │
│    2 │ data_entrada         │ 2023-12-31      │ 2024-01-04    │
│    3 │ data_alta            │ 2024-01-26      │ 2024-01-22    │
│    4 │ destino_alta         │ consulta externa│ enfcp         │
╰──────┴──────────────────────┴─────────────────┴───────────────╯

Options:
  a - Update all fields for this record
  s - Select specific fields to update
  n - Skip this record
  q - Quit (save selections so far)
```

Row numbers display correctly and allow precise field selection.

## Usage Examples

### Example 1: Update All Fields

```bash
uv run python database/interactive_updater.py

# When prompted:
What would you like to do? [a/s/n/q] (n): a
✓ Queued all 4 fields for update

# Confirm:
⚠ This will modify the database. Continue? [y/N]: y
✓ 1 record(s) updated successfully
```

### Example 2: Update Only Dates

```bash
uv run python database/interactive_updater.py

# When prompted:
What would you like to do? [a/s/n/q] (n): s

Enter field numbers to update (comma-separated, e.g., 1,3,4) or 'all':
Fields to update: 2,3

✓ Queued 2 field(s) for update

# Confirm and execute:
⚠ This will modify the database. Continue? [y/N]: y
✓ 1 record(s) updated successfully
```

### Example 3: Via Database Menu

```bash
uv run python main.py
# → Option 4: Database Management
# → Option 7: Update database from CSV (interactive)
# Review and select fields interactively
```

## Field Mapping Reference

| Comparison Field   | MongoDB Path               | CSV Field  | Type   |
|--------------------|----------------------------|------------|--------|
| ano_internamento   | ano_internamento           | year       | number |
| numero_processo    | doente.numero_processo     | processo   | number |
| nome               | doente.nome                | nome       | string |
| data_entrada       | internamento.data_entrada  | data_ent   | date   |
| data_alta          | internamento.data_alta     | data_alta  | date   |
| destino_alta       | internamento.destino_alta  | destino    | string |
| data_nascimento    | doente.data_nascimento     | data_nasc  | date   |
| data_queimadura    | queimaduras.0.data         | data_queim | date   |

## Benefits

### Over Automatic Update

- **Selective control** - Choose exactly which fields to update
- **Review confidence** - See what changes before committing
- **Granular decisions** - Different choices for different records
- **Less risky** - Update only what you're confident about

### Over Manual Update

- **Faster** - No manual MongoDB commands needed
- **Tracked** - All updates get timestamps automatically
- **Validated** - Data normalized before update
- **Reported** - Clear statistics on what was updated

## Safety Features

1. **Preview discrepancies** - See all differences before deciding
2. **Field-by-field selection** - Choose specific fields per record
3. **Quit anytime** - Save selections and stop reviewing
4. **Final confirmation** - Must confirm before database modification
5. **Update metadata** - All changes tracked with `updated_at` and `updated_from_csv`
6. **Error handling** - Failed updates reported clearly
7. **Progress tracking** - Visual feedback during updates

## Updated Menu Structure

The database menu now offers three update paths:

1. **Option 5:** Validate data vs CSV
   - Read-only validation
   - View discrepancies
   - Export report

2. **Option 6:** Update database (dry run)
   - Simulate updates
   - See what would change
   - No database modification

3. **Option 7:** Update database (interactive) ← **NEW**
   - Review each discrepancy
   - Select fields to update
   - Actually modifies database

## Updated Record Example

After interactive update:

```json
{
  "_id": ObjectId("..."),
  "ano_internamento": 2024,           // ← Updated (was 2023)
  "doente": {
    "numero_processo": 23056175,
    "nome": "maria goreti pereira de p",
    "data_nascimento": "1966-01-21"
  },
  "internamento": {
    "numero_internamento": 2401,
    "data_entrada": "2024-01-04",     // ← Updated (was 2023-12-31)
    "data_alta": "2024-01-22",        // ← Updated (was 2024-01-26)
    "destino_alta": "enfcp"           // ← Updated (was "consulta externa...")
  },
  "queimaduras": [...],
  "updated_at": "2025-10-10T15:45:30.123456",  // ← Added
  "updated_from_csv": true                      // ← Added
}
```

## Files Modified

1. **`database/data_validator.py`** (MODIFIED)
   - Fixed `ano_internamento` lookup to check root level first

2. **`database/data_updater.py`** (MODIFIED)
   - Fixed `ano_internamento` path to `ano_internamento` (not nested)

3. **`database/interactive_updater.py`** (NEW)
   - 372 lines
   - Complete interactive update system

4. **`database/db_menu.py`** (MODIFIED)
   - Changed option 7 label
   - Changed option 7 to launch interactive updater

5. **`database/INTERACTIVE_UPDATER.md`** (NEW)
   - Complete user guide
   - Examples and tips

## Query Updated Records

```javascript
// Find all updated records
db.internamentos.find({updated_from_csv: true})

// Find records updated in last hour
db.internamentos.find({
  updated_at: {
    $gte: new Date(Date.now() - 3600000).toISOString()
  }
})

// Check which fields were updated for a record
db.internamentos.findOne({
  "internamento.numero_internamento": 2401
})
```

## Future Enhancements

Potential improvements:
- Field-level undo (restore original value)
- Bulk operations (update same field across multiple records)
- Comparison mode (show before/after side by side)
- Export selection to script for reproducibility
- Conflict resolution suggestions
- Automated decision rules (e.g., always trust CSV dates)

## Summary

Successfully implemented an interactive database updater with:
- ✅ Fixed `ano_internamento` lookup (root level)
- ✅ Numbered field display for selection
- ✅ Four action options (all/select/skip/quit)
- ✅ Field selection by number
- ✅ Update summary before execution
- ✅ Final confirmation prompt
- ✅ Progress tracking and results
- ✅ Update metadata tracking
- ✅ Menu integration
- ✅ Complete documentation

The system now provides maximum control over selective database updates while maintaining safety and traceability!
