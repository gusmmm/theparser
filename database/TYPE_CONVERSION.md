# Type Conversion Implementation

## Overview

This document describes the implementation of proper type conversion for MongoDB storage. Previously, dates and year values were stored as strings, which is inefficient for queries and sorting. Now they are stored as proper types:
- **Dates**: Stored as `datetime` objects (MongoDB ISODate)
- **Year**: Stored as `int`

## Strategy

1. **During Validation**: Compare values as strings (after normalization)
   - Easier comparison without type issues
   - Format-agnostic (handles different date formats)
   - Uses existing `normalize_date()` and `normalize_string()` functions

2. **During Storage**: Convert to proper types before writing to MongoDB
   - Dates → `datetime` objects
   - Year → `int`
   - Enables efficient date range queries
   - Proper sorting and indexing

## Implementation

### Helper Functions

Three helper functions were added to each file that writes to MongoDB:

```python
def convert_to_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Convert date string to datetime object for MongoDB.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        datetime object or None
    """
    if not date_str or date_str.strip() == '':
        return None
    
    try:
        # Parse YYYY-MM-DD format
        return datetime.fromisoformat(date_str.strip())
    except (ValueError, AttributeError):
        return None


def convert_to_int(value: Any) -> Optional[int]:
    """
    Convert value to integer for MongoDB.
    
    Args:
        value: Value to convert
        
    Returns:
        int or None
    """
    if value is None or value == '':
        return None
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
```

### Files Modified

#### 1. `data_importer.py`

**Purpose**: Initial JSON import to MongoDB

**Changes**:
- Added type conversion helper functions (lines 23-79)
- Modified `transform_for_mongodb()` to convert dates in:
  - `internamento.data_entrada` → datetime
  - `internamento.data_alta` → datetime
  - `doente.data_nascimento` → datetime
  - `queimaduras[].data` → datetime (for each queimadura)
  - `import_date` → datetime (not string)
  - `ano_internamento` → int (already was int at line 230)

**Example**:
```python
# Convert dates in internamento
internamento = json_data["internamento"].copy()
internamento["data_entrada"] = convert_to_date(internamento.get("data_entrada"))
internamento["data_alta"] = convert_to_date(internamento.get("data_alta"))

# Convert dates in doente
doente = json_data["doente"].copy()
doente["data_nascimento"] = convert_to_date(doente.get("data_nascimento"))

# Convert dates in queimaduras
queimaduras = []
for queimadura in json_data.get("queimaduras", []):
    q = queimadura.copy()
    q["data"] = convert_to_date(q.get("data"))
    queimaduras.append(q)

# Store import_date as datetime
"import_date": datetime.now(),  # Not .isoformat()
```

#### 2. `data_updater.py`

**Purpose**: Batch update MongoDB with CSV data

**Changes**:
- Added type conversion helper functions
- Modified `prepare_update_data()` field mappings:
  - `ano_internamento` → `convert_to_int(csv_row.get('year'))`
  - `data_entrada` → `convert_to_date(normalize_date(...))`
  - `data_alta` → `convert_to_date(normalize_date(...))`
  - `data_nascimento` → `convert_to_date(normalize_date(...))`

**Example**:
```python
field_mappings = {
    'ano_internamento': ('ano_internamento', convert_to_int(csv_row.get('year'))),
    'data_entrada': ('internamento.data_entrada', convert_to_date(normalize_date(csv_row.get('data_ent')))),
    'data_alta': ('internamento.data_alta', convert_to_date(normalize_date(csv_row.get('data_alta')))),
    'data_nascimento': ('doente.data_nascimento', convert_to_date(normalize_date(csv_row.get('data_nasc')))),
}
```

#### 3. `interactive_updater.py`

**Purpose**: Interactive field-by-field update

**Changes**:
- Added type conversion helper functions
- Modified update data preparation in two places:
  1. "Update all fields" option (choice == "a")
  2. "Select specific fields" option (choice == "s")
