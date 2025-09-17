"""
Project detection module for Resume Customizer.
Handles detection of projects, tech stacks, and responsibilities sections in documents.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from docx.document import Document as DocumentType
import re


@dataclass
class ProjectInfo:
    """Data class to hold project information."""
    name: str
    start_index: int
    end_index: int
    role: str = ""
    company: str = ""
    date_range: str = ""
    bullet_points: List[str] = None

    def __post_init__(self):
        self.bullet_points = self.bullet_points or []


class ProjectDetector:
    """
    Handles detection of projects and responsibilities sections in resumes.

    Notes:
    - Can detect generic tech stack headers followed by bullets.
    - Conservatively detects experience sections.
    - Extracts company, role, date if formatted.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            "project_exclude_keywords": [
                "summary", "skills", "education", "achievements", "responsibilities:",
                "contact", "professional"
            ],
            "job_title_keywords": [
                "manager", "developer", "engineer", "analyst", "lead",
                "architect", "specialist", "consultant", "intern", "administrator"
            ],
            "section_headings": [
                "professional experience", "work experience",
                "employment", "career history", "work history"
            ]
        }

    def find_projects(self, doc: DocumentType) -> List[ProjectInfo]:
        """
        Find all projects, tech stacks, and their bullet points in the resume.
        """
        projects: List[ProjectInfo] = []
        current_project: Optional[ProjectInfo] = None
        in_experience_section = False
        i = 0
        paragraphs = doc.paragraphs

        while i < len(paragraphs):
            para = paragraphs[i]
            text = para.text.strip()

            # Skip empty paragraphs
            if not text:
                i += 1
                continue

            # Check if current paragraph is a section heading
            if self._is_section_heading(text):
                in_experience_section = True
                i += 1
                continue

            # Only process inside experience section if section exists
            # Comment out next line if you want to allow outside-section detection
            # if not in_experience_section:
            #     i += 1
            #     continue

            # Check if line looks like company/date header
            if self._looks_like_company_date(text):
                if current_project:
                    projects.append(current_project)
                
                # Get company/date info
                role, company, date_range = self._parse_project_header(text)
                
                # Check if next paragraph might be a job title/role
                next_role = ""
                if i + 1 < len(paragraphs):
                    next_text = paragraphs[i + 1].text.strip()
                    if next_text and not self._is_bullet_point(next_text) and not self._looks_like_company_date(next_text):
                        # This is likely the job title/role
                        next_role = next_text
                        i += 1  # Skip this line in next iteration
                
                current_project = ProjectInfo(
                    name=company or f"Project {len(projects)+1}",
                    start_index=i,
                    end_index=i,
                    role=next_role or role,
                    company=company,
                    date_range=date_range
                )
                i += 1
                continue

            # Start a new project if line is non-bullet, not excluded, and has following bullets
            if (not self._is_bullet_point(text) and 
                text.lower() not in self.config["project_exclude_keywords"]):

                # Check next lines for bullets
                bullets = []
                j = i + 1
                while j < len(paragraphs):
                    next_text = paragraphs[j].text.strip()
                    if not next_text:
                        j += 1
                        continue
                    if self._is_bullet_point(next_text):
                        bullets.append(next_text)
                        j += 1
                    else:
                        break

                if bullets:
                    # Finish previous project
                    if current_project:
                        projects.append(current_project)

                    current_project = ProjectInfo(
                        name=text,
                        start_index=i,
                        end_index=i + len(bullets),
                        bullet_points=bullets
                    )
                    projects.append(current_project)
                    current_project = None
                    i = j
                    continue

            # Collect bullets for current project if any
            if current_project and self._is_bullet_point(text):
                current_project.bullet_points.append(text)
                current_project.end_index = i

            i += 1

        # Append last project if exists
        if current_project:
            projects.append(current_project)

        return projects

    def _parse_project_header(self, text: str) -> Tuple[str, str, str]:
        """
        Parse project header into role, company, and date range.
        Handles multiple formats like:
          - Company | Date
          - Company - Date
          - Company (Date)
          - Role only
          - Job title | Company | Industry | Date
        """
        # Check for the specific format: "Job title | Company | Industry | Date"
        job_title_pattern = r"^((?:Senior|Junior|Lead|Principal|Staff)?\s*(?:Software|Web|Mobile|Frontend|Backend|Full-stack|Full Stack|UI|UX)?\s*(?:Developer|Engineer|Architect|Designer|Programmer|Consultant))\s*\|(.*?)\|(.*?)\|(.*\d{4}.*)$"
        match = re.search(job_title_pattern, text, re.IGNORECASE)
        if match:
            role = match.group(1).strip()
            company = match.group(2).strip()
            industry = match.group(3).strip()  # Industry info
            date_range = match.group(4).strip()
            # Include industry in company name for better context
            if industry:
                company += f" | {industry}"
            return role, company, date_range
            
        if '\n' in text:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            first_line = lines[0] if lines else text.strip()
            if '|' in first_line:
                parts = [p.strip() for p in first_line.split('|')]
                company = parts[0].strip()
                date_range = parts[-1].strip()
                role = lines[1].strip() if len(lines) > 1 else ""
                return role, company, date_range

        if '|' in text:
            parts = [p.strip() for p in text.split('|')]
            if len(parts) >= 2:
                return "", parts[0], parts[-1]

        for separator in [' - ', ' – ', ' — ']:
            if separator in text:
                parts = [p.strip() for p in text.split(separator)]
                if len(parts) == 2:
                    return "", parts[0], parts[1]
                break

        m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", text.strip())
        if m:
            return "", m.group(1).strip(), m.group(2).strip()

        return text, "", ""

    def _is_responsibilities_heading(self, text: str) -> bool:
        """Check if text is a responsibilities heading."""
        text_lower = text.lower()
        return any(
            text_lower.startswith(prefix)
            for prefix in ["responsibilities", "key responsibilities", "duties:", "tasks:", "role:", "achievements:"]
        )

    def _is_bullet_point(self, text: str) -> bool:
        """Check if text looks like a bullet point."""
        text = text.strip()
        bullet_markers = ['•', '●', '◦', '▪', '▫', '‣', '*', '-']
        return any(text.startswith(marker) for marker in bullet_markers) or \
               (text and text[0].isdigit() and '.' in text[:3])

    def _looks_like_company_date(self, text: str) -> bool:
        """Check if text looks like Company | Date or Company - Date format."""
        tl = text.strip().lower()
        has_year = re.search(r"\b(19|20)\d{2}\b", tl) is not None
        has_month = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", tl) is not None
        has_present = 'present' in tl

        # Check for job title | company | industry | date format
        job_title_pattern = r"^(?:Senior|Junior|Lead|Principal|Staff)?\s*(?:Software|Web|Mobile|Frontend|Backend|Full-stack|Full Stack|UI|UX)?\s*(?:Developer|Engineer|Architect|Designer|Programmer|Consultant)\s*\|.*\|.*\|.*\d{4}"
        if re.search(job_title_pattern, text, re.IGNORECASE):
            return True

        if has_year or has_month or has_present:
            if len(tl.split()) >= 2:
                if '|' in text or ' - ' in text or ' – ' in text or ' — ' in text or '(' in text or ' to ' in tl:
                    return True
                if re.search(r".+\(\s*(19|20)\d{2}", text):
                    return True
        return False

    def _is_section_heading(self, text: str) -> bool:
        """Check if text is a section heading like 'Professional Experience'."""
        text_lower = text.lower().strip()
        text_nocol = text_lower.rstrip(':').strip()

        if text_nocol in self.config["section_headings"]:
            return True

        if text_lower.endswith(':') and any(h in text_lower for h in self.config["section_headings"]):
            if len(text_lower.split()) <= 6:
                return True

        if 'experience' in text_lower and len(text_lower.split()) <= 4 and not any(ch in text_lower for ch in ['.', ',']):
            return True

        return False
