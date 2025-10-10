"""
Data Validator - Compare MongoDB records with CSV data

Compares internamento records in MongoDB with corresponding rows in BD_doentes_clean.csv
to identify discrepancies and prepare for updates.

Author: Agent
Date: 2025-10-10
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import csv

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from icecream import ic

from db_manager import MongoDBManager

console = Console()


def load_csv_data(csv_path: str = "./csv/BD_doentes_clean.csv") -> Dict[int, Dict]:
    """
    Load CSV data into a dictionary keyed by ID.
    
    Args:
        csv_path: Path to BD_doentes_clean.csv
        
    Returns:
        Dict mapping ID to row data
    """
    csv_data = {}
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        console.print(f"[red]CSV file not found: {csv_path}[/red]")
        return csv_data
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # ID is the primary key
                id_value = int(row['ID'])
                csv_data[id_value] = row
            except (ValueError, KeyError) as e:
                console.print(f"[yellow]Warning: Could not parse row: {e}[/yellow]")
                continue
    
    console.print(f"[green]✓ Loaded {len(csv_data)} records from CSV[/green]")
    return csv_data


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date to YYYY-MM-DD format.
    Handles both string dates and datetime objects from database.
    
    Args:
        date_str: Date string in various formats or datetime object
        
    Returns:
        Normalized date string or None
    """
    if not date_str:
        return None
    
    # Handle datetime objects from database (stored as ISODate)
    if isinstance(date_str, datetime):
        return date_str.strftime('%Y-%m-%d')
    
    # Handle string dates
    if not isinstance(date_str, str) or date_str.strip() == '':
        return None
    
    date_str = date_str.strip()
    
    # Already in YYYY-MM-DD format
    if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str
    
    # Try parsing various formats
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Could not parse
    return date_str


def normalize_string(s: Optional[str]) -> str:
    """Normalize string for comparison (lowercase, stripped)."""
    if not s:
        return ""
    return str(s).strip().lower()


def compare_values(db_value: Any, csv_value: Any, field_type: str = "string") -> Tuple[bool, str, str]:
    """
    Compare database and CSV values.
    
    Args:
        db_value: Value from database
        csv_value: Value from CSV
        field_type: Type of field (string, date, number)
        
    Returns:
        Tuple of (matches, normalized_db_value, normalized_csv_value)
    """
    if field_type == "date":
        db_norm = normalize_date(db_value)
        csv_norm = normalize_date(csv_value)
        return db_norm == csv_norm, str(db_norm or ""), str(csv_norm or "")
    
    elif field_type == "number":
        try:
            db_num = int(db_value) if db_value else None
            csv_num = int(csv_value) if csv_value else None
            return db_num == csv_num, str(db_num or ""), str(csv_num or "")
        except (ValueError, TypeError):
            return False, str(db_value or ""), str(csv_value or "")
    
    else:  # string
        db_norm = normalize_string(db_value)
        csv_norm = normalize_string(csv_value)
        return db_norm == csv_norm, db_norm, csv_norm


