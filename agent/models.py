# pydantic models for structured output with google-genai sdk
"""
Pydantic models for extracting structured data from cleaned medical records.
These models map to the database schema at /home/gusmmm/Desktop/mydb/src/schemas/schemas.py

The extraction process:
1. Parse cleaned markdown files with patient medical records
2. Use AI (google-genai) to extract structured data into these models
3. Serialize to JSON for review
4. Populate SQLite database using the database schemas

Author: Agent
Date: 2024-01-26
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# ============================================================================
# ENUMS - Match database schema exactly
# ============================================================================

class SexoEnum(str, Enum):
    """Patient sex/gender"""
    M = 'M'
    F = 'F'


class LocalAnatomicoEnum(str, Enum):
    """Anatomical location for burns - be as specific as possible"""
    HEAD = 'HEAD'  # Cabeça (excluding face)
    FACE = 'FACE'  # Face
    CERVICAL = 'CERVICAL'  # Pescoço/cervical region
    CHEST = 'CHEST'  # Tórax/peito
    ABDOMEN = 'ABDOMEN'  # Abdómen
    BACK = 'BACK'  # Costas/dorso
    PERINEUM = 'PERINEUM'  # Períneo/genitais
    UPPER_LIMB = 'UPPER_LIMB'  # Membro superior (arm excluding hand)
    LOWER_LIMB = 'LOWER_LIMB'  # Membro inferior (leg excluding foot)
    HAND = 'HAND'  # Mão
    FOOT = 'FOOT'  # Pé


class GrauMaximoEnum(str, Enum):
    """
    Maximum burn degree (grau máximo de queimadura).
    
    Clinical classification:
    - PRIMEIRO: Superficial, epidermis only (eritema)
    - SEGUNDO_SUPERFICIAL: Superficial partial thickness (papillary dermis, blisters)
    - SEGUNDO_PROFUNDO: Deep partial thickness (reticular dermis, may need grafting)
    - TERCEIRO: Full thickness (entire dermis destroyed, requires grafting)
    - QUARTO: Extension to muscle, tendon, bone (requires debridement/amputation)
    """
    PRIMEIRO = 'PRIMEIRO'
    SEGUNDO_SUPERFICIAL = 'SEGUNDO_SUPERFICIAL'
    SEGUNDO_PROFUNDO = 'SEGUNDO_PROFUNDO'
    TERCEIRO = 'TERCEIRO'
    QUARTO = 'QUARTO'
    
    # Aliases for compatibility and AI extraction
    SEGUNDO = 'SEGUNDO_PROFUNDO'  # Default to deep when not specified


class LesaoInalatoriaEnum(str, Enum):
    """Inhalation injury status"""
    SIM = 'SIM'
    NAO = 'NAO'
    SUSPEITA = 'SUSPEITA'


class IntubacaoOTEnum(str, Enum):
    """Orotracheal intubation status"""
    SIM = 'SIM'
    NAO = 'NAO'
    JA_VINHA_INTUBADO = 'JA_VINHA_INTUBADO'


class BurnMechanismEnum(str, Enum):
    """
    Burn mechanism classification - detailed for epidemiological analysis.
    
    Categories:
    - THERMAL: Heat transfer injuries (most common)
    - ELECTRICAL: Electrical current injuries
    - CHEMICAL: Chemical agent injuries
    - RADIATION: Radiation exposure
    - INHALATION: Respiratory tract burns
    """
    # Thermal mechanisms
    THERMAL_FLAME = 'THERMAL_FLAME'  # Chama, fogo direto
    THERMAL_SCALD = 'THERMAL_SCALD'  # Escaldadura (líquidos quentes)
    THERMAL_CONTACT = 'THERMAL_CONTACT'  # Contacto (superfícies quentes)
    THERMAL_STEAM = 'THERMAL_STEAM'  # Vapor
    THERMAL_FLASH = 'THERMAL_FLASH'  # Flash (explosão rápida)
    
    # Electrical mechanisms
    ELECTRICAL_HIGH_VOLTAGE = 'ELECTRICAL_HIGH_VOLTAGE'  # Alta tensão (>1000V)
    ELECTRICAL_LOW_VOLTAGE = 'ELECTRICAL_LOW_VOLTAGE'  # Baixa tensão (<1000V)
    ELECTRICAL_LIGHTNING = 'ELECTRICAL_LIGHTNING'  # Raio
    
    # Chemical mechanisms
    CHEMICAL_ACID = 'CHEMICAL_ACID'  # Ácido
    CHEMICAL_ALKALI = 'CHEMICAL_ALKALI'  # Álcali/base
    CHEMICAL_ORGANIC = 'CHEMICAL_ORGANIC'  # Composto orgânico
    
    # Radiation mechanisms
    RADIATION_SOLAR = 'RADIATION_SOLAR'  # Solar/UV
    RADIATION_IONIZING = 'RADIATION_IONIZING'  # Radiação ionizante
    
    # Inhalation
    INHALATION = 'INHALATION'  # Lesão inalatória
    
    # Other/Unknown
    OTHER = 'OTHER'
    UNKNOWN = 'UNKNOWN'


class BurnAgentEnum(str, Enum):
    """
    Specific burn agent classification for detailed epidemiology.
    
    Common agents in Portuguese burn units.
    """
    # Hot liquids (escaldadura)
    AGUA_QUENTE = 'AGUA_QUENTE'  # Hot water
    OLEO_QUENTE = 'OLEO_QUENTE'  # Hot oil
    SOPA = 'SOPA'  # Soup
    LEITE = 'LEITE'  # Milk
    CAFE_CHA = 'CAFE_CHA'  # Coffee/tea
    
    # Flames (chama)
    FOGO_DIRETO = 'FOGO_DIRETO'  # Direct fire
    GASOLINA = 'GASOLINA'  # Gasoline
    ALCOOL = 'ALCOOL'  # Alcohol
    GAS = 'GAS'  # Gas
    INCENDIO = 'INCENDIO'  # Building fire
    EXPLOSAO = 'EXPLOSAO'  # Explosion
    
    # Contact (contacto)
    FERRO_ENGOMAR = 'FERRO_ENGOMAR'  # Iron
    FOGAO = 'FOGAO'  # Stove
    FORNO = 'FORNO'  # Oven
    ESCAPE_MOTO = 'ESCAPE_MOTO'  # Motorcycle exhaust
    METAL_QUENTE = 'METAL_QUENTE'  # Hot metal
    PLASTICO_DERRETIDO = 'PLASTICO_DERRETIDO'  # Melted plastic
    
    # Steam
    VAPOR = 'VAPOR'  # Steam
    
    # Electrical
    CORRENTE_ELETRICA = 'CORRENTE_ELETRICA'  # Electrical current
    RAIO = 'RAIO'  # Lightning
    
    # Chemical
    ACIDO = 'ACIDO'  # Acid
    SODA_CAUSTICA = 'SODA_CAUSTICA'  # Caustic soda
    LIXIVIA = 'LIXIVIA'  # Bleach
    CAL = 'CAL'  # Lime
    
    # Other
    SOL = 'SOL'  # Sun
    OTHER = 'OTHER'
    UNKNOWN = 'UNKNOWN'


class AccidentTypeEnum(str, Enum):
    """
    Accident context/setting classification.
    """
    DOMESTICO = 'DOMESTICO'  # Home accident
    TRABALHO = 'TRABALHO'  # Work-related
    LAZER = 'LAZER'  # Leisure/recreational
    TRAFEGO = 'TRAFEGO'  # Traffic accident
    DESPORTIVO = 'DESPORTIVO'  # Sports-related
    VIOLENCIA_DOMESTICA = 'VIOLENCIA_DOMESTICA'  # Domestic violence
    AGRESSAO = 'AGRESSAO'  # Assault
    AUTOINFLIGIDO = 'AUTOINFLIGIDO'  # Self-inflicted
    INCENDIO_ESTRUTURAL = 'INCENDIO_ESTRUTURAL'  # Structural fire
    INCENDIO_FLORESTAL = 'INCENDIO_FLORESTAL'  # Forest fire
    OTHER = 'OTHER'
    UNKNOWN = 'UNKNOWN'


class ContextoViolentoEnum(str, Enum):
    """Violent context classification"""
    VIOLENCIA_DOMESTICA = 'VIOLENCIA_DOMESTICA'
    AGRESSAO = 'AGRESSAO'
    OUTRO = 'OUTRO'
    NAO = 'NAO'


# ============================================================================
# CORE PATIENT MODEL
# ============================================================================

class Doente(BaseModel):
    """
    Patient (Doente) information
    Maps to: DoenteCreate schema
    """
    nome: str = Field(description="Full patient name")
    numero_processo: int = Field(description="Process/medical record number (subject ID)")
    data_nascimento: str = Field(
        description="Birth date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    sexo: SexoEnum = Field(description="Patient sex (M/F)")
    morada: str = Field(description="Full address")
    
    # Source validation fields
    source_text_nome: Optional[str] = Field(default=None, description="Source text where name was found")
    source_text_nascimento: Optional[str] = Field(default=None, description="Source text where birth date was found")
    source_text_morada: Optional[str] = Field(default=None, description="Source text where address was found")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )
    
    @field_validator('data_nascimento')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in correct format"""
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD")


