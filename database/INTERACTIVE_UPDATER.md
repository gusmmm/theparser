# Interactive Database Updater - Quick Guide

## Overview

The interactive updater allows you to review each discrepancy and selectively choose which fields to update in the database.

## Features

- **View discrepancies with row numbers** - Each mismatched field is numbered for easy selection
- **Per-record decisions** - Review and decide for each internamento record
- **Selective field updates** - Choose specific fields or update all
- **Safe confirmation** - Final confirmation before database modification
- **Update tracking** - All updated records get `updated_at` and `updated_from_csv` metadata

## Usage

### From Database Menu

```bash
uv run python main.py
# Select option 4: Database Management
# Select option 7: Update database from CSV (interactive)
```

### Standalone

```bash
uv run python database/interactive_updater.py
```

## Interactive Workflow

### Step 1: Validation

The tool automatically validates all records against CSV data and shows summary:

```
Step 1: Validating data...
✓ Loaded 738 records from CSV
Comparing 1 internamentos with CSV...
```

### Step 2: Review Discrepancies

For each record with discrepancies, you'll see:

```
╭────────────────────╮
│ Record 1 of 1      │
│ Internamento: 2401 │
╰────────────────────╯

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

What would you like to do? [a/s/n/q] (n):
```

### Step 3: Choose Action

**Option `a` - Update All Fields**
- Updates all mismatched fields shown in the table
- Quick way to accept all CSV values for this record

**Option `s` - Select Specific Fields**
- Prompts: "Enter field numbers to update (comma-separated, e.g., 1,3,4) or 'all':"
- Enter numbers like: `1,2` to update only ano_internamento and data_entrada
- Enter `all` to update all fields (same as option `a`)

**Option `n` - Skip This Record**
- Don't update this record at all
- Move to next record with discrepancies

**Option `q` - Quit and Save**
- Stop reviewing remaining records
- Keep selections made so far
- Proceed to confirmation and update

## Example Session

### Example 1: Update All Fields

```
What would you like to do? [a/s/n/q] (n): a
✓ Queued all 4 fields for update
```

### Example 2: Select Specific Fields

```
What would you like to do? [a/s/n/q] (n): s

Enter field numbers to update (comma-separated, e.g., 1,3,4) or 'all':
Fields to update: 1,2

✓ Queued 2 field(s) for update
```

### Example 3: Skip Record

```
What would you like to do? [a/s/n/q] (n): n
Skipping this record
```

## Selection Summary

After reviewing all records (or quitting), you'll see a summary:

```
Update Summary
Total records to update: 1

  Internamento   Fields to Update                          Count
  2401           ano_internamento, data_entrada, data_alta   3

Total fields to update: 3
```

## Final Confirmation

Before updating the database:

```
Step 3: Execute updates...

⚠ This will modify the database. Continue? [y/N]:
```

Type `y` to proceed or `n` to cancel.

## Update Results

After successful update:

```
Updating records... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Update Complete!
╭──────────────────────┬────────╮
│ Category             │  Count │
├──────────────────────┼────────┤
│ Total Records        │      1 │
│ Successfully Updated │      1 │
│ Failed               │      0 │
╰──────────────────────┴────────╯

✓ 1 record(s) updated successfully
All updated records have 'updated_at' and 'updated_from_csv' fields
```

## Field Selection Tips

### Update Year Only
```
Fields to update: 1
```

### Update All Dates
```
Fields to update: 2,3
```

### Update Everything Except Destination
```
Fields to update: 1,2,3
(skips field 4: destino_alta)
```

### Update All Fields
```
Fields to update: all
```
or just press `a` in the options menu.

## Field Numbers Reference

Based on the current test record (2401):

| No | Field              | Description              |
|----|--------------------|-----------------------|
| 1  | ano_internamento   | Year of admission     |
| 2  | data_entrada       | Admission date        |
| 3  | data_alta          | Discharge date        |
| 4  | destino_alta       | Discharge destination |

*Note: Field numbers are assigned sequentially for each record based on which fields have discrepancies. They may vary between records.*

## Safety Features

1. **Preview First** - See all discrepancies before deciding
2. **Selective Update** - Choose exactly which fields to update
3. **Quit Anytime** - Can quit and save selections made so far
4. **Final Confirmation** - Must confirm before database is modified
5. **Update Tracking** - All changes tracked with timestamps
6. **No Partial Updates** - If update fails, transaction is rolled back

## Updated Record Structure

Records updated through this tool will have:

```json
{
  "ano_internamento": 2024,           // ← Updated
  "internamento": {
    "data_entrada": "2024-01-04",     // ← Updated
    "data_alta": "2024-01-22"         // ← Updated
  },
  "updated_at": "2025-10-10T15:30:45", // ← Added
  "updated_from_csv": true             // ← Added
}
```

## Query Updated Records

After updating, you can query which records were modified:

```javascript
// Find all records updated via this tool
db.internamentos.find({updated_from_csv: true})

// Count updated records
db.internamentos.countDocuments({updated_from_csv: true})

// Find recently updated (last hour)
db.internamentos.find({
  updated_at: {
    $gte: new Date(Date.now() - 3600000).toISOString()
  }
})
```

## Troubleshooting

### No Discrepancies Found
```
✓ All records match perfectly! No updates needed.
```
**Meaning:** Database and CSV are already synchronized.

### Invalid Field Numbers
```
Invalid input. Skipping this record.
```
**Solution:** Enter valid field numbers (e.g., `1,2,3`) or `all`.

### Update Failed
```
[red]Error updating 2401: [error message][/red]
```
**Action:** Check error message, verify database permissions, ensure MongoDB is running.

## Best Practices

1. **Review Carefully** - Take time to review each discrepancy
2. **Start Small** - Test with a few records first before updating many
3. **Backup Database** - Always backup before large updates
4. **Verify Results** - Check a few updated records after completion
5. **Use Field Numbers** - More precise than updating all fields blindly

## Related Tools

- **Option 5: Validate data vs CSV** - Just view discrepancies without updating
- **Option 6: Update database (dry run)** - Simulate updates without modifying database
- **Option 7: Interactive update** - This tool (selective field updates)

## Summary

The interactive updater provides maximum control over which database fields get updated from CSV:
- ✅ See each discrepancy clearly
- ✅ Choose fields to update per record
- ✅ Safe confirmation before changes
- ✅ Update tracking with timestamps
- ✅ Detailed results reporting

Perfect for careful, selective data synchronization!
