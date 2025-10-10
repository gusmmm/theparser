# Agent Management Menu

## Overview

The Agent Management menu provides comprehensive tools to manage AI extraction of medical records and database integration. It tracks the complete pipeline from cleaned markdown files to JSON extraction to MongoDB storage.

## Purpose

Manage the AI agent that:
1. Extracts structured data from cleaned markdown files using Google Gemini
2. Generates JSON files with validated medical data
3. Imports extracted data into MongoDB database
4. Tracks processing status across all subjects

## Menu Structure

```
Agent Management Menu
├── Statistics Dashboard (automatic)
├── 1. Process single subject (AI extraction)
├── 2. Process all ready subjects (batch AI extraction)
├── 3. Process missing subjects only
├── 4. Import single subject to database
├── 5. Import all extracted subjects to database
├── 6. Import missing subjects to database
├── 7. Show detailed subject list
├── 8. Full pipeline: Extract + Import for ready subjects
└── 0. Back to Main Menu
```

## Features

### 1. Automatic Statistics Dashboard

When you enter the menu, you'll see:

**Overall Statistics**:
- Total Subjects: All subjects in output directory
- With Cleaned Markdown: Subjects ready for extraction
- With Extracted JSON: Subjects already processed by AI
- Inserted to Database: Subjects in MongoDB
- Ready for Extraction: Cleaned but not extracted
- Extracted, Not in DB: JSON exists but not in database

**Year Breakdown**:
- Statistics split by admission year
- Shows progression through pipeline by year
- Identifies gaps and missing subjects per year

### 2. Process Single Subject (Option 1)

**Purpose**: Extract structured data from one subject's cleaned markdown file

**Process**:
1. Enter 4-digit subject ID (e.g., 2401)
2. Agent reads `{subject}_merged_medical_records.cleaned.md`
3. Uses Google Gemini 2.5-flash with structured output
4. Validates extraction against Pydantic models
5. Saves to `{subject}_extracted.json`

**Requirements**:
- Cleaned markdown file must exist
- GEMINI_API_KEY in environment
- Internet connection for API calls

**Example**:
```
Enter subject ID (4 digits): 2401

🤖 AI Medical Data Extraction
Starting extraction from: 2401_merged_medical_records.cleaned.md
✓ Extraction completed successfully!
✓ Data validated and structured!
✓ JSON saved: 2401_extracted.json
```

### 3. Process All Ready Subjects (Option 2)

**Purpose**: Batch process all subjects with cleaned markdown but no JSON

**Process**:
1. Menu shows count of ready subjects
2. Lists first 20 subjects (more if available)
3. Confirmation required before processing
4. Progress bar shows extraction status
5. Summary report with success/failure counts

**Use Case**: Initial bulk extraction after cleaning all markdown files

**Performance**:
- Each subject takes ~30-60 seconds (API dependent)
- Processes sequentially for stability
- Shows detailed errors for failures

### 4. Process Missing Subjects Only (Option 3)

**Purpose**: Extract only subjects that were skipped or failed previously

**Difference from Option 2**: 
- Option 2: All ready subjects
- Option 3: Only ready subjects (emphasizes missing/incomplete)

**Use Case**: Fill in gaps after previous extraction runs

### 5. Import Single Subject to Database (Option 4)

**Purpose**: Insert one subject's JSON data into MongoDB

**Process**:
1. Enter 4-digit subject ID
2. Reads `{subject}_extracted.json`
3. Validates data against database schema
4. Inserts to `internamentos` collection
5. Sets indexes and metadata

**Requirements**:
- Extracted JSON file must exist
- MongoDB running on localhost:27017
- Database "UQ" accessible

**Example**:
```
Enter subject ID (4 digits): 2401

Importing subject 2401 to database...
✓ Successfully imported subject 2401 to database
```

### 6. Import All Extracted Subjects (Option 5)

**Purpose**: Batch import all subjects with JSON but not in database