def compare_internamento_with_csv(
    internamento_doc: Dict,
    csv_data: Dict[int, Dict]
) -> Dict:
    """
    Compare a single internamento document with corresponding CSV row.
    
    Args:
        internamento_doc: MongoDB document
        csv_data: Dictionary of CSV data keyed by ID
        
    Returns:
        Dict with comparison results
    """
    # Extract values from MongoDB document
    numero_internamento = internamento_doc.get('internamento', {}).get('numero_internamento')
    
    # Get ano_internamento from main document (not nested in internamento)
    ano_internamento = internamento_doc.get('ano_internamento')
    
    # If not present, calculate from numero_internamento (first 2 digits represent year offset)
    if ano_internamento is None:
        try:
            ano_internamento = 2000 + int(str(numero_internamento)[:2])
        except (ValueError, TypeError):
            ano_internamento = None
    
    doente = internamento_doc.get('doente', {})
    internamento = internamento_doc.get('internamento', {})
    
    # Get first queimadura date if exists
    queimaduras = internamento_doc.get('queimaduras', [])
    data_queimadura = queimaduras[0].get('data') if queimaduras else None
    
    db_values = {
        'numero_internamento': numero_internamento,
        'ano_internamento': ano_internamento,
        'numero_processo': doente.get('numero_processo'),
        'nome': doente.get('nome'),
        'data_entrada': internamento.get('data_entrada'),
        'data_alta': internamento.get('data_alta'),
        'destino_alta': internamento.get('destino_alta'),
        'data_nascimento': doente.get('data_nascimento'),
        'data_queimadura': data_queimadura,
    }
    
    # Find corresponding CSV row
    csv_row = csv_data.get(numero_internamento)
    
    if not csv_row:
        return {
            'numero_internamento': numero_internamento,
            'csv_found': False,
            'comparisons': {},
            'has_discrepancies': False,
        }
    
    # Perform comparisons
    comparisons = {}
    has_discrepancies = False
    
    # Field mapping: (csv_field, field_type)
    field_mappings = {
        'ano_internamento': ('year', 'number'),
        'numero_processo': ('processo', 'number'),
        'nome': ('nome', 'string'),
        'data_entrada': ('data_ent', 'date'),
        'data_alta': ('data_alta', 'date'),
        'destino_alta': ('destino', 'string'),
        'data_nascimento': ('data_nasc', 'date'),
        'data_queimadura': ('data_queim', 'date'),
    }
    
    for db_field, (csv_field, field_type) in field_mappings.items():
        db_value = db_values.get(db_field)
        csv_value = csv_row.get(csv_field)
        
        matches, db_norm, csv_norm = compare_values(db_value, csv_value, field_type)
        
        comparisons[db_field] = {
            'csv_field': csv_field,
            'matches': matches,
            'db_value': db_norm,
            'csv_value': csv_norm,
            'db_raw': db_value,
            'csv_raw': csv_value,
        }
        
        if not matches:
            has_discrepancies = True
    
    return {
        'numero_internamento': numero_internamento,
        'csv_found': True,
        'comparisons': comparisons,
        'has_discrepancies': has_discrepancies,
        'csv_row': csv_row,
    }


def validate_all_internamentos(
    db_manager: MongoDBManager,
    csv_path: str = "./csv/BD_doentes_clean.csv"
) -> List[Dict]:
    """
    Validate all internamentos against CSV data.
    
    Args:
        db_manager: MongoDB manager instance
        csv_path: Path to CSV file
        
    Returns:
        List of comparison results
    """
    # Connect to database
    if not db_manager.connect():
        console.print("[red]Failed to connect to database. Exiting.[/red]")
        return []
    
    # Load CSV data
    console.print("\n[bold cyan]Loading CSV data...[/bold cyan]")
    csv_data = load_csv_data(csv_path)
    
    if not csv_data:
        console.print("[red]No CSV data loaded. Exiting.[/red]")
        return []
    
    # Get all internamentos from database
    collection = db_manager.db['internamentos']
    total_docs = collection.count_documents({})
    
    console.print(f"\n[bold cyan]Comparing {total_docs} internamentos with CSV...[/bold cyan]")
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Validating...", total=total_docs)
        
        for doc in collection.find({}):
            result = compare_internamento_with_csv(doc, csv_data)
            results.append(result)
            progress.update(task, advance=1)
    
    return results