# ============================================================================
# HOSPITALIZATION/ADMISSION MODEL
# ============================================================================

class Internamento(BaseModel):
    """
    Hospitalization/admission (Internamento) record
    Maps to: InternamentoPatch schema (most complete)
    """
    numero_internamento: int = Field(description="Admission number")
    
    # Dates
    data_entrada: str = Field(
        description="Admission date (YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    data_alta: Optional[str] = Field(
        default=None,
        description="Discharge date (YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    data_queimadura: Optional[str] = Field(
        default=None,
        description="Burn date (YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    
    # Origin and destination (as text descriptions instead of IDs)
    origem_entrada: Optional[str] = Field(default=None, description="Origin location description (e.g., 'Hospital de Viana do Castelo')")
    destino_alta: Optional[str] = Field(default=None, description="Discharge destination description (e.g., 'Consulta Externa', 'Domicílio')")
    
    # Burn specifics
    ASCQ_total: Optional[float] = Field(
        default=None,
        description="Total ASCQ (Área de Superfície Corporal Queimada) percentage - use decimal for precision (e.g., 8.5)"
    )
    lesao_inalatoria: Optional[str] = Field(
        default=None,
        description="Inhalation injury (SIM/NAO/SUSPEITA)"
    )
    
    # Mechanism and agent - now using enums for better classification
    mecanismo_queimadura: Optional[str] = Field(
        default=None, 
        description="Burn mechanism from BurnMechanismEnum (e.g., 'THERMAL_SCALD', 'THERMAL_FLAME', 'THERMAL_CONTACT'). If not clear, use text description."
    )
    agente_queimadura: Optional[str] = Field(
        default=None, 
        description="Burn agent from BurnAgentEnum (e.g., 'AGUA_QUENTE', 'OLEO_QUENTE', 'FOGO_DIRETO'). If not in enum, use text description."
    )
    tipo_acidente: Optional[str] = Field(
        default=None, 
        description="Accident type from AccidentTypeEnum (e.g., 'DOMESTICO', 'TRABALHO', 'LAZER'). If not clear, use text description."
    )
    
    # Contextual flags
    incendio_florestal: Optional[bool] = Field(default=None, description="Forest fire involved")
    contexto_violento: Optional[str] = Field(default=None, description="Violent context type")
    suicidio_tentativa: Optional[bool] = Field(default=None, description="Suicide attempt")
    fogueira_queda: Optional[bool] = Field(default=None, description="Bonfire fall")
    lareira_queda: Optional[bool] = Field(default=None, description="Fireplace fall")
    
    # Treatment specifics
    escarotomias_entrada: Optional[bool] = Field(
        default=None,
        description="Escharotomies on admission"
    )
    intubacao_OT: Optional[str] = Field(
        default=None,
        description="Orotracheal intubation status"
    )
    VMI_dias: Optional[int] = Field(
        default=None,
        description="Mechanical ventilation days"
    )
    VNI: Optional[bool] = Field(default=None, description="Non-invasive ventilation")
    
    # Source validation fields
    source_text_dates: Optional[str] = Field(default=None, description="Source text where dates were found")
    source_text_origem: Optional[str] = Field(default=None, description="Source text for origin")
    source_text_destino: Optional[str] = Field(default=None, description="Source text for destination")
    source_text_ascq: Optional[str] = Field(default=None, description="Source text for ASCQ calculation")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )
    
    @field_validator('data_entrada', 'data_alta', 'data_queimadura')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        """Validate date formats"""
        if v is None:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD")


