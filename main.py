import os
import json
import shutil
import asyncio
import argparse
from datetime import datetime
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# Rich / UI imports (lazy fallback if not installed will degrade gracefully)
try:
    from rich.console import Console  # type: ignore[import-not-found]
    from rich.table import Table      # type: ignore[import-not-found]
    from rich.panel import Panel      # type: ignore[import-not-found]
    from rich.prompt import Prompt, Confirm  # type: ignore[import-not-found]
    from rich.text import Text        # type: ignore[import-not-found]
    from rich import box              # type: ignore[import-not-found]
except Exception:  # pragma: no cover - best effort
    Console = None  # type: ignore

CONSOLE = Console() if Console else None

from llama_cloud_services import LlamaParse
from icecream import ic

# Load environment variables from .env file
load_dotenv()
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

if not LLAMA_CLOUD_API_KEY:
    print("[WARN] LLAMA_CLOUD_API_KEY not set – parsing calls will fail until you export it.")

# Region-aware base URL (default to EU as requested; allow override via env)
LLAMA_CLOUD_BASE_URL = os.getenv("LLAMA_CLOUD_BASE_URL", "https://api.cloud.eu.llamaindex.ai")

try:
    # NOTE: Pylance might not know these keyword args depending on installed version; suppress type warnings.
    parser = LlamaParse(  # type: ignore[call-arg]
        api_key=LLAMA_CLOUD_API_KEY or "",
        base_url=LLAMA_CLOUD_BASE_URL,
        language="pt",  # adjust if needed
        verbose=True,
    )
    if CONSOLE:
        CONSOLE.print(Panel(f"Using LlamaParse endpoint: [bold]{LLAMA_CLOUD_BASE_URL}[/bold]", title="LlamaParse", border_style="cyan"))
    else:
        print(f"Using LlamaParse endpoint: {LLAMA_CLOUD_BASE_URL}")
except Exception as _e:  # pragma: no cover
    print(f"[WARN] Failed to initialize LlamaParse with base_url={LLAMA_CLOUD_BASE_URL}: {_e}")
    parser = None  # type: ignore

# ---------------------------------------------------------------------------
# Reporting & Utility Helpers
# ---------------------------------------------------------------------------

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)
REPORT_INDEX_FILE = REPORTS_DIR / "parsing_reports_index.json"


def _load_report_index() -> Dict[str, Any]:
    if REPORT_INDEX_FILE.exists():
        try:
            return json.load(open(REPORT_INDEX_FILE, 'r', encoding='utf-8'))
        except Exception:
            return {"reports": []}
    return {"reports": []}


def _save_report_index(index: Dict[str, Any]) -> None:
    with open(REPORT_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


SCHEMA_VERSION = "1.1"
SUBJECT_LOG_VERSION = "1.0"


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _subject_history_file(subject_dir: Path) -> Path:
    return subject_dir / "subject_history.json"


def _subject_log_file(subject_dir: Path) -> Path:
    return subject_dir / "subject_log.json"


def load_subject_log(subject_dir: Path) -> Dict[str, Any]:
    f = _subject_log_file(subject_dir)
    if f.exists():
        try:
            return json.load(open(f, 'r', encoding='utf-8'))
        except Exception:
            pass
    return {
        "log_version": SUBJECT_LOG_VERSION,
        "subject": subject_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec='seconds'),
        "events": []
    }


def append_subject_log(subject_dir: Path, event_type: str, payload: Dict[str, Any]) -> None:
    log = load_subject_log(subject_dir)
    log.setdefault("events", [])
    log["events"].append({
        "ts": datetime.now(timezone.utc).isoformat(timespec='seconds'),
        "type": event_type,
        **payload
    })
    log["log_version"] = SUBJECT_LOG_VERSION
    try:
        with open(_subject_log_file(subject_dir), 'w', encoding='utf-8') as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Failed writing subject log for {subject_dir.name}: {e}")


def load_subject_history(subject_dir: Path) -> Dict[str, Any]:
    f = _subject_history_file(subject_dir)
    if f.exists():
        try:
            return json.load(open(f, 'r', encoding='utf-8'))
        except Exception:
            pass
    return {"schema_version": SCHEMA_VERSION, "subject": subject_dir.name, "events": []}


def append_subject_event(subject_dir: Path, event_type: str, payload: Dict[str, Any]) -> None:
    history = load_subject_history(subject_dir)
    history.setdefault("events", [])
    event_record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec='seconds'),
        "type": event_type,
        **payload
    }
    history["events"].append(event_record)
    ic("subject_event_recorded", {"subject": subject_dir.name, "event": event_type, "payload_keys": list(payload.keys())})
    history["schema_version"] = SCHEMA_VERSION
    try:
        with open(_subject_history_file(subject_dir), 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Failed writing subject history for {subject_dir.name}: {e}")


def collect_subject_file_hashes(pdf_files: List[Path]) -> List[Dict[str, str]]:
    return [{"file": p.name, "sha256": _hash_file(p)} for p in pdf_files]


def report_parser(event: str, parsed_files: Optional[List[str]] = None, errors: Optional[List[str]] = None, details: Optional[Dict[str, Any]] = None) -> Path:
    """Create a timestamped report capturing parsing outcomes.

    Parameters
    ----------
    event: str
        Description of the event (e.g., 'initial_parse', 'reparse').
    parsed_files: list[str]
        Files successfully parsed in this run.
    errors: list[str]
        Error messages captured.
    """
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    report_file = REPORTS_DIR / f"parse_report_{ts}.json"
    record = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": ts,
        "event": event,
        "items": parsed_files or [],  # generalized field
        "errors": errors or [],
        "count_items": len(parsed_files or []),
        "count_errors": len(errors or []),
        "details": details or {},
    }
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    # update index
    index = _load_report_index()
    index.setdefault("reports", []).append({"file": report_file.name, **record})
    _save_report_index(index)

    if CONSOLE:
        CONSOLE.print(Panel.fit(f"Report saved: [bold]{report_file.name}[/bold] (event={event}, items={len(record['items'])})", title="Report", style="green"))
    else:
        print(f"Report saved: {report_file}")
    return report_file


def latest_report() -> Optional[Dict[str, Any]]:
    index = _load_report_index()
    if not index.get("reports"):
        return None
    return index["reports"][-1]


def list_unparsed_pdfs(pdf_root: str = "./pdf") -> List[Path]:
    root = Path(pdf_root)
    return [p for p in root.glob('*.pdf') if p.is_file()]


def list_subjects(base_output_dir: str = "./pdf/output") -> List[Path]:
    base = Path(base_output_dir)
    if not base.exists():
        return []
    return [d for d in base.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 4]


def list_parsed_files(base_output_dir: str = "./pdf/output") -> List[Path]:
    parsed = []
    for subj in list_subjects(base_output_dir):
        for doc_dir in subj.iterdir():
            if doc_dir.is_dir() and (doc_dir / 'markdown').exists():
                parsed.append(doc_dir)
    return parsed


def render_table(title: str, rows: List[List[str]], headers: List[str]) -> None:
    if not CONSOLE:
        print(title)
        print(headers)
        for r in rows:
            print(r)
        return
    table = Table(
        title=f"[bold]{title}[/bold]",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold bright_cyan",
        title_style="bold magenta",
        show_lines=False,
        padding=(0,1)
    )
    for h in headers:
        table.add_column(h, style="white", overflow="fold")
    if not rows:
        table.add_row(*(["[dim]—[/dim]"] * len(headers)))
    else:
        for row in rows:
            styled = []
            for idx, c in enumerate(row):
                txt = str(c)
                if idx == 0:
                    txt = f"[bold green]{txt}[/bold green]"
                styled.append(txt)
            table.add_row(*styled)
    CONSOLE.print(table)


def _print_banner():
    if not CONSOLE:
        print("=== LlamaParse Menu ===")
        return
    banner_text = Text()
    banner_text.append(" LlamaParse CLI ", style="bold white on magenta")
    banner_text.append("  •  PDF Intelligence  ", style="bold black on bright_white")
    CONSOLE.print(Panel(banner_text, style="magenta", expand=True, padding=(1,2), title="🚀", subtitle="Use numbers or q to exit"))


def _menu_options() -> Table:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0,1))
    table.add_column("Opt", style="bold cyan", width=4, justify="right")
    table.add_column("Action", style="white")
    options = [
        ("1", "List unparsed PDF files"),
        ("2", "List parsed PDF subjects/files"),
        ("3", "Show latest parse report"),
        ("4", "Parse unparsed PDF files"),
        ("5", "Re-parse already parsed files (force)"),
        ("0", "Back / Exit")
    ]
    for key, label in options:
        table.add_row(f"[bold]{key}[/bold]", label)
    return table


def _status_panel(pdf_dir: str, base_output_dir: str) -> Panel:
    unparsed = list_unparsed_pdfs(pdf_dir)
    parsed_count = len(list_parsed_files(base_output_dir))
    subjects = len(list_subjects(base_output_dir))
    content = (
        f"[bright_cyan]Unparsed:[/bright_cyan] {len(unparsed)}  |  "
        f"[bright_cyan]Documents Parsed:[/bright_cyan] {parsed_count}  |  "
        f"[bright_cyan]Subjects:[/bright_cyan] {subjects}"
    )
    return Panel(content, title="Status", border_style="cyan", padding=(0,1))


def compute_markdown_status(base_output_dir: str = "./pdf/output") -> Dict[str, List[str]]:
    status = {"merged": [], "cleaned": [], "unmerged": [], "uncleaned": []}
    for subj in list_subjects(base_output_dir):
        subject = subj.name
        merged_file = subj / f"{subject}_merged_medical_records.md"
        cleaned_file = subj / f"{subject}_merged_medical_records.cleaned.md"
        if merged_file.exists():
            status["merged"].append(subject)
            if cleaned_file.exists():
                status["cleaned"].append(subject)
            else:
                status["uncleaned"].append(subject)
        else:
            # Determine if there is parsed content (markdown directories) but no merged file
            doc_folders = [d for d in subj.iterdir() if d.is_dir() and (d / 'markdown').exists()]
            if doc_folders:
                status["unmerged"].append(subject)
    return status


