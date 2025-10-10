"""
Exhaustive Analysis of UQ Database - Internamentos Collection

Comprehensive statistical analysis and visualization of burn unit hospitalizations.
Includes quality checks, temporal analysis, clinical patterns, and detailed reports.

Author: Agent
Date: 2025-10-10
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import warnings

# Data manipulation and analysis
import pandas as pd
import numpy as np

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates

# Rich terminal output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

# Database
sys.path.append(str(Path(__file__).parent.parent))
from database.db_manager import MongoDBManager

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure plotting style
sns.set_theme(style="whitegrid", palette="husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

console = Console()


class InternamentosAnalyzer:
    """Comprehensive analyzer for burn unit hospitalizations."""
    
    def __init__(self, db_manager: MongoDBManager):
        """
        Initialize analyzer with database connection.
        
        Args:
            db_manager: Connected MongoDB manager instance
        """
        self.db_manager = db_manager
        self.collection = db_manager.db['internamentos']
        self.df_main = None
        self.df_burns = None
        self.df_procedures = None
        self.df_pathologies = None
        self.df_medications = None
        self.df_infections = None
        self.df_antibiotics = None
        
        self.report_dir = Path("reports/internamentos_analysis")
        self.report_dir.mkdir(exist_ok=True, parents=True)
        
        self.quality_issues: List[Dict[str, Any]] = []
        
    def extract_data_from_mongodb(self) -> None:
        """Extract and transform all data from MongoDB to pandas DataFrames."""
        
        console.print("\n[bold cyan]📊 Extracting data from MongoDB...[/bold cyan]")
        
        # Get all documents
        documents = list(self.collection.find({}))
        
        if not documents:
            console.print("[red]No data found in collection![/red]")
            return
        
        console.print(f"[green]✓ Found {len(documents)} internamento records[/green]")
        
        # Extract main internamento data
        main_records = []
        burns_records = []
        procedures_records = []
        pathologies_records = []
        medications_records = []
        infections_records = []
        antibiotics_records = []
        
        for doc in documents:
            internamento = doc.get('internamento', {})
            doente = doc.get('doente', {})
            
            # Main record
            main_record = {
                '_id': str(doc['_id']),
                'numero_internamento': internamento.get('numero_internamento'),
                'numero_processo': doente.get('numero_processo'),
                'nome_paciente': doente.get('nome'),
                'sexo': doente.get('sexo'),
                'data_nascimento': doente.get('data_nascimento'),
                'data_entrada': internamento.get('data_entrada'),
                'data_alta': internamento.get('data_alta'),
                'data_queimadura': internamento.get('data_queimadura'),
                'origem_entrada': internamento.get('origem_entrada'),
                'destino_alta': internamento.get('destino_alta'),
                'ASCQ_total': internamento.get('ASCQ_total'),
                'lesao_inalatoria': internamento.get('lesao_inalatoria'),
                'mecanismo_queimadura': internamento.get('mecanismo_queimadura'),
                'agente_queimadura': internamento.get('agente_queimadura'),
                'tipo_acidente': internamento.get('tipo_acidente'),
                'incendio_florestal': internamento.get('incendio_florestal'),
                'contexto_violento': internamento.get('contexto_violento'),
                'suicidio_tentativa': internamento.get('suicidio_tentativa'),
                'escarotomias_entrada': internamento.get('escarotomias_entrada'),
                'intubacao_OT': internamento.get('intubacao_OT'),
                'VMI_dias': internamento.get('VMI_dias'),
                'VNI': internamento.get('VNI'),
                'num_queimaduras': len(doc.get('queimaduras', [])),
                'num_procedimentos': len(doc.get('procedimentos', [])),
                'num_patologias': len(doente.get('patologias', [])),
                'num_medicacoes': len(doente.get('medicacoes', [])),
                'num_infecoes': len(doc.get('infecoes', [])),
                'num_antibioticos': len(doc.get('antibioticos', [])),
                'source_file': doc.get('source_file'),
                'extraction_date': doc.get('extraction_date'),
            }
            main_records.append(main_record)
            
            # Burns
            for burn in doc.get('queimaduras', []):
                burns_records.append({
                    'numero_internamento': internamento.get('numero_internamento'),
                    'local_anatomico': burn.get('local_anatomico'),
                    'grau_maximo': burn.get('grau_maximo'),
                    'percentagem': burn.get('percentagem'),
                    'notas': burn.get('notas'),
                })
            
            # Procedures
            for proc in doc.get('procedimentos', []):
                procedures_records.append({
                    'numero_internamento': internamento.get('numero_internamento'),
                    'nome_procedimento': proc.get('nome_procedimento'),
                    'tipo_procedimento': proc.get('tipo_procedimento'),
                    'data_procedimento': proc.get('data_procedimento'),
                })
            
            # Pathologies
            for path in doente.get('patologias', []):
                pathologies_records.append({
                    'numero_internamento': internamento.get('numero_internamento'),
                    'nome_patologia': path.get('nome_patologia'),
                    'classe_patologia': path.get('classe_patologia'),
                })
            
            # Medications
            for med in doente.get('medicacoes', []):
                medications_records.append({
                    'numero_internamento': internamento.get('numero_internamento'),
                    'nome_medicacao': med.get('nome_medicacao'),
                    'dosagem': med.get('dosagem'),
                    'posologia': med.get('posologia'),
                })
            
            # Infections
            for inf in doc.get('infecoes', []):
                infections_records.append({
                    'numero_internamento': internamento.get('numero_internamento'),
                    'nome_agente': inf.get('nome_agente'),
                    'tipo_agente': inf.get('tipo_agente'),
                    'local_infecao': inf.get('local_infecao'),
                    'tipo_infecao': inf.get('tipo_infecao'),
                })
            
            # Antibiotics
            for anti in doc.get('antibioticos', []):
                antibiotics_records.append({
                    'numero_internamento': internamento.get('numero_internamento'),
                    'nome_antibiotico': anti.get('nome_antibiotico'),
                    'classe': anti.get('classe'),
                    'indicacao': anti.get('indicacao'),
                })
        
        # Create DataFrames
        self.df_main = pd.DataFrame(main_records)
        self.df_burns = pd.DataFrame(burns_records) if burns_records else pd.DataFrame()
        self.df_procedures = pd.DataFrame(procedures_records) if procedures_records else pd.DataFrame()
        self.df_pathologies = pd.DataFrame(pathologies_records) if pathologies_records else pd.DataFrame()
        self.df_medications = pd.DataFrame(medications_records) if medications_records else pd.DataFrame()
        self.df_infections = pd.DataFrame(infections_records) if infections_records else pd.DataFrame()
        self.df_antibiotics = pd.DataFrame(antibiotics_records) if antibiotics_records else pd.DataFrame()
        
        console.print(f"[green]✓ Created DataFrames:[/green]")
        console.print(f"  - Main: {len(self.df_main)} records")
        console.print(f"  - Burns: {len(self.df_burns)} records")
        console.print(f"  - Procedures: {len(self.df_procedures)} records")
        console.print(f"  - Pathologies: {len(self.df_pathologies)} records")
        console.print(f"  - Medications: {len(self.df_medications)} records")
        console.print(f"  - Infections: {len(self.df_infections)} records")
        console.print(f"  - Antibiotics: {len(self.df_antibiotics)} records")
    
    def convert_dates(self) -> None:
        """Convert all date fields to proper datetime objects."""
        
        console.print("\n[bold cyan]📅 Converting dates...[/bold cyan]")
        
        date_fields = ['data_nascimento', 'data_entrada', 'data_alta', 'data_queimadura', 'extraction_date']
        
        for field in date_fields:
            if field in self.df_main.columns:
                # Handle mixed datetime and string types
                self.df_main[field] = pd.to_datetime(self.df_main[field], errors='coerce')
                non_null = self.df_main[field].notna().sum()
                console.print(f"  ✓ {field}: {non_null}/{len(self.df_main)} valid dates")
        
        # Convert procedure dates
        if 'data_procedimento' in self.df_procedures.columns:
            self.df_procedures['data_procedimento'] = pd.to_datetime(
                self.df_procedures['data_procedimento'], errors='coerce'
            )
            non_null = self.df_procedures['data_procedimento'].notna().sum()
            console.print(f"  ✓ data_procedimento: {non_null}/{len(self.df_procedures)} valid dates")
        
        # Calculate derived date fields
        if 'data_nascimento' in self.df_main.columns and 'data_entrada' in self.df_main.columns:
            self.df_main['idade_entrada'] = (
                (self.df_main['data_entrada'] - self.df_main['data_nascimento']).dt.days / 365.25
            )
        
        if 'data_entrada' in self.df_main.columns and 'data_alta' in self.df_main.columns:
            self.df_main['dias_internamento'] = (
                (self.df_main['data_alta'] - self.df_main['data_entrada']).dt.days
            )
        
        if 'data_queimadura' in self.df_main.columns and 'data_entrada' in self.df_main.columns:
            self.df_main['dias_ate_admissao'] = (
                (self.df_main['data_entrada'] - self.df_main['data_queimadura']).dt.days
            )
        
        # Extract year and month for temporal analysis
        if 'data_entrada' in self.df_main.columns:
            self.df_main['ano_entrada'] = self.df_main['data_entrada'].dt.year
            self.df_main['mes_entrada'] = self.df_main['data_entrada'].dt.month
            self.df_main['trimestre_entrada'] = self.df_main['data_entrada'].dt.quarter
        
        console.print("[green]✓ Date conversion complete[/green]")
    
    def perform_quality_checks(self) -> None:
        """Perform comprehensive data quality checks."""
        
        console.print("\n[bold cyan]🔍 Performing quality checks...[/bold cyan]")
        
        # Check for missing critical fields
        critical_fields = [
            'numero_internamento', 'numero_processo', 'data_entrada',
            'sexo', 'ASCQ_total'
        ]
        
        for field in critical_fields:
            missing = self.df_main[field].isna().sum()
            if missing > 0:
                self.quality_issues.append({
                    'type': 'missing_critical',
                    'field': field,
                    'count': missing,
                    'percentage': (missing / len(self.df_main)) * 100
                })
                console.print(f"  [yellow]⚠ {field}: {missing} missing ({(missing/len(self.df_main)*100):.1f}%)[/yellow]")
        
        # Check for duplicates
        duplicates = self.df_main['numero_internamento'].duplicated().sum()
        if duplicates > 0:
            self.quality_issues.append({
                'type': 'duplicates',
                'field': 'numero_internamento',
                'count': duplicates
            })
            console.print(f"  [red]✗ Duplicate internamento numbers: {duplicates}[/red]")
        
        # Check date logic
        invalid_stay = (self.df_main['dias_internamento'] < 0).sum()
        if invalid_stay > 0:
            self.quality_issues.append({
                'type': 'invalid_date_logic',
                'field': 'dias_internamento',
                'count': invalid_stay
            })
            console.print(f"  [red]✗ Negative hospital stays: {invalid_stay}[/red]")
        
        # Check age ranges
        invalid_age = ((self.df_main['idade_entrada'] < 0) | (self.df_main['idade_entrada'] > 120)).sum()
        if invalid_age > 0:
            self.quality_issues.append({
                'type': 'invalid_age',
                'field': 'idade_entrada',
                'count': invalid_age
            })
            console.print(f"  [red]✗ Invalid ages: {invalid_age}[/red]")
        
        # Check ASCQ range
        invalid_ascq = ((self.df_main['ASCQ_total'] < 0) | (self.df_main['ASCQ_total'] > 100)).sum()
        if invalid_ascq > 0:
            self.quality_issues.append({
                'type': 'invalid_ascq',
                'field': 'ASCQ_total',
                'count': invalid_ascq
            })
            console.print(f"  [red]✗ ASCQ outside 0-100%: {invalid_ascq}[/red]")
        
        # Check for records with no burns
        no_burns = (self.df_main['num_queimaduras'] == 0).sum()
        if no_burns > 0:
            self.quality_issues.append({
                'type': 'missing_data',
                'field': 'num_queimaduras',
                'count': no_burns
            })
            console.print(f"  [yellow]⚠ Records with no burns: {no_burns}[/yellow]")
        
        if not self.quality_issues:
            console.print("[green]✓ No quality issues found![/green]")
        else:
            console.print(f"[yellow]⚠ Found {len(self.quality_issues)} quality issues[/yellow]")
    
    def generate_descriptive_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive descriptive statistics."""
        
        console.print("\n[bold cyan]📈 Generating descriptive statistics...[/bold cyan]")
        
        stats = {}
        
        # Overall statistics
        stats['total_records'] = len(self.df_main)
        stats['date_range'] = {
            'first_admission': self.df_main['data_entrada'].min(),
            'last_admission': self.df_main['data_entrada'].max(),
        }
        
        # Demographics
        stats['demographics'] = {
            'age_mean': self.df_main['idade_entrada'].mean(),
            'age_median': self.df_main['idade_entrada'].median(),
            'age_std': self.df_main['idade_entrada'].std(),
            'age_min': self.df_main['idade_entrada'].min(),
            'age_max': self.df_main['idade_entrada'].max(),
            'sex_distribution': self.df_main['sexo'].value_counts().to_dict(),
        }
        
        # Hospitalization statistics
        stats['hospitalization'] = {
            'length_of_stay_mean': self.df_main['dias_internamento'].mean(),
            'length_of_stay_median': self.df_main['dias_internamento'].median(),
            'length_of_stay_std': self.df_main['dias_internamento'].std(),
            'length_of_stay_min': self.df_main['dias_internamento'].min(),
            'length_of_stay_max': self.df_main['dias_internamento'].max(),
            'time_to_admission_mean': self.df_main['dias_ate_admissao'].mean(),
            'time_to_admission_median': self.df_main['dias_ate_admissao'].median(),
        }
        
        # Burn severity
        stats['burns'] = {
            'ascq_mean': self.df_main['ASCQ_total'].mean(),
            'ascq_median': self.df_main['ASCQ_total'].median(),
            'ascq_std': self.df_main['ASCQ_total'].std(),
            'ascq_min': self.df_main['ASCQ_total'].min(),
            'ascq_max': self.df_main['ASCQ_total'].max(),
            'inhalation_injury': self.df_main['lesao_inalatoria'].value_counts().to_dict() if 'lesao_inalatoria' in self.df_main else {},
            'num_burns_mean': self.df_main['num_queimaduras'].mean(),
        }
        
        # Clinical interventions
        stats['clinical'] = {
            'procedures_mean': self.df_main['num_procedimentos'].mean(),
            'procedures_median': self.df_main['num_procedimentos'].median(),
            'pathologies_mean': self.df_main['num_patologias'].mean(),
            'medications_mean': self.df_main['num_medicacoes'].mean(),
            'infections_total': len(self.df_infections),
            'antibiotics_total': len(self.df_antibiotics),
        }
        
        # Temporal patterns
        if 'ano_entrada' in self.df_main.columns:
            stats['temporal'] = {
                'admissions_by_year': self.df_main['ano_entrada'].value_counts().sort_index().to_dict(),
                'admissions_by_month': self.df_main['mes_entrada'].value_counts().sort_index().to_dict(),
                'admissions_by_quarter': self.df_main['trimestre_entrada'].value_counts().sort_index().to_dict(),
            }
        
        console.print("[green]✓ Statistics generated[/green]")
        return stats
    
    def analyze_burn_mechanisms(self) -> pd.DataFrame:
        """Analyze burn mechanisms and agents."""
        
        console.print("\n[bold cyan]🔥 Analyzing burn mechanisms...[/bold cyan]")
        
        mechanisms = self.df_main['mecanismo_queimadura'].value_counts()
        agents = self.df_main['agente_queimadura'].value_counts()
        accident_types = self.df_main['tipo_acidente'].value_counts()
        
        console.print(f"  ✓ {len(mechanisms)} unique mechanisms")
        console.print(f"  ✓ {len(agents)} unique agents")
        console.print(f"  ✓ {len(accident_types)} accident types")
        
        return pd.DataFrame({
            'mecanismo': mechanisms,
            'agente': agents.reindex(mechanisms.index, fill_value=0),
        })
    
    def analyze_anatomical_locations(self) -> pd.DataFrame:
        """Analyze burn anatomical locations."""
        
        console.print("\n[bold cyan]🗺️ Analyzing anatomical locations...[/bold cyan]")
        
        if self.df_burns.empty:
            console.print("[yellow]⚠ No burn location data available[/yellow]")
            return pd.DataFrame()
        
        locations = self.df_burns['local_anatomico'].value_counts()
        degrees = self.df_burns.groupby('local_anatomico')['grau_maximo'].value_counts().unstack(fill_value=0)
        
        console.print(f"  ✓ {len(locations)} anatomical locations")
        
        return pd.DataFrame({
            'count': locations,
            **degrees.to_dict()
        })
    
    def analyze_procedures(self) -> Dict[str, Any]:
        """Analyze surgical and clinical procedures."""
        
        console.print("\n[bold cyan]🏥 Analyzing procedures...[/bold cyan]")
        
        if self.df_procedures.empty:
            console.print("[yellow]⚠ No procedure data available[/yellow]")
            return {}
        
        procedure_counts = self.df_procedures['nome_procedimento'].value_counts()
        procedure_types = self.df_procedures['tipo_procedimento'].value_counts()
        
        # Procedures per patient
        procedures_per_patient = self.df_procedures.groupby('numero_internamento').size()
        
        console.print(f"  ✓ {len(procedure_counts)} unique procedures")
        console.print(f"  ✓ {len(procedure_types)} procedure types")
        
        return {
            'top_procedures': procedure_counts.head(20).to_dict(),
            'procedure_types': procedure_types.to_dict(),
            'mean_per_patient': procedures_per_patient.mean(),
            'median_per_patient': procedures_per_patient.median(),
        }
    
    def analyze_pathologies(self) -> Dict[str, Any]:
        """Analyze pre-existing pathologies."""
        
        console.print("\n[bold cyan]💊 Analyzing pathologies...[/bold cyan]")
        
        if self.df_pathologies.empty:
            console.print("[yellow]⚠ No pathology data available[/yellow]")
            return {}
        
        pathology_counts = self.df_pathologies['nome_patologia'].value_counts()
        pathology_classes = self.df_pathologies['classe_patologia'].value_counts()
        
        # Pathologies per patient
        pathologies_per_patient = self.df_pathologies.groupby('numero_internamento').size()
        
        # Patients with no pathologies
        patients_with_pathologies = len(self.df_pathologies['numero_internamento'].unique())
        patients_without = len(self.df_main) - patients_with_pathologies
        
        console.print(f"  ✓ {len(pathology_counts)} unique pathologies")
        console.print(f"  ✓ {patients_with_pathologies} patients with pathologies")
        console.print(f"  ✓ {patients_without} patients without recorded pathologies")
        
        return {
            'top_pathologies': pathology_counts.head(20).to_dict(),
            'pathology_classes': pathology_classes.to_dict(),
            'mean_per_patient': pathologies_per_patient.mean(),
            'median_per_patient': pathologies_per_patient.median(),
            'patients_with_pathologies': patients_with_pathologies,
            'patients_without_pathologies': patients_without,
        }
    
    def analyze_medications(self) -> Dict[str, Any]:
        """Analyze regular medications."""
        
        console.print("\n[bold cyan]💉 Analyzing medications...[/bold cyan]")
        
        if self.df_medications.empty:
            console.print("[yellow]⚠ No medication data available[/yellow]")
            return {}
        
        medication_counts = self.df_medications['nome_medicacao'].value_counts()
        
        # Medications per patient
        medications_per_patient = self.df_medications.groupby('numero_internamento').size()
        
        console.print(f"  ✓ {len(medication_counts)} unique medications")
        
        return {
            'top_medications': medication_counts.head(30).to_dict(),
            'mean_per_patient': medications_per_patient.mean(),
            'median_per_patient': medications_per_patient.median(),
        }
    
    def analyze_infections(self) -> Dict[str, Any]:
        """Analyze infections during hospitalization."""
        
        console.print("\n[bold cyan]🦠 Analyzing infections...[/bold cyan]")
        
        if self.df_infections.empty:
            console.print("[yellow]⚠ No infection data available[/yellow]")
            return {}
        
        agent_counts = self.df_infections['nome_agente'].value_counts()
        agent_types = self.df_infections['tipo_agente'].value_counts()
        infection_locations = self.df_infections['local_infecao'].value_counts()
        
        # Infection rate
        patients_with_infections = len(self.df_infections['numero_internamento'].unique())
        infection_rate = (patients_with_infections / len(self.df_main)) * 100
        
        console.print(f"  ✓ {len(agent_counts)} different infectious agents")
        console.print(f"  ✓ Infection rate: {infection_rate:.1f}%")
        
        return {
            'top_agents': agent_counts.head(20).to_dict(),
            'agent_types': agent_types.to_dict(),
            'infection_locations': infection_locations.to_dict(),
            'patients_with_infections': patients_with_infections,
            'infection_rate': infection_rate,
        }
    
    def analyze_antibiotics(self) -> Dict[str, Any]:
        """Analyze antibiotic usage."""
        
        console.print("\n[bold cyan]💊 Analyzing antibiotics...[/bold cyan]")
        
        if self.df_antibiotics.empty:
            console.print("[yellow]⚠ No antibiotic data available[/yellow]")
            return {}
        
        antibiotic_counts = self.df_antibiotics['nome_antibiotico'].value_counts()
        antibiotic_classes = self.df_antibiotics['classe'].value_counts()
        
        # Antibiotic usage rate
        patients_with_antibiotics = len(self.df_antibiotics['numero_internamento'].unique())
        usage_rate = (patients_with_antibiotics / len(self.df_main)) * 100
        
        console.print(f"  ✓ {len(antibiotic_counts)} different antibiotics")
        console.print(f"  ✓ Usage rate: {usage_rate:.1f}%")
        
        return {
            'top_antibiotics': antibiotic_counts.head(20).to_dict(),
            'antibiotic_classes': antibiotic_classes.to_dict(),
            'patients_with_antibiotics': patients_with_antibiotics,
            'usage_rate': usage_rate,
        }
    
    def create_visualizations(self, stats: Dict[str, Any]) -> None:
        """Create comprehensive visualizations and save to PDF."""
        
        console.print("\n[bold cyan]📊 Creating visualizations...[/bold cyan]")
        
        pdf_path = self.report_dir / f"visualizations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        with PdfPages(pdf_path) as pdf:
            # 1. Age distribution
            self._plot_age_distribution(pdf)
            
            # 2. Length of stay distribution
            self._plot_length_of_stay(pdf)
            
            # 3. ASCQ distribution
            self._plot_ascq_distribution(pdf)
            
            # 4. Temporal admissions
            self._plot_temporal_admissions(pdf)
            
            # 5. Burn mechanisms
            self._plot_burn_mechanisms(pdf)
            
            # 6. Anatomical locations
            self._plot_anatomical_locations(pdf)
            
            # 7. Top procedures
            self._plot_top_procedures(pdf)
            
            # 8. Top pathologies
            self._plot_top_pathologies(pdf)
            
            # 9. Top medications
            self._plot_top_medications(pdf)
            
            # 10. Infections
            self._plot_infections(pdf)
            
            # 11. Correlation matrix
            self._plot_correlation_matrix(pdf)
            
            # 12. ASCQ vs Length of Stay
            self._plot_ascq_vs_stay(pdf)
        
        console.print(f"[green]✓ Visualizations saved: {pdf_path}[/green]")
    
    def _plot_age_distribution(self, pdf: PdfPages) -> None:
        """Plot age distribution."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Histogram
        axes[0].hist(self.df_main['idade_entrada'].dropna(), bins=30, edgecolor='black', alpha=0.7)
        axes[0].set_xlabel('Age (years)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Age Distribution at Admission')
        axes[0].axvline(self.df_main['idade_entrada'].mean(), color='red', linestyle='--', 
                       label=f'Mean: {self.df_main["idade_entrada"].mean():.1f}')
        axes[0].legend()
        
        # Box plot by sex
        sex_data = [self.df_main[self.df_main['sexo'] == sex]['idade_entrada'].dropna() 
                    for sex in self.df_main['sexo'].unique() if pd.notna(sex)]
        axes[1].boxplot(sex_data, labels=self.df_main['sexo'].dropna().unique())
        axes[1].set_xlabel('Sex')
        axes[1].set_ylabel('Age (years)')
        axes[1].set_title('Age Distribution by Sex')
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_length_of_stay(self, pdf: PdfPages) -> None:
        """Plot length of stay distribution."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Histogram
        stay_data = self.df_main['dias_internamento'].dropna()
        axes[0].hist(stay_data, bins=50, edgecolor='black', alpha=0.7)
        axes[0].set_xlabel('Days')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Length of Stay Distribution')
        axes[0].axvline(stay_data.mean(), color='red', linestyle='--', 
                       label=f'Mean: {stay_data.mean():.1f} days')
        axes[0].legend()
        
        # Box plot
        axes[1].boxplot(stay_data)
        axes[1].set_ylabel('Days')
        axes[1].set_title('Length of Stay (Box Plot)')
        axes[1].set_xticklabels(['All Patients'])
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_ascq_distribution(self, pdf: PdfPages) -> None:
        """Plot ASCQ distribution."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        ascq_data = self.df_main['ASCQ_total'].dropna()
        
        # Histogram
        axes[0].hist(ascq_data, bins=30, edgecolor='black', alpha=0.7)
        axes[0].set_xlabel('ASCQ (%)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Total Burn Surface Area (ASCQ) Distribution')
        axes[0].axvline(ascq_data.mean(), color='red', linestyle='--', 
                       label=f'Mean: {ascq_data.mean():.1f}%')
        axes[0].legend()
        
        # Categories
        ascq_categories = pd.cut(ascq_data, bins=[0, 10, 20, 30, 40, 100], 
                                labels=['0-10%', '10-20%', '20-30%', '30-40%', '>40%'])
        category_counts = ascq_categories.value_counts().sort_index()
        axes[1].bar(range(len(category_counts)), category_counts.values)
        axes[1].set_xticks(range(len(category_counts)))
        axes[1].set_xticklabels(category_counts.index, rotation=45)
        axes[1].set_xlabel('ASCQ Category')
        axes[1].set_ylabel('Count')
        axes[1].set_title('ASCQ by Category')
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_temporal_admissions(self, pdf: PdfPages) -> None:
        """Plot temporal admission patterns."""
        if 'ano_entrada' not in self.df_main.columns:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Admissions by year
        yearly = self.df_main['ano_entrada'].value_counts().sort_index()
        axes[0, 0].bar(yearly.index, yearly.values)
        axes[0, 0].set_xlabel('Year')
        axes[0, 0].set_ylabel('Number of Admissions')
        axes[0, 0].set_title('Admissions by Year')
        
        # Admissions by month
        monthly = self.df_main['mes_entrada'].value_counts().sort_index()
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        axes[0, 1].bar(monthly.index, monthly.values)
        axes[0, 1].set_xticks(range(1, 13))
        axes[0, 1].set_xticklabels(month_names, rotation=45)
        axes[0, 1].set_xlabel('Month')
        axes[0, 1].set_ylabel('Number of Admissions')
        axes[0, 1].set_title('Admissions by Month (All Years)')
        
        # Admissions by quarter
        quarterly = self.df_main['trimestre_entrada'].value_counts().sort_index()
        axes[1, 0].bar(quarterly.index, quarterly.values)
        axes[1, 0].set_xlabel('Quarter')
        axes[1, 0].set_ylabel('Number of Admissions')
        axes[1, 0].set_title('Admissions by Quarter')
        
        # Timeline
        timeline = self.df_main.groupby(self.df_main['data_entrada'].dt.to_period('M')).size()
        timeline.index = timeline.index.to_timestamp()
        axes[1, 1].plot(timeline.index, timeline.values, marker='o')
        axes[1, 1].set_xlabel('Date')
        axes[1, 1].set_ylabel('Number of Admissions')
        axes[1, 1].set_title('Admission Timeline')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_burn_mechanisms(self, pdf: PdfPages) -> None:
        """Plot burn mechanisms and agents."""
        mechanisms = self.df_main['mecanismo_queimadura'].value_counts().head(10)
        agents = self.df_main['agente_queimadura'].value_counts().head(10)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Mechanisms
        axes[0].barh(range(len(mechanisms)), mechanisms.values)
        axes[0].set_yticks(range(len(mechanisms)))
        axes[0].set_yticklabels(mechanisms.index)
        axes[0].set_xlabel('Count')
        axes[0].set_title('Top 10 Burn Mechanisms')
        axes[0].invert_yaxis()
        
        # Agents
        axes[1].barh(range(len(agents)), agents.values)
        axes[1].set_yticks(range(len(agents)))
        axes[1].set_yticklabels(agents.index)
        axes[1].set_xlabel('Count')
        axes[1].set_title('Top 10 Burn Agents')
        axes[1].invert_yaxis()
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_anatomical_locations(self, pdf: PdfPages) -> None:
        """Plot anatomical locations."""
        if self.df_burns.empty:
            return
        
        locations = self.df_burns['local_anatomico'].value_counts()
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Bar chart
        axes[0].barh(range(len(locations)), locations.values)
        axes[0].set_yticks(range(len(locations)))
        axes[0].set_yticklabels(locations.index)
        axes[0].set_xlabel('Count')
        axes[0].set_title('Burns by Anatomical Location')
        axes[0].invert_yaxis()
        
        # Pie chart
        axes[1].pie(locations.values, labels=locations.index, autopct='%1.1f%%', startangle=90)
        axes[1].set_title('Burns by Anatomical Location (%)')
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_top_procedures(self, pdf: PdfPages) -> None:
        """Plot top procedures."""
        if self.df_procedures.empty:
            return
        
        procedures = self.df_procedures['nome_procedimento'].value_counts().head(15)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(range(len(procedures)), procedures.values)
        ax.set_yticks(range(len(procedures)))
        ax.set_yticklabels(procedures.index, fontsize=9)
        ax.set_xlabel('Count')
        ax.set_title('Top 15 Procedures')
        ax.invert_yaxis()
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_top_pathologies(self, pdf: PdfPages) -> None:
        """Plot top pathologies."""
        if self.df_pathologies.empty:
            return
        
        pathologies = self.df_pathologies['nome_patologia'].value_counts().head(20)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(range(len(pathologies)), pathologies.values)
        ax.set_yticks(range(len(pathologies)))
        ax.set_yticklabels(pathologies.index, fontsize=9)
        ax.set_xlabel('Count')
        ax.set_title('Top 20 Pre-existing Pathologies')
        ax.invert_yaxis()
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_top_medications(self, pdf: PdfPages) -> None:
        """Plot top medications."""
        if self.df_medications.empty:
            return
        
        medications = self.df_medications['nome_medicacao'].value_counts().head(20)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(range(len(medications)), medications.values)
        ax.set_yticks(range(len(medications)))
        ax.set_yticklabels(medications.index, fontsize=8)
        ax.set_xlabel('Count')
        ax.set_title('Top 20 Regular Medications')
        ax.invert_yaxis()
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_infections(self, pdf: PdfPages) -> None:
        """Plot infection data."""
        if self.df_infections.empty:
            return
        
        agents = self.df_infections['nome_agente'].value_counts().head(15)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(range(len(agents)), agents.values)
        ax.set_yticks(range(len(agents)))
        ax.set_yticklabels(agents.index, fontsize=9)
        ax.set_xlabel('Count')
        ax.set_title('Top 15 Infectious Agents')
        ax.invert_yaxis()
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_correlation_matrix(self, pdf: PdfPages) -> None:
        """Plot correlation matrix of numerical variables."""
        numerical_cols = [
            'idade_entrada', 'dias_internamento', 'ASCQ_total',
            'num_queimaduras', 'num_procedimentos', 'num_patologias',
            'num_medicacoes', 'VMI_dias'
        ]
        
        # Select only existing columns
        available_cols = [col for col in numerical_cols if col in self.df_main.columns]
        corr_data = self.df_main[available_cols].corr()
        
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, square=True, ax=ax, cbar_kws={'shrink': 0.8})
        ax.set_title('Correlation Matrix')
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def _plot_ascq_vs_stay(self, pdf: PdfPages) -> None:
        """Plot ASCQ vs length of stay."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        data = self.df_main[['ASCQ_total', 'dias_internamento']].dropna()
        ax.scatter(data['ASCQ_total'], data['dias_internamento'], alpha=0.5)
        ax.set_xlabel('ASCQ Total (%)')
        ax.set_ylabel('Length of Stay (days)')
        ax.set_title('ASCQ vs Length of Stay')
        
        # Add trend line
        z = np.polyfit(data['ASCQ_total'], data['dias_internamento'], 1)
        p = np.poly1d(z)
        ax.plot(data['ASCQ_total'].sort_values(), 
               p(data['ASCQ_total'].sort_values()), 
               "r--", alpha=0.8, label=f'Trend: y={z[0]:.2f}x+{z[1]:.2f}')
        ax.legend()
        
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
    def generate_text_report(self, stats: Dict[str, Any], 
                           procedures_analysis: Dict[str, Any],
                           pathologies_analysis: Dict[str, Any],
                           medications_analysis: Dict[str, Any],
                           infections_analysis: Dict[str, Any],
                           antibiotics_analysis: Dict[str, Any]) -> None:
        """Generate comprehensive text report."""
        
        console.print("\n[bold cyan]📄 Generating text report...[/bold cyan]")
        
        report_path = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE ANALYSIS OF BURN UNIT HOSPITALIZATIONS\n")
            f.write("UQ Database - Internamentos Collection\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Overall statistics
            f.write("OVERALL STATISTICS\n")
            f.write("-"*80 + "\n")
            f.write(f"Total Records: {stats['total_records']}\n")
            f.write(f"Date Range: {stats['date_range']['first_admission']} to {stats['date_range']['last_admission']}\n")
            f.write(f"Time Span: {(stats['date_range']['last_admission'] - stats['date_range']['first_admission']).days} days\n")
            f.write("\n")
            
            # Demographics
            f.write("DEMOGRAPHICS\n")
            f.write("-"*80 + "\n")
            f.write(f"Age at Admission:\n")
            f.write(f"  Mean: {stats['demographics']['age_mean']:.1f} years\n")
            f.write(f"  Median: {stats['demographics']['age_median']:.1f} years\n")
            f.write(f"  Std Dev: {stats['demographics']['age_std']:.1f} years\n")
            f.write(f"  Range: {stats['demographics']['age_min']:.1f} - {stats['demographics']['age_max']:.1f} years\n")
            f.write(f"\nSex Distribution:\n")
            for sex, count in stats['demographics']['sex_distribution'].items():
                pct = (count / stats['total_records']) * 100
                f.write(f"  {sex}: {count} ({pct:.1f}%)\n")
            f.write("\n")
            
            # Hospitalization
            f.write("HOSPITALIZATION STATISTICS\n")
            f.write("-"*80 + "\n")
            f.write(f"Length of Stay:\n")
            f.write(f"  Mean: {stats['hospitalization']['length_of_stay_mean']:.1f} days\n")
            f.write(f"  Median: {stats['hospitalization']['length_of_stay_median']:.1f} days\n")
            f.write(f"  Std Dev: {stats['hospitalization']['length_of_stay_std']:.1f} days\n")
            f.write(f"  Range: {stats['hospitalization']['length_of_stay_min']:.0f} - {stats['hospitalization']['length_of_stay_max']:.0f} days\n")
            f.write(f"\nTime from Burn to Admission:\n")
            f.write(f"  Mean: {stats['hospitalization']['time_to_admission_mean']:.1f} days\n")
            f.write(f"  Median: {stats['hospitalization']['time_to_admission_median']:.1f} days\n")
            f.write("\n")
            
            # Burn severity
            f.write("BURN SEVERITY\n")
            f.write("-"*80 + "\n")
            f.write(f"ASCQ (Total Burn Surface Area):\n")
            f.write(f"  Mean: {stats['burns']['ascq_mean']:.1f}%\n")
            f.write(f"  Median: {stats['burns']['ascq_median']:.1f}%\n")
            f.write(f"  Std Dev: {stats['burns']['ascq_std']:.1f}%\n")
            f.write(f"  Range: {stats['burns']['ascq_min']:.1f}% - {stats['burns']['ascq_max']:.1f}%\n")
            f.write(f"\nInhalation Injury:\n")
            for status, count in stats['burns']['inhalation_injury'].items():
                if status:
                    pct = (count / stats['total_records']) * 100
                    f.write(f"  {status}: {count} ({pct:.1f}%)\n")
            f.write(f"\nMean Burns per Patient: {stats['burns']['num_burns_mean']:.1f}\n")
            f.write("\n")
            
            # Clinical interventions
            f.write("CLINICAL INTERVENTIONS\n")
            f.write("-"*80 + "\n")
            f.write(f"Procedures:\n")
            f.write(f"  Mean per patient: {stats['clinical']['procedures_mean']:.1f}\n")
            f.write(f"  Median per patient: {stats['clinical']['procedures_median']:.1f}\n")
            f.write(f"  Total procedures: {len(self.df_procedures)}\n")
            f.write(f"\nPre-existing Conditions:\n")
            f.write(f"  Mean per patient: {stats['clinical']['pathologies_mean']:.1f}\n")
            f.write(f"  Total pathologies: {len(self.df_pathologies)}\n")
            f.write(f"\nMedications:\n")
            f.write(f"  Mean per patient: {stats['clinical']['medications_mean']:.1f}\n")
            f.write(f"  Total medications: {len(self.df_medications)}\n")
            f.write(f"\nInfections: {stats['clinical']['infections_total']}\n")
            f.write(f"Antibiotics: {stats['clinical']['antibiotics_total']}\n")
            f.write("\n")
            
            # Temporal patterns
            if 'temporal' in stats:
                f.write("TEMPORAL PATTERNS\n")
                f.write("-"*80 + "\n")
                f.write("Admissions by Year:\n")
                for year, count in sorted(stats['temporal']['admissions_by_year'].items()):
                    f.write(f"  {year}: {count}\n")
                f.write("\n")
            
            # Procedures
            if procedures_analysis:
                f.write("TOP PROCEDURES\n")
                f.write("-"*80 + "\n")
                for i, (proc, count) in enumerate(list(procedures_analysis['top_procedures'].items())[:20], 1):
                    f.write(f"{i:2d}. {proc}: {count}\n")
                f.write("\n")
            
            # Pathologies
            if pathologies_analysis:
                f.write("TOP PRE-EXISTING PATHOLOGIES\n")
                f.write("-"*80 + "\n")
                f.write(f"Patients with pathologies: {pathologies_analysis['patients_with_pathologies']}\n")
                f.write(f"Patients without: {pathologies_analysis['patients_without_pathologies']}\n\n")
                for i, (path, count) in enumerate(list(pathologies_analysis['top_pathologies'].items())[:30], 1):
                    f.write(f"{i:2d}. {path}: {count}\n")
                f.write("\n")
            
            # Medications
            if medications_analysis:
                f.write("TOP REGULAR MEDICATIONS\n")
                f.write("-"*80 + "\n")
                for i, (med, count) in enumerate(list(medications_analysis['top_medications'].items())[:30], 1):
                    f.write(f"{i:2d}. {med}: {count}\n")
                f.write("\n")
            
            # Infections
            if infections_analysis:
                f.write("INFECTIONS\n")
                f.write("-"*80 + "\n")
                f.write(f"Infection Rate: {infections_analysis['infection_rate']:.1f}%\n")
                f.write(f"Patients with infections: {infections_analysis['patients_with_infections']}\n\n")
                f.write("Top Infectious Agents:\n")
                for i, (agent, count) in enumerate(list(infections_analysis['top_agents'].items())[:20], 1):
                    f.write(f"{i:2d}. {agent}: {count}\n")
                f.write("\n")
            
            # Antibiotics
            if antibiotics_analysis:
                f.write("ANTIBIOTICS\n")
                f.write("-"*80 + "\n")
                f.write(f"Usage Rate: {antibiotics_analysis['usage_rate']:.1f}%\n")
                f.write(f"Patients using antibiotics: {antibiotics_analysis['patients_with_antibiotics']}\n\n")
                f.write("Top Antibiotics:\n")
                for i, (anti, count) in enumerate(list(antibiotics_analysis['top_antibiotics'].items())[:20], 1):
                    f.write(f"{i:2d}. {anti}: {count}\n")
                f.write("\n")
            
            # Quality issues
            f.write("DATA QUALITY ISSUES\n")
            f.write("-"*80 + "\n")
            if not self.quality_issues:
                f.write("No quality issues detected.\n")
            else:
                for issue in self.quality_issues:
                    f.write(f"Type: {issue['type']}\n")
                    f.write(f"Field: {issue['field']}\n")
                    f.write(f"Count: {issue['count']}\n")
                    if 'percentage' in issue:
                        f.write(f"Percentage: {issue['percentage']:.1f}%\n")
                    f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("END OF REPORT\n")
            f.write("="*80 + "\n")
        
        console.print(f"[green]✓ Text report saved: {report_path}[/green]")
    
    def export_to_csv(self) -> None:
        """Export all DataFrames to CSV for further analysis."""
        
        console.print("\n[bold cyan]💾 Exporting to CSV...[/bold cyan]")
        
        csv_dir = self.report_dir / "csv_exports"
        csv_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export main data
        main_csv = csv_dir / f"main_data_{timestamp}.csv"
        self.df_main.to_csv(main_csv, index=False, encoding='utf-8')
        console.print(f"  ✓ Main data: {main_csv}")
        
        # Export related data
        if not self.df_burns.empty:
            burns_csv = csv_dir / f"burns_{timestamp}.csv"
            self.df_burns.to_csv(burns_csv, index=False, encoding='utf-8')
            console.print(f"  ✓ Burns: {burns_csv}")
        
        if not self.df_procedures.empty:
            proc_csv = csv_dir / f"procedures_{timestamp}.csv"
            self.df_procedures.to_csv(proc_csv, index=False, encoding='utf-8')
            console.print(f"  ✓ Procedures: {proc_csv}")
        
        if not self.df_pathologies.empty:
            path_csv = csv_dir / f"pathologies_{timestamp}.csv"
            self.df_pathologies.to_csv(path_csv, index=False, encoding='utf-8')
            console.print(f"  ✓ Pathologies: {path_csv}")
        
        if not self.df_medications.empty:
            med_csv = csv_dir / f"medications_{timestamp}.csv"
            self.df_medications.to_csv(med_csv, index=False, encoding='utf-8')
            console.print(f"  ✓ Medications: {med_csv}")
        
        if not self.df_infections.empty:
            inf_csv = csv_dir / f"infections_{timestamp}.csv"
            self.df_infections.to_csv(inf_csv, index=False, encoding='utf-8')
            console.print(f"  ✓ Infections: {inf_csv}")
        
        if not self.df_antibiotics.empty:
            anti_csv = csv_dir / f"antibiotics_{timestamp}.csv"
            self.df_antibiotics.to_csv(anti_csv, index=False, encoding='utf-8')
            console.print(f"  ✓ Antibiotics: {anti_csv}")
        
        console.print("[green]✓ CSV export complete[/green]")
    
    def run_complete_analysis(self) -> None:
        """Run complete analysis pipeline."""
        
        console.print(Panel.fit(
            "[bold cyan]🏥 Comprehensive Burn Unit Analysis[/bold cyan]\n"
            "[dim]UQ Database - Internamentos Collection[/dim]",
            border_style="cyan"
        ))
        
        # 1. Extract data
        self.extract_data_from_mongodb()
        
        if self.df_main is None or self.df_main.empty:
            console.print("[red]No data to analyze![/red]")
            return
        
        # 2. Convert dates
        self.convert_dates()
        
        # 3. Quality checks
        self.perform_quality_checks()
        
        # 4. Generate statistics
        stats = self.generate_descriptive_statistics()
        
        # 5. Analyze specific aspects
        self.analyze_burn_mechanisms()
        self.analyze_anatomical_locations()
        procedures_analysis = self.analyze_procedures()
        pathologies_analysis = self.analyze_pathologies()
        medications_analysis = self.analyze_medications()
        infections_analysis = self.analyze_infections()
        antibiotics_analysis = self.analyze_antibiotics()
        
        # 6. Create visualizations
        self.create_visualizations(stats)
        
        # 7. Generate text report
        self.generate_text_report(
            stats, 
            procedures_analysis,
            pathologies_analysis,
            medications_analysis,
            infections_analysis,
            antibiotics_analysis
        )
        
        # 8. Export to CSV
        self.export_to_csv()
        
        # Final summary
        console.print("\n" + "="*80)
        console.print(Panel(
            f"[bold green]✓ Analysis Complete![/bold green]\n\n"
            f"[cyan]Reports Directory:[/cyan] {self.report_dir}\n"
            f"[cyan]Total Records Analyzed:[/cyan] {len(self.df_main)}\n"
            f"[cyan]Quality Issues Found:[/cyan] {len(self.quality_issues)}\n\n"
            f"[yellow]Generated:[/yellow]\n"
            f"  • Comprehensive text report\n"
            f"  • PDF visualizations\n"
            f"  • CSV exports for further analysis",
            title="📊 Analysis Summary",
            border_style="green"
        ))


def main():
    """Main execution function."""
    
    # Connect to database
    db_manager = MongoDBManager()
    
    if not db_manager.connect():
        console.print("[red]Failed to connect to database![/red]")
        return
    
    try:
        # Create analyzer
        analyzer = InternamentosAnalyzer(db_manager)
        
        # Run complete analysis
        analyzer.run_complete_analysis()
        
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    main()
