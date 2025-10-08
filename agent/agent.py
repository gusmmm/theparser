"""
AI Agent for extracting structured data from cleaned medical record markdown files.

Uses Google Gemini API with structured output (Pydantic models) to parse medical records
and save as JSON for database population.

Author: Agent
Date: 2024-10-08
"""

from google import genai
from google.genai import types
from dotenv import load_dotenv
from icecream import ic
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from pathlib import Path
from datetime import datetime
import json
import sys

from .models import MedicalRecordExtraction

# Configure icecream for debugging
ic.configureOutput(prefix='[DEBUG] ')

# Rich console for beautiful output
console = Console()

# Load environment variables
load_dotenv()
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    console.print("[bold red]ERROR:[/bold red] GEMINI_API_KEY not found in environment variables!")
    console.print("Please add it to your .env file")
    sys.exit(1)

ic("API Key loaded successfully")


def read_markdown_file(file_path: str) -> str:
    """
    Read the cleaned markdown file containing medical records.
    
    Args:
        file_path: Path to the .cleaned.md file
        
    Returns:
        File contents as string
    """
    ic(f"Reading file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ic(f"File read successfully. Length: {len(content)} characters")
        return content
        
    except FileNotFoundError:
        console.print(f"[bold red]ERROR:[/bold red] File not found: {file_path}")
        raise
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] Failed to read file: {e}")
        raise


def create_extraction_prompt(markdown_content: str) -> str:
    """
    Create a detailed prompt for Gemini to extract structured data from medical records.
    
    Args:
        markdown_content: The markdown file content
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a medical data extraction AI assistant specialized in Portuguese medical records from a burn unit (Unidade de Queimados).

Your task is to extract ALL relevant information from the following medical record and structure it according to the provided Pydantic schema.

## CRITICAL EXTRACTION RULES:

### 1. SOURCE TEXT VALIDATION (MANDATORY):
- For EVERY extracted item, you MUST include the `source_text` field
- Copy the EXACT phrase/sentence from the medical record where you found the information
- This allows humans to validate your extraction
- Include enough context to identify the source (typically the full sentence)

### 2. BURN ANATOMICAL LOCATIONS (BE SPECIFIC):
**Available locations (LocalAnatomicoEnum):**
- HEAD (cabeça, excluding face)
- FACE (face, rosto)
- CERVICAL (pescoço, neck)
- CHEST (tórax, peito)
- ABDOMEN (abdómen, ventre)
- BACK (costas, dorso)
- PERINEUM (períneo, genitais)
- UPPER_LIMB (braço, antebraço, membro superior - EXCLUDING hand)
- LOWER_LIMB (perna, coxa, membro inferior - EXCLUDING foot)
- HAND (mão, dedos da mão)
- FOOT (pé, dedos do pé)

**CRITICAL SPECIFICITY RULES:**
- If burn affects HAND specifically → Create separate HAND entry
- If burn affects arm/forearm → Create separate UPPER_LIMB entry
- If text says "membro superior direito e mão" → Create TWO entries: UPPER_LIMB and HAND
- If burn affects FOOT specifically → Create separate FOOT entry
- If burn affects leg/thigh → Create separate LOWER_LIMB entry
- If text says "membro inferior e pé" → Create TWO entries: LOWER_LIMB and FOOT
- DO NOT combine hand with upper limb or foot with lower limb
- Create as many burn entries as distinct anatomical regions mentioned
- If same region mentioned multiple times with different details, consolidate into one entry

**Examples:**
- "Queimadura 2º grau face" → 1 entry: FACE
- "Queimadura membro superior direito e mão" → 2 entries: UPPER_LIMB + HAND
- "Queimadura panfacial" → 1 entry: FACE
- "Queimadura braço direito, antebraço e mão" → 2 entries: UPPER_LIMB + HAND
- "Queimadura mama direita e hemitórax" → 1 entry: CHEST

### 3. Patient Information (Doente):
- Extract full name, process number (número processo), birth date, sex, and full address
- Process number is typically a 8-digit number (e.g., 23056175)
- Birth date must be in YYYY-MM-DD format
- Sex: M or F
- Include source_text fields for name, birth date, and address

### 4. Hospitalization (Internamento):
- Extract admission date (data entrada), discharge date (data alta/saída)
- Burn date (data queimadura) if explicitly mentioned
- Total burn surface area percentage (SCQ/ASCQ) - this is the total percentage
- Inhalation injury status (lesão inalatória): SIM/NAO/SUSPEITA
- Origin: text description (e.g., "Hospital de Viana do Castelo", "SU")
- Destination: text description (e.g., "Consulta Externa", "Domicílio", "Enfermaria")
- Burn mechanism: text (e.g., "escaldadura", "chama", "contacto")
- Burn agent: text (e.g., "líquido quente", "fogo direto", "óleo quente")
- Include source_text for dates, origin, destination, and ASCQ calculation

### 5. Burns (Queimaduras):
- For EACH distinct anatomical location, create a separate entry
- Include: location enum, maximum degree, percentage (if mentioned), notes
- **MANDATORY**: Include source_text with the exact phrase describing this burn
- Degree conversion: "2º grau"→SEGUNDO, "3º grau"→TERCEIRO, "1º grau"→PRIMEIRO, "4º grau"→QUARTO
- If percentage given for specific location, include it

### 6. Pre-existing Conditions (Patologias):
- Look in "Antecedentes Pessoais" (AP) section
- Extract: condition name, class (if identifiable), notes
- Common: HTA, Diabetes Mellitus tipo 2, DPOC, IRC, etc.
- **MANDATORY**: Include source_text from AP section

### 7. Regular Medications (Medicações):
- Look in "Medicação Habitual" (MH) section or medication lists
- Extract: medication name, dosage, posology (e.g., "1+0+1")
- **MANDATORY**: Include source_text from MH section
- Examples: "Ramipril, 2.5 mg", "Metformina, 1000 mg"

### 8. Procedures (Procedimentos):
- Surgical interventions, debridement, skin grafts, escharotomies
- Include procedure name, type, date (if mentioned)
- **MANDATORY**: Include source_text describing the procedure
- Look for: "Submetida a intervenção cirúrgica", "Desbridamento", "Enxerto", "Escarotomias"

### 9. Antibiotics (during hospitalization):
- Extract antibiotic name, class (if known), indication
- **MANDATORY**: Include source_text
- Only include antibiotics given during hospitalization, not pre-admission medications

### 10. Infections:
- Extract agent name, agent type (bacteria/fungos/virus), location, type
- **MANDATORY**: Include source_text
- Look for culture results, infection mentions

### 11. Traumas:
- Extract trauma type, location, whether emergency surgery needed
- **MANDATORY**: Include source_text

## GENERAL RULES:
- Dates MUST be in YYYY-MM-DD format
- If information is not present, leave field as null
- Be precise with numerical values (percentages, ages, days)
- Preserve Portuguese medical terminology in text fields
- DO NOT invent information - only extract what is explicitly stated
- When in doubt about location specificity, create separate entries
- Timestamps (created_at) will be auto-generated

## MEDICAL RECORD TO EXTRACT:

{markdown_content}

## OUTPUT:
Provide a complete structured extraction following the MedicalRecordExtraction Pydantic model.
Include ALL information found in the document.
Ensure ALL source_text fields are filled with exact phrases from the document.
Be SPECIFIC with burn anatomical locations - separate hand/foot from limbs.
"""
    
    ic(f"Prompt created. Length: {len(prompt)} characters")
    return prompt