# ============================================================================
# REFERENCE DATA MODELS (lookup tables)
# ============================================================================

class TipoAcidente(BaseModel):
    """Accident type classification"""
    acidente: str = Field(description="Accident category")
    tipo_acidente: str = Field(description="Specific accident type")


class AgenteQueimadura(BaseModel):
    """Burn agent (causative agent)"""
    agente_queimadura: str = Field(description="Burn agent name")
    nota: str = Field(description="Additional notes")


class MecanismoQueimadura(BaseModel):
    """Burn mechanism"""
    mecanismo_queimadura: str = Field(description="Burn mechanism description")
    nota: str = Field(description="Additional notes")


class OrigemDestino(BaseModel):
    """Origin/destination location"""
    local: str = Field(description="Location name")
    int_ext: str = Field(description="Internal/External classification")
    descricao: str = Field(description="Location description")


class LocalAnatomico(BaseModel):
    """Anatomical location"""
    local_anatomico: str = Field(description="Anatomical location name")
    regiao_anatomica: Optional[str] = Field(default=None, description="Anatomical region")


# ============================================================================
# BURN-SPECIFIC MODELS
# ============================================================================

class Queimadura(BaseModel):
    """
    Individual burn (Queimadura) record
    Represents a burn at a specific anatomical location
    
    IMPORTANT: Be as SPECIFIC as possible with anatomical locations AND burn depth:
    
    ANATOMICAL SPECIFICITY:
    - If burn affects HAND specifically, create a HAND entry
    - If burn affects rest of upper limb, create separate UPPER_LIMB entry
    - If burn affects FOOT specifically, create a FOOT entry
    - If burn affects rest of lower limb, create separate LOWER_LIMB entry
    - Do NOT group hand/foot with limbs - create separate entries
    - Create one entry per distinct anatomical region mentioned
    
    BURN DEPTH SPECIFICITY:
    - "2º grau superficial" → SEGUNDO_SUPERFICIAL
    - "2º grau profundo" → SEGUNDO_PROFUNDO
    - "2º grau" (unspecified) → SEGUNDO_PROFUNDO (default to deep)
    - "3º grau" → TERCEIRO
    - "1º grau" → PRIMEIRO
    - "4º grau" → QUARTO
    - If multiple depths mentioned in same area, use MAXIMUM depth
    
    PERCENTAGE:
    - Extract if mentioned for this specific location
    - Use decimal precision (e.g., 8.5, 12.3)
    - If range given (e.g., "6-8%"), use middle value or note in 'notas'
    """
    local_anatomico: LocalAnatomicoEnum = Field(
        description="Anatomical location (use enum: HEAD, FACE, CERVICAL, CHEST, ABDOMEN, BACK, PERINEUM, UPPER_LIMB, LOWER_LIMB, HAND, FOOT)"
    )
    grau_maximo: Optional[GrauMaximoEnum] = Field(
        default=None, 
        description="Maximum burn degree - be specific: PRIMEIRO, SEGUNDO_SUPERFICIAL, SEGUNDO_PROFUNDO, TERCEIRO, QUARTO"
    )
    percentagem: Optional[float] = Field(
        default=None, 
        description="Percentage of body surface for this location (use decimal precision, e.g., 8.5)"
    )
    lateralidade: Optional[str] = Field(
        default=None,
        description="Laterality: 'direita', 'esquerda', 'bilateral', None if not specified or midline"
    )
    circunferencial: Optional[bool] = Field(
        default=None,
        description="True if burn is described as circumferential/circular around limb or body part"
    )
    notas: Optional[str] = Field(
        default=None, 
        description="Additional clinical details: depth variation, specific areas (e.g., 'dorso da mão', 'face anterior'), special features"
    )
    
    # Source validation
    source_text: str = Field(
        description="Exact phrase from medical record describing this burn (for human validation)"
    )
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