def extract_year_from_subject(subject: str) -> int:
    """Extract year from subject ID based on digit count rules."""
    if len(subject) == 4:
        # 4 digits: first 2 are year (e.g., 2401 -> 2024)
        year_digits = subject[:2]
        return 2000 + int(year_digits)
    elif len(subject) == 3:
        # 3 digits: first digit is year (e.g., 901 -> 2009)
        year_digit = subject[0]
        return 2000 + int(year_digit)
    else:
        # Fallback for unexpected formats
        return 2000


def analyze_subjects_by_year(base_output_dir: str = "./pdf/output") -> Dict[str, Any]:
    """Analyze processed subjects by year with detailed document type and processing status.

    Adds per-year serial statistics: min_serial, max_serial, and missing_serials (zero-padded strings).
    """
    base = Path(base_output_dir)
    analysis = {
        "by_year": {},
        "summary": {
            "total_subjects": 0,
            "years_covered": set(),
            "document_types": {"A": 0, "E": 0, "BIC": 0, "O": 0},
        }
    }
    
    for subj_path in list_subjects(base_output_dir):
        subject = subj_path.name
        year = extract_year_from_subject(subject)
        analysis["summary"]["years_covered"].add(year)
        analysis["summary"]["total_subjects"] += 1
        
        if year not in analysis["by_year"]:
            analysis["by_year"][year] = {
                "subjects": [],
                "total_count": 0,
                "document_types": {"A": 0, "E": 0, "BIC": 0, "O": 0},
                "processing_status": {"parsed": 0, "merged": 0, "cleaned": 0},
                # Serial stats, computed after collecting subjects
                "min_serial": None,
                "max_serial": None,
                "missing_serials": [],
            }
        
        year_data = analysis["by_year"][year]
        year_data["total_count"] += 1
        
        # Analyze document types in this subject
        doc_types_found = {"A": [], "E": [], "BIC": [], "O": []}
        for item in subj_path.iterdir():
            if item.is_dir() and item.name not in {'merged', '__pycache__'}:
                folder_name = item.name
                # Determine document type by suffix
                if folder_name.endswith('BIC'):
                    doc_types_found['BIC'].append(folder_name)
                    year_data["document_types"]["BIC"] += 1
                    analysis["summary"]["document_types"]["BIC"] += 1
                elif folder_name.endswith('E'):
                    doc_types_found['E'].append(folder_name)
                    year_data["document_types"]["E"] += 1
                    analysis["summary"]["document_types"]["E"] += 1
                elif folder_name.endswith('A'):
                    doc_types_found['A'].append(folder_name)
                    year_data["document_types"]["A"] += 1
                    analysis["summary"]["document_types"]["A"] += 1
                elif folder_name.endswith('O'):
                    doc_types_found['O'].append(folder_name)
                    year_data["document_types"]["O"] += 1
                    analysis["summary"]["document_types"]["O"] += 1
        
        # Check processing status
        has_parsed = any(
            (subj_path / doc).is_dir() and (subj_path / doc / 'markdown').exists()
            for doc_type_list in doc_types_found.values()
            for doc in doc_type_list
        )
        merged_file = subj_path / f"{subject}_merged_medical_records.md"
        cleaned_file = subj_path / f"{subject}_merged_medical_records.cleaned.md"
        
        processing_status = {
            "parsed": has_parsed,
            "merged": merged_file.exists(),
            "cleaned": cleaned_file.exists()
        }
        
        if processing_status["parsed"]:
            year_data["processing_status"]["parsed"] += 1
        if processing_status["merged"]:
            year_data["processing_status"]["merged"] += 1
        if processing_status["cleaned"]:
            year_data["processing_status"]["cleaned"] += 1
        
        # Store subject details
        subject_info = {
            "id": subject,
            "year": year,
            "serial": subject[2:] if len(subject) == 4 else subject[1:],
            "document_types": {k: len(v) for k, v in doc_types_found.items() if v},
            "processing_status": processing_status,
            "total_documents": sum(len(v) for v in doc_types_found.values())
        }
        year_data["subjects"].append(subject_info)
    
    # Sort subjects within each year
    for y, year_data in analysis["by_year"].items():
        year_data["subjects"].sort(key=lambda x: x["id"])
        # Compute serial stats
        serial_ints: List[int] = []
        for s in year_data["subjects"]:
            try:
                serial_ints.append(int(s["serial"]))
            except Exception:
                continue
        if serial_ints:
            mn = min(serial_ints)
            mx = max(serial_ints)
            present = set(serial_ints)
            missing = [i for i in range(mn, mx + 1) if i not in present]
            # Store zero-padded two-digit strings for missing
            year_data["min_serial"] = mn
            year_data["max_serial"] = mx
            year_data["missing_serials"] = [f"{i:02d}" for i in missing]
        else:
            year_data["min_serial"] = None
            year_data["max_serial"] = None
            year_data["missing_serials"] = []
    
    # Convert set to sorted list for JSON serialization
    analysis["summary"]["years_covered"] = sorted(list(analysis["summary"]["years_covered"]))
    
    return analysis


def summarize_subject_logs(base_output_dir: str = "./pdf/output") -> Dict[str, Any]:
    """Aggregate subject_log.json files to provide project-wide statistics."""
    base = Path(base_output_dir)
    summary = {
        "subjects": 0,
        "parsed_events": 0,
        "merge_events": 0,
        "clean_events": 0,
        "subjects_with_parse": 0,
        "subjects_with_merge": 0,
        "subjects_with_clean": 0,
    }
    for subj in list_subjects(base_output_dir):
        log_file = subj / 'subject_log.json'
        if not log_file.exists():
            continue
        try:
            data = json.load(open(log_file, 'r', encoding='utf-8'))
        except Exception:
            continue
        events = data.get('events', [])
        if not events:
            continue
        summary['subjects'] += 1
        types = {e.get('type') for e in events}
        if 'parse' in types:
            summary['subjects_with_parse'] += 1
        if 'merge' in types:
            summary['subjects_with_merge'] += 1
        if 'clean' in types:
            summary['subjects_with_clean'] += 1
        summary['parsed_events'] += sum(1 for e in events if e.get('type') == 'parse')
        summary['merge_events'] += sum(1 for e in events if e.get('type') == 'merge')
        summary['clean_events'] += sum(1 for e in events if e.get('type') == 'clean')
    return summary