**Process**:
1. Identifies subjects with `_extracted.json` files
2. Filters out subjects already in database
3. Shows count and confirmation
4. Progress bar during import
5. Summary with success/failure counts

**Use Case**: Bulk database population after extraction phase

**Safety**: 
- Checks for duplicates (by numero_internamento)
- Skips existing records
- Transactional inserts

### 7. Import Missing Subjects to Database (Option 6)

**Purpose**: Import only subjects not yet in database

**Difference from Option 5**:
- Option 5: All extracted subjects ready for DB
- Option 6: Emphasizes missing/incomplete (same result)

**Use Case**: Fill database gaps after previous import runs

### 8. Show Detailed Subject List (Option 7)

**Purpose**: View detailed status of subjects with flexible filtering

**Filters Available**:
- `all`: All subjects
- `ready`: Ready for extraction (has cleaned MD, no JSON)
- `extracted`: Has extracted JSON
- `in_db`: In MongoDB database
- `missing_extraction`: Cleaned but not extracted
- `missing_db`: Extracted but not in database

**Display**:
- Subject ID
- Year
- Cleaned MD status (✓/✗)
- Extracted status (✓/✗)
- In DB status (✓/✗)

**Pagination**: Shows first 50 subjects

**Example**:
```
Filter by: missing_extraction

Subject Details - MISSING_EXTRACTION
┌─────────┬──────┬────────────┬───────────┬───────┐
│ Subject │ Year │ Cleaned MD │ Extracted │ In DB │
├─────────┼──────┼────────────┼───────────┼───────┤
│ 2401    │ 2024 │ ✓          │ ✗         │ ✗     │
│ 2402    │ 2024 │ ✓          │ ✗         │ ✗     │
└─────────┴──────┴────────────┴───────────┴───────┘
```

### 9. Full Pipeline (Option 8)

**Purpose**: Complete automation - extract and import in one go

**Process**:
1. Identifies subjects ready for extraction
2. **Step 1: AI Extraction**
   - Batch processes all ready subjects
   - Shows progress and results
3. **Step 2: Database Import**
   - Automatically imports successfully extracted subjects
   - Shows progress and results
4. Final summary of complete pipeline

**Use Case**: 
- Initial setup: clean markdown → database
- Regular updates: new subjects → database
- Most efficient for bulk processing

**Example**:
```
Full Pipeline: Extract and Import 10 subjects
2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410

Run full pipeline for 10 subjects? Yes

Step 1: AI Extraction
[████████████████████] 10/10 Completed

Extraction Results:
  Successful: 10
  Failed: 0

Step 2: Database Import
[████████████████████] 10/10 Completed

Import Results:
  Successful: 10
  Failed: 0

Pipeline Complete!
  • Extracted: 10 subjects
  • Imported to DB: 10 subjects
```

## Statistics Explained

### Processing States

Each subject can be in one of several states:

1. **Not Ready**: No cleaned markdown → needs cleaning
2. **Ready for Extraction**: Has cleaned MD, no JSON → ready for AI
3. **Extracted**: Has JSON, not in DB → ready for database
4. **Complete**: In database → fully processed

### Percentages

All percentages calculated from total subjects:
- `With Cleaned Markdown / Total Subjects * 100%`
- Shows completion of each pipeline stage

### Year Analysis

Breaks down statistics by admission year:
- Year extracted from subject ID (first 2 digits)
- Shows pipeline progress per year
- Helps identify year-specific issues

## File Locations

### Input Files
- Cleaned markdown: `pdf/output/{subject}/{subject}_merged_medical_records.cleaned.md`

### Output Files
- Extracted JSON: `pdf/output/{subject}/{subject}_extracted.json`

### Database
- MongoDB: `localhost:27017`
- Database: `UQ`
- Collection: `internamentos`

## Common Workflows

### Initial Setup (Clean State)

```
1. Parse PDFs → Document folders
2. Merge markdown → Merged files
3. Clean markdown → Cleaned files
4. Agent Menu → Option 2 (batch extract)
5. Agent Menu → Option 5 (batch import)
```

