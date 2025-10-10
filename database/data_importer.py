"""
Data Importer for Medical Records JSON to MongoDB

Imports extracted medical record JSON files into MongoDB with an embedded document structure.
The main collection is 'internamentos' (admissions), with embedded patient info and related data.

Database Structure:
- Main unit: internamento (admission)
- Each admission has ONE patient (embedded)
- Same patient can have multiple admissions (separate documents)
- Each admission embeds: burns, procedures, antibiotics, infections, traumas
- Patient pathologies and medications are embedded in patient subdocument

Author: Agent
Date: 2025-10-10
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, BulkWriteError
from icecream import ic
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from db_manager import MongoDBManager

# Configure icecream
ic.configureOutput(prefix='[IMPORT DEBUG] ')

# Rich console
console = Console()


class MedicalRecordImporter:
    """
    Imports medical record JSON files into MongoDB.
    
    Uses embedded document structure for optimal performance with low read/write operations.
    """
    
    def __init__(self, db_manager: MongoDBManager):
        """
        Initialize importer with database manager.
        
        Args:
            db_manager: Connected MongoDBManager instance
        """
        self.db_manager = db_manager
        self.db = db_manager.db
        
        # Collection names
        self.INTERNAMENTOS_COLLECTION = "internamentos"
        
        ic("Medical Record Importer initialized")
    
    def setup_collections_and_indexes(self) -> bool:
        """
        Set up collections and create indexes for optimal query performance.
        
        Returns:
            bool: True if successful
        """
        console.print("\n[bold yellow]Setting up collections and indexes...[/bold yellow]")
        
        try:
            # Create internamentos collection if it doesn't exist
            if self.INTERNAMENTOS_COLLECTION not in self.db.list_collection_names():
                self.db.create_collection(self.INTERNAMENTOS_COLLECTION)
                ic(f"Collection created: {self.INTERNAMENTOS_COLLECTION}")
            
            collection = self.db[self.INTERNAMENTOS_COLLECTION]
            
            # Create indexes for efficient querying
            indexes_created = []
            
            # 1. Unique index on numero_internamento (admission number)
            collection.create_index(
                [("internamento.numero_internamento", ASCENDING)],
                unique=True,
                name="idx_numero_internamento"
            )
            indexes_created.append("numero_internamento (unique)")
            
            # 2. Index on patient process number for finding all admissions of a patient
            collection.create_index(
                [("doente.numero_processo", ASCENDING)],
                name="idx_patient_processo"
            )
            indexes_created.append("patient processo")
            
            # 3. Index on admission date for chronological queries
            collection.create_index(
                [("internamento.data_entrada", DESCENDING)],
                name="idx_data_entrada"
            )
            indexes_created.append("admission date")
            
            # 4. Index on patient name for searches
            collection.create_index(
                [("doente.nome", ASCENDING)],
                name="idx_patient_name"
            )
            indexes_created.append("patient name")
            
            # 5. Compound index for patient queries with date
            collection.create_index(
                [
                    ("doente.numero_processo", ASCENDING),
                    ("internamento.data_entrada", DESCENDING)
                ],
                name="idx_patient_date"
            )
            indexes_created.append("patient + date")
            
            # 6. Index on source file for tracking imports
            collection.create_index(
                [("source_file", ASCENDING)],
                name="idx_source_file"
            )
            indexes_created.append("source file")
            
            # 7. Index on extraction date for audit
            collection.create_index(
                [("extraction_date", DESCENDING)],
                name="idx_extraction_date"
            )
            indexes_created.append("extraction date")
            
            ic(f"Indexes created: {indexes_created}")
            console.print(f"[bold green]✓ Created {len(indexes_created)} indexes[/bold green]")
            
            for idx in indexes_created:
                console.print(f"  [cyan]•[/cyan] {idx}")
            
            return True
            
        except Exception as e:
            ic(f"Error setting up collections: {e}")
            console.print(f"[bold red]✗ Error setting up collections:[/bold red] {e}")
            return False
    
    def load_json_file(self, json_path: str) -> Optional[Dict]:
        """
        Load and parse JSON file.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Parsed JSON data or None on error
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            ic(f"Loaded JSON file: {json_path}")
            return data
            
        except FileNotFoundError:
            console.print(f"[bold red]✗ File not found:[/bold red] {json_path}")
            return None
        except json.JSONDecodeError as e:
            console.print(f"[bold red]✗ Invalid JSON:[/bold red] {e}")
            return None
        except Exception as e:
            console.print(f"[bold red]✗ Error loading file:[/bold red] {e}")
            return None
    
    def transform_for_mongodb(self, json_data: Dict) -> Dict:
        """
        Transform JSON data to MongoDB document structure.
        
        The main document represents an INTERNAMENTO (admission) with all related data embedded.
        
        Structure:
        {
            _id: ObjectId (auto-generated),
            internamento: { ... admission data ... },
            doente: { 
                ... patient data ...,
                patologias: [ ... pre-existing conditions ... ],
                medicacoes: [ ... regular medications ... ]
            },
            queimaduras: [ ... burns ... ],
            procedimentos: [ ... procedures ... ],
            antibioticos: [ ... antibiotics during admission ... ],
            infecoes: [ ... infections ... ],
            traumas: [ ... traumas ... ],
            source_file: "...",
            extraction_date: "...",
            import_date: "..." (added by importer)
        }
        
        Args:
            json_data: Raw JSON data from extraction
            
        Returns:
            Transformed document for MongoDB
        """
        # Create document with internamento as main unit
        document = {
            # Main admission data
            "internamento": json_data["internamento"],
            
            # Patient data with embedded pathologies and medications
            "doente": {
                **json_data["doente"],
                "patologias": json_data.get("patologias", []),
                "medicacoes": json_data.get("medicacoes", [])
            },
            
            # Embedded arrays for admission-related data
            "queimaduras": json_data.get("queimaduras", []),
            "procedimentos": json_data.get("procedimentos", []),
            "antibioticos": json_data.get("antibioticos", []),
            "infecoes": json_data.get("infecoes", []),
            "traumas": json_data.get("traumas", []),
            
            # Metadata
            "source_file": json_data.get("source_file"),
            "extraction_date": json_data.get("extraction_date"),
            "import_date": datetime.now().isoformat(),
            
            # Computed fields for easier querying
            "ano_internamento": int(json_data["internamento"]["data_entrada"][:4]) 
                if json_data["internamento"].get("data_entrada") else None,
            "tem_queimaduras": len(json_data.get("queimaduras", [])) > 0,
            "tem_procedimentos": len(json_data.get("procedimentos", [])) > 0,
            "tem_infecoes": len(json_data.get("infecoes", [])) > 0,
        }
        
        ic(f"Document transformed for admission: {document['internamento']['numero_internamento']}")
        return document
    
    def import_json_file(self, json_path: str, skip_duplicates: bool = True) -> Dict:
        """
        Import a single JSON file into MongoDB.
        
        Args:
            json_path: Path to JSON file
            skip_duplicates: If True, skip files already imported (based on numero_internamento)
            
        Returns:
            dict: Import result with status and details
        """
        result = {
            "success": False,
            "file": json_path,
            "admission_number": None,
            "message": "",
            "error": None
        }
        
        # Load JSON data
        json_data = self.load_json_file(json_path)
        if not json_data:
            result["error"] = "Failed to load JSON file"
            return result
        
        # Transform to MongoDB document
        document = self.transform_for_mongodb(json_data)
        admission_number = document["internamento"]["numero_internamento"]
        result["admission_number"] = admission_number
        
        # Check if already exists
        collection = self.db[self.INTERNAMENTOS_COLLECTION]
        existing = collection.find_one({
            "internamento.numero_internamento": admission_number
        })
        
        if existing:
            if skip_duplicates:
                result["message"] = f"Admission {admission_number} already exists - skipped"
                result["success"] = True
                result["skipped"] = True
                ic(f"Skipped duplicate admission: {admission_number}")
                return result
            else:
                # Update existing document
                try:
                    collection.replace_one(
                        {"internamento.numero_internamento": admission_number},
                        document
                    )
                    result["success"] = True
                    result["message"] = f"Admission {admission_number} updated"
                    result["updated"] = True
                    ic(f"Updated admission: {admission_number}")
                    return result
                except Exception as e:
                    result["error"] = f"Update failed: {e}"
                    ic(f"Update error: {e}")
                    return result
        
        # Insert new document
        try:
            insert_result = collection.insert_one(document)
            result["success"] = True
            result["message"] = f"Admission {admission_number} imported successfully"
            result["document_id"] = str(insert_result.inserted_id)
            ic(f"Inserted admission: {admission_number}, _id: {insert_result.inserted_id}")
            return result
            
        except DuplicateKeyError:
            result["error"] = "Duplicate admission number"
            result["message"] = f"Admission {admission_number} already exists"
            ic(f"Duplicate key error for admission: {admission_number}")
            return result
        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"Import failed: {e}"
            ic(f"Insert error: {e}")
            return result
    
    def import_directory(self, directory_path: str, pattern: str = "*.json", 
                        skip_duplicates: bool = True) -> Dict:
        """
        Import all JSON files from a directory.
        
        Args:
            directory_path: Path to directory containing JSON files
            pattern: File pattern to match (default: *.json)
            skip_duplicates: Skip already imported files
            
        Returns:
            dict: Summary of import operation
        """
        dir_path = Path(directory_path)
        
        if not dir_path.exists():
            console.print(f"[bold red]✗ Directory not found:[/bold red] {directory_path}")
            return {"success": False, "error": "Directory not found"}
        
        # Find all matching JSON files
        json_files = list(dir_path.rglob(pattern))
        
        if not json_files:
            console.print(f"[yellow]⚠ No JSON files found in {directory_path}[/yellow]")
            return {"success": False, "error": "No JSON files found"}
        
        console.print(f"\n[bold cyan]Found {len(json_files)} JSON file(s)[/bold cyan]")
        
        # Import each file with progress bar
        results = {
            "total": len(json_files),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "updated": 0,
            "details": []
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Importing files...", total=len(json_files))
            
            for json_file in json_files:
                result = self.import_json_file(str(json_file), skip_duplicates)
                results["details"].append(result)
                
                if result["success"]:
                    if result.get("skipped"):
                        results["skipped"] += 1
                    elif result.get("updated"):
                        results["updated"] += 1
                    else:
                        results["successful"] += 1
                else:
                    results["failed"] += 1
                
                progress.update(task, advance=1)
        
        # Display summary
        self._display_import_summary(results)
        
        return results
    
    def _display_import_summary(self, results: Dict) -> None:
        """Display import summary in a formatted panel."""
        
        summary = f"""[cyan]Total Files:[/cyan] {results['total']}
[green]Successfully Imported:[/green] {results['successful']}
[blue]Updated:[/blue] {results['updated']}
[yellow]Skipped (duplicates):[/yellow] {results['skipped']}
[red]Failed:[/red] {results['failed']}"""
        
        console.print("\n" + "="*80)
        console.print(Panel(
            summary,
            title="📊 Import Summary",
            border_style="cyan"
        ))
        
        # Show details for failed imports
        if results['failed'] > 0:
            console.print("\n[bold red]Failed Imports:[/bold red]")
            for detail in results['details']:
                if not detail['success'] and not detail.get('skipped'):
                    console.print(f"  [red]✗[/red] {detail['file']}: {detail.get('error', 'Unknown error')}")
    
    def get_patient_admissions(self, numero_processo: int) -> List[Dict]:
        """
        Get all admissions for a specific patient.
        
        Args:
            numero_processo: Patient process number
            
        Returns:
            List of admission documents
        """
        collection = self.db[self.INTERNAMENTOS_COLLECTION]
        admissions = list(collection.find(
            {"doente.numero_processo": numero_processo}
        ).sort("internamento.data_entrada", DESCENDING))
        
        ic(f"Found {len(admissions)} admissions for patient {numero_processo}")
        return admissions
    
    def get_admission_by_number(self, numero_internamento: int) -> Optional[Dict]:
        """
        Get a specific admission by admission number.
        
        Args:
            numero_internamento: Admission number
            
        Returns:
            Admission document or None
        """
        collection = self.db[self.INTERNAMENTOS_COLLECTION]
        admission = collection.find_one(
            {"internamento.numero_internamento": numero_internamento}
        )
        
        ic(f"Found admission: {numero_internamento}" if admission else f"Admission not found: {numero_internamento}")
        return admission
    
    def display_admission_summary(self, admission: Dict) -> None:
        """Display a formatted summary of an admission."""
        
        internamento = admission["internamento"]
        doente = admission["doente"]
        
        info = f"""[cyan]Patient:[/cyan] {doente['nome']}
[cyan]Process:[/cyan] {doente['numero_processo']}
[cyan]Birth Date:[/cyan] {doente['data_nascimento']}

[yellow]Admission:[/yellow] {internamento['numero_internamento']}
[yellow]Dates:[/yellow] {internamento['data_entrada']} → {internamento.get('data_alta', 'ongoing')}
[yellow]Origin:[/yellow] {internamento.get('origem_entrada', 'N/A')}
[yellow]Destination:[/yellow] {internamento.get('destino_alta', 'N/A')}
[yellow]ASCQ:[/yellow] {internamento.get('ASCQ_total', 'N/A')}%

[green]Burns:[/green] {len(admission.get('queimaduras', []))}
[green]Procedures:[/green] {len(admission.get('procedimentos', []))}
[green]Pathologies:[/green] {len(doente.get('patologias', []))}
[green]Medications:[/green] {len(doente.get('medicacoes', []))}
[green]Infections:[/green] {len(admission.get('infecoes', []))}"""
        
        console.print(Panel(
            info,
            title=f"🏥 Admission {internamento['numero_internamento']}",
            border_style="cyan"
        ))


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def import_single_file(json_path: str, db_manager: Optional[MongoDBManager] = None) -> Dict:
    """
    Convenience function to import a single JSON file.
    
    Args:
        json_path: Path to JSON file
        db_manager: Optional existing database manager
        
    Returns:
        Import result
    """
    if db_manager is None:
        db_manager = MongoDBManager()
        if not db_manager.connect():
            return {"success": False, "error": "Failed to connect to database"}
    
    importer = MedicalRecordImporter(db_manager)
    importer.setup_collections_and_indexes()
    result = importer.import_json_file(json_path)
    
    return result


def import_from_directory(directory_path: str, pattern: str = "*_extracted.json",
                         db_manager: Optional[MongoDBManager] = None) -> Dict:
    """
    Convenience function to import all JSON files from a directory.
    
    Args:
        directory_path: Directory containing JSON files
        pattern: File pattern to match
        db_manager: Optional existing database manager
        
    Returns:
        Import summary
    """
    if db_manager is None:
        db_manager = MongoDBManager()
        if not db_manager.connect():
            return {"success": False, "error": "Failed to connect to database"}
    
    importer = MedicalRecordImporter(db_manager)
    importer.setup_collections_and_indexes()
    results = importer.import_directory(directory_path, pattern)
    
    return results


# ============================================================================
# MAIN EXECUTION - Testing
# ============================================================================

if __name__ == "__main__":
    console.print("\n" + "="*80)
    console.print("[bold cyan]Medical Record Data Importer[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Connect to database
    db_manager = MongoDBManager()
    if not db_manager.connect():
        console.print("[bold red]Failed to connect to database![/bold red]")
        exit(1)
    
    # Create importer
    importer = MedicalRecordImporter(db_manager)
    
    # Setup collections and indexes
    importer.setup_collections_and_indexes()
    
    # Test with single file
    test_file = "/home/gusmmm/Desktop/theparser/pdf/output/2401/2401_extracted.json"
    console.print(f"\n[bold yellow]Testing import of:[/bold yellow] {test_file}\n")
    
    result = importer.import_json_file(test_file)
    
    if result["success"]:
        console.print(f"\n[bold green]✓ {result['message']}[/bold green]")
        
        # Display the imported admission
        if not result.get("skipped"):
            admission = importer.get_admission_by_number(result["admission_number"])
            if admission:
                importer.display_admission_summary(admission)
    else:
        console.print(f"\n[bold red]✗ Import failed:[/bold red] {result.get('error')}")
    
    # Show database info
    db_manager.list_database_info()
    
    # Disconnect
    db_manager.disconnect()
    
    console.print("\n[bold green]✓ Import test completed![/bold green]\n")