# ============================================================================
# TRAUMA MODELS
# ============================================================================

class TraumaTipo(BaseModel):
    """Trauma type and location"""
    local: str = Field(description="Trauma location")
    tipo: str = Field(description="Trauma type")


class Trauma(BaseModel):
    """
    Trauma record associated with hospitalization
    """
    tipo: str = Field(description="Trauma type (e.g., 'fratura', 'contusão', 'laceração')")
    local: str = Field(description="Trauma location description")
    cirurgia_urgente: Optional[bool] = Field(default=None, description="Emergency surgery required")
    
    # Source validation
    source_text: str = Field(description="Source text describing this trauma")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


# ============================================================================
# INFECTION MODELS
# ============================================================================

class AgenteInfeccioso(BaseModel):
    """Infectious agent"""
    nome: str = Field(description="Agent name")
    tipo_agente: str = Field(description="Agent type")
    codigo_snomedct: Optional[str] = Field(default=None, description="SNOMED CT code")
    subtipo_agent: Optional[str] = Field(default=None, description="Agent subtype")


class TipoInfecao(BaseModel):
    """Infection type and location"""
    tipo_infeccao: str = Field(description="Infection type")
    local: str = Field(description="Infection location")


class Infecao(BaseModel):
    """
    Infection record
    """
    agente: Optional[str] = Field(default=None, description="Infectious agent name (e.g., 'Staphylococcus aureus', 'Pseudomonas')")
    tipo_agente: Optional[str] = Field(default=None, description="Agent type (e.g., 'bacteria', 'fungos', 'virus')")
    local: Optional[str] = Field(default=None, description="Infection location")
    tipo_infecao: Optional[str] = Field(default=None, description="Infection type (e.g., 'bacteriemia', 'pneumonia', 'ferida')")
    nota: Optional[str] = Field(default=None, description="Additional notes")
    
    # Source validation
    source_text: str = Field(description="Source text describing this infection")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


