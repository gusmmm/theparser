"""
Interactive Data Updater - Select which discrepancies to update

Interactive interface to review and selectively update database records
with CSV data. Allows choosing which fields to update for each record.

Author: Agent
Date: 2025-10-10
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

from db_manager import MongoDBManager
from data_validator import validate_all_internamentos, normalize_date

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


def display_discrepancies_interactive(results: List[Dict]) -> List[Dict]:
    """
    Display discrepancies interactively and let user select which to update.
    
    Args:
        results: List of comparison results
        
    Returns:
        List of selected updates
    """
    discrepancies = [r for r in results if r.get('has_discrepancies', False)]
    
    if not discrepancies:
        console.print("\n[green]✓ All records match perfectly! No updates needed.[/green]")
        return []
    
    console.print(f"\n[bold cyan]Found {len(discrepancies)} record(s) with discrepancies[/bold cyan]\n")
    
    selected_updates = []
    
    for idx, result in enumerate(discrepancies, start=1):
        numero = result['numero_internamento']
        csv_row = result.get('csv_row', {})
        
        # Display record header
        console.print(Panel.fit(
            f"[bold white]Record {idx} of {len(discrepancies)}[/bold white]\n"
            f"Internamento: [cyan]{numero}[/cyan]",
            border_style="cyan"
        ))
        
        # Create comparison table with row numbers
        table = Table(
            title=f"Field Discrepancies",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold yellow"
        )
        table.add_column("No", style="bold cyan", width=4, justify="right")
        table.add_column("Field", style="white", width=20)
        table.add_column("Database Value", style="red", width=30)
        table.add_column("CSV Value", style="green", width=30)
        
        # Build field list with only mismatches
        mismatched_fields = []
        field_row_number = 1
        
        for field, comp in result['comparisons'].items():
            if not comp['matches']:
                mismatched_fields.append({
                    'row_number': field_row_number,
                    'field': field,
                    'db_value': comp['db_value'],
                    'csv_value': comp['csv_value'],
                    'mongo_path': get_mongo_path(field),
                    'csv_field': comp['csv_field'],
                    'csv_raw': comp['csv_raw']
                })
                
                table.add_row(
                    str(field_row_number),
                    field,
                    comp['db_value'][:30] if comp['db_value'] else "[dim]empty[/dim]",
                    comp['csv_value'][:30] if comp['csv_value'] else "[dim]empty[/dim]"
                )
                
                field_row_number += 1
        
        console.print(table)
        
        # Ask user what to do
        console.print("\n[bold yellow]Options:[/bold yellow]")
        console.print("  [cyan]a[/cyan] - Update all fields for this record")
        console.print("  [cyan]s[/cyan] - Select specific fields to update")
        console.print("  [cyan]n[/cyan] - Skip this record")
        console.print("  [cyan]q[/cyan] - Quit (save selections so far)")
        
        choice = Prompt.ask(
            "\nWhat would you like to do?",
            choices=["a", "s", "n", "q"],
            default="n"
        )
        
        if choice == "q":
            console.print("[yellow]Stopping selection process...[/yellow]")
            break
        
        elif choice == "n":
            console.print("[dim]Skipping this record[/dim]")
            continue
        
        elif choice == "a":
            # Update all fields
            update_data = {}
            for field_info in mismatched_fields:
                mongo_path = field_info['mongo_path']
                csv_value = field_info['csv_raw']
                
                # Handle date normalization and conversion to datetime
                if field_info['field'] in ['data_entrada', 'data_alta', 'data_nascimento', 'data_queimadura']:
                    csv_value = convert_to_date(normalize_date(csv_value))
                # Handle year conversion to int
                elif field_info['field'] == 'ano_internamento':
                    csv_value = convert_to_int(csv_value)
                
                if csv_value is not None:
                    update_data[mongo_path] = csv_value
            
            if update_data:
                selected_updates.append({
                    'numero_internamento': numero,
                    'update_data': update_data,
                    'fields_updated': [f['field'] for f in mismatched_fields]
                })
                console.print(f"[green]✓ Queued all {len(mismatched_fields)} fields for update[/green]")
        
        elif choice == "s":
            # Select specific fields
            console.print("\n[cyan]Enter field numbers to update (comma-separated, e.g., 1,3,4) or 'all':[/cyan]")
            selection = Prompt.ask("Fields to update", default="")
            
            if selection.lower() == 'all':
                selected_numbers = [f['row_number'] for f in mismatched_fields]
            else:
                try:
                    selected_numbers = [int(x.strip()) for x in selection.split(',') if x.strip()]
                except ValueError:
                    console.print("[red]Invalid input. Skipping this record.[/red]")
                    continue
            
            # Build update data for selected fields
            update_data = {}
            fields_updated = []
            
            for field_info in mismatched_fields:
                if field_info['row_number'] in selected_numbers:
                    mongo_path = field_info['mongo_path']
                    csv_value = field_info['csv_raw']
                    
                    # Handle date normalization and conversion to datetime
                    if field_info['field'] in ['data_entrada', 'data_alta', 'data_nascimento', 'data_queimadura']:
                        csv_value = convert_to_date(normalize_date(csv_value))
                    # Handle year conversion to int
                    elif field_info['field'] == 'ano_internamento':
                        csv_value = convert_to_int(csv_value)
                    
                    if csv_value is not None:
                        update_data[mongo_path] = csv_value
                        fields_updated.append(field_info['field'])
            
            if update_data:
                selected_updates.append({
                    'numero_internamento': numero,
                    'update_data': update_data,
                    'fields_updated': fields_updated
                })
                console.print(f"[green]✓ Queued {len(fields_updated)} field(s) for update[/green]")
            else:
                console.print("[yellow]No valid fields selected[/yellow]")
        
        console.print()  # Spacing
    
    return selected_updates


def get_mongo_path(field: str) -> str:
    """
    Get MongoDB document path for a field.
    
    Args:
        field: Field name from comparison
        
    Returns:
        MongoDB path string
    """
    field_mappings = {
        'ano_internamento': 'ano_internamento',  # Top level, not nested
        'numero_processo': 'doente.numero_processo',
        'nome': 'doente.nome',
        'data_entrada': 'internamento.data_entrada',
        'data_alta': 'internamento.data_alta',
        'destino_alta': 'internamento.destino_alta',
        'data_nascimento': 'doente.data_nascimento',
        'data_queimadura': 'queimaduras.0.data',  # First queimadura
    }
    
    return field_mappings.get(field, field)


def display_update_summary(selected_updates: List[Dict]):
    """Display summary of selected updates."""
    
    if not selected_updates:
        console.print("\n[yellow]No updates selected.[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Update Summary[/bold cyan]")
    console.print(f"Total records to update: [yellow]{len(selected_updates)}[/yellow]\n")
    
    summary_table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    summary_table.add_column("Internamento", style="cyan", width=12)
    summary_table.add_column("Fields to Update", style="yellow")
    summary_table.add_column("Count", style="green", justify="right", width=8)
    
    for update in selected_updates:
        numero = update['numero_internamento']
        fields = update['fields_updated']
        count = len(fields)
        
        # Show first 3 fields, then "..." if more
        fields_str = ", ".join(fields[:3])
        if len(fields) > 3:
            fields_str += f", ... (+{len(fields)-3} more)"
        
        summary_table.add_row(str(numero), fields_str, str(count))
    
    console.print(summary_table)
    
    total_fields = sum(len(u['fields_updated']) for u in selected_updates)
    console.print(f"\nTotal fields to update: [bold yellow]{total_fields}[/bold yellow]")


def execute_selected_updates(
    db_manager: MongoDBManager,
    selected_updates: List[Dict]
) -> Dict:
    """
    Execute the selected updates.
    
    Args:
        db_manager: MongoDB manager instance
        selected_updates: List of selected update operations
        
    Returns:
        Dict with execution statistics
    """
    if not selected_updates:
        return {'total': 0, 'updated': 0, 'failed': 0}
    
    collection = db_manager.db['internamentos']
    stats = {'total': len(selected_updates), 'updated': 0, 'failed': 0}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Updating records...", total=len(selected_updates))
        
        for update in selected_updates:
            numero = update['numero_internamento']
            update_data = update['update_data'].copy()
            
            # Add metadata
            update_data['updated_at'] = datetime.now().isoformat()
            update_data['updated_from_csv'] = True
            
            try:
                result = collection.update_one(
                    {'internamento.numero_internamento': numero},
                    {'$set': update_data}
                )
                
                if result.modified_count > 0:
                    stats['updated'] += 1
                else:
                    stats['failed'] += 1
                    console.print(f"[yellow]Warning: Record {numero} not modified[/yellow]")
                    
            except Exception as e:
                stats['failed'] += 1
                console.print(f"[red]Error updating {numero}: {e}[/red]")
            
            progress.update(task, advance=1)
    
    return stats


def interactive_update_main():
    """Main interactive update function."""
    
    console.print(Panel.fit(
        "[bold cyan]🔄 Interactive Database Updater[/bold cyan]\n"
        "[dim]Review and select which discrepancies to update[/dim]",
        border_style="cyan"
    ))
    
    # Connect to database
    db_manager = MongoDBManager()
    if not db_manager.connect():
        console.print("[red]Failed to connect to database. Exiting.[/red]")
        return
    
    try:
        # Step 1: Validate data
        console.print("\n[bold yellow]Step 1: Validating data...[/bold yellow]")
        results = validate_all_internamentos(db_manager)
        
        if not results:
            console.print("[yellow]No results to process.[/yellow]")
            return
        
        # Step 2: Interactive selection
        console.print("\n[bold yellow]Step 2: Review discrepancies and select updates...[/bold yellow]")
        selected_updates = display_discrepancies_interactive(results)
        
        if not selected_updates:
            console.print("\n[yellow]No updates selected. Exiting.[/yellow]")
            return
        
        # Step 3: Show summary
        display_update_summary(selected_updates)
        
        # Step 4: Confirm and execute
        console.print("\n[bold yellow]Step 3: Execute updates...[/bold yellow]")
        
        if not Confirm.ask(
            "\n[bold red]⚠ This will modify the database. Continue?[/bold red]",
            default=False
        ):
            console.print("[yellow]Update cancelled.[/yellow]")
            return
        
        stats = execute_selected_updates(db_manager, selected_updates)
        
        # Step 5: Show results
        console.print("\n[bold green]✓ Update Complete![/bold green]")
        
        results_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        results_table.add_column("Category", style="cyan")
        results_table.add_column("Count", style="yellow", justify="right")
        
        results_table.add_row("Total Records", str(stats['total']))
        results_table.add_row("Successfully Updated", str(stats['updated']))
        results_table.add_row("Failed", str(stats['failed']))
        
        console.print(results_table)
        
        if stats['updated'] > 0:
            console.print(f"\n[green]✓ {stats['updated']} record(s) updated successfully[/green]")
            console.print("[dim]All updated records have 'updated_at' and 'updated_from_csv' fields[/dim]")
        
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    interactive_update_main()
