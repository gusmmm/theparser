import os
import json
import shutil
import asyncio
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


async def main():
    print("Hello from theparser - Batch Processing Mode!")
    print(f"LLAMA_CLOUD_API_KEY: {LLAMA_CLOUD_API_KEY}")
    
    # Step 1: Organize PDF files by subject
    pdf_dir = "./pdf"
    base_output_dir = "./pdf/output"
    
    print(f"\n=== Step 1: Organizing PDF files by subject ===")
    subjects = organize_pdf_files_by_subject(pdf_dir)
    
    if not subjects:
        print("No PDF files found with valid subject patterns (4-digit prefixes)")
        return
    
    print(f"\nFound {len(subjects)} subjects:")
    for subject, files in subjects.items():
        print(f"  Subject {subject}: {len(files)} files")
        for file in files:
            print(f"    - {file.name}")
    
    # Step 2: Process each subject in batch
    print(f"\n=== Step 2: Batch Processing Subjects ===")
    successful_subjects = []
    failed_subjects = []
    
    for subject, pdf_files in subjects.items():
        try:
            success = await process_subject_batch(subject, pdf_files, base_output_dir)
            if success:
                successful_subjects.append(subject)
            else:
                failed_subjects.append(subject)
        except Exception as e:
            print(f"❌ Critical error processing subject {subject}: {e}")
            failed_subjects.append(subject)
    
    # Step 3: Summary
    print(f"\n=== Processing Summary ===")
    print(f"✅ Successfully processed: {len(successful_subjects)} subjects")
    for subject in successful_subjects:
        subject_dir = Path(base_output_dir) / subject
        print(f"  - Subject {subject}: {subject_dir}")
    
    if failed_subjects:
        print(f"❌ Failed to process: {len(failed_subjects)} subjects")
        for subject in failed_subjects:
            print(f"  - Subject {subject}")
    
    print(f"\nOutput structure:")
    print(f"  {base_output_dir}/")
    for subject in successful_subjects:
        print(f"    {subject}/")
        subject_dir = Path(base_output_dir) / subject
        if subject_dir.exists():
            for file_dir in subject_dir.iterdir():
                if file_dir.is_dir():
                    print(f"      {file_dir.name}/")
                    print(f"        - markdown/: Page-by-page markdown files")
                    print(f"        - text/: Plain text documents")
                    print(f"        - images/: Extracted images")
                    print(f"        - layout/: Page layout information (JSON)")
                    print(f"        - structured_data/: Structured data (JSON)")
    
    print(f"\n🎉 Batch processing completed!")
    print(f"Total subjects processed: {len(successful_subjects)}/{len(subjects)}")


if __name__ == "__main__":
    asyncio.run(main())