def extract_data_from_markdown(file_path: str) -> MedicalRecordExtraction:
    """
    Extract structured data from a markdown medical record using Gemini AI.
    
    Args:
        file_path: Path to the .cleaned.md file
        
    Returns:
        MedicalRecordExtraction object with structured data
    """
    console.print(Panel(
        f"[bold cyan]Starting extraction from:[/bold cyan]\n{file_path}",
        title="🤖 AI Medical Data Extraction",
        border_style="cyan"
    ))
    
    # Read markdown content
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Reading markdown file...", total=None)
        markdown_content = read_markdown_file(file_path)
        progress.update(task, completed=True)
    
    # Create extraction prompt
    console.print("\n[bold yellow]Creating extraction prompt...[/bold yellow]")
    prompt = create_extraction_prompt(markdown_content)
    ic("Prompt ready for Gemini")
    
    # Initialize Gemini client
    console.print("[bold yellow]Initializing Gemini client...[/bold yellow]")
    client = genai.Client(api_key=GEMINI_API_KEY)
    ic("Client initialized")
    
    # Generate structured content with thinking budget
    console.print("\n[bold magenta]🧠 Calling Gemini API with structured output...[/bold magenta]")
    console.print("[dim]Using gemini-2.5-flash with thinking budget for complex extraction[/dim]\n")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing with Gemini (this may take a moment)...", total=None)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MedicalRecordExtraction,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=2048  # Use thinking budget for complex extraction
                    )
                ),
            )
            
            progress.update(task, completed=True)
        
        ic("API call successful")
        console.print("[bold green]✓ Extraction completed successfully![/bold green]\n")
        
        # Parse response to Pydantic model
        console.print("[bold yellow]Parsing response to structured model...[/bold yellow]")
        extracted_data = MedicalRecordExtraction.model_validate_json(response.text)
        ic("Data validated successfully")
        
        # Add metadata
        extracted_data.source_file = Path(file_path).name
        extracted_data.extraction_date = datetime.now().isoformat()
        
        console.print("[bold green]✓ Data validated and structured![/bold green]\n")
        
        return extracted_data
        
    except Exception as e:
        console.print(f"\n[bold red]ERROR during extraction:[/bold red] {e}")
        ic(f"Exception: {type(e).__name__}: {e}")
        raise