async def menu_llamaparse(pdf_dir: str = "./pdf", base_output_dir: str = "./pdf/output") -> None:
    """Interactive submenu for LlamaParse related actions with Rich UI."""
    def subject_history(subject: str) -> Optional[Dict[str, Any]]:
        subj_dir = Path(base_output_dir) / subject
        hist_file = subj_dir / "subject_history.json"
        if hist_file.exists():
            try:
                return json.load(open(hist_file,'r',encoding='utf-8'))
            except Exception:
                return None
        return None

    def stale_subjects() -> List[str]:
        stale: List[str] = []
        for subj_dir in list_subjects(base_output_dir):
            hist = load_subject_history(subj_dir)
            # Find last parse event hashes
            last_parse = None
            for ev in reversed(hist.get('events', [])):
                if ev.get('type') == 'parse':
                    last_parse = ev
                    break
            if not last_parse:
                continue
            recorded = {f['file']: f['sha256'] for f in last_parse.get('files', []) if f.get('file')}
            # Current pdfs (if still present) inside subject folder
            current_pdfs = list(subj_dir.glob('*.pdf'))
            changed = False
            for p in current_pdfs:
                h = _hash_file(p)
                if p.name not in recorded or recorded[p.name] != h:
                    changed = True
                    break
            if changed:
                stale.append(subj_dir.name)
        return stale

    while True:
        if CONSOLE:
            _print_banner()
            CONSOLE.print(_status_panel(pdf_dir, base_output_dir))
            CONSOLE.print(_menu_options())
            extra = Table(show_header=False, box=box.SIMPLE)
            extra.add_column("Opt", style="bold cyan", width=4, justify="right")
            extra.add_column("Action")
            for k,label in [
                ("6","View subject history"),
                ("7","List stale subjects"),
                ("8","Re-parse stale subjects"),
            ]:
                extra.add_row(k,label)
            CONSOLE.print(extra)
        else:
            print("(Rich not available) LlamaParse Menu")
        choice = (Prompt.ask("Enter choice", choices=["0","1","2","3","4","5","6","7","8","q"], default="0")
                  if CONSOLE else input("Choice (q to quit): ").strip())
        if choice in {"q","Q","0"}:
            if CONSOLE:
                CONSOLE.print("[bold green]Exiting menu...[/bold green]")
            return

        if choice == "1":
            unparsed = list_unparsed_pdfs(pdf_dir)
            render_table("Unparsed PDFs", [[p.name, f"{p.stat().st_size/1024:.1f} KB", datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')] for p in unparsed], ["File", "Size", "Modified"])
        elif choice == "2":
            parsed = list_parsed_files(base_output_dir)
            rows = []
            for d in parsed:
                subject = d.parent.name
                pages = len(list((d / 'markdown').glob('page_*.md')))
                rows.append([subject, d.name, pages])
            render_table("Parsed Files", rows, ["Subject", "Document", "Pages"])
        elif choice == "3":
            rep = latest_report()
            if not rep:
                if CONSOLE:
                    CONSOLE.print(Panel("No reports yet", style="yellow"))
                else:
                    print("No reports yet")
            else:
                # Backward & forward compatible extraction of counts and item lists
                parsed_count = (
                    rep.get('count_items')
                    or rep.get('count_parsed')  # legacy
                    or (len(rep.get('items', [])) if rep.get('items') else len(rep.get('parsed_files', [])))
                )
                errors_count = rep.get('count_errors') if rep.get('count_errors') is not None else len(rep.get('errors', []))
                render_table(
                    "Latest Report",
                    [[
                        rep.get('timestamp', ''),
                        rep.get('event', ''),
                        str(parsed_count),
                        str(errors_count),
                    ]],
                    ["Timestamp","Event","Items","Errors"]
                )
                # Show items (new schema) or parsed_files (legacy)
                if rep.get('items'):
                    render_table("Items", [[f] for f in rep['items']], ["Item"])
                elif rep.get('parsed_files'):
                    render_table("Files Parsed", [[f] for f in rep['parsed_files']], ["File"])
                if rep.get('errors'):
                    render_table("Errors", [[e] for e in rep['errors']], ["Error"])
        elif choice == "4":
            unparsed = list_unparsed_pdfs(pdf_dir)
            if not unparsed:
                if CONSOLE:
                    CONSOLE.print(Panel("No unparsed PDFs found", style="yellow"))
                else:
                    print("No unparsed PDFs found")
                continue
            if CONSOLE and not Confirm.ask(f"Parse {len(unparsed)} unparsed file(s)?"):
                continue
            subjects = organize_pdf_files_by_subject(pdf_dir)
            parsed_files = []
            errors = []
            if CONSOLE:
                from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn  # type: ignore[import-not-found]
                with Progress(SpinnerColumn(), "[progress.description]{task.description}", TimeElapsedColumn(), transient=True) as progress:
                    task = progress.add_task("Parsing subjects...", total=len(subjects))
                    for subject, files in subjects.items():
                        ok = await process_subject_batch(subject, files, base_output_dir)
                        if ok:
                            parsed_files.extend([f.name for f in files])
                        else:
                            errors.append(subject)
                        progress.advance(task)
            else:
                for subject, files in subjects.items():
                    ok = await process_subject_batch(subject, files, base_output_dir)
                    if ok:
                        parsed_files.extend([f.name for f in files])
                    else:
                        errors.append(subject)
            report_parser("parse_new", parsed_files, errors)
        elif choice == "5":
            parsed = list_parsed_files(base_output_dir)
            if not parsed:
                if CONSOLE:
                    CONSOLE.print(Panel("No previously parsed files found", style="yellow"))
                else:
                    print("No previously parsed files found")
                continue
            if CONSOLE and not Confirm.ask("Re-parse ALL existing parsed subjects? This will force reprocessing."):
                continue
            parsed_files = []
            errors = []
            subjects_dirs = list_subjects(base_output_dir)
            if CONSOLE:
                from rich.progress import Progress, BarColumn, TimeElapsedColumn  # type: ignore[import-not-found]
                with Progress("[progress.description]{task.description}", BarColumn(), TimeElapsedColumn(), transient=True) as progress:
                    task = progress.add_task("Re-parsing subjects", total=len(subjects_dirs))
                    for subj_dir in subjects_dirs:
                        pdfs = list(subj_dir.glob('*.pdf'))
                        if not pdfs:
                            progress.advance(task)
                            continue
                        ok = await process_subject_batch(subj_dir.name, pdfs, base_output_dir)
                        if ok:
                            parsed_files.extend([p.name for p in pdfs])
                        else:
                            errors.append(subj_dir.name)
                        progress.advance(task)
            else:
                for subj_dir in subjects_dirs:
                    pdfs = list(subj_dir.glob('*.pdf'))
                    if not pdfs:
                        continue
                    ok = await process_subject_batch(subj_dir.name, pdfs, base_output_dir)
                    if ok:
                        parsed_files.extend([p.name for p in pdfs])
                    else:
                        errors.append(subj_dir.name)
            report_parser("reparse_existing", parsed_files, errors)
        elif choice == "6":  # view subject history
            subj = Prompt.ask("Subject (4 digits)") if CONSOLE else input("Subject: ").strip()
            hist = subject_history(subj)
            if not hist:
                (CONSOLE.print(Panel(f"No history for subject {subj}", style="yellow")) if CONSOLE else print("No history"))
            else:
                events = hist.get('events', [])
                rows = [[e.get('ts',''), e.get('type',''), json.dumps({k:v for k,v in e.items() if k not in {'ts','type'} })[:60]] for e in events[-20:]]
                render_table(f"History {subj} (last {len(rows)})", rows, ["Timestamp","Type","Data"])
        elif choice == "7":  # list stale
            stale = stale_subjects()
            if stale:
                render_table("Stale Subjects", [[s] for s in stale], ["Subject"])
            else:
                (CONSOLE.print(Panel("No stale subjects detected", style="green")) if CONSOLE else print("No stale subjects"))
        elif choice == "8":  # re-parse stale
            stale = stale_subjects()
            if not stale:
                (CONSOLE.print(Panel("No stale subjects to re-parse", style="green")) if CONSOLE else print("No stale subjects"))
            else:
                if CONSOLE and not Confirm.ask(f"Re-parse {len(stale)} stale subject(s)?"):
                    continue
                parsed_files = []
                errors = []
                for subj in stale:
                    subj_dir = Path(base_output_dir) / subj
                    pdfs = list(subj_dir.glob('*.pdf'))
                    if not pdfs:
                        continue
                    ok = await process_subject_batch(subj, pdfs, base_output_dir)
                    if ok:
                        parsed_files.extend([p.name for p in pdfs])
                    else:
                        errors.append(subj)
                report_parser("reparse_stale", parsed_files, errors, details={"subjects": stale})
        else:
            if CONSOLE:
                CONSOLE.print(Panel("Invalid option", style="red"))
            else:
                print("Invalid option")
        # Loop continues


# ---------------------------------------------------------------------------
# Merging & Cleaning Submenu
# ---------------------------------------------------------------------------
def _merge_markdown_for_all(subjects_root: str = "./pdf/output") -> List[str]:
    """Wrapper to merge markdown for all subjects and return list of subjects processed."""
    processed: List[str] = []
    for subj_path in list_subjects(subjects_root):
        try:
            merge_documents_by_subject(str(subj_path))
            processed.append(subj_path.name)
        except Exception as e:
            if CONSOLE:
                CONSOLE.print(f"[red]Error merging subject {subj_path.name}: {e}[/red]")
            else:
                print(f"Error merging subject {subj_path.name}: {e}")
    return processed


def _clean_markdown_for_all(subjects_root: str = "./pdf/output") -> List[str]:
    """Wrapper to clean merged markdown for all subjects and return list of cleaned file names."""
    cleaned_all: List[str] = []
    for subj_path in list_subjects(subjects_root):
        merged_file = subj_path / f"{subj_path.name}_merged_medical_records.md"
        if not merged_file.exists():
            continue
        try:
            results = clean_merged_markdown_files(subj_path)
            if isinstance(results, list):
                cleaned_all.extend([f"{subj_path.name}/{fname}" for fname in results])
        except Exception as e:
            msg = f"Error cleaning subject {subj_path.name}: {e}"
            if CONSOLE:
                CONSOLE.print(f"[red]{msg}[/red]")
            else:
                print(msg)
    return cleaned_all


async def menu_markdown_utils(base_output_dir: str = "./pdf/output") -> None:
    """Interactive submenu for merging and cleaning markdown outputs."""
    def get_markdown_status() -> Dict[str, List[str]]:
        status = {"merged": [], "cleaned": [], "unmerged": [], "uncleaned": []}
        for subj in list_subjects(base_output_dir):
            subject = subj.name
            merged_file = subj / f"{subject}_merged_medical_records.md"
            cleaned_file = subj / f"{subject}_merged_medical_records.cleaned.md"
            if merged_file.exists():
                status["merged"].append(subject)
                if cleaned_file.exists():
                    status["cleaned"].append(subject)
                else:
                    status["uncleaned"].append(subject)
            else:
                # there are parsed folders but no merged file
                doc_folders = [d for d in subj.iterdir() if d.is_dir() and d.name not in {"merged"}]
                if doc_folders:
                    status["unmerged"].append(subject)
        return status

    while True:
        if CONSOLE:
            CONSOLE.rule("[bold magenta]Markdown Utilities")
            options_table = Table(box=box.SIMPLE, show_header=False, padding=(0,1))
            options_table.add_column("Opt", style="bold cyan", width=4, justify="right")
            options_table.add_column("Action", style="white")
            for k, label in [
                ("1","Merge markdown for all subjects"),
                ("2","Clean merged markdown for all subjects"),
                ("3","Show latest report"),
                ("4","Show merge/clean status"),
                ("5","Merge single subject"),
                ("6","Clean single subject"),
                ("7","View subject history"),
                ("8","Merge only unmerged subjects"),
                ("0","Back")
            ]:
                options_table.add_row(k, label)
            CONSOLE.print(options_table)
            choice = Prompt.ask("Enter choice", choices=["0","1","2","3","4","5","6","7","8"], default="0")
        else:
            print("Markdown Utilities:\n 1) Merge all\n 2) Clean all\n 3) Latest report\n 4) Status\n 5) Merge subject\n 6) Clean subject\n 7) Subject history\n 0) Back")
            choice = input("Choice: ").strip()

        if choice == "0":
            return
        elif choice == "1":
            subs = list_subjects(base_output_dir)
            if not subs:
                (CONSOLE.print(Panel("No subjects found", style="yellow")) if CONSOLE else print("No subjects found"))
                continue
            if CONSOLE and not Confirm.ask(f"Merge markdown for {len(subs)} subject(s)?"):
                continue
            processed = _merge_markdown_for_all(base_output_dir)
            report_parser("merge_markdown", processed, [])
        elif choice == "2":
            subs = list_subjects(base_output_dir)
            if not subs:
                (CONSOLE.print(Panel("No subjects found", style="yellow")) if CONSOLE else print("No subjects found"))
                continue
            if CONSOLE and not Confirm.ask(f"Clean merged markdown for {len(subs)} subject(s)?"):
                continue
            cleaned_files = _clean_markdown_for_all(base_output_dir)
            report_parser("clean_markdown", cleaned_files, [], details={"count_subjects": len(set(p.split('/')[0] for p in cleaned_files))})
        elif choice == "3":
            rep = latest_report()
            if not rep:
                (CONSOLE.print(Panel("No reports yet", style="yellow")) if CONSOLE else print("No reports yet"))
            else:
                cols = ["Timestamp","Event","Items","Errors"]
                render_table("Latest Report", [[str(rep.get('timestamp','')), str(rep.get('event','')), str(rep.get('count_items','')), str(rep.get('count_errors',''))]], cols)
                if rep.get('items'):
                    render_table("Items", [[f] for f in rep['items']], ["Item"])
        elif choice == "4":
            status = get_markdown_status()
            render_table("Markdown Status", [
                ["Merged", str(len(status['merged']))],
                ["Cleaned", str(len(status['cleaned']))],
                ["Unmerged", str(len(status['unmerged']))],
                ["Uncleaned", str(len(status['uncleaned']))],
            ], ["Category","Count"])
            if status['unmerged']:
                render_table("Unmerged Subjects", [[s] for s in status['unmerged']], ["Subject"])
            if status['uncleaned']:
                render_table("Uncleaned Subjects", [[s] for s in status['uncleaned']], ["Subject"])
        elif choice == "5":  # merge single
            subj = Prompt.ask("Subject (4 digits)") if CONSOLE else input("Subject: ").strip()
            subj_dir = Path(base_output_dir) / subj
            if not subj_dir.exists():
                (CONSOLE.print(Panel("Subject not found", style="red")) if CONSOLE else print("Subject not found"))
                continue
            if CONSOLE and not Confirm.ask(f"Merge markdown for subject {subj}?"):
                continue
            ok = merge_documents_by_subject(subj_dir)
            report_parser("merge_markdown_subject", [subj], [] if ok else [subj])
        elif choice == "6":  # clean single
            subj = Prompt.ask("Subject (4 digits)") if CONSOLE else input("Subject: ").strip()
            subj_dir = Path(base_output_dir) / subj
            merged_file = subj_dir / f"{subj}_merged_medical_records.md"
            if not merged_file.exists():
                (CONSOLE.print(Panel("Merged file not found", style="red")) if CONSOLE else print("Merged file not found"))
                continue
            if CONSOLE and not Confirm.ask(f"Clean merged markdown for subject {subj}?"):
                continue
            cleaned = clean_merged_markdown_files(subj_dir)
            cleaned_list = [f"{subj}/{f}" for f in cleaned] if isinstance(cleaned, list) else []
            report_parser("clean_markdown_subject", cleaned_list, [], details={"subject": subj})
        elif choice == "7":  # subject history
            subj = Prompt.ask("Subject (4 digits)") if CONSOLE else input("Subject: ").strip()
            subj_dir = Path(base_output_dir) / subj
            hist = load_subject_history(subj_dir)
            events = hist.get('events', [])
            if not events:
                (CONSOLE.print(Panel("No history", style="yellow")) if CONSOLE else print("No history"))
            else:
                rows = [[e.get('ts',''), e.get('type',''), json.dumps({k:v for k,v in e.items() if k not in {'ts','type'} })[:60]] for e in events[-20:]]
                render_table(f"History {subj}", rows, ["Timestamp","Type","Data"])
        elif choice == "8":  # merge only unmerged subjects
            status = compute_markdown_status(base_output_dir)
            unmerged_subjects = status.get('unmerged', [])
            if not unmerged_subjects:
                (CONSOLE.print(Panel("No unmerged subjects found", style="green")) if CONSOLE else print("No unmerged subjects found"))
                continue
            if CONSOLE and not Confirm.ask(f"Merge markdown for {len(unmerged_subjects)} unmerged subject(s)?"):
                continue
            merge_successful = 0
            merge_failed = 0
            for subj in unmerged_subjects:
                try:
                    subj_dir = Path(base_output_dir) / subj
                    ok = merge_documents_by_subject(subj_dir)
                    if ok:
                        merge_successful += 1
                    else:
                        merge_failed += 1
                except Exception as e:
                    merge_failed += 1
                    if CONSOLE:
                        CONSOLE.print(f"[red]Error merging subject {subj}: {e}[/red]")
                    else:
                        print(f"Error merging subject {subj}: {e}")
            report_parser("merge_unmerged_subjects", unmerged_subjects, [], details={"success": merge_successful, "failed": merge_failed})
            if CONSOLE:
                CONSOLE.print(Panel(f"Merged {merge_successful} subjects, failed {merge_failed}", title="Merge Unmerged", style="green"))
        # loop continues


async def menu_root(pdf_dir: str = "./pdf", base_output_dir: str = "./pdf/output") -> None:
    """Top-level menu offering categories: parsing utilities and markdown utilities."""
    while True:
        if CONSOLE:
            _print_banner()
            # Dynamic reporting block with year overview
            unparsed = list_unparsed_pdfs(pdf_dir)
            parsed_subjects = list_subjects(base_output_dir)
            md_status = compute_markdown_status(base_output_dir)
            analysis = analyze_subjects_by_year(base_output_dir)
            
            report_table = Table(title="Session Snapshot", box=box.SIMPLE, show_header=True, header_style="bold magenta")
            report_table.add_column("Metric", style="cyan", no_wrap=True)
            report_table.add_column("Count", style="bold yellow")
            report_table.add_row("Unparsed PDFs", str(len(unparsed)))
            report_table.add_row("Parsed Subjects", str(len(parsed_subjects)))
            report_table.add_row("Years Covered", str(len(analysis['summary']['years_covered'])) if analysis['summary']['years_covered'] else "0")
            report_table.add_row("Subjects w/ parsed not merged", str(len(md_status['unmerged'])))
            report_table.add_row("Merged not cleaned", str(len(md_status['uncleaned'])))
            CONSOLE.print(report_table)
            
            # Quick year overview if we have data
            if analysis['summary']['years_covered']:
                year_overview = Table(title="Quick Year Overview", box=box.SIMPLE, header_style="bold cyan")
                year_overview.add_column("Year", style="yellow", justify="center")
                year_overview.add_column("Subjects", style="white", justify="center")
                year_overview.add_column("Documents", style="green", justify="center")
                
                for year in sorted(analysis['summary']['years_covered']):
                    if year in analysis['by_year']:
                        year_data = analysis['by_year'][year]
                        total_docs = sum(year_data['document_types'].values())
                        year_overview.add_row(str(year), str(year_data['total_count']), str(total_docs))
                CONSOLE.print(year_overview)
            # Optionally list subsets if small
            def maybe_list(label: str, items: List[str]):
                if not CONSOLE:
                    return
                if items and len(items) <= 15:
                    CONSOLE.print(Panel("\n".join(items), title=label, border_style="blue"))
            maybe_list("Unparsed PDFs", [p.name for p in unparsed])
            maybe_list("Unmerged Subjects", md_status['unmerged'])
            maybe_list("Uncleaned Subjects", md_status['uncleaned'])
            top = Table(show_header=False, box=box.SIMPLE_HEAVY, padding=(0,1))
            top.add_column("Opt", style="bold cyan", width=4, justify="right")
            top.add_column("Category", style="white")
            for k,label in [("1","PDF Parsing Utilities"),("2","Merging & Cleaning Markdown"),("3","Full Statistics"),("4","Exit")]:
                top.add_row(k,label)
            CONSOLE.print(top)
            choice = Prompt.ask("Select", choices=["1","2","3","4"], default="4")
        else:
            print("Unparsed PDFs:")
            for p in list_unparsed_pdfs(pdf_dir):
                print(f"  - {p.name}")
            print("1) PDF Parsing Utilities\n2) Merging & Cleaning Markdown\n3) Full Statistics\n4) Exit")
            choice = input("Choice: ").strip()
        if choice == "4":
            if CONSOLE:
                CONSOLE.print("[green]Goodbye![/green]")
            break
        if choice == "1":
            await menu_llamaparse(pdf_dir=pdf_dir, base_output_dir=base_output_dir)
        elif choice == "2":
            await menu_markdown_utils(base_output_dir=base_output_dir)
        elif choice == "3":
            # Full statistics view with year-based analysis
            if CONSOLE:
                # Basic overview
                stats_panel = Table(title="Project Overview", box=box.MINIMAL_DOUBLE_HEAD, header_style="bold magenta")
                stats_panel.add_column("Category", style="cyan")
                stats_panel.add_column("Value", style="bold yellow")
                
                # Gather basic stats
                unparsed = list_unparsed_pdfs(pdf_dir)
                subjects = list_subjects(base_output_dir)
                md_status = compute_markdown_status(base_output_dir)
                parsed_files = list_parsed_files(base_output_dir)
                
                stats_panel.add_row("Total PDFs (root)", str(len(list(Path(pdf_dir).glob('*.pdf')))))
                stats_panel.add_row("Unparsed PDFs", str(len(unparsed)))
                stats_panel.add_row("Subjects (parsed dir)", str(len(subjects)))
                stats_panel.add_row("Total Parsed Document Folders", str(len(parsed_files)))
                stats_panel.add_row("Subjects Merged", str(len(md_status['merged'])))
                stats_panel.add_row("Subjects Cleaned", str(len(md_status['cleaned'])))
                CONSOLE.print(stats_panel)
                
                # Year-based detailed analysis
                analysis = analyze_subjects_by_year(base_output_dir)
                
                # Year summary table with serial stats
                if analysis["by_year"]:
                    year_table = Table(title="Subjects by Year", box=box.MINIMAL_DOUBLE_HEAD, header_style="bold cyan")
                    year_table.add_column("Year", style="bold yellow", justify="center")
                    year_table.add_column("Subjects", style="white", justify="center")
                    year_table.add_column("A", style="green", justify="center")
                    year_table.add_column("E", style="blue", justify="center") 
                    year_table.add_column("BIC", style="red", justify="center")
                    year_table.add_column("O", style="magenta", justify="center")
                    year_table.add_column("Parsed", style="bright_green", justify="center")
                    year_table.add_column("Merged", style="bright_blue", justify="center")
                    year_table.add_column("Cleaned", style="bright_magenta", justify="center")
                    year_table.add_column("Min", style="cyan", justify="center")
                    year_table.add_column("Max", style="cyan", justify="center")
                    year_table.add_column("Missing", style="cyan", justify="center")
                    
                    for year in sorted(analysis["by_year"].keys()):
                        year_data = analysis["by_year"][year]
                        year_table.add_row(
                            str(year),
                            str(year_data["total_count"]),
                            str(year_data["document_types"]["A"]),
                            str(year_data["document_types"]["E"]),
                            str(year_data["document_types"]["BIC"]),
                            str(year_data["document_types"]["O"]),
                            str(year_data["processing_status"]["parsed"]),
                            str(year_data["processing_status"]["merged"]),
                            str(year_data["processing_status"]["cleaned"]),
                            f"{year_data['min_serial']:02d}" if year_data["min_serial"] is not None else "—",
                            f"{year_data['max_serial']:02d}" if year_data["max_serial"] is not None else "—",
                            str(len(year_data.get("missing_serials", [])))
                        )
                    CONSOLE.print(year_table)
                    # Optionally list missing serials per year
                    has_missing = any(analysis["by_year"][y].get("missing_serials") for y in analysis["by_year"])            
                    if has_missing and Confirm.ask("List missing serials per year?", default=False):
                        for year in sorted(analysis["by_year"].keys()):
                            ydata = analysis["by_year"][year]
                            missing = ydata.get("missing_serials", [])
                            if missing:
                                CONSOLE.print(Panel(
                                    ", ".join(missing),
                                    title=f"Missing Serials - {year}",
                                    border_style="red"
                                ))
                
                # Detailed subject breakdown by year (show only if requested)
                if Confirm.ask("Show detailed subject breakdown by year?", default=False):
                    for year in sorted(analysis["by_year"].keys()):
                        year_data = analysis["by_year"][year]
                        subjects_in_year = year_data["subjects"]
                        
                        if subjects_in_year:
                            detail_table = Table(
                                title=f"Year {year} - {len(subjects_in_year)} Subjects",
                                box=box.SIMPLE,
                                header_style="bold cyan"
                            )
                            detail_table.add_column("Subject", style="bold yellow")
                            detail_table.add_column("Serial", style="white")
                            detail_table.add_column("Docs", style="white")
                            detail_table.add_column("Types", style="cyan")
                            detail_table.add_column("Status", style="green")
                            
                            for subj in subjects_in_year:
                                # Format document types
                                doc_types = []
                                for dtype, count in subj["document_types"].items():
                                    if count > 0:
                                        doc_types.append(f"{dtype}({count})" if count > 1 else dtype)
                                types_str = ", ".join(doc_types) if doc_types else "None"
                                
                                # Format processing status
                                status_parts = []
                                if subj["processing_status"]["parsed"]:
                                    status_parts.append("P")
                                if subj["processing_status"]["merged"]:
                                    status_parts.append("M")
                                if subj["processing_status"]["cleaned"]:
                                    status_parts.append("C")
                                status_str = "•".join(status_parts) if status_parts else "—"
                                
                                detail_table.add_row(
                                    subj["id"],
                                    subj["serial"],
                                    str(subj["total_documents"]),
                                    types_str,
                                    status_str
                                )
                            
                            CONSOLE.print(detail_table)
                
                # Document type summary
                doc_summary = Table(title="Document Type Summary", box=box.SIMPLE, header_style="bold magenta")
                doc_summary.add_column("Type", style="cyan")
                doc_summary.add_column("Description", style="white")
                doc_summary.add_column("Count", style="bold yellow")
                
                doc_descriptions = {
                    "A": "Release Notes",
                    "E": "Admission Notes", 
                    "BIC": "Death Notices",
                    "O": "Death Certificates"
                }
                
                for doc_type, count in analysis["summary"]["document_types"].items():
                    doc_summary.add_row(
                        doc_type,
                        doc_descriptions.get(doc_type, "Unknown"),
                        str(count)
                    )
                CONSOLE.print(doc_summary)
                
            else:
                # Basic textual fallback
                print("Full Statistics:")
                print(f"Unparsed PDFs: {len(list_unparsed_pdfs(pdf_dir))}")
                print(f"Subjects: {len(list_subjects(base_output_dir))}")
                md_status = compute_markdown_status(base_output_dir)
                print(f"Merged Subjects: {len(md_status['merged'])}")
                print(f"Cleaned Subjects: {len(md_status['cleaned'])}")
                print(f"Unmerged Subjects: {len(md_status['unmerged'])}")
                print(f"Uncleaned Subjects: {len(md_status['uncleaned'])}")
                
                # Year-based analysis (text format)
                analysis = analyze_subjects_by_year(base_output_dir)
                print(f"\nYears covered: {', '.join(map(str, analysis['summary']['years_covered']))}")
                for year in sorted(analysis["by_year"].keys()):
                    year_data = analysis["by_year"][year]
                    print(f"Year {year}: {year_data['total_count']} subjects")
                    for doc_type, count in year_data["document_types"].items():
                        if count > 0:
                            print(f"  {doc_type}: {count}")
                    print(f"  Status: P:{year_data['processing_status']['parsed']} M:{year_data['processing_status']['merged']} C:{year_data['processing_status']['cleaned']}")
                    print(f"  Serial range: min={year_data['min_serial']} max={year_data['max_serial']}")
                    if year_data.get('missing_serials'):
                        print(f"  Missing: {', '.join(year_data['missing_serials'])}")


def save_markdown_documents(markdown_documents, output_dir):
    """Save markdown documents to individual files"""
    markdown_dir = Path(output_dir) / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    for i, doc in enumerate(markdown_documents):
        filename = f"page_{i+1}.md"
        filepath = markdown_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc.text)
        print(f"Saved markdown: {filepath}")


def save_text_documents(text_documents, output_dir):
    """Save text documents to files"""
    text_dir = Path(output_dir) / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    
    for i, doc in enumerate(text_documents):
        filename = f"document_{i+1}.txt"
        filepath = text_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc.text)
        print(f"Saved text document: {filepath}")


def save_images(image_documents, output_dir):
    """Save image documents"""
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    for i, doc in enumerate(image_documents):
        if hasattr(doc, 'image_path') and doc.image_path:
            # If image is already saved to disk, copy it
            source_path = Path(doc.image_path)
            if source_path.exists():
                filename = f"image_{i+1}_{source_path.name}"
                dest_path = images_dir / filename
                shutil.copy2(source_path, dest_path)
                print(f"Copied image: {dest_path}")
        elif hasattr(doc, 'image') and doc.image:
            # If image is in memory, save it
            filename = f"image_{i+1}.png"
            filepath = images_dir / filename
            with open(filepath, 'wb') as f:
                f.write(doc.image)
            print(f"Saved image: {filepath}")


def save_page_data(pages, output_dir):
    """Save page text, markdown, layout, and structured data"""
    layout_dir = Path(output_dir) / "layout"
    structured_dir = Path(output_dir) / "structured_data"
    text_dir = Path(output_dir) / "text"
    markdown_dir = Path(output_dir) / "markdown"
    
    # Create directories
    for dir_path in [layout_dir, structured_dir, text_dir, markdown_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    for i, page in enumerate(pages):
        page_num = i + 1
        
        # Save page text
        if hasattr(page, 'text') and page.text:
            text_file = text_dir / f"page_{page_num}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(page.text)
            print(f"Saved page text: {text_file}")
        
        # Save page markdown
        if hasattr(page, 'md') and page.md:
            md_file = markdown_dir / f"page_{page_num}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(page.md)
            print(f"Saved page markdown: {md_file}")
        
        # Save page layout
        if hasattr(page, 'layout') and page.layout:
            layout_file = layout_dir / f"page_{page_num}_layout.json"
            with open(layout_file, 'w', encoding='utf-8') as f:
                try:
                    json.dump(page.layout, f, indent=2, ensure_ascii=False, default=str)
                    print(f"Saved page layout: {layout_file}")
                except Exception as e:
                    f.write(str(page.layout))
                    print(f"Saved page layout as string: {layout_file} (Error: {e})")
        
        # Save structured data
        if hasattr(page, 'structuredData') and page.structuredData:
            structured_file = structured_dir / f"page_{page_num}_structured_data.json"
            with open(structured_file, 'w', encoding='utf-8') as f:
                try:
                    json.dump(page.structuredData, f, indent=2, ensure_ascii=False, default=str)
                    print(f"Saved structured data: {structured_file}")
                except Exception as e:
                    f.write(str(page.structuredData))
                    print(f"Saved structured data as string: {structured_file} (Error: {e})")
        
        # Save page images info
        if hasattr(page, 'images') and page.images:
            images_info_file = layout_dir / f"page_{page_num}_images_info.json"
            with open(images_info_file, 'w', encoding='utf-8') as f:
                try:
                    # Try to convert image objects to dictionaries
                    images_data = []
                    for img in page.images:
                        if hasattr(img, 'model_dump'):
                            images_data.append(img.model_dump())
                        elif hasattr(img, 'dict'):
                            images_data.append(img.dict())
                        elif hasattr(img, '__dict__'):
                            # Convert object attributes to dict, handling non-serializable values
                            img_dict = {}
                            for key, value in img.__dict__.items():
                                try:
                                    # Test if the value is JSON serializable
                                    json.dumps(value)
                                    img_dict[key] = value
                                except (TypeError, ValueError):
                                    img_dict[key] = str(value)
                            images_data.append(img_dict)
                        else:
                            images_data.append(str(img))
                    
                    json.dump(images_data, f, indent=2, ensure_ascii=False)
                    print(f"Saved page images info: {images_info_file}")
                except Exception as e:
                    # Fallback: save as string representation
                    f.write(f"Images (string representation): {str(page.images)}")
                    print(f"Saved page images info as string: {images_info_file} (Error: {e})")


def organize_pdf_files_by_subject(pdf_dir):
    """
    Organize PDF files in the pdf directory by subject (first 4 digits of filename)
    Returns a dictionary with subject as key and list of file paths as values
    """
    pdf_path = Path(pdf_dir)
    subjects = defaultdict(list)
    
    # Find all PDF files in the directory
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
    
    # Group files by subject (first 4 digits)
    for pdf_file in pdf_files:
        filename = pdf_file.name
        if len(filename) >= 4 and filename[:4].isdigit():
            subject = filename[:4]
            subjects[subject].append(pdf_file)
            print(f"  {filename} -> subject {subject}")
        else:
            print(f"  Skipping {filename} - doesn't start with 4 digits")
    
    # Create subject directories and move files
    for subject, files in subjects.items():
        subject_dir = pdf_path / subject
        subject_dir.mkdir(exist_ok=True)
        
        moved_files = []
        for file_path in files:
            new_path = subject_dir / file_path.name
            if not new_path.exists():  # Only move if not already there
                shutil.move(str(file_path), str(new_path))
                print(f"Moved {file_path.name} to {subject_dir}")
            moved_files.append(new_path)
        
        subjects[subject] = moved_files
    
    return dict(subjects)


async def process_subject_batch(subject, pdf_files, base_output_dir):
    """
    Process all PDF files for a subject using batch parsing
    """
    ic("parse_start", {"subject": subject, "file_count": len(pdf_files)})
    print(f"\n=== Processing Subject {subject} ===")
    print(f"Files: {[f.name for f in pdf_files]}")
    
    # Create subject output directory
    subject_output_dir = Path(base_output_dir) / subject
    subject_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert paths to strings for the parser
    pdf_paths = [str(pdf_file) for pdf_file in pdf_files]
    
    try:
        # Batch parse all files for this subject
        print(f"Starting batch parsing of {len(pdf_paths)} files...")
        # aparse expects a sequence of FileInput; runtime library accepts list[str] paths.
        results = await parser.aparse(pdf_paths)  # type: ignore[arg-type]

        # Handle batch results (should be a list of JobResult objects)
        if not isinstance(results, list):
            results = [results]

        print(f"Got {len(results)} results from batch processing")

        # Process each result
        for i, result in enumerate(results):
            file_name = pdf_files[i].stem  # filename without extension
            print(f"\nProcessing result {i+1}/{len(results)} for file: {file_name}")

            # Create output directory for this specific file
            file_output_dir = subject_output_dir / file_name

            # Save debug information
            debug_file = file_output_dir / "results_debug.json"
            debug_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                debug_data = {
                    "file_name": file_name,
                    "subject": subject,
                    "result_type": str(type(result)),
                    "attributes": [attr for attr in dir(result) if not attr.startswith('_')],
                }

                if hasattr(result, 'pages'):
                    try:
                        if isinstance(result.pages, list):
                            debug_data["pages_count"] = len(result.pages)
                        else:
                            debug_data["pages_info"] = str(result.pages)
                    except Exception:
                        debug_data["pages_info"] = "Cannot determine pages info"

                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(debug_data, f, indent=2, ensure_ascii=False, default=str)
                print(f"Saved debug results to: {debug_file}")

            except Exception as e:
                print(f"Error saving debug results: {e}")

            # Process the result if it has pages
            if hasattr(result, 'pages'):
                try:
                    pages_count = len(result.pages) if isinstance(result.pages, list) else "unknown"
                    print(f"  Processing {pages_count} pages...")
                except Exception:
                    print("  Processing pages...")

                # Save all page data (text, markdown, layout, structured data)
                save_page_data(result.pages, file_output_dir)

                # Get and save the llama-index documents
                try:
                    markdown_documents = result.get_markdown_documents(split_by_page=True)
                    save_markdown_documents(markdown_documents, file_output_dir)
                except Exception as e:
                    print(f"  Error getting markdown documents: {e}")

                try:
                    text_documents = result.get_text_documents(split_by_page=False)
                    save_text_documents(text_documents, file_output_dir)
                except Exception as e:
                    print(f"  Error getting text documents: {e}")

                try:
                    image_documents = result.get_image_documents(
                        include_screenshot_images=True,
                        include_object_images=False,
                        image_download_dir=str(file_output_dir / "images"),
                    )
                    save_images(image_documents, file_output_dir)
                except Exception as e:
                    print(f"  Error getting image documents: {e}")

                print(f"  ✅ Completed processing for {file_name}")
            else:
                print(f"  ⚠️  Result for {file_name} has no pages attribute")

        # Record subject-level parse event with file hashes
        append_subject_event(subject_output_dir, "parse", {
            "files": collect_subject_file_hashes(pdf_files),
            "result_count": len(results)
        })
        append_subject_log(subject_output_dir, "parse", {
            "files": collect_subject_file_hashes(pdf_files),
            "result_count": len(results)
        })
        ic("parse_complete", {"subject": subject, "results": len(results)})
        print(f"\n✅ Subject {subject} batch processing completed!")
        print(f"Results saved to: {subject_output_dir}")
        return True

    except Exception as e:
        print(f"❌ Error processing subject {subject}: {e}")
        return False


def categorize_documents_by_type(subject_output_dir):
    """
    Categorize documents in a subject folder by their ending letters
    Returns a dictionary with document types as keys and lists of document folders as values
    """
    subject_path = Path(subject_output_dir)
    
    # Document type mapping with descriptions
    doc_types = {
        'E': {'name': 'Admission Notes', 'folders': []},
        'A': {'name': 'Release Notes', 'folders': []},
        'BIC': {'name': 'Death Notices', 'folders': []},
        'O': {'name': 'Death Certificates', 'folders': []}
    }
    
    # Find all document folders in the subject directory
    if not subject_path.exists():
        print(f"Subject directory not found: {subject_path}")
        return doc_types
    
    for item in subject_path.iterdir():
        if item.is_dir() and item.name != 'merged':  # Skip merged folder if it exists
            folder_name = item.name
            
            # Check document type by ending
            if folder_name.endswith('BIC'):
                doc_types['BIC']['folders'].append(item)
            elif folder_name.endswith('E'):
                doc_types['E']['folders'].append(item)
            elif folder_name.endswith('A'):
                doc_types['A']['folders'].append(item)
            elif folder_name.endswith('O'):
                doc_types['O']['folders'].append(item)
            else:
                print(f"Unknown document type for folder: {folder_name}")
    
    # Sort folders within each type for consistent ordering
    for doc_type in doc_types.values():
        doc_type['folders'].sort(key=lambda x: x.name)
    
    return doc_types


def merge_pages_for_document(doc_folder):
    """
    Merge all markdown pages for a single document into one text
    Returns the merged content with page separators
    """
    markdown_dir = doc_folder / 'markdown'
    
    if not markdown_dir.exists():
        print(f"No markdown folder found in: {doc_folder}")
        return ""
    
    # Get all markdown files and sort them by page number
    md_files = list(markdown_dir.glob('page_*.md'))
    md_files.sort(key=lambda x: int(x.stem.split('_')[1]))  # Sort by page number
    
    if not md_files:
        print(f"No markdown files found in: {markdown_dir}")
        return ""
    
    merged_content = []
    
    for md_file in md_files:
        page_num = md_file.stem.split('_')[1]
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                page_content = f.read().strip()
            
            # Add page separator and content
            merged_content.append(f"## Page {page_num}")
            merged_content.append("")  # Empty line
            merged_content.append(page_content)
            merged_content.append("")  # Empty line after content
            
        except Exception as e:
            print(f"Error reading {md_file}: {e}")
            merged_content.append(f"## Page {page_num}")
            merged_content.append("")
            merged_content.append(f"*Error reading page content: {e}*")
            merged_content.append("")
    
    return "\n".join(merged_content)


def merge_documents_by_subject(subject_output_dir):
    """
    Merge all documents for a subject in the specified order with clear separations
    """
    subject_path = Path(subject_output_dir)
    subject_name = subject_path.name
    
    ic("merge_start", {"subject": subject_name})
    print(f"\n=== Merging documents for Subject {subject_name} ===")
    
    # Categorize documents
    doc_types = categorize_documents_by_type(subject_output_dir)
    
    # Check if there are any documents to merge
    total_docs = sum(len(doc_type['folders']) for doc_type in doc_types.values())
    if total_docs == 0:
        print(f"No documents found for subject {subject_name}")
        return False
    
    # Create the merged document content
    merged_content = []
    
    # Add document header
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    merged_content.extend([
        f"# Medical Records - Subject {subject_name}",
        "",
        f"*Generated on: {current_time}*",
        "",
        "---",
        ""
    ])
    
    # Process documents in the specified order
    processing_order = ['E', 'A', 'BIC', 'O']
    
    for doc_type in processing_order:
        doc_info = doc_types[doc_type]
        folders = doc_info['folders']
        
        if not folders:
            continue
        
        print(f"  Processing {len(folders)} {doc_info['name']} documents...")
        
        # Add section header
        merged_content.extend([
            f"# {doc_info['name']} ({doc_type})",
            "",
        ])
        
        # Process each document of this type
        for i, doc_folder in enumerate(folders, 1):
            doc_name = doc_folder.name
            print(f"    - {doc_name}")
            
            # Add document separator
            merged_content.extend([
                f"## Document: {doc_name}",
                "",
            ])
            
            # Merge pages for this document
            document_content = merge_pages_for_document(doc_folder)
            if document_content:
                merged_content.append(document_content)
            else:
                merged_content.extend([
                    "*No content available for this document.*",
                    ""
                ])
            
            # Add separator between documents (except for the last one in the type)
            if i < len(folders):
                merged_content.extend([
                    "",
                    "---",
                    ""
                ])
        
        # Add section separator (except for the last section)
        merged_content.extend([
            "",
            "=" * 80,
            ""
        ])
    
    # Save the merged document
    merged_file = subject_path / f"{subject_name}_merged_medical_records.md"
    
    try:
        with open(merged_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(merged_content))
        
        print(f"  ✅ Merged document saved: {merged_file}")
        append_subject_event(subject_path, "merge", {
            "output_file": merged_file.name,
            "total_documents": total_docs,
            "doc_types": {k: len(v['folders']) for k, v in doc_types.items()}
        })
        append_subject_log(subject_path, "merge", {
            "output_file": merged_file.name,
            "total_documents": total_docs,
            "doc_types": {k: len(v['folders']) for k, v in doc_types.items()}
        })
        ic("merge_complete", {"subject": subject_name, "docs": total_docs})
        
        # Create a summary
        summary_lines = [
            f"## Merge Summary for Subject {subject_name}",
            "",
        ]
        
        for doc_type in processing_order:
            doc_info = doc_types[doc_type]
            folders = doc_info['folders']
            if folders:
                summary_lines.append(f"- **{doc_info['name']} ({doc_type})**: {len(folders)} documents")
                for folder in folders:
                    summary_lines.append(f"  - {folder.name}")
        
        summary_lines.extend([
            "",
            f"**Total documents merged**: {total_docs}",
            f"**Output file**: `{merged_file.name}`"
        ])
        
        print("\n" + "\n".join(summary_lines))
        return True
        
    except Exception as e:
        print(f"  ❌ Error saving merged document: {e}")
        return False


def process_all_subjects_markdown(base_output_dir):
    """
    Process markdown merging for all subjects in the output directory
    """
    base_path = Path(base_output_dir)
    
    if not base_path.exists():
        print(f"Output directory not found: {base_output_dir}")
        return
    
    print(f"\n=== Processing Markdown Merging for All Subjects ===")
    
    # Find all subject directories (4-digit numbers)
    subject_dirs = [d for d in base_path.iterdir() 
                   if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
    
    if not subject_dirs:
        print("No subject directories found")
        return
    
    successful_merges = 0
    failed_merges = 0
    
    for subject_dir in subject_dirs:
        try:
            success = merge_documents_by_subject(subject_dir)
            if success:
                successful_merges += 1
            else:
                failed_merges += 1
        except Exception as e:
            print(f"❌ Critical error processing subject {subject_dir.name}: {e}")
            failed_merges += 1
    
    # Final summary
    print(f"\n=== Markdown Merging Summary ===")
    print(f"✅ Successfully merged: {successful_merges} subjects")
    print(f"❌ Failed to merge: {failed_merges} subjects")
    print(f"📁 Total subjects: {len(subject_dirs)}")


def clean_merged_markdown_files(base_output_dir: str | Path):
    """Clean merged markdown files by removing hospital-specific expressions.

    Supports being called with either the root output directory (cleans all subjects)
    or a specific subject directory. Always writes a cleaned file (even if unchanged)
    to make downstream tooling deterministic. Returns list of cleaned file names.
    """
    print(f"\n=== Cleaning Merged Markdown Files (non-destructive) ===")
    
    # Define expressions to remove
    expressions_to_remove = [
        "ULS DE SAO JOAO, E.P.E.",
        "H. SAO JOAO",
        "ALAMEDA PROF. HERNANI MONTEIRO",
        "4200-319 PORTO",
        "Tel. : 225512100  Email:",
        "Tel.: 225512100",
        "Processado por computador - SClínico",
        "Email:",
        "SÃO JOÃO"
    ]
    
    base_path = Path(base_output_dir)
    
    if not base_path.exists():
        print(f"Output directory not found: {base_output_dir}")
        return 0
    
    # Determine scope: single subject dir or all subjects
    if base_path.name.isdigit() and len(base_path.name) == 4 and (base_path / f"{base_path.name}_merged_medical_records.md").parent.exists():
        subject_dirs = [base_path]
    else:
        subject_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
    
    if not subject_dirs:
        print("No subject directories found")
        return 0
    
    cleaned_files: List[str] = []
    total_removals = 0
    
    for subject_dir in subject_dirs:
        subject = subject_dir.name
        merged_file = subject_dir / f"{subject}_merged_medical_records.md"
        cleaned_file = subject_dir / f"{subject}_merged_medical_records.cleaned.md"

        if not merged_file.exists():
            print(f"  ⚠️  No merged file found for subject {subject}")
            continue

        try:
            with open(merged_file, 'r', encoding='utf-8') as f:
                content = f.read()
            original_content = content
            file_removals = 0
            for expression in expressions_to_remove:
                count_before = content.count(expression)
                if count_before > 0:
                    content = content.replace(expression, "")
                    file_removals += count_before
                    print(f"    - Removed '{expression}' ({count_before} occurrences)")
            lines = content.split('\n')
            cleaned_lines: List[str] = []
            for line in lines:
                cleaned_line = line.lstrip(' \t')
                stripped_line = cleaned_line.strip()
                if stripped_line or (cleaned_lines and cleaned_lines[-1].strip()):
                    cleaned_lines.append(cleaned_line)
            while cleaned_lines and not cleaned_lines[-1].strip():
                cleaned_lines.pop()
            content = '\n'.join(cleaned_lines)
            # Always write cleaned file for determinism
            with open(cleaned_file, 'w', encoding='utf-8') as f:
                f.write(content)
            cleaned_files.append(cleaned_file.name)
            total_removals += file_removals
            status_msg = "(modified)" if content != original_content else "(no changes)"
            print(f"  ✅ Cleaned -> {cleaned_file.name} {status_msg}; expressions removed: {file_removals}")
            append_subject_event(subject_dir, "clean", {
                "source": merged_file.name,
                "output": cleaned_file.name,
                "expressions_removed": file_removals
            })
            append_subject_log(subject_dir, "clean", {
                "source": merged_file.name,
                "output": cleaned_file.name,
                "expressions_removed": file_removals
            })
            ic("clean_complete", {"subject": subject, "removed": file_removals})
        except Exception as e:
            print(f"  ❌ Error cleaning {merged_file.name}: {e}")
    
    print(f"\n📊 Cleaning Summary:")
    print(f"  ✅ Files cleaned: {len(cleaned_files)}/{len(subject_dirs)} (cleaned copies written)")
    print(f"  🧹 Total expressions removed: {total_removals}")
    return cleaned_files


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="PDF Parser with LlamaParse - Batch processing with markdown merging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run full workflow (default)
  python main.py --full             # Run full workflow explicitly
  python main.py --parse-only       # Only parse PDFs with LlamaParse
  python main.py --merge-only       # Only merge markdown files
  python main.py --clean-only       # Only clean merged markdown files
  python main.py --force            # Force processing, skip all checkpoints
        """
    )
    
    # Workflow mode flags (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--full', 
        action='store_true', 
        help='Run full workflow: PDF parsing + markdown merging (default)'
    )
    mode_group.add_argument(
        '--parse-only', 
        action='store_true', 
        help='Only run PDF parsing with LlamaParse'
    )
    mode_group.add_argument(
        '--merge-only', 
        action='store_true', 
        help='Only run markdown merging (skip PDF parsing)'
    )
    mode_group.add_argument(
        '--clean-only', 
        action='store_true', 
        help='Only clean merged markdown files (remove hospital info)'
    )
    parser.add_argument(
        '--menu',
        action='store_true',
        help='Launch interactive menu (overrides other workflow flags)'
    )
    
    # Control flags
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Force processing, skip all checkpoints'
    )
    parser.add_argument(
        '--skip-existing', 
        action='store_true', 
        default=True,
        help='Skip processing if outputs already exist (default: True)'
    )
    parser.add_argument(
        '--no-skip-existing', 
        dest='skip_existing',
        action='store_false', 
        help='Process even if outputs already exist'
    )
    
    args = parser.parse_args()
    
    # Default to full workflow if no mode specified
    if not any([args.full, args.parse_only, args.merge_only, args.clean_only]):
        args.full = True
    
    return args


def check_new_pdfs(pdf_dir):
    """
    Check if there are new PDF files in the main pdf/ folder
    Returns: (has_new_pdfs, pdf_files_list)
    """
    pdf_path = Path(pdf_dir)
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    if not pdf_files:
        return False, []
    
    print(f"📄 Found {len(pdf_files)} PDF files in {pdf_dir}:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    return True, pdf_files


def check_subject_already_processed(subject, base_output_dir):
    """
    Check if a subject has already been processed
    Returns: (is_processed, subject_output_dir)
    """
    subject_output_dir = Path(base_output_dir) / subject
    
    if not subject_output_dir.exists():
        return False, subject_output_dir
    
    # Check if there are any document folders in the subject directory
    doc_folders = [d for d in subject_output_dir.iterdir() 
                  if d.is_dir() and d.name != 'merged']
    
    if not doc_folders:
        return False, subject_output_dir
    
    # Check if at least one document folder has content
    for doc_folder in doc_folders:
        markdown_dir = doc_folder / 'markdown'
        if markdown_dir.exists() and list(markdown_dir.glob('*.md')):
            return True, subject_output_dir
    
    return False, subject_output_dir


def check_subject_already_merged(subject, base_output_dir):
    """
    Check if a subject's markdown has already been merged
    Returns: (is_merged, merged_file_path)
    """
    subject_output_dir = Path(base_output_dir) / subject
    merged_file = subject_output_dir / f"{subject}_merged_medical_records.md"
    
    if merged_file.exists() and merged_file.stat().st_size > 0:
        return True, merged_file
    
    return False, merged_file


def get_processing_plan(args, pdf_dir, base_output_dir):
    """
    Analyze current state and create a processing plan based on args and checkpoints
    """
    plan = {
        'parse_pdfs': False,
        'merge_markdown': False,
        'subjects_to_parse': {},
        'subjects_to_merge': [],
        'skip_reasons': [],
        'force_reasons': []
    }
    
    # Check for new PDFs
    has_new_pdfs, pdf_files = check_new_pdfs(pdf_dir)
    
    # Determine what to do based on mode and checkpoints
    if args.parse_only or args.full:
        if not has_new_pdfs and not args.force:
            plan['skip_reasons'].append("No new PDFs found in main pdf/ folder")
        else:
            if has_new_pdfs:
                # Organize files by subject and check if already processed
                subjects = {}
                for pdf_file in pdf_files:
                    filename = pdf_file.name
                    if len(filename) >= 4 and filename[:4].isdigit():
                        subject = filename[:4]
                        if subject not in subjects:
                            subjects[subject] = []
                        subjects[subject].append(pdf_file)
                
                for subject, files in subjects.items():
                    is_processed, subject_dir = check_subject_already_processed(subject, base_output_dir)
                    
                    if is_processed and args.skip_existing and not args.force:
                        plan['skip_reasons'].append(f"Subject {subject} already processed")
                    else:
                        plan['subjects_to_parse'][subject] = files
                        if is_processed and args.force:
                            plan['force_reasons'].append(f"Subject {subject} - reprocessing (forced)")
                
                if plan['subjects_to_parse']:
                    plan['parse_pdfs'] = True
    
    if args.merge_only or args.full:
        # Find all subjects in output directory
        base_path = Path(base_output_dir)
        if base_path.exists():
            subject_dirs = [d for d in base_path.iterdir() 
                           if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
            
            for subject_dir in subject_dirs:
                subject = subject_dir.name
                is_merged, merged_file = check_subject_already_merged(subject, base_output_dir)
                
                if is_merged and args.skip_existing and not args.force:
                    plan['skip_reasons'].append(f"Subject {subject} already merged")
                else:
                    plan['subjects_to_merge'].append(subject)
                    if is_merged and args.force:
                        plan['force_reasons'].append(f"Subject {subject} - remerging (forced)")
            
            if plan['subjects_to_merge']:
                plan['merge_markdown'] = True
    
    return plan


async def main():
    # Parse command line arguments
    args = parse_arguments()

    # If interactive menu requested, launch it and exit
    if getattr(args, 'menu', False):
        if CONSOLE:
            CONSOLE.print(Panel("Launching Interactive Menu", style="cyan", title="CLI"))
        await menu_root()
        return
    
    print("🔥 PDF Parser with LlamaParse - Advanced Workflow")
    print(f"LLAMA_CLOUD_API_KEY: {LLAMA_CLOUD_API_KEY}")
    
    # Configuration
    pdf_dir = "./pdf"
    base_output_dir = "./pdf/output"
    
    # Show current mode
    if args.full:
        mode = "Full Workflow (PDF Parsing + Markdown Merging + Cleaning)"
    elif args.parse_only:
        mode = "PDF Parsing Only"
    elif args.merge_only:
        mode = "Markdown Merging Only"
    elif args.clean_only:
        mode = "Markdown Cleaning Only"
    
    print(f"🎯 Mode: {mode}")
    print(f"⚡ Force processing: {'Yes' if args.force else 'No'}")
    print(f"🔍 Skip existing: {'Yes' if args.skip_existing else 'No'}")
    
    # Step 1: Analyze current state and create processing plan
    print(f"\n=== Step 1: Analyzing Current State ===")
    plan = get_processing_plan(args, pdf_dir, base_output_dir)
    
    # Display plan
    print(f"\n📋 Processing Plan:")
    print(f"  📄 Parse PDFs: {'Yes' if plan['parse_pdfs'] else 'No'}")
    print(f"  📝 Merge Markdown: {'Yes' if plan['merge_markdown'] else 'No'}")
    print(f"  🧹 Clean Markdown: {'Yes' if args.clean_only or args.full else 'No'}")
    
    if plan['skip_reasons']:
        print(f"\n⏭️  Skipping reasons:")
        for reason in plan['skip_reasons']:
            print(f"    - {reason}")
    
    if plan['force_reasons']:
        print(f"\n💪 Force processing:")
        for reason in plan['force_reasons']:
            print(f"    - {reason}")
    
    if plan['subjects_to_parse']:
        print(f"\n📄 Subjects to parse ({len(plan['subjects_to_parse'])}):")
        for subject, files in plan['subjects_to_parse'].items():
            print(f"    - Subject {subject}: {len(files)} files")
    
    if plan['subjects_to_merge']:
        print(f"\n📝 Subjects to merge ({len(plan['subjects_to_merge'])}):")
        for subject in plan['subjects_to_merge']:
            print(f"    - Subject {subject}")
    
    # Step 2: Execute PDF parsing if needed
    successful_subjects = []
    failed_subjects = []
    
    if plan['parse_pdfs']:
        print(f"\n=== Step 2: PDF Processing ===")
        
        # Organize PDF files by subject first
        print("📁 Organizing PDF files by subject...")
        subjects = organize_pdf_files_by_subject(pdf_dir)
        
        # Filter subjects based on plan
        subjects_to_process = {k: v for k, v in subjects.items() 
                             if k in plan['subjects_to_parse']}
        
        if subjects_to_process:
            print(f"\n🔄 Processing {len(subjects_to_process)} subjects...")
            
            for subject, pdf_files in subjects_to_process.items():
                try:
                    success = await process_subject_batch(subject, pdf_files, base_output_dir)
                    if success:
                        successful_subjects.append(subject)
                    else:
                        failed_subjects.append(subject)
                except Exception as e:
                    print(f"❌ Critical error processing subject {subject}: {e}")
                    failed_subjects.append(subject)
            
            # Summary
            print(f"\n📊 PDF Processing Summary:")
            print(f"  ✅ Successfully processed: {len(successful_subjects)} subjects")
            print(f"  ❌ Failed to process: {len(failed_subjects)} subjects")
        else:
            print("📭 No subjects need PDF processing")
    else:
        print(f"\n=== Step 2: PDF Processing (Skipped) ===")
        print("📭 No PDF processing needed based on current plan")
    
    # Step 3: Execute markdown merging if needed
    if plan['merge_markdown']:
        print(f"\n=== Step 3: Markdown Merging ===")
        
        # Filter subjects to merge based on plan
        subjects_to_merge = plan['subjects_to_merge']
        
        if subjects_to_merge:
            print(f"🔄 Processing markdown merging for {len(subjects_to_merge)} subjects...")
            
            merge_successful = 0
            merge_failed = 0
            
            for subject in subjects_to_merge:
                try:
                    subject_output_dir = Path(base_output_dir) / subject
                    success = merge_documents_by_subject(subject_output_dir)
                    if success:
                        merge_successful += 1
                    else:
                        merge_failed += 1
                except Exception as e:
                    print(f"❌ Critical error merging subject {subject}: {e}")
                    merge_failed += 1
            
            print(f"\n📊 Markdown Merging Summary:")
            print(f"  ✅ Successfully merged: {merge_successful} subjects")
            print(f"  ❌ Failed to merge: {merge_failed} subjects")
        else:
            print("📭 No subjects need markdown merging")
    else:
        print(f"\n=== Step 3: Markdown Merging (Skipped) ===")
        print("📭 No markdown merging needed based on current plan")
    
    # Final Summary
    print(f"\n🎉 Workflow Completed!")
    
    if plan['parse_pdfs']:
        print(f"📄 PDF Processing: {len(successful_subjects)}/{len(successful_subjects) + len(failed_subjects)} subjects completed")
    
    if plan['merge_markdown']:
        print(f"📝 Markdown Merging: Processed {len(plan['subjects_to_merge'])} subjects")
    
    # Step 4: Clean markdown files if needed
    if args.clean_only or args.full:
        print(f"\n=== Step 4: Markdown Cleaning ===")
        cleaned_files_list = clean_merged_markdown_files(base_output_dir)
        cleaned_count = len(cleaned_files_list) if isinstance(cleaned_files_list, list) else 0
        if cleaned_count > 0:
            print(f"🧹 Markdown Cleaning: Created {cleaned_count} cleaned file(s)")
            report_parser("clean_markdown", cleaned_files_list if isinstance(cleaned_files_list, list) else [], [])
        else:
            print("🧹 Markdown Cleaning: No files needed cleaning")
    else:
        print(f"\n=== Step 4: Markdown Cleaning (Skipped) ===")
        print("🧹 No markdown cleaning needed based on current plan")
    
    if not plan['parse_pdfs'] and not plan['merge_markdown'] and not (args.clean_only or args.full):
        print("📭 Nothing to process - all outputs are up to date!")
        print("💡 Use --force to reprocess existing files")
    
    print(f"\n📁 Check outputs in: {base_output_dir}/")
    print("💡 Use --help to see all available options")


if __name__ == "__main__":
    asyncio.run(main())
