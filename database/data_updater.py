"""
Data Updater - Update MongoDB records with CSV data

Updates internamento records in MongoDB with validated data from BD_doentes_clean.csv.
Adds updated_at timestamp to track changes.

Author: Agent
Date: 2025-10-10
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
from rich import box
from icecream import ic

from db_manager import MongoDBManager
from data_validator import (
    load_csv_data,
    validate_all_internamentos,
    normalize_date,
    display_comparison_summary,
)

console = Console()


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


def prepare_update_data(comparison_result: Dict) -> Optional[Dict]:
    """
    Prepare update data for a single internamento based on comparison results.
    
    Args:
        comparison_result: Result from compare_internamento_with_csv
        
    Returns:
        Dict with update operations or None if no updates needed
    """
    if not comparison_result.get('has_discrepancies', False):
        return None
    
    if not comparison_result.get('csv_found', False):
        return None
    
    update_ops = {}
    csv_row = comparison_result.get('csv_row', {})
    
    # Map fields to MongoDB paths and their CSV sources
    # Convert types: dates to datetime, year to int
    field_mappings = {
        'ano_internamento': ('ano_internamento', convert_to_int(csv_row.get('year'))),  # Root level, not nested
        'numero_processo': ('doente.numero_processo', csv_row.get('processo')),
        'nome': ('doente.nome', csv_row.get('nome')),
        'data_entrada': ('internamento.data_entrada', convert_to_date(normalize_date(csv_row.get('data_ent')))),
        'data_alta': ('internamento.data_alta', convert_to_date(normalize_date(csv_row.get('data_alta')))),
        'destino_alta': ('internamento.destino_alta', csv_row.get('destino')),
        'data_nascimento': ('doente.data_nascimento', convert_to_date(normalize_date(csv_row.get('data_nasc')))),
    }
    
    # Check which fields have discrepancies and need updates
    for field, comp in comparison_result['comparisons'].items():
        if not comp['matches'] and field in field_mappings:
            mongo_path, csv_value = field_mappings[field]
            
            # Only update if CSV has a value
            if csv_value:
                update_ops[mongo_path] = csv_value
    
    # Handle data_queimadura specially (update first queimadura in array if exists)
    if 'data_queimadura' in comparison_result['comparisons']:
        comp = comparison_result['comparisons']['data_queimadura']
        if not comp['matches'] and csv_row.get('data_queim'):
            # We'll handle this separately as it requires array update
            pass
    
    if not update_ops:
        return None
    
    return update_ops


def update_internamento(
    db_manager: MongoDBManager,
    numero_internamento: int,
    update_data: Dict,
    dry_run: bool = False
) -> bool:
    """
    Update a single internamento record.
    
    Args:
        db_manager: MongoDB manager instance
        numero_internamento: Internamento number to update
        update_data: Dictionary of fields to update
        dry_run: If True, don't actually update
        
    Returns:
        bool: True if successful
    """
    collection = db_manager.db['internamentos']
    
    # Add updated_at timestamp
    update_data['updated_at'] = datetime.now().isoformat()
    update_data['updated_from_csv'] = True
    
    if dry_run:
        console.print(f"[dim]DRY RUN: Would update {numero_internamento}[/dim]")
        return True
    
    try:
        result = collection.update_one(
            {'internamento.numero_internamento': numero_internamento},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        console.print(f"[red]Error updating {numero_internamento}: {e}[/red]")
        return False


def update_all_internamentos(
    db_manager: MongoDBManager,
    comparison_results: List[Dict],
    dry_run: bool = False
) -> Dict:
    """
    Update all internamentos with discrepancies.
    
    Args:
        db_manager: MongoDB manager instance
        comparison_results: List of comparison results
        dry_run: If True, simulate updates without writing
        
    Returns:
        Dict with update statistics
    """
    records_to_update = [r for r in comparison_results if r.get('has_discrepancies', False)]
    
    if not records_to_update:
        console.print("[green]✓ No updates needed - all records match![/green]")
        return {'total': 0, 'updated': 0, 'failed': 0, 'skipped': 0}
    
    console.print(f"\n[bold cyan]Preparing to update {len(records_to_update)} records...[/bold cyan]")
    
    # Show what will be updated
    preview_table = Table(title="Records to Update", box=box.SIMPLE)
    preview_table.add_column("Internamento", style="cyan", width=12)
    preview_table.add_column("Fields to Update", style="yellow")
    
    updates_prepared = {}
    
    for result in records_to_update[:10]:  # Show first 10
        numero = result['numero_internamento']
        update_data = prepare_update_data(result)
        
        if update_data:
            updates_prepared[numero] = update_data
            fields = ", ".join([k.split('.')[-1] for k in update_data.keys() if k != 'updated_at' and k != 'updated_from_csv'])
            preview_table.add_row(str(numero), fields)
    
    console.print(preview_table)
    
    if len(records_to_update) > 10:
        console.print(f"[dim]... and {len(records_to_update) - 10} more records[/dim]")
    
    # Confirm update
    if not dry_run:
        mode_str = "UPDATE" if not dry_run else "DRY RUN"
        if not Confirm.ask(f"\n[yellow]{mode_str}: Update {len(updates_prepared)} records in database?[/yellow]", default=False):
            return {'total': len(updates_prepared), 'updated': 0, 'failed': 0, 'skipped': len(updates_prepared)}
    
    # Perform updates
    stats = {'total': len(updates_prepared), 'updated': 0, 'failed': 0, 'skipped': 0}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]{'Simulating' if dry_run else 'Updating'} records...",
            total=len(updates_prepared)
        )
        
        for numero, update_data in updates_prepared.items():
            success = update_internamento(db_manager, numero, update_data, dry_run)
            
            if success:
                stats['updated'] += 1
            else:
                stats['failed'] += 1
            
            progress.update(task, advance=1)
    
    return stats


def display_update_summary(stats: Dict):
    """Display summary of update operation."""
    
    summary = Table(title="📝 Update Summary", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    summary.add_column("Category", style="cyan", width=20)
    summary.add_column("Count", justify="right", style="bold yellow", width=10)
    
    summary.add_row("Total Records", str(stats['total']))
    summary.add_row("", "")
    summary.add_row("Successfully Updated", str(stats['updated']))
    summary.add_row("Failed", str(stats['failed']))
    summary.add_row("Skipped", str(stats['skipped']))
    
    console.print(summary)
    
    if stats['updated'] > 0:
        console.print(f"\n[green]✓ Successfully updated {stats['updated']} records[/green]")
        console.print("[dim]All updated records now have 'updated_at' and 'updated_from_csv' fields[/dim]")
    
    if stats['failed'] > 0:
        console.print(f"\n[red]✗ {stats['failed']} records failed to update[/red]")


def verify_updates(db_manager: MongoDBManager) -> Dict:
    """
    Verify that updates were applied correctly.
    
    Args:
        db_manager: MongoDB manager instance
        
    Returns:
        Dict with verification statistics
    """
    collection = db_manager.db['internamentos']
    
    total_updated = collection.count_documents({'updated_from_csv': True})
    recent_updates = collection.count_documents({
        'updated_at': {'$exists': True},
        'updated_from_csv': True
    })
    
    # Check a sample
    sample = list(collection.find({'updated_from_csv': True}).limit(5))
    
    stats = {
        'total_with_flag': total_updated,
        'total_with_timestamp': recent_updates,
        'sample_records': sample
    }
    
    return stats


def display_verification_results(stats: Dict):
    """Display verification results."""
    
    console.print("\n[bold cyan]Verification Results:[/bold cyan]")
    
    verify_table = Table(box=box.SIMPLE)
    verify_table.add_column("Metric", style="yellow")
    verify_table.add_column("Count", style="green", justify="right")
    
    verify_table.add_row("Records with 'updated_from_csv' flag", str(stats['total_with_flag']))
    verify_table.add_row("Records with 'updated_at' timestamp", str(stats['total_with_timestamp']))
    
    console.print(verify_table)
    
    if stats['sample_records']:
        console.print("\n[dim]Sample of updated records:[/dim]")
        sample_table = Table(box=box.SIMPLE)
        sample_table.add_column("Internamento", style="cyan")
        sample_table.add_column("Updated At", style="yellow")
        
        for record in stats['sample_records'][:5]:
            numero = record.get('internamento', {}).get('numero_internamento', 'N/A')
            updated_at = record.get('updated_at', 'N/A')
            sample_table.add_row(str(numero), updated_at[:19] if updated_at != 'N/A' else 'N/A')
        
        console.print(sample_table)


def main(dry_run: bool = True):
    """
    Main update function.
    
    Args:
        dry_run: If True, simulate updates without writing
    """
    mode = "DRY RUN" if dry_run else "LIVE UPDATE"
    
    console.print(Panel.fit(
        f"[bold cyan]📝 Data Updater - {mode}[/bold cyan]\n"
        "[dim]Update MongoDB with CSV data[/dim]",
        border_style="cyan" if dry_run else "red"
    ))
    
    # Connect to database
    db_manager = MongoDBManager()
    if not db_manager.connect():
        console.print("[red]Failed to connect to database. Exiting.[/red]")
        return
    
    try:
        # Validate data first
        console.print("\n[bold yellow]Step 1: Validating data...[/bold yellow]")
        results = validate_all_internamentos(db_manager)
        
        if not results:
            console.print("[yellow]No results to process.[/yellow]")
            return
        
        # Display validation summary
        display_comparison_summary(results)
        
        # Perform updates
        console.print("\n[bold yellow]Step 2: Updating records...[/bold yellow]")
        stats = update_all_internamentos(db_manager, results, dry_run)
        
        # Display update summary
        console.print()
        display_update_summary(stats)
        
        # Verify updates if not dry run
        if not dry_run and stats['updated'] > 0:
            console.print("\n[bold yellow]Step 3: Verifying updates...[/bold yellow]")
            verify_stats = verify_updates(db_manager)
            display_verification_results(verify_stats)
        
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    import sys
    
    # Check for --live flag
    live_mode = '--live' in sys.argv or '--no-dry-run' in sys.argv
    
    if live_mode:
        console.print("[bold red]⚠ LIVE MODE - Database will be modified![/bold red]")
        if Confirm.ask("Are you sure you want to proceed with live updates?", default=False):
            main(dry_run=False)
        else:
            console.print("[yellow]Update cancelled.[/yellow]")
    else:
        console.print("[bold green]Running in DRY RUN mode (no changes will be made)[/bold green]")
        console.print("[dim]Use --live flag to perform actual updates[/dim]\n")
        main(dry_run=True)