# ============================================================================
# ANTIBIOTIC MODELS
# ============================================================================

class Antibiotico(BaseModel):
    """Antibiotic medication"""
    nome_antibiotico: str = Field(description="Antibiotic name")
    classe_antibiotico: Optional[str] = Field(default=None, description="Antibiotic class")
    codigo: Optional[str] = Field(default=None, description="Medication code")


class IndicacaoAntibiotico(BaseModel):
    """Antibiotic indication/reason"""
    indicacao: str = Field(description="Indication for antibiotic use")


class InternamentoAntibiotico(BaseModel):
    """
    Antibiotic prescribed during hospitalization
    """
    nome_antibiotico: str = Field(description="Antibiotic name")
    classe_antibiotico: Optional[str] = Field(default=None, description="Antibiotic class")
    indicacao: Optional[str] = Field(default=None, description="Indication/reason for use")
    
    # Source validation
    source_text: str = Field(description="Source text mentioning this antibiotic")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


# ============================================================================
# PROCEDURE MODELS
# ============================================================================

class Procedimento(BaseModel):
    """Medical procedure"""
    nome_procedimento: str = Field(description="Procedure name")
    tipo_procedimento: Optional[str] = Field(default=None, description="Procedure type")


class InternamentoProcedimento(BaseModel):
    """
    Procedure performed during hospitalization
    """
    nome_procedimento: str = Field(description="Procedure name")
    tipo_procedimento: Optional[str] = Field(default=None, description="Procedure type (e.g., 'cirúrgico', 'diagnóstico')")
    data_procedimento: Optional[str] = Field(default=None, description="Date when procedure was performed (YYYY-MM-DD)")
    
    # Source validation
    source_text: str = Field(description="Source text describing this procedure")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


# ============================================================================
# PATIENT HISTORY MODELS (pre-existing conditions)
# ============================================================================

class Patologia(BaseModel):
    """Pathology/condition"""
    nome_patologia: str = Field(description="Pathology name")
    classe_patologia: Optional[str] = Field(default=None, description="Pathology class")
    codigo: Optional[str] = Field(default=None, description="Disease code")