def display_comparison_summary(results: List[Dict]):
    """Display summary of comparison results."""
    
    total = len(results)
    csv_not_found = sum(1 for r in results if not r['csv_found'])
    with_discrepancies = sum(1 for r in results if r.get('has_discrepancies', False))
    perfect_matches = total - csv_not_found - with_discrepancies
    
    # Summary table
    summary = Table(title="📊 Validation Summary", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    summary.add_column("Category", style="cyan", width=30)
    summary.add_column("Count", justify="right", style="bold yellow", width=10)
    summary.add_column("Percentage", justify="right", style="green", width=12)
    
    summary.add_row("Total Internamentos", str(total), "100.0%")
    summary.add_row("", "", "")
    summary.add_row(
        "Perfect Matches",
        str(perfect_matches),
        f"{perfect_matches/total*100:.1f}%" if total > 0 else "0.0%"
    )
    summary.add_row(
        "With Discrepancies",
        str(with_discrepancies),
        f"{with_discrepancies/total*100:.1f}%" if total > 0 else "0.0%"
    )
    summary.add_row(
        "Not in CSV",
        str(csv_not_found),
        f"{csv_not_found/total*100:.1f}%" if total > 0 else "0.0%"
    )
    
    console.print(summary)
    
    # Field-level discrepancy breakdown
    if with_discrepancies > 0:
        field_discrepancies = {}
        
        for result in results:
            if result.get('has_discrepancies', False):
                for field, comp in result['comparisons'].items():
                    if not comp['matches']:
                        field_discrepancies[field] = field_discrepancies.get(field, 0) + 1
        
        if field_discrepancies:
            field_table = Table(
                title="Field-Level Discrepancies",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold yellow"
            )
            field_table.add_column("Field", style="cyan")
            field_table.add_column("Discrepancies", justify="right", style="red")
            field_table.add_column("Percentage", justify="right", style="yellow")
            
            for field, count in sorted(field_discrepancies.items(), key=lambda x: x[1], reverse=True):
                pct = count / with_discrepancies * 100
                field_table.add_row(field, str(count), f"{pct:.1f}%")
            
            console.print(field_table)


def display_detailed_comparisons(results: List[Dict], limit: int = 10):
    """
    Display detailed comparison results for records with discrepancies.
    
    Args:
        results: List of comparison results
        limit: Maximum number of records to display in detail
    """
    discrepancies = [r for r in results if r.get('has_discrepancies', False)]
    
    if not discrepancies:
        console.print("\n[green]✓ All records match perfectly![/green]")
        return
    
    console.print(f"\n[bold yellow]Showing first {min(limit, len(discrepancies))} records with discrepancies:[/bold yellow]\n")
    
    for i, result in enumerate(discrepancies[:limit]):
        numero = result['numero_internamento']
        
        # Create table for this internamento
        table = Table(
            title=f"Internamento {numero}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Field", style="white", width=20)
        table.add_column("Database", style="yellow", width=25)
        table.add_column("CSV", style="green", width=25)
        table.add_column("Match", style="white", width=8, justify="center")
        
        for field, comp in result['comparisons'].items():
            match_symbol = "✓" if comp['matches'] else "✗"
            match_style = "green" if comp['matches'] else "red"
            
            table.add_row(
                field,
                comp['db_value'][:25] if comp['db_value'] else "",
                comp['csv_value'][:25] if comp['csv_value'] else "",
                f"[{match_style}]{match_symbol}[/{match_style}]"
            )
        
        console.print(table)
        
        if i < len(discrepancies) - 1:
            console.print()  # Spacing between tables
    
    if len(discrepancies) > limit:
        console.print(f"\n[dim]... and {len(discrepancies) - limit} more records with discrepancies[/dim]")


def export_discrepancies_report(results: List[Dict], output_path: str = "./reports/data_validation_report.csv"):
    """
    Export detailed discrepancies report to CSV.
    
    Args:
        results: List of comparison results
        output_path: Path to output CSV file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    discrepancies = [r for r in results if r.get('has_discrepancies', False)]
    
    if not discrepancies:
        console.print("\n[green]No discrepancies to export.[/green]")
        return
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'numero_internamento',
            'field',
            'csv_field',
            'matches',
            'db_value',
            'csv_value',
        ])
        
        # Data
        for result in discrepancies:
            numero = result['numero_internamento']
            for field, comp in result['comparisons'].items():
                if not comp['matches']:  # Only export mismatches
                    writer.writerow([
                        numero,
                        field,
                        comp['csv_field'],
                        comp['matches'],
                        comp['db_value'],
                        comp['csv_value'],
                    ])
    
    console.print(f"\n[green]✓ Discrepancies report exported to: {output_file}[/green]")


def main():
    """Main validation function."""
    console.print(Panel.fit(
        "[bold cyan]🔍 Data Validator[/bold cyan]\n"
        "[dim]Compare MongoDB with CSV data[/dim]",
        border_style="cyan"
    ))
    
    # Connect to database
    db_manager = MongoDBManager()
    if not db_manager.connect():
        console.print("[red]Failed to connect to database. Exiting.[/red]")
        return
    
    try:
        # Validate all internamentos
        results = validate_all_internamentos(db_manager)
        
        if not results:
            console.print("[yellow]No results to display.[/yellow]")
            return
        
        # Display summary
        console.print()
        display_comparison_summary(results)
        
        # Display detailed comparisons
        console.print()
        display_detailed_comparisons(results, limit=10)
        
        # Export report
        export_discrepancies_report(results)
        
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    main()
