import os
import json
import shutil
import asyncio
import argparse
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

from llama_cloud_services import LlamaParse

# Load environment variables from .env file
load_dotenv()
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

parser = LlamaParse(
    api_key=LLAMA_CLOUD_API_KEY,
    base_url='https://api.cloud.eu.llamaindex.ai',
    num_workers=1,       # if multiple files passed, split in `num_workers` API calls
    verbose=True,
    language="pt",       # optionally define a language, default=en
)


def save_markdown_documents(markdown_documents, output_dir):
    """Save markdown documents to individual files"""
    markdown_dir = Path(output_dir) / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    for i, doc in enumerate(markdown_documents):
        filename = f"page_{i+1}.md"
        filepath = markdown_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc.text)
        print(f"Saved markdown: {filepath}")


def save_text_documents(text_documents, output_dir):
    """Save text documents to files"""
    text_dir = Path(output_dir) / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    
    for i, doc in enumerate(text_documents):
        filename = f"document_{i+1}.txt"
        filepath = text_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc.text)
        print(f"Saved text document: {filepath}")


def save_images(image_documents, output_dir):
    """Save image documents"""
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    for i, doc in enumerate(image_documents):
        if hasattr(doc, 'image_path') and doc.image_path:
            # If image is already saved to disk, copy it
            source_path = Path(doc.image_path)
            if source_path.exists():
                filename = f"image_{i+1}_{source_path.name}"
                dest_path = images_dir / filename
                shutil.copy2(source_path, dest_path)
                print(f"Copied image: {dest_path}")
        elif hasattr(doc, 'image') and doc.image:
            # If image is in memory, save it
            filename = f"image_{i+1}.png"
            filepath = images_dir / filename
            with open(filepath, 'wb') as f:
                f.write(doc.image)
            print(f"Saved image: {filepath}")


