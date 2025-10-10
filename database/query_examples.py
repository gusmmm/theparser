"""
Query examples for the UQ MongoDB database.

Demonstrates various queries for the embedded document structure.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
import json

from db_manager import MongoDBManager
from data_importer import MedicalRecordImporter

console = Console()


def query_examples():
    """Demonstrate various query patterns."""
    
    # Connect
    db_manager = MongoDBManager()
    if not db_manager.connect():
        return
    
    importer = MedicalRecordImporter(db_manager)
    collection = db_manager.db["internamentos"]
    
    console.print("\n" + "="*80)
    console.print("[bold cyan]MongoDB Query Examples[/bold cyan]")
    console.print("="*80 + "\n")
    
    # 1. Get specific admission
    console.print("[bold yellow]1. Get Admission by Number[/bold yellow]")
    admission = importer.get_admission_by_number(2401)
    if admission:
        importer.display_admission_summary(admission)
    
    # 2. Get all admissions for a patient
    console.print("\n[bold yellow]2. Get All Admissions for Patient 23056175[/bold yellow]")
    patient_admissions = importer.get_patient_admissions(23056175)
    console.print(f"[cyan]Found {len(patient_admissions)} admission(s)[/cyan]\n")
    
    # 3. Count documents
    console.print("[bold yellow]3. Database Statistics[/bold yellow]")
    total_admissions = collection.count_documents({})
    admissions_with_burns = collection.count_documents({"tem_queimaduras": True})
    admissions_with_infections = collection.count_documents({"tem_infecoes": True})
    
    stats_text = f"""[cyan]Total Admissions:[/cyan] {total_admissions}
[cyan]Admissions with Burns:[/cyan] {admissions_with_burns}
[cyan]Admissions with Infections:[/cyan] {admissions_with_infections}"""
    
    console.print(Panel(stats_text, title="📊 Statistics", border_style="cyan"))
    
    # 4. Show burn details
    console.print("\n[bold yellow]4. Burns Details for Admission 2401[/bold yellow]")
    if admission:
        burns = admission.get("queimaduras", [])
        if burns:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Location", style="cyan")
            table.add_column("Degree", style="yellow")
            table.add_column("%", justify="right", style="green")
            table.add_column("Notes", style="white")
            
            for burn in burns:
                table.add_row(
                    burn.get("local_anatomico", "N/A"),
                    burn.get("grau_maximo", "N/A"),
                    str(burn.get("percentagem", "-")),
                    burn.get("notas", "-") or "-"
                )
            
            console.print(table)
    
    # 5. Show procedures
    console.print("\n[bold yellow]5. Procedures for Admission 2401[/bold yellow]")
    if admission:
        procedures = admission.get("procedimentos", [])
        if procedures:
            for i, proc in enumerate(procedures, 1):
                console.print(f"\n[cyan]{i}. {proc.get('nome_procedimento')}[/cyan]")
                console.print(f"   Date: {proc.get('data_procedimento', 'N/A')}")
                console.print(f"   Type: {proc.get('tipo_procedimento', 'N/A')}")
    
    # 6. Show patient pathologies
    console.print("\n[bold yellow]6. Patient Pre-existing Conditions[/bold yellow]")
    if admission:
        pathologies = admission["doente"].get("patologias", [])
        if pathologies:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Pathology", style="cyan")
            table.add_column("Class", style="yellow")
            table.add_column("Notes", style="white")
            
            for path in pathologies:
                table.add_row(
                    path.get("nome_patologia", "N/A"),
                    path.get("classe_patologia", "-") or "-",
                    path.get("nota", "-") or "-"
                )
            
            console.print(table)
    
    # 7. Show medications
    console.print("\n[bold yellow]7. Patient Regular Medications[/bold yellow]")
    if admission:
        medications = admission["doente"].get("medicacoes", [])
        if medications:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Medication", style="cyan", width=30)
            table.add_column("Dosage", style="yellow")
            table.add_column("Schedule", style="green")
            
            for med in medications:
                table.add_row(
                    med.get("nome_medicacao", "N/A"),
                    med.get("dosagem", "-") or "-",
                    med.get("posologia", "-") or "-"
                )
            
            console.print(table)
    
    # 8. Example aggregation - Admissions by year
    console.print("\n[bold yellow]8. Admissions by Year[/bold yellow]")
    pipeline = [
        {"$group": {
            "_id": "$ano_internamento",
            "count": {"$sum": 1},
            "avg_ascq": {"$avg": "$internamento.ASCQ_total"}
        }},
        {"$sort": {"_id": -1}}
    ]
    
    year_stats = list(collection.aggregate(pipeline))
    if year_stats:
        for stat in year_stats:
            year = stat["_id"]
            count = stat["count"]
            avg_ascq = stat.get("avg_ascq", 0) or 0
            console.print(f"  [cyan]{year}:[/cyan] {count} admission(s), Avg ASCQ: {avg_ascq:.1f}%")
    
    # 9. Show complete document structure (sample)
    console.print("\n[bold yellow]9. Document Structure (Sample)[/bold yellow]")
    if admission:
        # Remove _id for display
        display_doc = {k: v for k, v in admission.items() if k != "_id"}
        
        # Show abbreviated version
        abbreviated = {
            "internamento": display_doc["internamento"],
            "doente": {
                "nome": display_doc["doente"]["nome"],
                "numero_processo": display_doc["doente"]["numero_processo"],
                "patologias_count": len(display_doc["doente"].get("patologias", [])),
                "medicacoes_count": len(display_doc["doente"].get("medicacoes", []))
            },
            "queimaduras_count": len(display_doc.get("queimaduras", [])),
            "procedimentos_count": len(display_doc.get("procedimentos", [])),
            "metadata": {
                "source_file": display_doc.get("source_file"),
                "extraction_date": display_doc.get("extraction_date"),
                "import_date": display_doc.get("import_date")
            }
        }
        
        json_str = json.dumps(abbreviated, indent=2, ensure_ascii=False)
        json_obj = JSON(json_str)
        console.print(Panel(json_obj, title="📄 Document Structure", border_style="green"))
    
    console.print("\n" + "="*80)
    
    # Disconnect
    db_manager.disconnect()


if __name__ == "__main__":
    query_examples()
