# MongoDB Database Structure - UQ (Unidade de Queimados)

## Overview

The UQ database uses an **embedded document structure** optimized for low read/write operations. The main collection is `internamentos` (admissions), with all related data embedded within each admission document.

## Design Decisions

### Why Embedded Documents?

✅ **Low Read/Write Operations**: Your requirement indicates infrequent database access  
✅ **Atomic Operations**: All data for an admission updated together  
✅ **Simplified Queries**: No joins required - single query gets complete admission  
✅ **Better Performance**: Fewer round trips to database  
✅ **Natural Document Structure**: Medical records are naturally hierarchical  

### Main Unit: Internamento (Admission)

Each MongoDB document represents **one admission** to the burn unit with all associated data embedded.

## Database Schema

### Collection: `internamentos`

```javascript
{
  _id: ObjectId,  // Auto-generated MongoDB ID
  
  // MAIN ADMISSION DATA
  internamento: {
    numero_internamento: 2401,  // Unique admission number
    data_entrada: "2023-12-31",  // Admission date
    data_alta: "2024-01-26",     // Discharge date
    data_queimadura: null,        // Burn date (if different)
    
    // Origin and destination
    origem_entrada: "Hospital de Viana do Castelo",
    destino_alta: "Consulta Externa - Cex Cir.Plastica",
    
    // Burn specifics
    ASCQ_total: 15,  // Total burn surface area %
    lesao_inalatoria: "NAO",  // Inhalation injury
    mecanismo_queimadura: "liquido quente",
    agente_queimadura: "liquido quente",
    tipo_acidente: null,
    
    // Contextual flags
    incendio_florestal: false,
    contexto_violento: null,
    suicidio_tentativa: false,
    fogueira_queda: false,
    lareira_queda: false,
    
    // Treatment
    escarotomias_entrada: false,
    intubacao_OT: "NAO",
    VMI_dias: null,
    VNI: false,
    
    // Source text for validation
    source_text_dates: "Internado em: 31 Dezembro 2023...",
    source_text_origem: "Transferida do Hospital...",
    source_text_destino: "CONSULTA EXTERNA...",
    source_text_ascq: "SCQ 15%",
    
    created_at: "2024-07-28T12:00:00Z"
  },
  
  // PATIENT DATA (EMBEDDED)
  doente: {
    nome: "Maria Goreti Pereira De Passos Araujo",
    numero_processo: 23056175,  // Patient process number
    data_nascimento: "1966-01-21",
    sexo: "F",
    morada: "Rua Da Telhada N. 290 Cepões...",
    
    // Source validation
    source_text_nome: "Maria Goreti...",
    source_text_nascimento: "Feminino Data Nasc: 1966-01-21...",
    source_text_morada: "Rua Da Telhada...",
    created_at: "2024-07-28T12:00:00Z",
    
    // EMBEDDED PRE-EXISTING CONDITIONS
    patologias: [
      {
        nome_patologia: "HTA",
        classe_patologia: "cardiovascular",
        nota: null,
        source_text: "HTA;",
        created_at: "2024-07-28T12:00:00Z"
      },
      {
        nome_patologia: "DM tipo 2 não controlada",
        classe_patologia: "endócrina",
        nota: "Incumprimento terapêutico...",
        source_text: "DM tipo 2...",
        created_at: "2024-07-28T12:00:00Z"
      }
    ],
    
    // EMBEDDED REGULAR MEDICATIONS (PRE-ADMISSION)
    medicacoes: [
      {
        nome_medicacao: "Metformina",
        classe_terapeutica: "anti-diabética oral",
        dosagem: "1000 mg",
        posologia: "0+1+0",
        nota: null,
        source_text: "Metformina 1000 mg 0+1+0",
        created_at: "2024-07-28T12:00:00Z"
      }
    ]
  },
  
  // BURNS (EMBEDDED ARRAY)
  queimaduras: [
    {
      local_anatomico: "FACE",  // Enum: HEAD, FACE, CERVICAL, CHEST, etc.
      grau_maximo: "SEGUNDO",   // Enum: PRIMEIRO, SEGUNDO, TERCEIRO, QUARTO
      percentagem: 4.5,
      notas: null,
      source_text: "Queimadura 2º grau face...",
      created_at: "2024-07-28T12:00:00Z"
    },
    {
      local_anatomico: "UPPER_LIMB",
      grau_maximo: "SEGUNDO",
      percentagem: 8.5,
      notas: "circular",
      source_text: "Queimadura 2º grau circular...",
      created_at: "2024-07-28T12:00:00Z"
    }
  ],
  
  // PROCEDURES (EMBEDDED ARRAY)
  procedimentos: [
    {
      nome_procedimento: "Desbridamento queimadura...",
      tipo_procedimento: "cirúrgico",
      data_procedimento: "2024-01-11",
      source_text: "Submetida a intervenção...",
      created_at: "2024-07-28T12:00:00Z"
    }
  ],
  
  // ANTIBIOTICS DURING ADMISSION (EMBEDDED ARRAY)
  antibioticos: [
    {
      nome_antibiotico: "Vancomicina",
      classe_antibiotico: "glicopeptídeo",
      indicacao: "profilaxia cirúrgica",
      source_text: "Iniciou Vancomicina...",
      created_at: "2024-07-28T12:00:00Z"
    }
  ],
  
  // INFECTIONS (EMBEDDED ARRAY)
  infecoes: [
    {
      agente: "Staphylococcus aureus",
      tipo_agente: "bacteria",
      local: "ferida operatória",
      tipo_infecao: "infecção de ferida",
      nota: "MRSA positivo",
      source_text: "Cultura positiva para MRSA...",
      created_at: "2024-07-28T12:00:00Z"
    }
  ],
  
  // TRAUMAS (EMBEDDED ARRAY)
  traumas: [
    {
      tipo: "fratura",
      local: "úmero direito",
      cirurgia_urgente: true,
      source_text: "Fratura de úmero...",
      created_at: "2024-07-28T12:00:00Z"
    }
  ],
  
  // METADATA
  source_file: "2401_merged_medical_records.cleaned.md",
  extraction_date: "2025-10-08T18:29:44.204320",
  import_date: "2025-10-10T14:33:33.829114",
  
  // COMPUTED FIELDS (for easier querying)
  ano_internamento: 2023,
  tem_queimaduras: true,
  tem_procedimentos: true,
  tem_infecoes: false
}
```