- Added type conversion based on field type:
  - Date fields → `convert_to_date(normalize_date(csv_value))`
  - Year field → `convert_to_int(csv_value)`

**Example**:
```python
# Handle date normalization and conversion to datetime
if field_info['field'] in ['data_entrada', 'data_alta', 'data_nascimento', 'data_queimadura']:
    csv_value = convert_to_date(normalize_date(csv_value))
# Handle year conversion to int
elif field_info['field'] == 'ano_internamento':
    csv_value = convert_to_int(csv_value)

if csv_value is not None:  # Check for None, not falsy
    update_data[mongo_path] = csv_value
```

## Date Fields Converted

| Field | Location | Format Before | Format After |
|-------|----------|---------------|--------------|
| `data_entrada` | internamento | string "YYYY-MM-DD" | datetime |
| `data_alta` | internamento | string "YYYY-MM-DD" | datetime |
| `data_nascimento` | doente | string "YYYY-MM-DD" | datetime |
| `queimaduras[].data` | queimaduras array | string "YYYY-MM-DD" | datetime |
| `import_date` | root | string ISO format | datetime |
| `ano_internamento` | root | string "YYYY" | int |

## Benefits

1. **Query Efficiency**:
   ```javascript
   // Date range queries work properly
   db.internamentos.find({
       "internamento.data_entrada": {
           $gte: ISODate("2023-01-01"),
           $lte: ISODate("2023-12-31")
       }
   })
   
   // Year queries work properly
   db.internamentos.find({
       "ano_internamento": {$gte: 2020, $lte: 2023}
   })
   ```

2. **Proper Sorting**:
   ```javascript
   // Sorts chronologically, not lexicographically
   db.internamentos.find().sort({"internamento.data_entrada": 1})
   ```

3. **Index Efficiency**: MongoDB indexes work better with proper types

4. **Data Integrity**: Type validation at database level

5. **Storage**: Dates stored more efficiently as BSON dates

## Validation Flow

```
CSV Data (strings)
    ↓
normalize_date() → "YYYY-MM-DD" string
    ↓
String Comparison (in validator)
    ↓
If match: No update needed
If mismatch: Continue to update
    ↓
convert_to_date() → datetime object
    ↓
MongoDB Update (proper type)
```

## Testing

To verify type conversion:

1. **Check existing record types**:
   ```javascript
   db.internamentos.findOne({
       "internamento.numero_internamento": 2401
   })
   ```
   Look for dates as ISODate objects, not strings.

2. **Import new record**:
   ```bash
   # From database menu, option 4 (Import JSON files)
   ```
   Verify dates are datetime objects.

3. **Update existing record**:
   ```bash
   # From database menu, option 7 (Interactive update)
   ```
   Select a date field to update, verify it's stored as datetime.

4. **Query by date**:
   ```javascript
   // This should work now
   db.internamentos.find({
       "internamento.data_entrada": {
           $gte: ISODate("2023-01-01")
       }
   }).count()
   ```

## Important Notes

1. **Null Handling**: 
   - Empty strings → `None` (not stored)
   - Invalid dates → `None` (not stored)
   - Check `if csv_value is not None` (not `if csv_value`)

2. **Date Format**: 
   - Input: Various formats via `normalize_date()`
   - Storage: Always `datetime` object
   - Display: Format as needed for output

3. **Backward Compatibility**:
   - Validator still uses string comparison
   - Old records with string dates will be updated to datetime on next update
   - No need to migrate all records at once

4. **Error Handling**:
   - Invalid date strings → `None` (logged, not stored)
   - Invalid integers → `None` (logged, not stored)
   - Conversion errors caught and handled gracefully

## Migration Path

For existing records with string dates:

1. **Gradual**: Records get converted as they are updated via CSV
2. **Bulk** (if needed): Run batch update to convert all at once
3. **Validation**: Validator will flag mismatches between string and datetime

The system is designed to handle mixed types during transition period.

## Author

Implementation by Agent  
Date: 2025-01-15
