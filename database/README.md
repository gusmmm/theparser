# MongoDB Database Manager - UQ Database

## Overview

This module provides a comprehensive MongoDB manager for the UQ (Unidade de Queimados) database. It handles all database operations including connection management, health checks, and database information display.

## Features

### ✅ Core Functionality

1. **Connect to Database**
   - Connects to local MongoDB instance
   - Creates 'UQ' database if it doesn't exist
   - Configurable host/port/database name
   - Connection timeout handling (5 seconds)

2. **Health Checks**
   - Server connectivity verification
   - Database statistics retrieval
   - Collection enumeration
   - Size and object count reporting

3. **Disconnect**
   - Clean disconnection from database
   - Resource cleanup

4. **Database Information Display**
   - Beautiful Rich terminal output
   - Comprehensive database statistics
   - Detailed collection information table
   - Real-time status updates

## Installation

```bash
# Install required packages
uv add pymongo
```

## Usage

### Basic Usage

```python
from database.db_manager import MongoDBManager

# Create manager instance
db_manager = MongoDBManager()

# Connect to database
if db_manager.connect():
    # Check health
    health_info = db_manager.check_health()
    
    # List database info
    db_manager.list_database_info()
    
    # Disconnect
    db_manager.disconnect()
```

### Context Manager Usage

```python
from database.db_manager import MongoDBManager

# Use as context manager (auto-connect/disconnect)
with MongoDBManager() as db:
    db.list_database_info()
    # Do database operations
```

### Custom Configuration

```python
from database.db_manager import MongoDBManager

# Custom host/port/database
db_manager = MongoDBManager(
    host="localhost",
    port=27017,
    db_name="UQ"
)
```

### Convenience Function

```python
from database.db_manager import get_db_manager

# Get manager with defaults
db = get_db_manager()
db.connect()
```

## API Reference

### MongoDBManager Class

#### `__init__(host="localhost", port=27017, db_name="UQ")`
Initialize the MongoDB manager.

**Parameters:**
- `host` (str): MongoDB host address
- `port` (int): MongoDB port
- `db_name` (str): Database name

#### `connect() -> bool`
Connect to MongoDB database. Creates database if it doesn't exist.

**Returns:**
- `bool`: True if connection successful, False otherwise

**Example:**
```python
if db_manager.connect():
    print("Connected!")
```

#### `check_health() -> Dict`
Check database connection and server health.

**Returns:**
- `dict`: Health status information including:
  - `connected`: Connection status
  - `mongodb_version`: MongoDB version
  - `collections_count`: Number of collections
  - `database_size_mb`: Database size in MB
  - `objects_count`: Total documents
  - `timestamp`: Check timestamp

**Example:**
```python
health = db_manager.check_health()
print(f"Collections: {health['collections_count']}")
print(f"Size: {health['database_size_mb']} MB")
```

#### `disconnect() -> bool`
Disconnect from MongoDB.

**Returns:**
- `bool`: True if successful

#### `list_database_info() -> None`
Display comprehensive database and collection information to terminal.

Outputs:
- Database statistics panel
- Collections table with:
  - Document counts
  - Average document size
  - Total size
  - Index counts

**Example:**
```python
db_manager.list_database_info()
```

#### `create_collection(collection_name: str) -> bool`
Create a new collection in the database.

**Parameters:**
- `collection_name` (str): Name of collection to create

**Returns:**
- `bool`: True if successful

**Example:**
```python
db_manager.create_collection("patients")
db_manager.create_collection("burns")
```

## Output Examples

### Connection Success
```
✓ Connected to MongoDB: localhost:27017
✓ Database: UQ
```

### Health Check
```
✓ Database is healthy
```

### Database Info Panel
```
╭──────────────────────── 📊 Database: UQ ────────────────────────╮
│ Host: localhost:27017                                           │
│ Database: UQ                                                    │
│ MongoDB Version: 8.2.1                                          │
│ Collections: 3                                                  │
│ Total Objects: 150                                              │
│ Data Size: 2.45 MB                                              │
│ Storage Size: 3.12 MB                                           │
│ Indexes: 8                                                      │
│ Status: Connected ✓                                             │
│ Timestamp: 2025-10-10T11:56:13.565763                           │
╰─────────────────────────────────────────────────────────────────╯
```

### Collections Table
```
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Collection             ┃ Documents ┃ Avg Doc Size ┃ Total Size ┃ Indexes ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ patients               │        67 │      1.23 KB │   82.41 KB │       2 │
│ burns                  │       145 │      0.89 KB │  129.05 KB │       2 │
│ procedures             │        89 │      1.45 KB │  129.05 KB │       2 │
└────────────────────────┴───────────┴──────────────┴────────────┴─────────┘
```

## Error Handling

The manager handles common MongoDB errors:

### Connection Failure
```
✗ Connection failed: [Error details]
Make sure MongoDB is running: sudo systemctl start mongod
```

### Timeout
```
✗ Connection timeout: Could not connect to MongoDB
Check if MongoDB is running on localhost:27017
```

## Testing

Run the test script to verify functionality:

```bash
# Test basic connection
uv run python database/db_manager.py

# Test with sample data
uv run python database/test_db.py
```

## MongoDB Service Management

### Start MongoDB
```bash
sudo systemctl start mongod
```

### Check Status
```bash
sudo systemctl status mongod
```

### Enable Auto-start
```bash
sudo systemctl enable mongod
```

## Dependencies

- `pymongo>=4.15.3`: MongoDB Python driver
- `rich`: Terminal formatting and tables
- `icecream`: Debug logging

## Features by Requirement

✅ **Connect to local database named UQ**: Implemented with auto-creation  
✅ **Check health of connection**: Comprehensive health checks with statistics  
✅ **Disconnect from database**: Clean disconnection with resource cleanup  
✅ **List database info to terminal**: Beautiful Rich output with tables and panels

## Architecture

```
MongoDBManager
├── Connection Management
│   ├── connect()
│   ├── disconnect()
│   └── Context manager support
├── Health Monitoring
│   └── check_health()
├── Information Display
│   └── list_database_info()
└── Collection Management
    └── create_collection()
```

## Integration with Medical Records System

This database manager will be used to:
1. Store extracted medical record data from JSON files
2. Manage patient records collections
3. Store burn data with anatomical locations
4. Track procedures and medications
5. Maintain audit trails with timestamps

## Next Steps

- Implement data insertion from agent JSON exports
- Create indexes for optimal query performance
- Add data validation schemas
- Implement backup/restore functionality
- Add query helper methods

## Author

Agent - Created 2025-10-10

## License

Part of the theparser medical records processing system.
