# Data Validation and Update System

## Overview

The data validation and update system compares MongoDB records with the authoritative CSV data (`BD_doentes_clean.csv`) and provides tools to update the database with corrected information.

## Components

### 1. Data Validator (`data_validator.py`)

**Purpose:** Compare all internamento records in MongoDB with corresponding rows in the CSV file.

**Features:**
- Loads CSV data into memory for fast comparison
- Iterates through all MongoDB documents
- Compares 8 key fields:
  - `ano_internamento` ↔ CSV `year`
  - `doente.numero_processo` ↔ CSV `processo`
  - `doente.nome` ↔ CSV `nome`
  - `internamento.data_entrada` ↔ CSV `data_ent`
  - `internamento.data_alta` ↔ CSV `data_alta`
  - `internamento.destino_alta` ↔ CSV `destino`
  - `doente.data_nascimento` ↔ CSV `data_nasc`
  - `internamento.data_queimadura` ↔ CSV `data_queim`
- Normalizes dates for comparison (handles various formats)
- Normalizes strings (lowercase, trimmed)
- Generates detailed comparison reports

**Output:**
- Validation summary table (perfect matches, discrepancies, not in CSV)
- Field-level discrepancy breakdown
- Detailed comparison tables for records with mismatches
- Exported CSV report at `reports/data_validation_report.csv`

**Usage:**
```bash
# Standalone
uv run python database/data_validator.py

# From database menu - Option 5
```

**Example Output:**
```
📊 Validation Summary
┌────────────────────────────────┬────────────┬──────────────┐
│ Category                       │      Count │   Percentage │
├────────────────────────────────┼────────────┼──────────────┤
│ Total Internamentos            │          1 │       100.0% │
│ Perfect Matches                │          0 │         0.0% │
│ With Discrepancies             │          1 │       100.0% │
│ Not in CSV                     │          0 │         0.0% │
└────────────────────────────────┴────────────┴──────────────┘

Field-Level Discrepancies
  Field          Discrepancies   Percentage
  data_entrada               1       100.0%
  data_alta                  1       100.0%
  destino_alta               1       100.0%
```

### 2. Data Updater (`data_updater.py`)

**Purpose:** Update MongoDB records with validated data from CSV file.

**Features:**
- Two modes: **DRY RUN** (default) and **LIVE UPDATE**
- Validates data before updating
- Shows preview of records to be updated
- Requires user confirmation for live updates
- Adds metadata to updated records:
  - `updated_at`: ISO timestamp of update
  - `updated_from_csv`: Boolean flag (true)
- Performs batch updates with progress bar
- Verifies updates after completion
- Detailed statistics and reporting

**Safety Features:**
- Default mode is DRY RUN (no changes)
- Double confirmation required for live updates
- Preview of changes before execution
- Verification step after updates
- Transaction-safe updates

**Usage:**
```bash
# Dry run (default) - no changes made
uv run python database/data_updater.py

# Live update - actually modifies database
uv run python database/data_updater.py --live

# From database menu:
# - Option 6: Dry run
# - Option 7: Live update (requires confirmation)
```

**Example Output:**
```
📝 Data Updater - DRY RUN
Update MongoDB with CSV data

Step 1: Validating data...
[validation summary]

Step 2: Updating records...
Records to Update
  Internamento   Fields to Update
  2401           data_entrada, data_alta, destino_alta

DRY RUN: Would update 2401
✓ Successfully updated 1 records
```

## Database Menu Integration

The validation and update tools are integrated into the database menu with new options:

**Updated Menu Structure:**
```
1. Import all not-yet-imported subjects
2. Import single subject by ID
3. View database statistics
4. Query database
5. Validate data vs CSV (NEW)
6. Update database from CSV (dry run) (NEW)
7. Update database from CSV (LIVE) (NEW)
8. Refresh status
0. Return to main menu
```

## Field Comparison Details

### Date Fields

Dates are normalized to `YYYY-MM-DD` format before comparison:
- Handles multiple input formats: `DD-MM-YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`, `YYYY/MM/DD`
- Empty or missing dates are handled gracefully
- Comparison is exact after normalization

**Example:**
- DB: `2023-12-31`
- CSV: `2024-01-04`
- Result: ✗ (different dates)

### String Fields

Strings are normalized (lowercase, trimmed) before comparison:
- Case-insensitive comparison
- Leading/trailing whitespace removed
- Empty strings treated consistently

**Example:**
- DB: `Consulta Externa - CEX Cirurgia Plástica`
- CSV: `ENFCP`
- Result: ✗ (different strings)

### Number Fields

Numbers are compared as integers:
- `numero_processo`: Patient process number
- `ano_internamento`: Year of admission

**Example:**
- DB: `23056175`
- CSV: `23056175`
- Result: ✓ (match)

## Update Process

### Step 1: Validation

1. Load CSV data (738 records)
2. Query all internamentos from MongoDB
3. Compare each field
4. Generate discrepancy report

### Step 2: Preparation

1. Identify records with discrepancies
2. Prepare update operations for each field
3. Show preview of changes
4. Request confirmation (if live mode)

### Step 3: Update (if confirmed)

1. For each record with discrepancies:
   - Update mismatched fields with CSV values
   - Add `updated_at` timestamp
   - Add `updated_from_csv: true` flag
2. Show progress bar during updates
3. Report success/failure for each record

### Step 4: Verification (live mode only)