### Adding New Subjects

```
1. Add PDFs to pdf/ folder
2. Parse new PDFs
3. Merge & clean new subjects
4. Agent Menu → Option 3 (process missing)
5. Agent Menu → Option 6 (import missing)
```

### Full Pipeline (Fastest)

```
1-3. [Same as above]
4. Agent Menu → Option 8 (full pipeline)
```

### Recovery from Errors

**If extraction fails**:
- Check error messages
- Verify GEMINI_API_KEY
- Check cleaned markdown quality
- Retry with Option 1 (single subject)
- Use Option 3 (missing subjects)

**If import fails**:
- Check MongoDB is running
- Verify database connection
- Check JSON file validity
- Retry with Option 4 (single subject)
- Use Option 6 (missing from DB)

## Error Handling

### Extraction Errors

Common causes:
- API key invalid/missing
- Internet connection issues
- Malformed markdown content
- API rate limits
- Invalid date formats in source

Solutions:
- Check `.env` file has GEMINI_API_KEY
- Verify markdown content is complete
- Process smaller batches
- Retry failed subjects individually

### Import Errors

Common causes:
- MongoDB not running
- Database connection failed
- Duplicate numero_internamento
- Invalid JSON structure
- Missing required fields

Solutions:
- Start MongoDB: `sudo systemctl start mongodb`
- Check connection: `mongosh localhost:27017`
- Verify JSON with validator
- Check for duplicate subject IDs

## Performance

### Extraction Speed
- Single subject: ~30-60 seconds
- Batch (10 subjects): ~5-10 minutes
- Depends on: API speed, document complexity, network

### Import Speed
- Single subject: ~0.5-1 second
- Batch (100 subjects): ~1-2 minutes
- Depends on: MongoDB performance, document size

### Recommendations
- Extract in batches of 10-20 for stability
- Import in batches of 50-100 for efficiency
- Use full pipeline for maximum automation

## Integration with Other Menus

### Connection to Main Menu
```
Main Menu
├── 5. Agent Management (this menu)
│   ├── Extract subjects
│   └── Import to database
└── 4. Database Management
    ├── Query database
    ├── Validate data
    └── Update records
```

### Data Flow
```
PDF Parsing → Markdown Merging → Markdown Cleaning
                                         ↓
                                  Agent Extraction
                                         ↓
                                  JSON Generation
                                         ↓
                                  Database Import
                                         ↓
                              Database Management
```

## Monitoring Progress

### Check Extraction Status
```
Option 7 → Filter: "missing_extraction"
Shows: Subjects with cleaned MD but no JSON
```

### Check Database Status
```
Option 7 → Filter: "missing_db"
Shows: Subjects with JSON but not in database
```

### Overall Health
```
Main menu statistics shows:
- Ready for extraction count
- Extracted not in DB count
```

## Best Practices

1. **Always check statistics first** - Understand current state
2. **Process in stages** - Extract first, then import
3. **Use full pipeline for bulk** - Most efficient
4. **Monitor errors** - Review error messages
5. **Validate JSON** - Check extracted files before import
6. **Backup database** - Before bulk imports
7. **Process year by year** - Easier to track progress

## Troubleshooting

### "No subjects ready for extraction"
→ Check if markdown files are cleaned
→ Look for `*_merged_medical_records.cleaned.md` files

### "Failed to process subject"
→ Check error message for specific issue
→ Verify cleaned markdown exists and is complete
→ Test with single subject first

### "Extracted JSON file not found"
→ Run extraction first (Options 1-3)
→ Check `pdf/output/{subject}/` for JSON file

### "MongoDB connection failed"
→ Start MongoDB: `sudo systemctl start mongodb`
→ Check MongoDB status: `sudo systemctl status mongodb`
→ Verify database exists: `mongosh` → `show dbs`

## Author

Implementation by Agent  
Date: 2025-01-15  
Part of: Medical Records Processing System