## Relationships

### One Patient, Multiple Admissions

The same patient (identified by `doente.numero_processo`) can have multiple admission documents:

```javascript
// Admission 1 (2023)
{
  internamento: { numero_internamento: 2401, data_entrada: "2023-12-31" },
  doente: { numero_processo: 23056175, nome: "Maria Goreti..." },
  // ... other data
}

// Admission 2 (2024)
{
  internamento: { numero_internamento: 2498, data_entrada: "2024-06-15" },
  doente: { numero_processo: 23056175, nome: "Maria Goreti..." },  // Same patient
  // ... other data
}
```

Query to get all admissions for a patient:
```javascript
db.internamentos.find({ "doente.numero_processo": 23056175 })
  .sort({ "internamento.data_entrada": -1 })
```

## Indexes

For optimal query performance, the following indexes are created:

1. **`idx_numero_internamento`** (UNIQUE): `internamento.numero_internamento`
   - Ensures each admission number is unique
   - Fast lookup by admission number

2. **`idx_patient_processo`**: `doente.numero_processo`
   - Find all admissions for a specific patient
   - Used frequently for patient history queries

3. **`idx_data_entrada`**: `internamento.data_entrada` (DESC)
   - Chronological queries
   - Recent admissions first

4. **`idx_patient_name`**: `doente.nome`
   - Search patients by name
   - Text search support

5. **`idx_patient_date`** (COMPOUND): `doente.numero_processo` + `internamento.data_entrada`
   - Combined patient + date queries
   - Optimized for patient timeline

6. **`idx_source_file`**: `source_file`
   - Track which files have been imported
   - Avoid duplicate imports

7. **`idx_extraction_date`**: `extraction_date` (DESC)
   - Audit trail
   - Find recently extracted data

## Common Query Patterns

### 1. Get Specific Admission
```javascript
db.internamentos.findOne({ "internamento.numero_internamento": 2401 })
```