1. Count records with `updated_from_csv` flag
2. Count records with `updated_at` timestamp
3. Show sample of updated records
4. Verify consistency

## Updated Record Structure

After update, records have additional metadata:

```json
{
  "internamento": {
    "numero_internamento": 2401,
    "data_entrada": "2024-01-04",  // ← Updated from CSV
    "data_alta": "2024-01-22",     // ← Updated from CSV
    "destino_alta": "ENFCP"        // ← Updated from CSV
  },
  "doente": { ... },
  "queimaduras": [ ... ],
  "updated_at": "2025-10-10T14:23:45.123456",  // ← Added
  "updated_from_csv": true                     // ← Added
}
```

## Workflow Examples

### Example 1: Check Data Quality

```bash
# 1. Run validator
uv run python database/data_validator.py

# 2. Review validation summary
# - How many records have discrepancies?
# - Which fields are problematic?
# - Check detailed comparison tables

# 3. Review exported report
# reports/data_validation_report.csv
```

### Example 2: Update Database (Safe)

```bash
# 1. Test with dry run first
uv run python database/data_updater.py

# Output shows:
# - What would be updated
# - Which fields would change
# - How many records affected

# 2. If satisfied, run live update
uv run python database/data_updater.py --live

# Confirm: Are you absolutely sure? [y/N]: y

# 3. Verify updates
# - Check verification results
# - Query updated records
```

### Example 3: Via Database Menu

```bash
# 1. Launch main menu
uv run python main.py

# 2. Select option 4: Database Management

# 3. Select option 5: Validate data vs CSV
# - Review validation results
# - Press Enter to return to menu

# 4. Select option 6: Update database (dry run)
# - Review what would be updated
# - Press Enter to return to menu

# 5. If satisfied, select option 7: Update database (LIVE)
# - Confirm: Are you absolutely sure? [y/N]: y
# - Confirm again in the tool
# - Watch progress and results
```

## Test Results

**Current Status (2025-10-10):**
- Total internamentos in database: 1 (subject 2401)
- Total records in CSV: 738
- Records with discrepancies: 1 (100%)
- Fields with discrepancies:
  - `data_entrada`: 1 (100%)
  - `data_alta`: 1 (100%)
  - `destino_alta`: 1 (100%)

**Specific Discrepancies Found:**

| Field          | Database         | CSV          | Match |
|----------------|------------------|--------------|-------|
| data_entrada   | 2023-12-31       | 2024-01-04   | ✗     |
| data_alta      | 2024-01-26       | 2024-01-22   | ✗     |
| destino_alta   | Consulta Externa | ENFCP        | ✗     |

## Error Handling

### CSV File Not Found
```
[red]CSV file not found: ./csv/BD_doentes_clean.csv[/red]
```
**Solution:** Ensure CSV file exists and path is correct.

### Record Not in CSV
```
Not in CSV: 1 (records)
```
**Meaning:** MongoDB has records that don't exist in CSV. These are skipped during updates.

### Update Failures
```
[red]Error updating 2401: [error message][/red]
```
**Action:** Check error message, verify database permissions, check data format.

## Best Practices

1. **Always validate first**
   - Run validator before updates
   - Review discrepancy report
   - Understand what will change

2. **Test with dry run**
   - Always test with dry run first
   - Review preview of changes
   - Verify field updates make sense

3. **Backup database**
   - Create backup before live updates
   - Use MongoDB dump: `mongodump --db UQ`

4. **Verify after updates**
   - Check verification results
   - Query sample records
   - Compare before/after

5. **Track updates**
   - All updated records have `updated_at` timestamp
   - Query: `db.internamentos.find({updated_from_csv: true})`
   - Monitor update history

## Query Updated Records

```javascript
// Find all records updated from CSV
db.internamentos.find({updated_from_csv: true})

// Count updated records
db.internamentos.countDocuments({updated_from_csv: true})

// Find recently updated (last hour)
db.internamentos.find({
  updated_at: {
    $gte: new Date(Date.now() - 3600000).toISOString()
  }
})

// Find records with specific field updated
db.internamentos.find({
  updated_from_csv: true,
  "internamento.data_entrada": "2024-01-04"
})
```

## Rollback Strategy

If updates need to be reversed:

1. **From backup:**
   ```bash
   mongorestore --db UQ --drop dump/UQ
   ```

2. **Remove update flags:**
   ```javascript
   db.internamentos.updateMany(
     {updated_from_csv: true},
     {
       $unset: {
         updated_at: "",
         updated_from_csv: ""
       }
     }
   )
   ```

3. **Selective rollback:**
   - Requires original values (backup recommended)
   - Manual field-by-field restoration

## Future Enhancements

Potential improvements:
- Audit log for all changes
- Rollback mechanism with history
- Conflict resolution UI
- Batch update with approval workflow
- Email notifications for updates
- Scheduled validation checks
- CSV version tracking

## Related Documentation

- `database/DB_MENU.md` - Database menu documentation
- `database/QUICK_START.md` - Quick start guide
- `csv/README.md` - CSV quality control
- `COMPLETE_MENU_STRUCTURE.md` - Full menu structure

## Summary

The validation and update system provides:
- ✅ Comprehensive data comparison
- ✅ Safe dry-run mode
- ✅ Detailed reporting
- ✅ Update tracking with timestamps
- ✅ Verification step
- ✅ Menu integration
- ✅ Export reports
- ✅ Error handling

Use this system to maintain data quality and ensure MongoDB records match the authoritative CSV source.
