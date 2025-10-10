"""
Test script for MongoDB Database Manager
Creates test collections and inserts sample data to demonstrate functionality
"""

from db_manager import MongoDBManager
from rich.console import Console

console = Console()

def test_database_manager():
    """Test the database manager with sample data"""
    
    # Create and connect
    db_manager = MongoDBManager()
    
    if not db_manager.connect():
        console.print("[bold red]Failed to connect![/bold red]")
        return
    
    # Create some test collections
    console.print("\n[bold cyan]Creating test collections...[/bold cyan]")
    db_manager.create_collection("patients")
    db_manager.create_collection("burns")
    db_manager.create_collection("procedures")
    
    # Insert test data
    console.print("\n[bold cyan]Inserting test data...[/bold cyan]")
    
    # Insert a test patient
    patients = db_manager.db["patients"]
    test_patient = {
        "nome": "Test Patient",
        "numero_processo": 9999,
        "data_nascimento": "1970-01-01",
        "sexo": "M"
    }
    patients.insert_one(test_patient)
    console.print("[green]✓ Inserted test patient[/green]")
    
    # Insert test burns
    burns = db_manager.db["burns"]
    test_burns = [
        {"location": "FACE", "degree": "SEGUNDO", "percentage": 5.0},
        {"location": "UPPER_LIMB", "degree": "TERCEIRO", "percentage": 10.0}
    ]
    burns.insert_many(test_burns)
    console.print(f"[green]✓ Inserted {len(test_burns)} test burns[/green]")
    
    # List database info
    db_manager.list_database_info()
    
    # Clean up test data
    console.print("\n[bold yellow]Cleaning up test data...[/bold yellow]")
    patients.delete_many({})
    burns.delete_many({})
    console.print("[green]✓ Test data cleaned up[/green]")
    
    # Show final state
    db_manager.list_database_info()
    
    # Disconnect
    db_manager.disconnect()

if __name__ == "__main__":
    console.print("\n" + "="*80)
    console.print("[bold cyan]Testing MongoDB Database Manager[/bold cyan]")
    console.print("="*80 + "\n")
    
    test_database_manager()
    
    console.print("\n[bold green]✓ Test completed![/bold green]\n")
