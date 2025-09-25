# PDF Parser with LlamaParse

A sophisticated batch processing system for parsing PDF documents using LlamaParse and automatically generating organized markdown outputs with intelligent workflow management.

## 🌟 Features

- **Batch Processing**: Process multiple PDFs simultaneously for maximum efficiency
- **Intelligent Organization**: Automatically organizes files by subject (first 4 digits of filename)
- **Smart Checkpoints**: Skip unnecessary processing when outputs already exist
- **Document Categorization**: Automatically categorizes documents by type (Admission, Release, Death notices, etc.)
- **Markdown Merging**: Creates comprehensive merged medical records from individual documents
- **CLI Control**: Flexible command-line interface with multiple workflow options
- **Comprehensive Output**: Extracts text, markdown, images, layout, and structured data

## 📁 Project Structure

```
theparser/
├── main.py                 # Main application with CLI interface
├── README.md              # This documentation
├── pyproject.toml         # Project dependencies
├── .env                   # Environment variables (API keys)
└── pdf/                   # Input and output directory
    ├── [subject folders]/ # Organized PDF files by subject
    └── output/           # Processing results
        └── [subject]/    # Subject-specific outputs
            ├── [document]/        # Individual document processing
            │   ├── markdown/      # Page-by-page markdown
            │   ├── text/          # Plain text extraction
            │   ├── images/        # Extracted images
            │   ├── layout/        # Layout information (JSON)
            │   └── structured_data/ # Structured data (JSON)
            └── [subject]_merged_medical_records.md  # Merged document
```

## ⚡ Quick Start