def save_to_json(data: MedicalRecordExtraction, original_file_path: str) -> str:
    """
    Save extracted data to JSON file in the same directory as the markdown file.
    
    Args:
        data: Extracted medical record data
        original_file_path: Path to the original .cleaned.md file
        
    Returns:
        Path to the saved JSON file
    """
    # Create JSON filename (replace .cleaned.md with .extracted.json)
    original_path = Path(original_file_path)
    json_filename = original_path.stem.replace('_merged_medical_records.cleaned', '_extracted') + '.json'
    json_path = original_path.parent / json_filename
    
    ic(f"Saving to: {json_path}")
    console.print(f"\n[bold yellow]Saving structured data to JSON...[/bold yellow]")
    
    try:
        # Convert to dict and save with pretty formatting
        data_dict = data.model_dump(mode='json', exclude_none=False)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=2)
        
        ic(f"JSON saved successfully: {json_path}")
        console.print(f"[bold green]✓ JSON saved:[/bold green] {json_path}\n")
        
        # Show JSON preview
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        syntax = Syntax(json_content[:1000] + "\n..." if len(json_content) > 1000 else json_content, 
                       "json", 
                       theme="monokai", 
                       line_numbers=True)
        console.print(Panel(syntax, title="📄 JSON Preview (first 1000 chars)", border_style="green"))
        
        return str(json_path)
        
    except Exception as e:
        console.print(f"[bold red]ERROR saving JSON:[/bold red] {e}")
        ic(f"Save exception: {type(e).__name__}: {e}")
        raise


def process_medical_record(file_path: str) -> dict:
    """
    Main processing pipeline: read markdown -> extract data -> save JSON.
    
    Args:
        file_path: Path to .cleaned.md file
        
    Returns:
        Dictionary with processing results
    """
    start_time = datetime.now()
    
    try:
        # Extract data
        extracted_data = extract_data_from_markdown(file_path)
        
        # Save to JSON
        json_path = save_to_json(extracted_data, file_path)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Summary
        console.print("\n" + "="*80)
        console.print(Panel(
            f"[bold green]✓ Processing Complete![/bold green]\n\n"
            f"[cyan]Source:[/cyan] {Path(file_path).name}\n"
            f"[cyan]Output:[/cyan] {Path(json_path).name}\n"
            f"[cyan]Duration:[/cyan] {duration:.2f} seconds\n\n"
            f"[yellow]Patient:[/yellow] {extracted_data.doente.nome}\n"
            f"[yellow]Process:[/yellow] {extracted_data.doente.numero_processo}\n"
            f"[yellow]Admission:[/yellow] {extracted_data.internamento.data_entrada}\n"
            f"[yellow]Burns:[/yellow] {len(extracted_data.queimaduras)} locations\n"
            f"[yellow]ASCQ:[/yellow] {extracted_data.internamento.ASCQ_total}%",
            title="📊 Extraction Summary",
            border_style="green"
        ))
        
        return {
            "success": True,
            "source_file": file_path,
            "json_file": json_path,
            "duration": duration,
            "patient_name": extracted_data.doente.nome,
            "process_number": extracted_data.doente.numero_processo
        }
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Processing failed:[/bold red] {e}")
        ic(f"Processing exception: {type(e).__name__}: {e}")
        return {
            "success": False,
            "source_file": file_path,
            "error": str(e)
        }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Test with subject 2401
    test_file = "/home/gusmmm/Desktop/theparser/pdf/output/2401/2401_merged_medical_records.cleaned.md"
    
    console.print("\n" + "="*80)
    console.print("[bold cyan]Medical Record Data Extraction Agent[/bold cyan]")
    console.print("="*80 + "\n")
    
    result = process_medical_record(test_file)
    
    if result["success"]:
        console.print("\n[bold green]🎉 Extraction pipeline completed successfully![/bold green]")
    else:
        console.print("\n[bold red]💥 Extraction pipeline failed![/bold red]")
        sys.exit(1)