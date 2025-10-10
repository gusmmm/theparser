"""
Database Menu for UQ MongoDB Database

Interactive menu for database operations including:
- Import extracted JSON files to database
- View import statistics
- Query and manage database

Author: Agent
Date: 2025-10-10
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

# Add database directory to path
sys.path.insert(0, str(Path(__file__).parent))

from db_manager import MongoDBManager
from data_importer import MedicalRecordImporter

console = Console()


def analyze_extraction_status(base_output_dir: str = "./pdf/output") -> Dict:
    """
    Analyze which extracted JSON files exist and which have been imported to database.
    
    Args:
        base_output_dir: Base directory containing subject folders
        
    Returns:
        Dict with analysis results
    """
    results = {
        'total_subjects': 0,
        'with_extracted': 0,
        'without_extracted': 0,
        'imported': 0,
        'not_imported': 0,
        'subjects_extracted': [],
        'subjects_not_extracted': [],
        'subjects_imported': [],
        'subjects_not_imported': [],
        'extraction_files': {}
    }
    
    output_path = Path(base_output_dir)
    
    if not output_path.exists():
        console.print(f"[red]Directory not found: {base_output_dir}[/red]")
        return results
    
    # Get all subject directories (4-digit folders)
    subject_dirs = sorted([d for d in output_path.iterdir() 
                          if d.is_dir() and d.name.isdigit() and len(d.name) == 4])
    
    results['total_subjects'] = len(subject_dirs)
    
    # Connect to database to check import status
    db_manager = MongoDBManager()
    db_connected = db_manager.connect()
    
    internamentos_collection = None
    if db_connected and db_manager.db is not None:
        internamentos_collection = db_manager.db['internamentos']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing extraction status...", total=len(subject_dirs))
        
        for subject_dir in subject_dirs:
            subject_id = subject_dir.name
            extracted_file = subject_dir / f"{subject_id}_extracted.json"
            
            if extracted_file.exists():
                results['with_extracted'] += 1
                results['subjects_extracted'].append(subject_id)
                results['extraction_files'][subject_id] = str(extracted_file)
                
                # Check if imported to database
                if db_connected and internamentos_collection is not None:
                    try:
                        # Load JSON to get numero_internamento
                        with open(extracted_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        numero_internamento = data.get('internamento', {}).get('numero_internamento')
                        
                        if numero_internamento:
                            # Check if exists in database
                            exists = internamentos_collection.find_one({
                                'internamento.numero_internamento': numero_internamento
                            })
                            
                            if exists:
                                results['imported'] += 1
                                results['subjects_imported'].append(subject_id)
                            else:
                                results['not_imported'] += 1
                                results['subjects_not_imported'].append(subject_id)
                        else:
                            results['not_imported'] += 1
                            results['subjects_not_imported'].append(subject_id)
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not check {subject_id}: {e}[/yellow]")
                        results['not_imported'] += 1
                        results['subjects_not_imported'].append(subject_id)
                else:
                    # Cannot check database, mark as not imported
                    results['not_imported'] += 1
                    results['subjects_not_imported'].append(subject_id)
            else:
                results['without_extracted'] += 1
                results['subjects_not_extracted'].append(subject_id)
            
            progress.update(task, advance=1)
    
    if db_connected:
        db_manager.disconnect()
    
    return results


def display_extraction_statistics(results: Dict):
    """Display extraction and import statistics in a formatted table."""
    
    # Overview panel
    overview = Table(title="📊 Database Import Status", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    overview.add_column("Category", style="cyan", width=30)
    overview.add_column("Count", justify="right", style="bold yellow", width=10)
    overview.add_column("Percentage", justify="right", style="green", width=12)
    
    total = results['total_subjects']
    
    rows = [
        ("Total Subjects", total, "100.0%"),
        ("", "", ""),
        ("With Extracted JSON", results['with_extracted'], 
         f"{results['with_extracted']/total*100:.1f}%" if total > 0 else "0.0%"),
        ("Without Extracted JSON", results['without_extracted'],
         f"{results['without_extracted']/total*100:.1f}%" if total > 0 else "0.0%"),
        ("", "", ""),
    ]
    
    # Only show import stats if we have extracted files
    if results['with_extracted'] > 0:
        with_ext = results['with_extracted']
        rows.extend([
            ("Imported to Database", results['imported'],
             f"{results['imported']/with_ext*100:.1f}%" if with_ext > 0 else "0.0%"),
            ("Not Yet Imported", results['not_imported'],
             f"{results['not_imported']/with_ext*100:.1f}%" if with_ext > 0 else "0.0%"),
        ])
    
    for metric, count, pct in rows:
        overview.add_row(metric, str(count), pct)
    
    console.print(overview)
    
    # Show lists if requested and reasonable size
    if results['subjects_not_imported'] and len(results['subjects_not_imported']) <= 30:
        if Confirm.ask("\n[yellow]Show subjects not yet imported?[/yellow]", default=False):
            subjects_table = Table(title="Subjects Not Yet Imported", box=box.SIMPLE)
            subjects_table.add_column("Subject ID", style="cyan", width=12)
            subjects_table.add_column("Status", style="yellow")
            
            for subject in results['subjects_not_imported'][:30]:
                subjects_table.add_row(subject, "Ready to import")
            
            console.print(subjects_table)
    elif results['subjects_not_imported']:
        console.print(f"\n[yellow]ℹ {len(results['subjects_not_imported'])} subjects ready to import[/yellow]")
    
    if results['subjects_not_extracted'] and len(results['subjects_not_extracted']) <= 20:
        if Confirm.ask("\n[yellow]Show subjects without extraction?[/yellow]", default=False):
            missing_table = Table(title="Subjects Without Extraction", box=box.SIMPLE)
            missing_table.add_column("Subject ID", style="red", width=12)
            missing_table.add_column("Status", style="yellow")
            
            for subject in results['subjects_not_extracted'][:20]:
                missing_table.add_row(subject, "Needs extraction")
            
            console.print(missing_table)
    elif results['subjects_not_extracted']:
        console.print(f"\n[red]⚠ {len(results['subjects_not_extracted'])} subjects need extraction[/red]")


def import_single_subject(subject_id: str, base_output_dir: str = "./pdf/output") -> bool:
    """
    Import a single subject's extracted JSON to database.
    
    Args:
        subject_id: Subject ID (e.g., "2401")
        base_output_dir: Base output directory
        
    Returns:
        bool: True if successful
    """
    json_file = Path(base_output_dir) / subject_id / f"{subject_id}_extracted.json"
    
    if not json_file.exists():
        console.print(f"[red]✗ Extracted JSON not found: {json_file}[/red]")
        return False
    
    # Connect to database
    db_manager = MongoDBManager()
    if not db_manager.connect():
        return False
    
    try:
        # Create importer
        importer = MedicalRecordImporter(db_manager)
        
        # Setup collections and indexes
        importer.setup_collections_and_indexes()
        
        # Import file
        console.print(f"\n[cyan]Importing {subject_id}...[/cyan]")
        result = importer.import_json_file(str(json_file), skip_duplicates=True)
        
        if result['status'] == 'success':
            console.print(f"[green]✓ Successfully imported {subject_id}[/green]")
            return True
        elif result['status'] == 'duplicate':
            console.print(f"[yellow]⚠ {subject_id} already in database[/yellow]")
            return True
        else:
            console.print(f"[red]✗ Failed to import {subject_id}: {result.get('error', 'Unknown error')}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]✗ Error importing {subject_id}: {e}[/red]")
        return False
    finally:
        db_manager.disconnect()


def import_all_subjects(results: Dict, base_output_dir: str = "./pdf/output") -> Dict:
    """
    Import all subjects that have extraction but are not yet imported.
    
    Args:
        results: Results from analyze_extraction_status
        base_output_dir: Base output directory
        
    Returns:
        Dict with import results
    """
    to_import = results['subjects_not_imported']
    
    if not to_import:
        console.print("[green]✓ All extracted subjects are already imported![/green]")
        return {'success': 0, 'failed': 0, 'skipped': 0}
    
    console.print(f"\n[bold cyan]Preparing to import {len(to_import)} subjects...[/bold cyan]")
    
    if not Confirm.ask(f"Import {len(to_import)} subjects to database?", default=True):
        return {'success': 0, 'failed': 0, 'skipped': len(to_import)}
    
    # Connect to database once
    db_manager = MongoDBManager()
    if not db_manager.connect():
        return {'success': 0, 'failed': len(to_import), 'skipped': 0}
    
    try:
        importer = MedicalRecordImporter(db_manager)
        importer.setup_collections_and_indexes()
        
        success_count = 0
        failed_count = 0
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Importing subjects...", total=len(to_import))
            
            for subject_id in to_import:
                json_file = Path(base_output_dir) / subject_id / f"{subject_id}_extracted.json"
                
                try:
                    result = importer.import_json_file(str(json_file), skip_duplicates=True)
                    
                    if result['status'] in ['success', 'duplicate']:
                        success_count += 1
                    else:
                        failed_count += 1
                        console.print(f"[red]Failed: {subject_id}[/red]")
                        
                except Exception as e:
                    failed_count += 1
                    console.print(f"[red]Error {subject_id}: {e}[/red]")
                
                progress.update(task, advance=1)
        
        return {'success': success_count, 'failed': failed_count, 'skipped': 0}
        
    finally:
        db_manager.disconnect()


async def menu_database(base_output_dir: str = "./pdf/output"):
    """Database operations menu."""
    
    while True:
        console.clear()
        
        # Banner
        console.print(Panel.fit(
            "[bold cyan]🗄️  Database Management[/bold cyan]\n"
            "[dim]MongoDB - UQ Database[/dim]",
            border_style="cyan"
        ))
        
        # Analyze extraction status
        console.print("\n[bold yellow]Analyzing extraction and import status...[/bold yellow]")
        results = analyze_extraction_status(base_output_dir)
        
        # Display statistics
        console.print()
        display_extraction_statistics(results)
        
        # Menu options
        console.print()
        menu_table = Table(show_header=False, box=box.SIMPLE_HEAVY, padding=(0, 1))
        menu_table.add_column("Opt", style="bold cyan", width=4, justify="right")
        menu_table.add_column("Action", style="white")
        
        menu_table.add_row("1", "Import all not-yet-imported subjects")
        menu_table.add_row("2", "Import single subject by ID")
        menu_table.add_row("3", "View database statistics")
        menu_table.add_row("4", "Query database")
        menu_table.add_row("5", "Refresh status")
        menu_table.add_row("0", "Return to main menu")
        
        console.print(menu_table)
        
        choice = Prompt.ask(
            "\n[bold cyan]Select an option[/bold cyan]",
            choices=["0", "1", "2", "3", "4", "5"],
            default="0"
        )
        
        if choice == "0":
            console.print("[green]Returning to main menu...[/green]")
            break
            
        elif choice == "1":
            # Import all not-yet-imported
            import_results = import_all_subjects(results, base_output_dir)
            console.print(f"\n[bold green]Import Summary:[/bold green]")
            console.print(f"  ✓ Success: {import_results['success']}")
            console.print(f"  ✗ Failed: {import_results['failed']}")
            console.print(f"  ⏭ Skipped: {import_results['skipped']}")
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            
        elif choice == "2":
            # Import single subject
            subject_id = Prompt.ask("\n[cyan]Enter subject ID (e.g., 2401)[/cyan]")
            if subject_id.isdigit() and len(subject_id) == 4:
                import_single_subject(subject_id, base_output_dir)
            else:
                console.print("[red]Invalid subject ID format. Must be 4 digits.[/red]")
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            
        elif choice == "3":
            # View database statistics
            db_manager = MongoDBManager()
            if db_manager.connect():
                db_manager.list_database_info()
                db_manager.disconnect()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            
        elif choice == "4":
            # Query database - launch query examples
            console.print("\n[cyan]Launching query examples...[/cyan]")
            import subprocess
            subprocess.run(["uv", "run", "python", "database/query_examples.py"])
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            
        elif choice == "5":
            # Refresh - just loop back
            continue


if __name__ == "__main__":
    import asyncio
    asyncio.run(menu_database())