1. **Get your LlamaParse API key** from [LlamaIndex Cloud](https://cloud.llamaindex.ai/)
2. **Place PDF files** in the `pdf/` folder with naming pattern: `[4digits][type].pdf`
   - Example: `2503E.pdf`, `2503A.pdf`, `1234BIC.pdf`
3. **Set API key**: `echo "LLAMA_CLOUD_API_KEY=your_key" > .env`
4. **Run**: `python main.py`

Your processed files will appear in `pdf/output/[subject]/` with individual documents and merged records!

## 🚀 Installation

### Prerequisites

- Python 3.11+
- LlamaParse API key

### Setup

1. **Clone or download the project**
   ```bash
   cd /path/to/theparser
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # Or if using uv:
   uv sync
   ```

4. **Configure API key**
   ```bash
   # Create .env file
   echo "LLAMA_CLOUD_API_KEY=your_api_key_here" > .env
   ```

## 📖 Usage

### Basic Commands

```bash
# Run complete workflow (default)
python main.py

# Show all available options
python main.py --help

# Force reprocessing (skip checkpoints)
python main.py --force
```

### Workflow Modes

#### 1. **Full Workflow** (Default)
```bash
python main.py
python main.py --full
```
- Organizes PDFs by subject
- Processes PDFs with LlamaParse
- Merges markdown into comprehensive documents
- Uses intelligent checkpoints to skip completed work

#### 2. **PDF Parsing Only**
```bash
python main.py --parse-only
```
- Only processes PDFs with LlamaParse
- Skips markdown merging
- Useful for initial processing or when only new PDFs need parsing

#### 3. **Markdown Merging Only**
```bash
python main.py --merge-only
```
- Only processes markdown merging
- Skips PDF parsing
- Useful after manual processing or when only merging is needed

#### 4. **Markdown Cleaning Only**
```bash
python main.py --clean-only
```
- Only cleans merged markdown files
- Removes hospital-specific information (headers, addresses, etc.)
- Useful for sanitizing documents for external sharing

### Control Options

#### Force Processing
```bash
python main.py --force
python main.py --parse-only --force
python main.py --merge-only --force
python main.py --clean-only
```
Bypasses all checkpoints and reprocesses everything.

#### Skip Existing (Default Behavior)
```bash
python main.py --skip-existing     # Default
python main.py --no-skip-existing  # Force reprocess existing
```

## 🏥 Document Types

The system automatically categorizes documents based on filename endings:

| Ending | Type | Description |
|--------|------|-------------|
| **E** | Admission Notes | Hospital admission records |
| **A** | Release Notes | Hospital discharge records |
| **BIC** | Death Notices | Death notification documents |
| **O** | Death Certificates | Official death certificates |

### Example Filenames
- `2503E.pdf` → Subject 2503, Admission Notes
- `2503A.pdf` → Subject 2503, Release Notes  
- `1234BIC.pdf` → Subject 1234, Death Notice
- `5678O.pdf` → Subject 5678, Death Certificate

## 🔄 Workflow Logic

### Step 1: File Organization
```
pdf/2503E.pdf + pdf/2503A.pdf → pdf/2503/2503E.pdf + pdf/2503/2503A.pdf
```
Files are automatically organized into subject folders based on the first 4 digits.

### Step 2: Intelligent Checkpoints
1. **New PDF Detection**: Checks for new PDFs in main `pdf/` folder
2. **Subject Processing Status**: Verifies if subject already has processed outputs
3. **Merged File Detection**: Checks if merged markdown already exists

### Step 3: Selective Processing
Only processes what needs to be done based on current state and user flags.

### Step 4: Batch Processing
```
Subject 2503: [2503E.pdf, 2503A.pdf] → Batch Parse → Individual Results
```
Multiple PDFs for the same subject are processed simultaneously for efficiency.

### Step 5: Markdown Merging
```
Individual Documents → Categorize by Type → Merge in Order → Final Document
```
Documents are merged in priority order: E → A → BIC → O

## 📊 Output Structure

### Individual Document Processing
Each document generates:
- **Markdown files**: Page-by-page content (`page_1.md`, `page_2.md`)
- **Text files**: Plain text extraction
- **Images**: Extracted images and metadata
- **Layout data**: Structural information (JSON)
- **Structured data**: Parsed structured content (JSON)
- **Debug info**: Processing metadata

### Merged Document
Final merged file structure:
```markdown
# Medical Records - Subject 2503
*Generated on: 2025-09-25 11:05:11*

# Admission Notes (E)
## Document: 2503E
## Page 1
[content]
## Page 2
[content]

================================================================================

# Release Notes (A)  
## Document: 2503A
## Page 1
[content]
## Page 2
[content]
```

## 🛠️ Advanced Features

### Checkpoint System
The system intelligently skips work that's already been completed:

- ✅ **No new PDFs** → Skip PDF parsing
- ✅ **Subject already processed** → Skip if output exists and has content  
- ✅ **Already merged** → Skip if merged file exists and has content
- 💪 **Force mode** → Override all checkpoints

### Document Cleaning
- Automatic removal of hospital-specific information:
  - Hospital names and addresses
  - Phone numbers and email addresses
  - System-generated footers
  - Administrative headers
- Text formatting cleanup:
  - Removes leading tabs and whitespaces from all lines
  - Cleans up excess empty lines
  - Maintains proper markdown structure
- Preserves medical content while sanitizing identifying information

### Error Handling
- Graceful handling of parsing errors
- Detailed error reporting
- Fallback mechanisms for non-serializable data
- Comprehensive logging

### Performance Optimization  
- Batch processing for same-subject documents
- Async operations for API calls
- Minimal redundant processing
- Efficient file organization

## 🔧 Configuration

### Environment Variables
```bash
# Required
LLAMA_CLOUD_API_KEY=your_llamaparse_api_key

# Optional (defaults shown)
PDF_INPUT_DIR=./pdf
OUTPUT_DIR=./pdf/output
```

### LlamaParse Configuration
The system is configured for:
- **Base URL**: `https://api.cloud.eu.llamaindex.ai`
- **Language**: Portuguese (`pt`)
- **Workers**: 1 (batch processing)
- **Verbose output**: Enabled

## 📝 Examples

### Complete Workflow Example
```bash
# 1. Place PDFs in pdf/ folder
cp /path/to/2503E.pdf pdf/
cp /path/to/2503A.pdf pdf/

# 2. Run processing
python main.py

# 3. Check results
ls pdf/output/2503/
# Output:
# 2503E/                              # Individual document results
# 2503A/                              # Individual document results  
# 2503_merged_medical_records.md      # Merged comprehensive document
```

### Development Workflow
```bash
# Initial processing
python main.py

# Add new PDFs and process only new ones
cp /path/to/new_files/*.pdf pdf/
python main.py  # Only processes new files

# Regenerate merged documents only
python main.py --merge-only --force

# Clean merged documents (remove hospital info)
python main.py --clean-only

# Reprocess everything
python main.py --force
```

## 🐛 Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   Error: No API key found
   Solution: Check .env file and LLAMA_CLOUD_API_KEY
   ```

2. **No PDFs Found**
   ```
   Issue: PDFs must start with 4 digits
   Solution: Rename files to format like 2503E.pdf
   ```

3. **Permission Errors**
   ```
   Issue: Cannot write to output directory
   Solution: Check folder permissions
   ```

### Debug Information
Each processing run generates debug files with detailed information about:
- API responses
- Processing metadata
- Error details
- Performance metrics

## 📚 Dependencies

- **llama-cloud-services**: LlamaParse integration
- **asyncio**: Async processing
- **pathlib**: File system operations
- **argparse**: CLI interface
- **json**: Data serialization
- **collections**: Data structures

## 🤝 Contributing

1. Follow the existing code structure
2. Add appropriate error handling
3. Update documentation for new features
4. Test with various PDF formats
5. Maintain backward compatibility

## 📄 License

This project is for internal use. Please ensure compliance with LlamaParse terms of service.

## 🆘 Support

For issues and questions:
1. Check this README for common solutions
2. Review debug output files
3. Verify API key and network connectivity
4. Check file naming conventions (4-digit prefixes)

---

**Happy parsing! 🎉**