class DoentePatologia(BaseModel):
    """
    Patient's pre-existing pathology
    """
    nome_patologia: str = Field(description="Pathology name (e.g., 'HTA', 'Diabetes Mellitus', 'DPOC')")
    classe_patologia: Optional[str] = Field(default=None, description="Pathology class (e.g., 'cardiovascular', 'endócrina', 'respiratória')")
    nota: Optional[str] = Field(default=None, description="Additional notes")
    
    # Source validation
    source_text: str = Field(description="Source text where this pathology was mentioned (usually in AP section)")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


class Medicacao(BaseModel):
    """Medication"""
    nome_medicacao: str = Field(description="Medication name")
    classe_terapeutica: Optional[str] = Field(default=None, description="Therapeutic class")
    codigo: Optional[str] = Field(default=None, description="Medication code")


class DoenteMedicacao(BaseModel):
    """
    Patient's regular medication (pre-admission)
    """
    nome_medicacao: str = Field(description="Medication name")
    classe_terapeutica: Optional[str] = Field(default=None, description="Therapeutic class")
    dosagem: Optional[str] = Field(default=None, description="Dosage (e.g., '1000 mg', '2.5 mg')")
    posologia: Optional[str] = Field(default=None, description="Posology/schedule (e.g., '1+0+1', '2x/dia')")
    nota: Optional[str] = Field(default=None, description="Additional notes")
    
    # Source validation
    source_text: str = Field(description="Source text where this medication was mentioned (usually in MH section)")
    
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp of record creation"
    )


# ============================================================================
# AGGREGATE MODEL - Complete Medical Record
# ============================================================================

class MedicalRecordExtraction(BaseModel):
    """
    Complete medical record extraction from a cleaned markdown file.
    This is the top-level model that aggregates all extracted information.
    
    Usage:
        1. AI agent parses markdown file
        2. Extracts data into this structured model
        3. Validates all fields
        4. Serializes to JSON
        5. Populates database tables
    """
    # Core patient info
    doente: Doente = Field(description="Patient information")
    
    # Hospitalization record
    internamento: Internamento = Field(description="Hospitalization record")
    
    # Burns (can have multiple burns at different locations)
    queimaduras: List[Queimadura] = Field(
        default_factory=list,
        description="List of burns by anatomical location"
    )
    
    # Traumas (if any)
    traumas: List[Trauma] = Field(
        default_factory=list,
        description="List of trauma records"
    )
    
    # Infections (if any)
    infecoes: List[Infecao] = Field(
        default_factory=list,
        description="List of infections"
    )
    
    # Antibiotics during hospitalization
    antibioticos: List[InternamentoAntibiotico] = Field(
        default_factory=list,
        description="Antibiotics administered during stay"
    )
    
    # Procedures performed
    procedimentos: List[InternamentoProcedimento] = Field(
        default_factory=list,
        description="Procedures performed during stay"
    )
    
    # Pre-existing conditions
    patologias: List[DoentePatologia] = Field(
        default_factory=list,
        description="Patient's pre-existing pathologies"
    )
    
    # Regular medications (before admission)
    medicacoes: List[DoenteMedicacao] = Field(
        default_factory=list,
        description="Patient's regular medications"
    )
    
    # Metadata
    source_file: str = Field(description="Source markdown filename")
    extraction_date: str = Field(description="Extraction timestamp (ISO format)")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "doente": {
                    "nome": "Maria Goreti Pereira",
                    "numero_processo": 2401,
                    "data_nascimento": "1966-01-15",
                    "sexo": "F",
                    "morada": "Rua Example, 123, Lisboa"
                },
                "internamento": {
                    "numero_internamento": 2401,
                    "data_entrada": "2024-01-15",
                    "data_alta": "2024-02-20",
                    "ASCQ_total": 45,
                    "lesao_inalatoria": "NAO"
                },
                "queimaduras": [
                    {
                        "local_anatomico": 1,
                        "grau_maximo": "TERCEIRO",
                        "notas": "Face and neck burns"
                    }
                ],
                "source_file": "2401_merged_medical_records.cleaned.md",
                "extraction_date": "2024-01-26T10:30:00"
            }
        }