"""
Local JSON-backed store for resume formats (fallback when DB is unavailable)
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
import uuid
from datetime import datetime


class LocalFormatStore:
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path or Path('data') / 'format_templates.json')
        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write([])

    def _read(self) -> List[Dict]:
        try:
            with self.file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def _write(self, data: List[Dict]):
        with self.file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def list_formats(self) -> List[Dict]:
        return self._read()

    def save_format(self, format_obj: Dict) -> str:
        records = self._read()
        # assign id and timestamps
        fid = format_obj.get('id') or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        record = {
            'id': fid,
            'name': format_obj.get('name'),
            'description': format_obj.get('description'),
            'name_pattern': format_obj.get('name_pattern', {}),
            'email_pattern': format_obj.get('email_pattern', {}),
            'phone_pattern': format_obj.get('phone_pattern', {}),
            'section_patterns': format_obj.get('section_patterns', {}),
            'company_patterns': format_obj.get('company_patterns', []),
            'title_patterns': format_obj.get('title_patterns', []),
            'last_used': format_obj.get('last_used', now),
            'match_count': format_obj.get('match_count', 0)
        }
        records.append(record)
        self._write(records)
        return fid

    def delete_format(self, fid: str) -> bool:
        records = self._read()
        new = [r for r in records if r.get('id') != fid]
        if len(new) == len(records):
            return False
        self._write(new)
        return True

    def get_format(self, fid: str) -> Optional[Dict]:
        records = self._read()
        for r in records:
            if r.get('id') == fid:
                return r
        return None