def save_page_data(pages, output_dir):
    """Save page text, markdown, layout, and structured data"""
    layout_dir = Path(output_dir) / "layout"
    structured_dir = Path(output_dir) / "structured_data"
    text_dir = Path(output_dir) / "text"
    markdown_dir = Path(output_dir) / "markdown"
    
    # Create directories
    for dir_path in [layout_dir, structured_dir, text_dir, markdown_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    for i, page in enumerate(pages):
        page_num = i + 1
        
        # Save page text
        if hasattr(page, 'text') and page.text:
            text_file = text_dir / f"page_{page_num}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(page.text)
            print(f"Saved page text: {text_file}")
        
        # Save page markdown
        if hasattr(page, 'md') and page.md:
            md_file = markdown_dir / f"page_{page_num}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(page.md)
            print(f"Saved page markdown: {md_file}")
        
        # Save page layout
        if hasattr(page, 'layout') and page.layout:
            layout_file = layout_dir / f"page_{page_num}_layout.json"
            with open(layout_file, 'w', encoding='utf-8') as f:
                try:
                    json.dump(page.layout, f, indent=2, ensure_ascii=False, default=str)
                    print(f"Saved page layout: {layout_file}")
                except Exception as e:
                    f.write(str(page.layout))
                    print(f"Saved page layout as string: {layout_file} (Error: {e})")
        
        # Save structured data
        if hasattr(page, 'structuredData') and page.structuredData:
            structured_file = structured_dir / f"page_{page_num}_structured_data.json"
            with open(structured_file, 'w', encoding='utf-8') as f:
                try:
                    json.dump(page.structuredData, f, indent=2, ensure_ascii=False, default=str)
                    print(f"Saved structured data: {structured_file}")
                except Exception as e:
                    f.write(str(page.structuredData))
                    print(f"Saved structured data as string: {structured_file} (Error: {e})")
        
        # Save page images info
        if hasattr(page, 'images') and page.images:
            images_info_file = layout_dir / f"page_{page_num}_images_info.json"
            with open(images_info_file, 'w', encoding='utf-8') as f:
                try:
                    # Try to convert image objects to dictionaries
                    images_data = []
                    for img in page.images:
                        if hasattr(img, 'model_dump'):
                            images_data.append(img.model_dump())
                        elif hasattr(img, 'dict'):
                            images_data.append(img.dict())
                        elif hasattr(img, '__dict__'):
                            # Convert object attributes to dict, handling non-serializable values
                            img_dict = {}
                            for key, value in img.__dict__.items():
                                try:
                                    # Test if the value is JSON serializable
                                    json.dumps(value)
                                    img_dict[key] = value
                                except (TypeError, ValueError):
                                    img_dict[key] = str(value)
                            images_data.append(img_dict)
                        else:
                            images_data.append(str(img))
                    
                    json.dump(images_data, f, indent=2, ensure_ascii=False)
                    print(f"Saved page images info: {images_info_file}")
                except Exception as e:
                    # Fallback: save as string representation
                    f.write(f"Images (string representation): {str(page.images)}")
                    print(f"Saved page images info as string: {images_info_file} (Error: {e})")


def organize_pdf_files_by_subject(pdf_dir):
    """
    Organize PDF files in the pdf directory by subject (first 4 digits of filename)
    Returns a dictionary with subject as key and list of file paths as values
    """
    pdf_path = Path(pdf_dir)
    subjects = defaultdict(list)
    
    # Find all PDF files in the directory
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
    
    # Group files by subject (first 4 digits)
    for pdf_file in pdf_files:
        filename = pdf_file.name
        if len(filename) >= 4 and filename[:4].isdigit():
            subject = filename[:4]
            subjects[subject].append(pdf_file)
            print(f"  {filename} -> subject {subject}")
        else:
            print(f"  Skipping {filename} - doesn't start with 4 digits")
    
    # Create subject directories and move files
    for subject, files in subjects.items():
        subject_dir = pdf_path / subject
        subject_dir.mkdir(exist_ok=True)
        
        moved_files = []
        for file_path in files:
            new_path = subject_dir / file_path.name
            if not new_path.exists():  # Only move if not already there
                shutil.move(str(file_path), str(new_path))
                print(f"Moved {file_path.name} to {subject_dir}")
            moved_files.append(new_path)
        
        subjects[subject] = moved_files
    
    return dict(subjects)


async def process_subject_batch(subject, pdf_files, base_output_dir):
    """
    Process all PDF files for a subject using batch parsing
    """
    print(f"\n=== Processing Subject {subject} ===")
    print(f"Files: {[f.name for f in pdf_files]}")
    
    # Create subject output directory
    subject_output_dir = Path(base_output_dir) / subject
    subject_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert paths to strings for the parser
    pdf_paths = [str(pdf_file) for pdf_file in pdf_files]
    
    try:
        # Batch parse all files for this subject
        print(f"Starting batch parsing of {len(pdf_paths)} files...")
        results = await parser.aparse(pdf_paths)
        
        # Handle batch results (should be a list of JobResult objects)
        if not isinstance(results, list):
            results = [results]
        
        print(f"Got {len(results)} results from batch processing")
        
        # Process each result
        for i, result in enumerate(results):
            file_name = pdf_files[i].stem  # filename without extension
            print(f"\nProcessing result {i+1}/{len(results)} for file: {file_name}")
            
            # Create output directory for this specific file
            file_output_dir = subject_output_dir / file_name
            
            # Save debug information
            debug_file = file_output_dir / "results_debug.json"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                debug_data = {
                    "file_name": file_name,
                    "subject": subject,
                    "result_type": str(type(result)),
                    "attributes": [attr for attr in dir(result) if not attr.startswith('_')],
                }
                
                if hasattr(result, 'pages'):
                    try:
                        if isinstance(result.pages, list):
                            debug_data["pages_count"] = len(result.pages)
                        else:
                            debug_data["pages_info"] = str(result.pages)
                    except:
                        debug_data["pages_info"] = "Cannot determine pages info"
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(debug_data, f, indent=2, ensure_ascii=False, default=str)
                print(f"Saved debug results to: {debug_file}")
                
            except Exception as e:
                print(f"Error saving debug results: {e}")
            
            # Process the result if it has pages
            if hasattr(result, 'pages'):
                try:
                    pages_count = len(result.pages) if isinstance(result.pages, list) else "unknown"
                    print(f"  Processing {pages_count} pages...")
                except:
                    print("  Processing pages...")
                
                # Save all page data (text, markdown, layout, structured data)
                save_page_data(result.pages, file_output_dir)
                
                # Get and save the llama-index documents
                try:
                    markdown_documents = result.get_markdown_documents(split_by_page=True)
                    save_markdown_documents(markdown_documents, file_output_dir)
                except Exception as e:
                    print(f"  Error getting markdown documents: {e}")

                try:
                    text_documents = result.get_text_documents(split_by_page=False)
                    save_text_documents(text_documents, file_output_dir)
                except Exception as e:
                    print(f"  Error getting text documents: {e}")

                try:
                    image_documents = result.get_image_documents(
                        include_screenshot_images=True,
                        include_object_images=False,
                        image_download_dir=str(file_output_dir / "images"),
                    )
                    save_images(image_documents, file_output_dir)
                except Exception as e:
                    print(f"  Error getting image documents: {e}")
                
                print(f"  ✅ Completed processing for {file_name}")
            else:
                print(f"  ⚠️  Result for {file_name} has no pages attribute")
        
        print(f"\n✅ Subject {subject} batch processing completed!")
        print(f"Results saved to: {subject_output_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing subject {subject}: {e}")
        return False


def categorize_documents_by_type(subject_output_dir):
    """
    Categorize documents in a subject folder by their ending letters
    Returns a dictionary with document types as keys and lists of document folders as values
    """
    subject_path = Path(subject_output_dir)
    
    # Document type mapping with descriptions
    doc_types = {
        'E': {'name': 'Admission Notes', 'folders': []},
        'A': {'name': 'Release Notes', 'folders': []},
        'BIC': {'name': 'Death Notices', 'folders': []},
        'O': {'name': 'Death Certificates', 'folders': []}
    }
    
    # Find all document folders in the subject directory
    if not subject_path.exists():
        print(f"Subject directory not found: {subject_path}")
        return doc_types
    
    for item in subject_path.iterdir():
        if item.is_dir() and item.name != 'merged':  # Skip merged folder if it exists
            folder_name = item.name
            
            # Check document type by ending
            if folder_name.endswith('BIC'):
                doc_types['BIC']['folders'].append(item)
            elif folder_name.endswith('E'):
                doc_types['E']['folders'].append(item)
            elif folder_name.endswith('A'):
                doc_types['A']['folders'].append(item)
            elif folder_name.endswith('O'):
                doc_types['O']['folders'].append(item)
            else:
                print(f"Unknown document type for folder: {folder_name}")
    
    # Sort folders within each type for consistent ordering
    for doc_type in doc_types.values():
        doc_type['folders'].sort(key=lambda x: x.name)
    
    return doc_types


def merge_pages_for_document(doc_folder):
    """
    Merge all markdown pages for a single document into one text
    Returns the merged content with page separators
    """
    markdown_dir = doc_folder / 'markdown'
    
    if not markdown_dir.exists():
        print(f"No markdown folder found in: {doc_folder}")
        return ""
    
    # Get all markdown files and sort them by page number
    md_files = list(markdown_dir.glob('page_*.md'))
    md_files.sort(key=lambda x: int(x.stem.split('_')[1]))  # Sort by page number
    
    if not md_files:
        print(f"No markdown files found in: {markdown_dir}")
        return ""
    
    merged_content = []
    
    for md_file in md_files:
        page_num = md_file.stem.split('_')[1]
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                page_content = f.read().strip()
            
            # Add page separator and content
            merged_content.append(f"## Page {page_num}")
            merged_content.append("")  # Empty line
            merged_content.append(page_content)
            merged_content.append("")  # Empty line after content
            
        except Exception as e:
            print(f"Error reading {md_file}: {e}")
            merged_content.append(f"## Page {page_num}")
            merged_content.append("")
            merged_content.append(f"*Error reading page content: {e}*")
            merged_content.append("")
    
    return "\n".join(merged_content)


def merge_documents_by_subject(subject_output_dir):
    """
    Merge all documents for a subject in the specified order with clear separations
    """
    subject_path = Path(subject_output_dir)
    subject_name = subject_path.name
    
    print(f"\n=== Merging documents for Subject {subject_name} ===")
    
    # Categorize documents
    doc_types = categorize_documents_by_type(subject_output_dir)
    
    # Check if there are any documents to merge
    total_docs = sum(len(doc_type['folders']) for doc_type in doc_types.values())
    if total_docs == 0:
        print(f"No documents found for subject {subject_name}")
        return False
    
    # Create the merged document content
    merged_content = []
    
    # Add document header
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    merged_content.extend([
        f"# Medical Records - Subject {subject_name}",
        "",
        f"*Generated on: {current_time}*",
        "",
        "---",
        ""
    ])
    
    # Process documents in the specified order
    processing_order = ['E', 'A', 'BIC', 'O']
    
    for doc_type in processing_order:
        doc_info = doc_types[doc_type]
        folders = doc_info['folders']
        
        if not folders:
            continue
        
        print(f"  Processing {len(folders)} {doc_info['name']} documents...")
        
        # Add section header
        merged_content.extend([
            f"# {doc_info['name']} ({doc_type})",
            "",
        ])
        
        # Process each document of this type
        for i, doc_folder in enumerate(folders, 1):
            doc_name = doc_folder.name
            print(f"    - {doc_name}")
            
            # Add document separator
            merged_content.extend([
                f"## Document: {doc_name}",
                "",
            ])
            
            # Merge pages for this document
            document_content = merge_pages_for_document(doc_folder)
            if document_content:
                merged_content.append(document_content)
            else:
                merged_content.extend([
                    "*No content available for this document.*",
                    ""
                ])
            
            # Add separator between documents (except for the last one in the type)
            if i < len(folders):
                merged_content.extend([
                    "",
                    "---",
                    ""
                ])
        
        # Add section separator (except for the last section)
        merged_content.extend([
            "",
            "=" * 80,
            ""
        ])
    
    # Save the merged document
    merged_file = subject_path / f"{subject_name}_merged_medical_records.md"
    
    try:
        with open(merged_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(merged_content))
        
        print(f"  ✅ Merged document saved: {merged_file}")
        
        # Create a summary
        summary_lines = [
            f"## Merge Summary for Subject {subject_name}",
            "",
        ]
        
        for doc_type in processing_order:
            doc_info = doc_types[doc_type]
            folders = doc_info['folders']
            if folders:
                summary_lines.append(f"- **{doc_info['name']} ({doc_type})**: {len(folders)} documents")
                for folder in folders:
                    summary_lines.append(f"  - {folder.name}")
        
        summary_lines.extend([
            "",
            f"**Total documents merged**: {total_docs}",
            f"**Output file**: `{merged_file.name}`"
        ])
        
        print("\n" + "\n".join(summary_lines))
        return True
        
    except Exception as e:
        print(f"  ❌ Error saving merged document: {e}")
        return False


def process_all_subjects_markdown(base_output_dir):
    """
    Process markdown merging for all subjects in the output directory
    """
    base_path = Path(base_output_dir)
    
    if not base_path.exists():
        print(f"Output directory not found: {base_output_dir}")
        return
    
    print(f"\n=== Processing Markdown Merging for All Subjects ===")
    
    # Find all subject directories (4-digit numbers)
    subject_dirs = [d for d in base_path.iterdir() 
                   if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
    
    if not subject_dirs:
        print("No subject directories found")
        return
    
    successful_merges = 0
    failed_merges = 0
    
    for subject_dir in subject_dirs:
        try:
            success = merge_documents_by_subject(subject_dir)
            if success:
                successful_merges += 1
            else:
                failed_merges += 1
        except Exception as e:
            print(f"❌ Critical error processing subject {subject_dir.name}: {e}")
            failed_merges += 1
    
    # Final summary
    print(f"\n=== Markdown Merging Summary ===")
    print(f"✅ Successfully merged: {successful_merges} subjects")
    print(f"❌ Failed to merge: {failed_merges} subjects")
    print(f"📁 Total subjects: {len(subject_dirs)}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="PDF Parser with LlamaParse - Batch processing with markdown merging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run full workflow (default)
  python main.py --full             # Run full workflow explicitly
  python main.py --parse-only       # Only parse PDFs with LlamaParse
  python main.py --merge-only       # Only merge markdown files
  python main.py --force            # Force processing, skip all checkpoints
        """
    )
    
    # Workflow mode flags (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--full', 
        action='store_true', 
        help='Run full workflow: PDF parsing + markdown merging (default)'
    )
    mode_group.add_argument(
        '--parse-only', 
        action='store_true', 
        help='Only run PDF parsing with LlamaParse'
    )
    mode_group.add_argument(
        '--merge-only', 
        action='store_true', 
        help='Only run markdown merging (skip PDF parsing)'
    )
    
    # Control flags
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Force processing, skip all checkpoints'
    )
    parser.add_argument(
        '--skip-existing', 
        action='store_true', 
        default=True,
        help='Skip processing if outputs already exist (default: True)'
    )
    parser.add_argument(
        '--no-skip-existing', 
        dest='skip_existing',
        action='store_false', 
        help='Process even if outputs already exist'
    )
    
    args = parser.parse_args()
    
    # Default to full workflow if no mode specified
    if not any([args.full, args.parse_only, args.merge_only]):
        args.full = True
    
    return args


def check_new_pdfs(pdf_dir):
    """
    Check if there are new PDF files in the main pdf/ folder
    Returns: (has_new_pdfs, pdf_files_list)
    """
    pdf_path = Path(pdf_dir)
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    if not pdf_files:
        return False, []
    
    print(f"📄 Found {len(pdf_files)} PDF files in {pdf_dir}:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    return True, pdf_files


def check_subject_already_processed(subject, base_output_dir):
    """
    Check if a subject has already been processed
    Returns: (is_processed, subject_output_dir)
    """
    subject_output_dir = Path(base_output_dir) / subject
    
    if not subject_output_dir.exists():
        return False, subject_output_dir
    
    # Check if there are any document folders in the subject directory
    doc_folders = [d for d in subject_output_dir.iterdir() 
                  if d.is_dir() and d.name != 'merged']
    
    if not doc_folders:
        return False, subject_output_dir
    
    # Check if at least one document folder has content
    for doc_folder in doc_folders:
        markdown_dir = doc_folder / 'markdown'
        if markdown_dir.exists() and list(markdown_dir.glob('*.md')):
            return True, subject_output_dir
    
    return False, subject_output_dir


def check_subject_already_merged(subject, base_output_dir):
    """
    Check if a subject's markdown has already been merged
    Returns: (is_merged, merged_file_path)
    """
    subject_output_dir = Path(base_output_dir) / subject
    merged_file = subject_output_dir / f"{subject}_merged_medical_records.md"
    
    if merged_file.exists() and merged_file.stat().st_size > 0:
        return True, merged_file
    
    return False, merged_file


def get_processing_plan(args, pdf_dir, base_output_dir):
    """
    Analyze current state and create a processing plan based on args and checkpoints
    """
    plan = {
        'parse_pdfs': False,
        'merge_markdown': False,
        'subjects_to_parse': {},
        'subjects_to_merge': [],
        'skip_reasons': [],
        'force_reasons': []
    }
    
    # Check for new PDFs
    has_new_pdfs, pdf_files = check_new_pdfs(pdf_dir)
    
    # Determine what to do based on mode and checkpoints
    if args.parse_only or args.full:
        if not has_new_pdfs and not args.force:
            plan['skip_reasons'].append("No new PDFs found in main pdf/ folder")
        else:
            if has_new_pdfs:
                # Organize files by subject and check if already processed
                subjects = {}
                for pdf_file in pdf_files:
                    filename = pdf_file.name
                    if len(filename) >= 4 and filename[:4].isdigit():
                        subject = filename[:4]
                        if subject not in subjects:
                            subjects[subject] = []
                        subjects[subject].append(pdf_file)
                
                for subject, files in subjects.items():
                    is_processed, subject_dir = check_subject_already_processed(subject, base_output_dir)
                    
                    if is_processed and args.skip_existing and not args.force:
                        plan['skip_reasons'].append(f"Subject {subject} already processed")
                    else:
                        plan['subjects_to_parse'][subject] = files
                        if is_processed and args.force:
                            plan['force_reasons'].append(f"Subject {subject} - reprocessing (forced)")
                
                if plan['subjects_to_parse']:
                    plan['parse_pdfs'] = True
    
    if args.merge_only or args.full:
        # Find all subjects in output directory
        base_path = Path(base_output_dir)
        if base_path.exists():
            subject_dirs = [d for d in base_path.iterdir() 
                           if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
            
            for subject_dir in subject_dirs:
                subject = subject_dir.name
                is_merged, merged_file = check_subject_already_merged(subject, base_output_dir)
                
                if is_merged and args.skip_existing and not args.force:
                    plan['skip_reasons'].append(f"Subject {subject} already merged")
                else:
                    plan['subjects_to_merge'].append(subject)
                    if is_merged and args.force:
                        plan['force_reasons'].append(f"Subject {subject} - remerging (forced)")
            
            if plan['subjects_to_merge']:
                plan['merge_markdown'] = True
    
    return plan


async def main():
    # Parse command line arguments
    args = parse_arguments()
    
    print("🔥 PDF Parser with LlamaParse - Advanced Workflow")
    print(f"LLAMA_CLOUD_API_KEY: {LLAMA_CLOUD_API_KEY}")
    
    # Configuration
    pdf_dir = "./pdf"
    base_output_dir = "./pdf/output"
    
    # Show current mode
    if args.full:
        mode = "Full Workflow (PDF Parsing + Markdown Merging)"
    elif args.parse_only:
        mode = "PDF Parsing Only"
    elif args.merge_only:
        mode = "Markdown Merging Only"
    
    print(f"🎯 Mode: {mode}")
    print(f"⚡ Force processing: {'Yes' if args.force else 'No'}")
    print(f"🔍 Skip existing: {'Yes' if args.skip_existing else 'No'}")
    
    # Step 1: Analyze current state and create processing plan
    print(f"\n=== Step 1: Analyzing Current State ===")
    plan = get_processing_plan(args, pdf_dir, base_output_dir)
    
    # Display plan
    print(f"\n📋 Processing Plan:")
    print(f"  📄 Parse PDFs: {'Yes' if plan['parse_pdfs'] else 'No'}")
    print(f"  📝 Merge Markdown: {'Yes' if plan['merge_markdown'] else 'No'}")
    
    if plan['skip_reasons']:
        print(f"\n⏭️  Skipping reasons:")
        for reason in plan['skip_reasons']:
            print(f"    - {reason}")
    
    if plan['force_reasons']:
        print(f"\n💪 Force processing:")
        for reason in plan['force_reasons']:
            print(f"    - {reason}")
    
    if plan['subjects_to_parse']:
        print(f"\n📄 Subjects to parse ({len(plan['subjects_to_parse'])}):")
        for subject, files in plan['subjects_to_parse'].items():
            print(f"    - Subject {subject}: {len(files)} files")
    
    if plan['subjects_to_merge']:
        print(f"\n📝 Subjects to merge ({len(plan['subjects_to_merge'])}):")
        for subject in plan['subjects_to_merge']:
            print(f"    - Subject {subject}")
    
    # Step 2: Execute PDF parsing if needed
    successful_subjects = []
    failed_subjects = []
    
    if plan['parse_pdfs']:
        print(f"\n=== Step 2: PDF Processing ===")
        
        # Organize PDF files by subject first
        print("📁 Organizing PDF files by subject...")
        subjects = organize_pdf_files_by_subject(pdf_dir)
        
        # Filter subjects based on plan
        subjects_to_process = {k: v for k, v in subjects.items() 
                             if k in plan['subjects_to_parse']}
        
        if subjects_to_process:
            print(f"\n🔄 Processing {len(subjects_to_process)} subjects...")
            
            for subject, pdf_files in subjects_to_process.items():
                try:
                    success = await process_subject_batch(subject, pdf_files, base_output_dir)
                    if success:
                        successful_subjects.append(subject)
                    else:
                        failed_subjects.append(subject)
                except Exception as e:
                    print(f"❌ Critical error processing subject {subject}: {e}")
                    failed_subjects.append(subject)
            
            # Summary
            print(f"\n📊 PDF Processing Summary:")
            print(f"  ✅ Successfully processed: {len(successful_subjects)} subjects")
            print(f"  ❌ Failed to process: {len(failed_subjects)} subjects")
        else:
            print("📭 No subjects need PDF processing")
    else:
        print(f"\n=== Step 2: PDF Processing (Skipped) ===")
        print("📭 No PDF processing needed based on current plan")
    
    # Step 3: Execute markdown merging if needed
    if plan['merge_markdown']:
        print(f"\n=== Step 3: Markdown Merging ===")
        
        # Filter subjects to merge based on plan
        subjects_to_merge = plan['subjects_to_merge']
        
        if subjects_to_merge:
            print(f"🔄 Processing markdown merging for {len(subjects_to_merge)} subjects...")
            
            merge_successful = 0
            merge_failed = 0
            
            for subject in subjects_to_merge:
                try:
                    subject_output_dir = Path(base_output_dir) / subject
                    success = merge_documents_by_subject(subject_output_dir)
                    if success:
                        merge_successful += 1
                    else:
                        merge_failed += 1
                except Exception as e:
                    print(f"❌ Critical error merging subject {subject}: {e}")
                    merge_failed += 1
            
            print(f"\n📊 Markdown Merging Summary:")
            print(f"  ✅ Successfully merged: {merge_successful} subjects")
            print(f"  ❌ Failed to merge: {merge_failed} subjects")
        else:
            print("📭 No subjects need markdown merging")
    else:
        print(f"\n=== Step 3: Markdown Merging (Skipped) ===")
        print("📭 No markdown merging needed based on current plan")
    
    # Final Summary
    print(f"\n🎉 Workflow Completed!")
    
    if plan['parse_pdfs']:
        print(f"📄 PDF Processing: {len(successful_subjects)}/{len(successful_subjects) + len(failed_subjects)} subjects completed")
    
    if plan['merge_markdown']:
        print(f"📝 Markdown Merging: Processed {len(plan['subjects_to_merge'])} subjects")
    
    if not plan['parse_pdfs'] and not plan['merge_markdown']:
        print("📭 Nothing to process - all outputs are up to date!")
        print("💡 Use --force to reprocess existing files")
    
    print(f"\n📁 Check outputs in: {base_output_dir}/")
    print("💡 Use --help to see all available options")


if __name__ == "__main__":
    asyncio.run(main())
