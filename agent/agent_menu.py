"""
Agent Menu - Manage AI extraction and database integration

This menu provides tools to:
1. Check agent extraction statistics
2. Process individual cases with AI
3. Batch process multiple cases
4. Track database insertion status

Author: Agent
Date: 2025-01-15
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from icecream import ic

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "database"))

from agent.agent import process_medical_record

# Import database modules with proper path handling
try:
    from database.db_manager import MongoDBManager
    from database.data_importer import MedicalRecordImporter
except ImportError:
    # Fallback for when running from agent directory
    from db_manager import MongoDBManager  # type: ignore
    from data_importer import MedicalRecordImporter  # type: ignore

console = Console()


# ============================================================================
# Statistics & Status Functions
# ============================================================================

def get_agent_statistics(base_output_dir: str = "./pdf/output") -> Dict[str, Any]:
    """
    Analyze agent extraction status for all subjects.
    
    Returns:
        Dictionary with comprehensive statistics
    """
    base = Path(base_output_dir)
    
    stats = {
        "total_subjects": 0,
        "with_cleaned_md": 0,
        "with_extracted_json": 0,
        "with_db_record": 0,
        "ready_for_extraction": 0,
        "extracted_not_in_db": 0,
        "subjects": {},
        "by_year": {}
    }
    
    # Get all subject directories (4-digit)
    subject_dirs = [d for d in base.iterdir() 
                    if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
    
    stats["total_subjects"] = len(subject_dirs)
    
    # Initialize MongoDB connection to check database status
    collection = None
    db_manager = None
    try:
        db_manager = MongoDBManager()
        db_connected = db_manager.connect()
        if db_connected and db_manager.db is not None:
            collection = db_manager.db['internamentos']
    except Exception as e:
        console.print(f"[yellow]Warning: Could not connect to database: {e}[/yellow]")
    
    for subject_dir in subject_dirs:
        subject_id = subject_dir.name
        year = extract_year_from_subject(subject_id)
        
        # Initialize year stats
        if year not in stats["by_year"]:
            stats["by_year"][year] = {
                "total": 0,
                "with_cleaned_md": 0,
                "with_extracted_json": 0,
                "with_db_record": 0,
                "ready_for_extraction": 0,
                "extracted_not_in_db": 0
            }
        
        stats["by_year"][year]["total"] += 1
        
        # Check for cleaned markdown file
        cleaned_file = subject_dir / f"{subject_id}_merged_medical_records.cleaned.md"
        has_cleaned = cleaned_file.exists()
        
        # Check for extracted JSON file
        extracted_file = subject_dir / f"{subject_id}_extracted.json"
        has_extracted = extracted_file.exists()
        
        # Check if record exists in database
        has_db_record = False
        if collection is not None:
            try:
                numero_internamento = int(subject_id)
                existing = collection.find_one({
                    "internamento.numero_internamento": numero_internamento
                })
                has_db_record = existing is not None
            except Exception:
                pass
        
        # Update stats
        if has_cleaned:
            stats["with_cleaned_md"] += 1
            stats["by_year"][year]["with_cleaned_md"] += 1
            
            if not has_extracted:
                stats["ready_for_extraction"] += 1
                stats["by_year"][year]["ready_for_extraction"] += 1
        
        if has_extracted:
            stats["with_extracted_json"] += 1
            stats["by_year"][year]["with_extracted_json"] += 1
            
            if not has_db_record:
                stats["extracted_not_in_db"] += 1
                stats["by_year"][year]["extracted_not_in_db"] += 1
        
        if has_db_record:
            stats["with_db_record"] += 1
            stats["by_year"][year]["with_db_record"] += 1
        
        # Store subject details
        stats["subjects"][subject_id] = {
            "year": year,
            "has_cleaned_md": has_cleaned,
            "has_extracted_json": has_extracted,
            "has_db_record": has_db_record,
            "ready_for_extraction": has_cleaned and not has_extracted,
            "ready_for_db": has_extracted and not has_db_record,
            "cleaned_file": str(cleaned_file) if has_cleaned else None,
            "extracted_file": str(extracted_file) if has_extracted else None
        }
    
    # Database connection will be closed automatically
    
    return stats


def extract_year_from_subject(subject: str) -> int:
    """Extract year from subject ID."""
    if len(subject) == 4:
        year_digits = subject[:2]
        return 2000 + int(year_digits)
    elif len(subject) == 3:
        year_digit = subject[0]
        return 2000 + int(year_digit)
    else:
        return 2000


def get_extracted_not_in_db_details(base_output_dir: str = "./pdf/output") -> List[Dict[str, Any]]:
    """
    Get detailed information about subjects that are extracted but not in database.
    Verifies by reading JSON files and checking database.
    
    Returns:
        List of dictionaries with subject details
    """
    details = []
    base = Path(base_output_dir)
    
    # Connect to MongoDB
    collection = None
    try:
        db_manager = MongoDBManager()
        db_connected = db_manager.connect()
        if db_connected and db_manager.db is not None:
            collection = db_manager.db['internamentos']
    except Exception:
        return details
    
    # Get all subject directories
    subject_dirs = [d for d in base.iterdir() 
                    if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
    
    for subject_dir in subject_dirs:
        subject_id = subject_dir.name
        extracted_file = subject_dir / f"{subject_id}_extracted.json"
        
        # Check if extracted JSON exists
        if not extracted_file.exists():
            continue
        
        # Read JSON to get numero_internamento
        try:
            with open(extracted_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Get numero_internamento from JSON
            numero_internamento = json_data.get("internamento", {}).get("numero_internamento")
            
            if numero_internamento is None:
                details.append({
                    "subject_id": subject_id,
                    "numero_internamento": None,
                    "in_database": False,
                    "error": "numero_internamento not found in JSON",
                    "json_file": str(extracted_file)
                })
                continue
            
            # Check if exists in database
            in_db = False
            if collection is not None:
                existing = collection.find_one({
                    "internamento.numero_internamento": numero_internamento
                })
                in_db = existing is not None
            
            # Only add if not in database
            if not in_db:
                # Get patient name for display
                patient_name = json_data.get("doente", {}).get("nome", "Unknown")
                
                details.append({
                    "subject_id": subject_id,
                    "numero_internamento": numero_internamento,
                    "patient_name": patient_name,
                    "in_database": False,
                    "json_file": str(extracted_file)
                })
        
        except Exception as e:
            details.append({
                "subject_id": subject_id,
                "numero_internamento": None,
                "in_database": False,
                "error": str(e),
                "json_file": str(extracted_file)
            })
    
    return details


def display_agent_statistics(stats: Dict[str, Any]):
    """Display agent statistics with Rich tables."""
    
    # Overall statistics
    overview = Table(
        title="[bold cyan]Agent Extraction Overview[/bold cyan]",
        box=box.ROUNDED,
        header_style="bold magenta"
    )
    overview.add_column("Metric", style="cyan", no_wrap=True)
    overview.add_column("Count", style="bold yellow", justify="right")
    overview.add_column("Percentage", style="green", justify="right")
    
    total = stats["total_subjects"]
    
    rows = [
        ("Total Subjects", stats["total_subjects"], "100%"),
        ("With Cleaned Markdown", stats["with_cleaned_md"], 
         f"{stats['with_cleaned_md']/total*100:.1f}%" if total > 0 else "0%"),
        ("With Extracted JSON", stats["with_extracted_json"], 
         f"{stats['with_extracted_json']/total*100:.1f}%" if total > 0 else "0%"),
        ("Inserted to Database", stats["with_db_record"], 
         f"{stats['with_db_record']/total*100:.1f}%" if total > 0 else "0%"),
        ("", "", ""),
        ("Ready for Extraction", stats["ready_for_extraction"], 
         f"{stats['ready_for_extraction']/total*100:.1f}%" if total > 0 else "0%"),
        ("Extracted, Not in DB", stats["extracted_not_in_db"], 
         f"{stats['extracted_not_in_db']/total*100:.1f}%" if total > 0 else "0%"),
    ]
    
    for metric, count, pct in rows:
        if metric == "":
            overview.add_row("─" * 25, "─" * 8, "─" * 10)
        else:
            overview.add_row(metric, str(count), pct)
    
    console.print(overview)
    
    # Year breakdown
    if stats["by_year"]:
        year_table = Table(
            title="[bold cyan]Statistics by Year[/bold cyan]",
            box=box.SIMPLE,
            header_style="bold cyan"
        )
        year_table.add_column("Year", style="yellow", justify="center")
        year_table.add_column("Total", style="white", justify="center")
        year_table.add_column("Cleaned", style="green", justify="center")
        year_table.add_column("Extracted", style="blue", justify="center")
        year_table.add_column("In DB", style="magenta", justify="center")
        year_table.add_column("Ready", style="bright_yellow", justify="center")
        year_table.add_column("Not in DB", style="red", justify="center")
        
        for year in sorted(stats["by_year"].keys()):
            year_data = stats["by_year"][year]
            year_table.add_row(
                str(year),
                str(year_data["total"]),
                str(year_data["with_cleaned_md"]),
                str(year_data["with_extracted_json"]),
                str(year_data["with_db_record"]),
                str(year_data["ready_for_extraction"]),
                str(year_data["extracted_not_in_db"])
            )
        
        console.print(year_table)
    
    # Show extracted but not in DB subjects if any exist
    if stats["extracted_not_in_db"] > 0:
        console.print()  # Spacing
        details = get_extracted_not_in_db_details()
        
        if details:
            not_in_db_table = Table(
                title=f"[bold red]⚠️  Extracted but Not in Database ({len(details)} subjects)[/bold red]",
                box=box.ROUNDED,
                header_style="bold red"
            )
            not_in_db_table.add_column("Subject ID", style="yellow", no_wrap=True)
            not_in_db_table.add_column("Num. Internamento", style="cyan", justify="center")
            not_in_db_table.add_column("Patient Name", style="white")
            not_in_db_table.add_column("Status", style="red")
            
            for detail in details:
                subject_id = detail["subject_id"]
                numero_int = str(detail["numero_internamento"]) if detail.get("numero_internamento") else "N/A"
                patient_name = detail.get("patient_name", "Unknown")[:40]  # Truncate long names
                
                if detail.get("error"):
                    status = f"Error: {detail['error'][:30]}"
                else:
                    status = "Not in DB"
                
                not_in_db_table.add_row(subject_id, numero_int, patient_name, status)
            
            console.print(not_in_db_table)


def list_subjects_by_status(stats: Dict[str, Any], status_filter: str) -> List[str]:
    """
    List subjects matching a specific status.
    
    Args:
        stats: Statistics dictionary
        status_filter: 'ready_extraction', 'ready_db', 'extracted', 'in_db'
    
    Returns:
        List of subject IDs
    """
    subjects = []
    
    for subject_id, subject_data in stats["subjects"].items():
        if status_filter == "ready_extraction" and subject_data["ready_for_extraction"]:
            subjects.append(subject_id)
        elif status_filter == "ready_db" and subject_data["ready_for_db"]:
            subjects.append(subject_id)
        elif status_filter == "extracted" and subject_data["has_extracted_json"]:
            subjects.append(subject_id)
        elif status_filter == "in_db" and subject_data["has_db_record"]:
            subjects.append(subject_id)
    
    return sorted(subjects)


# ============================================================================
# Processing Functions
# ============================================================================

def process_single_subject(subject_id: str, base_output_dir: str = "./pdf/output") -> bool:
    """
    Process a single subject with AI extraction.
    
    Args:
        subject_id: Subject ID (4 digits)
        base_output_dir: Base output directory
    
    Returns:
        True if successful
    """
    subject_dir = Path(base_output_dir) / subject_id
    cleaned_file = subject_dir / f"{subject_id}_merged_medical_records.cleaned.md"
    
    if not cleaned_file.exists():
        console.print(f"[red]Error: Cleaned markdown file not found for subject {subject_id}[/red]")
        console.print(f"[dim]Expected: {cleaned_file}[/dim]")
        return False
    
    try:
        console.print(f"\n[bold cyan]Processing subject {subject_id}...[/bold cyan]")
        result = process_medical_record(str(cleaned_file))
        
        if result["success"]:
            console.print(f"[bold green]✓ Successfully processed subject {subject_id}[/bold green]")
            return True
        else:
            console.print(f"[bold red]✗ Failed to process subject {subject_id}: {result.get('error')}[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]✗ Error processing subject {subject_id}: {e}[/bold red]")
        return False


def process_batch_subjects(subject_ids: List[str], base_output_dir: str = "./pdf/output") -> Dict[str, Any]:
    """
    Process multiple subjects with AI extraction.
    
    Args:
        subject_ids: List of subject IDs
        base_output_dir: Base output directory
    
    Returns:
        Dictionary with processing results
    """
    results = {
        "total": len(subject_ids),
        "successful": 0,
        "failed": 0,
        "errors": []
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]Processing {len(subject_ids)} subjects...",
            total=len(subject_ids)
        )
        
        for subject_id in subject_ids:
            try:
                success = process_single_subject(subject_id, base_output_dir)
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Subject {subject_id}: Processing failed")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Subject {subject_id}: {str(e)}")
            
            progress.advance(task)
    
    return results


def import_subject_to_database(subject_id: str, base_output_dir: str = "./pdf/output") -> bool:
    """
    Import a subject's extracted JSON to MongoDB.
    
    Args:
        subject_id: Subject ID (4 digits)
        base_output_dir: Base output directory
    
    Returns:
        True if successful
    """
    json_file = Path(base_output_dir) / subject_id / f"{subject_id}_extracted.json"
    
    if not json_file.exists():
        console.print(f"[red]Error: Extracted JSON file not found for subject {subject_id}[/red]")
        console.print(f"[dim]Expected: {json_file}[/dim]")
        return False
    
    try:
        db_manager = MongoDBManager()
        db_connected = db_manager.connect()
        
        if not db_connected:
            console.print(f"[red]Error: Could not connect to database[/red]")
            return False
        
        importer = MedicalRecordImporter(db_manager)
        
        console.print(f"\n[bold cyan]Importing subject {subject_id} to database...[/bold cyan]")
        result = importer.import_json_file(str(json_file))
        
        if result["success"]:
            console.print(f"[bold green]✓ Successfully imported subject {subject_id} to database[/bold green]")
            return True
        else:
            console.print(f"[bold red]✗ Failed to import subject {subject_id}: {result.get('error')}[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]✗ Error importing subject {subject_id}: {e}[/bold red]")
        return False


def import_batch_to_database(subject_ids: List[str], base_output_dir: str = "./pdf/output") -> Dict[str, Any]:
    """
    Import multiple subjects to MongoDB.
    
    Args:
        subject_ids: List of subject IDs
        base_output_dir: Base output directory
    
    Returns:
        Dictionary with import results
    """
    results = {
        "total": len(subject_ids),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]Importing {len(subject_ids)} subjects to database...",
            total=len(subject_ids)
        )
        
        for subject_id in subject_ids:
            try:
                success = import_subject_to_database(subject_id, base_output_dir)
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Subject {subject_id}: Import failed")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Subject {subject_id}: {str(e)}")
            
            progress.advance(task)
    
    return results


# ============================================================================
# Menu Functions
# ============================================================================

async def menu_agent(base_output_dir: str = "./pdf/output"):
    """Agent management menu."""
    
    while True:
        console.rule("[bold magenta]Agent Management Menu")
        
        # Get and display statistics
        console.print("\n[dim]Loading statistics...[/dim]")
        stats = get_agent_statistics(base_output_dir)
        display_agent_statistics(stats)
        
        # Menu options
        console.print()
        options_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        options_table.add_column("Opt", style="bold cyan", width=4, justify="right")
        options_table.add_column("Action", style="white")
        
        for k, label in [
            ("1", "Process single subject (AI extraction)"),
            ("2", "Process all ready subjects (batch AI extraction)"),
            ("3", "Process missing subjects only"),
            ("4", "Import single subject to database"),
            ("5", "Import all extracted subjects to database"),
            ("6", "Import missing subjects to database"),
            ("7", "Show detailed subject list"),
            ("8", "Full pipeline: Extract + Import for ready subjects"),
            ("0", "Back to Main Menu")
        ]:
            options_table.add_row(k, label)
        
        console.print(options_table)
        
        choice = Prompt.ask(
            "Enter choice",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            default="0"
        )
        
        if choice == "0":
            console.print("[green]Returning to main menu...[/green]")
            return
        
        elif choice == "1":
            # Process single subject
            subject_id = Prompt.ask("Enter subject ID (4 digits)")
            if len(subject_id) == 4 and subject_id.isdigit():
                process_single_subject(subject_id, base_output_dir)
            else:
                console.print("[red]Invalid subject ID. Must be 4 digits.[/red]")
        
        elif choice == "2":
            # Process all ready subjects
            ready_subjects = list_subjects_by_status(stats, "ready_extraction")
            
            if not ready_subjects:
                console.print("[yellow]No subjects ready for extraction.[/yellow]")
                continue
            
            console.print(f"\n[cyan]Found {len(ready_subjects)} subjects ready for extraction:[/cyan]")
            console.print(", ".join(ready_subjects[:20]))
            if len(ready_subjects) > 20:
                console.print(f"[dim]... and {len(ready_subjects) - 20} more[/dim]")
            
            if Confirm.ask(f"\nProcess all {len(ready_subjects)} subjects?"):
                results = process_batch_subjects(ready_subjects, base_output_dir)
                
                # Display results
                console.print(f"\n[bold]Processing Results:[/bold]")
                console.print(f"  [green]Successful: {results['successful']}[/green]")
                console.print(f"  [red]Failed: {results['failed']}[/red]")
                
                if results["errors"]:
                    console.print("\n[red]Errors:[/red]")
                    for error in results["errors"][:10]:
                        console.print(f"  • {error}")
                    if len(results["errors"]) > 10:
                        console.print(f"  [dim]... and {len(results['errors']) - 10} more errors[/dim]")
        
        elif choice == "3":
            # Process missing subjects only (ready but not extracted)
            ready_subjects = list_subjects_by_status(stats, "ready_extraction")
            
            if not ready_subjects:
                console.print("[green]All subjects have been processed![/green]")
                continue
            
            console.print(f"\n[cyan]Found {len(ready_subjects)} subjects missing extraction:[/cyan]")
            console.print(", ".join(ready_subjects[:20]))
            if len(ready_subjects) > 20:
                console.print(f"[dim]... and {len(ready_subjects) - 20} more[/dim]")
            
            if Confirm.ask(f"\nProcess {len(ready_subjects)} missing subjects?"):
                results = process_batch_subjects(ready_subjects, base_output_dir)
                
                console.print(f"\n[bold]Processing Results:[/bold]")
                console.print(f"  [green]Successful: {results['successful']}[/green]")
                console.print(f"  [red]Failed: {results['failed']}[/red]")
        
        elif choice == "4":
            # Import single subject to database
            subject_id = Prompt.ask("Enter subject ID (4 digits)")
            if len(subject_id) == 4 and subject_id.isdigit():
                import_subject_to_database(subject_id, base_output_dir)
            else:
                console.print("[red]Invalid subject ID. Must be 4 digits.[/red]")
        
        elif choice == "5":
            # Import all extracted subjects to database
            ready_db_subjects = list_subjects_by_status(stats, "ready_db")
            
            if not ready_db_subjects:
                console.print("[yellow]No extracted subjects waiting for database import.[/yellow]")
                continue
            
            console.print(f"\n[cyan]Found {len(ready_db_subjects)} subjects ready for database import:[/cyan]")
            console.print(", ".join(ready_db_subjects[:20]))
            if len(ready_db_subjects) > 20:
                console.print(f"[dim]... and {len(ready_db_subjects) - 20} more[/dim]")
            
            if Confirm.ask(f"\nImport all {len(ready_db_subjects)} subjects to database?"):
                results = import_batch_to_database(ready_db_subjects, base_output_dir)
                
                console.print(f"\n[bold]Import Results:[/bold]")
                console.print(f"  [green]Successful: {results['successful']}[/green]")
                console.print(f"  [red]Failed: {results['failed']}[/red]")
        
        elif choice == "6":
            # Import missing subjects to database
            ready_db_subjects = list_subjects_by_status(stats, "ready_db")
            
            if not ready_db_subjects:
                console.print("[green]All extracted subjects are in the database![/green]")
                continue
            
            console.print(f"\n[cyan]Found {len(ready_db_subjects)} subjects missing from database:[/cyan]")
            console.print(", ".join(ready_db_subjects[:20]))
            if len(ready_db_subjects) > 20:
                console.print(f"[dim]... and {len(ready_db_subjects) - 20} more[/dim]")
            
            if Confirm.ask(f"\nImport {len(ready_db_subjects)} missing subjects?"):
                results = import_batch_to_database(ready_db_subjects, base_output_dir)
                
                console.print(f"\n[bold]Import Results:[/bold]")
                console.print(f"  [green]Successful: {results['successful']}[/green]")
                console.print(f"  [red]Failed: {results['failed']}[/red]")
        
        elif choice == "7":
            # Show detailed subject list
            filter_choice = Prompt.ask(
                "\nFilter by",
                choices=["all", "ready", "extracted", "in_db", "missing_extraction", "missing_db"],
                default="all"
            )
            
            if filter_choice == "all":
                subjects = sorted(stats["subjects"].keys())
            elif filter_choice == "ready":
                subjects = list_subjects_by_status(stats, "ready_extraction")
            elif filter_choice == "extracted":
                subjects = list_subjects_by_status(stats, "extracted")
            elif filter_choice == "in_db":
                subjects = list_subjects_by_status(stats, "in_db")
            elif filter_choice == "missing_extraction":
                subjects = list_subjects_by_status(stats, "ready_extraction")
            elif filter_choice == "missing_db":
                subjects = list_subjects_by_status(stats, "ready_db")
            else:
                subjects = sorted(stats["subjects"].keys())
            
            if not subjects:
                console.print("[yellow]No subjects match the filter.[/yellow]")
                continue
            
            # Display in table
            detail_table = Table(
                title=f"[bold]Subject Details - {filter_choice.upper()}[/bold]",
                box=box.SIMPLE,
                header_style="bold cyan"
            )
            detail_table.add_column("Subject", style="yellow")
            detail_table.add_column("Year", style="white", justify="center")
            detail_table.add_column("Cleaned MD", style="green", justify="center")
            detail_table.add_column("Extracted", style="blue", justify="center")
            detail_table.add_column("In DB", style="magenta", justify="center")
            
            for subject_id in subjects[:50]:  # Limit to 50 for display
                subject_data = stats["subjects"][subject_id]
                detail_table.add_row(
                    subject_id,
                    str(subject_data["year"]),
                    "✓" if subject_data["has_cleaned_md"] else "✗",
                    "✓" if subject_data["has_extracted_json"] else "✗",
                    "✓" if subject_data["has_db_record"] else "✗"
                )
            
            console.print(detail_table)
            
            if len(subjects) > 50:
                console.print(f"\n[dim]Showing first 50 of {len(subjects)} subjects[/dim]")
        
        elif choice == "8":
            # Full pipeline: Extract + Import for ready subjects
            ready_subjects = list_subjects_by_status(stats, "ready_extraction")
            
            if not ready_subjects:
                console.print("[yellow]No subjects ready for full pipeline.[/yellow]")
                continue
            
            console.print(f"\n[cyan]Full Pipeline: Extract and Import {len(ready_subjects)} subjects[/cyan]")
            console.print(", ".join(ready_subjects[:20]))
            if len(ready_subjects) > 20:
                console.print(f"[dim]... and {len(ready_subjects) - 20} more[/dim]")
            
            if Confirm.ask(f"\nRun full pipeline for {len(ready_subjects)} subjects?"):
                # Step 1: Extract
                console.print("\n[bold]Step 1: AI Extraction[/bold]")
                extract_results = process_batch_subjects(ready_subjects, base_output_dir)
                
                console.print(f"\n[bold]Extraction Results:[/bold]")
                console.print(f"  [green]Successful: {extract_results['successful']}[/green]")
                console.print(f"  [red]Failed: {extract_results['failed']}[/red]")
                
                # Step 2: Import successfully extracted subjects
                if extract_results["successful"] > 0:
                    console.print("\n[bold]Step 2: Database Import[/bold]")
                    
                    # Refresh stats to get newly extracted subjects
                    updated_stats = get_agent_statistics(base_output_dir)
                    ready_db_subjects = [sid for sid in ready_subjects 
                                        if updated_stats["subjects"][sid]["has_extracted_json"]]
                    
                    if ready_db_subjects:
                        import_results = import_batch_to_database(ready_db_subjects, base_output_dir)
                        
                        console.print(f"\n[bold]Import Results:[/bold]")
                        console.print(f"  [green]Successful: {import_results['successful']}[/green]")
                        console.print(f"  [red]Failed: {import_results['failed']}[/red]")
                    
                    # Final summary
                    console.print("\n[bold green]Pipeline Complete![/bold green]")
                    console.print(f"  • Extracted: {extract_results['successful']} subjects")
                    console.print(f"  • Imported to DB: {import_results['successful']} subjects" if ready_db_subjects else "  • No subjects imported")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import asyncio
    asyncio.run(menu_agent())