### 2. Get All Patient Admissions
```javascript
db.internamentos.find({ "doente.numero_processo": 23056175 })
  .sort({ "internamento.data_entrada": -1 })
```

### 3. Get Admissions with Burns
```javascript
db.internamentos.find({ "tem_queimaduras": true })
```

### 4. Get Admissions by Year
```javascript
db.internamentos.find({ "ano_internamento": 2023 })
```

### 5. Get Admissions with High ASCQ
```javascript
db.internamentos.find({ "internamento.ASCQ_total": { $gte: 20 } })
```

### 6. Get Admissions with Specific Burn Location
```javascript
db.internamentos.find({ "queimaduras.local_anatomico": "FACE" })
```

### 7. Get Patients with Diabetes
```javascript
db.internamentos.find({ 
  "doente.patologias.nome_patologia": { $regex: /diabetes/i } 
})
```

### 8. Count Admissions by Year
```javascript
db.internamentos.aggregate([
  { $group: {
    _id: "$ano_internamento",
    count: { $sum: 1 },
    avg_ascq: { $avg: "$internamento.ASCQ_total" }
  }},
  { $sort: { _id: -1 }}
])
```

### 9. Get Recent Admissions
```javascript
db.internamentos.find()
  .sort({ "internamento.data_entrada": -1 })
  .limit(10)
```

### 10. Search by Patient Name
```javascript
db.internamentos.find({ 
  "doente.nome": { $regex: /maria/i } 
})
```

## Data Import

### Import Single File
```python
from database.data_importer import import_single_file

result = import_single_file("path/to/2401_extracted.json")
```

### Import Directory
```python
from database.data_importer import import_from_directory

results = import_from_directory("pdf/output", pattern="*_extracted.json")
```

### Using Importer Class
```python
from database.db_manager import MongoDBManager
from database.data_importer import MedicalRecordImporter

db_manager = MongoDBManager()
db_manager.connect()

importer = MedicalRecordImporter(db_manager)
importer.setup_collections_and_indexes()

# Import single file
result = importer.import_json_file("2401_extracted.json")

# Get admission
admission = importer.get_admission_by_number(2401)

# Get patient history
admissions = importer.get_patient_admissions(23056175)

db_manager.disconnect()
```

## Data Integrity

### Source Text Validation

Every extracted field includes `source_text` for human validation:
- Verifies AI extraction accuracy
- Allows manual review of complex cases
- Provides audit trail

### Timestamps

Every entity has `created_at` timestamp:
- Tracks when data was extracted
- Import date recorded separately
- Enables temporal queries

### Duplicate Prevention

- Unique index on `numero_internamento`
- Skip or update mode for re-imports
- Source file tracking

## Advantages of This Structure

1. **Simple Queries**: Single query retrieves complete admission
2. **Atomic Updates**: All admission data updated together
3. **Natural Model**: Reflects real medical record structure
4. **Performance**: No joins required, fewer database round trips
5. **Scalability**: Works well for low to medium volume
6. **Flexibility**: Easy to add new fields
7. **Audit Trail**: Source texts and timestamps throughout

## Disadvantages (Trade-offs)

1. **Data Duplication**: Patient info repeated across admissions
2. **Update Complexity**: Updating patient info requires updating all admissions
3. **Document Size**: Large admissions may hit 16MB MongoDB limit (unlikely)

For your use case (low read/write operations), the advantages far outweigh the disadvantages.

## Future Enhancements

Potential improvements as needs evolve:

1. **Text Search**: MongoDB text indexes on patient names, medications
2. **Aggregation Pipeline**: Complex statistical queries
3. **Data Validation**: MongoDB schema validation rules
4. **Backup Strategy**: Automated backups
5. **Archive Strategy**: Move old admissions to archive collection
6. **Reference Data**: Separate collections for medications, procedures (if needed)

## Summary

- **Main Collection**: `internamentos` (admissions)
- **Structure**: Embedded documents
- **Main Unit**: One admission = One document
- **Patient Tracking**: Via `numero_processo` field
- **Indexes**: 7 indexes for optimal query performance
- **Relationships**: Same patient can have multiple admission documents
- **Best For**: Low read/write operations with complete document queries
