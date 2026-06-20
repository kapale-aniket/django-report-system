"""Content-aware report analysis when no LLM API key is configured."""
from __future__ import annotations

import re
from typing import Any

_SECTION_CHECKS: list[tuple[str, str, re.Pattern[str]]] = [
    ('Introduction', 'introduction', re.compile(r'\b(introduction|background|overview|problem statement)\b', re.I)),
    ('Literature review', 'literature', re.compile(r'\b(literature review|related work|prior work|state of the art)\b', re.I)),
    ('Methodology', 'methodology', re.compile(r'\b(methodology|methods|system design|implementation|approach)\b', re.I)),
    ('Results / analysis', 'results', re.compile(r'\b(results|findings|analysis|evaluation|experiments)\b', re.I)),
    ('Conclusion', 'conclusion', re.compile(r'\b(conclusion|summary|future work|recommendations)\b', re.I)),
    ('References', 'references', re.compile(r'\b(references|bibliography|works cited)\b', re.I)),
]

_QUALITY_SIGNALS: list[tuple[str, re.Pattern[str]]] = [
    ('objectives', re.compile(r'\b(objective|aim|goal|purpose)\b', re.I)),
    ('diagrams', re.compile(r'\b(figure|diagram|chart|graph|table)\b', re.I)),
    ('citations', re.compile(r'\(\d{4}\)|\[\d+\]|et al\.', re.I)),
    ('appendix', re.compile(r'\bappendix\b', re.I)),
]


def _word_count(text: str) -> int:
    return len(re.findall(r'\w+', text))


def _detect_sections(text: str) -> dict[str, bool]:
    found: dict[str, bool] = {}
    for _label, key, pattern in _SECTION_CHECKS:
        found[key] = bool(pattern.search(text))
    return found


def _detect_signals(text: str) -> dict[str, bool]:
    return {key: bool(pattern.search(text)) for key, pattern in _QUALITY_SIGNALS}


def _length_band(words: int) -> str:
    if words < 500:
        return 'very_short'
    if words < 1200:
        return 'short'
    if words < 2500:
        return 'adequate'
    if words < 4500:
        return 'detailed'
    return 'comprehensive'


def _score_for_criterion(name: str, max_score: int, coverage: float, words: int) -> int:
    name_lower = (name or '').lower()
    base_ratio = 0.45 + (0.45 * coverage)
    if words >= 1200:
        base_ratio += 0.05
    if words >= 2500:
        base_ratio += 0.05

    if any(token in name_lower for token in ('content', 'technical', 'quality', 'understanding')):
        base_ratio += 0.05 if coverage >= 0.6 else -0.05
    if any(token in name_lower for token in ('presentation', 'format', 'structure', 'organization')):
        base_ratio += 0.05 if coverage >= 0.5 else -0.03
    if any(token in name_lower for token in ('original', 'creativity', 'innovation')):
        base_ratio += 0.03

    base_ratio = max(0.35, min(0.92, base_ratio))
    return max(0, min(max_score, int(round(max_score * base_ratio))))


def _build_summary(report_title: str, text: str, sections: dict[str, bool], words: int) -> str:
    if not text.strip():
        return (
            f'Report "{report_title}" could not be analyzed automatically because no readable text was extracted. '
            'The file may be scanned, image-based, or empty — please review it manually.'
        )

    present = [label for label, key, _ in _SECTION_CHECKS if sections.get(key)]
    missing = [label for label, key, _ in _SECTION_CHECKS if not sections.get(key)]
    band = _length_band(words)

    length_phrase = {
        'very_short': 'is quite brief',
        'short': 'is moderately sized but may need more depth',
        'adequate': 'has a reasonable length for a project report',
        'detailed': 'is detailed and substantial',
        'comprehensive': 'is comprehensive and well developed',
    }[band]

    parts = [
        f'Report "{report_title}" {length_phrase} (about {words:,} words).',
    ]
    if present:
        parts.append(f'Sections identified: {", ".join(present)}.')
    if missing:
        parts.append(f'Sections not clearly found: {", ".join(missing)}.')
    return ' '.join(parts)


def _build_feedback(
    report_title: str,
    text: str,
    sections: dict[str, bool],
    signals: dict[str, bool],
    words: int,
    criteria: list[dict],
) -> str:
    if not text.strip():
        return (
            f'I reviewed "{report_title}" but could not extract readable text from the uploaded file. '
            'Please open the document and confirm it includes a clear introduction, methodology, results, '
            'conclusion, and references. If this is a scanned PDF, ask the student to submit a text-based PDF or DOCX.'
        )

    strengths: list[str] = []
    improvements: list[str] = []

    band = _length_band(words)
    if band in ('adequate', 'detailed', 'comprehensive'):
        strengths.append(f'The report length ({words:,} words) suggests adequate effort and coverage.')
    elif band == 'short':
        improvements.append('Expand key sections — the report reads shorter than a typical final-year project submission.')
    else:
        improvements.append('The report is very short; ask the student to develop each required section in more depth.')

    present_labels = [label for label, key, _ in _SECTION_CHECKS if sections.get(key)]
    if len(present_labels) >= 4:
        strengths.append(f'Good structural coverage with identifiable sections ({", ".join(present_labels[:4])}).')
    else:
        missing = [label for label, key, _ in _SECTION_CHECKS if not sections.get(key)]
        if missing:
            improvements.append(f'Add or clearly label missing sections: {", ".join(missing[:4])}.')

    if signals.get('objectives'):
        strengths.append('Project objectives or aims are stated in the document.')
    else:
        improvements.append('State project objectives clearly in the introduction.')

    if signals.get('diagrams'):
        strengths.append('Visual elements (figures/tables/diagrams) are referenced in the text.')
    else:
        improvements.append('Include labelled figures or tables to support technical explanations.')

    if signals.get('citations'):
        strengths.append('In-text citations or references appear to be used.')
    elif sections.get('literature') or sections.get('references'):
        improvements.append('Strengthen in-text citations throughout the literature review and body.')
    else:
        improvements.append('Add a literature review with properly cited sources.')

    if sections.get('methodology') and sections.get('results'):
        strengths.append('Methodology and results/analysis sections are present.')
    elif not sections.get('methodology'):
        improvements.append('Describe methodology, tools, and implementation steps more explicitly.')
    elif not sections.get('results'):
        improvements.append('Present results, testing, or evaluation outcomes with supporting evidence.')

    if sections.get('conclusion'):
        strengths.append('A conclusion or summary section is included.')
    else:
        improvements.append('End with a conclusion that links findings back to the stated objectives.')

    criterion_notes: list[str] = []
    for row in criteria[:4]:
        name = (row.get('name') or 'Criterion').strip()
        criterion_notes.append(f'• {name}: review against rubric expectations before final marks.')

    paragraphs: list[str] = []
    if strengths:
        paragraphs.append('Strengths:\n' + '\n'.join(f'• {item}' for item in strengths[:4]))
    if improvements:
        paragraphs.append('Areas to address:\n' + '\n'.join(f'• {item}' for item in improvements[:5]))
    if criterion_notes:
        paragraphs.append('Rubric review:\n' + '\n'.join(criterion_notes))

    paragraphs.append(
        'Please edit this draft feedback before sending it to the student — adjust tone and marks '
        'based on your professional judgment.'
    )
    return '\n\n'.join(paragraphs)


def is_legacy_placeholder_analysis(analysis: dict[str, Any] | None) -> bool:
    """True when cached analysis used the old generic API-key placeholder."""
    if not analysis:
        return False
    feedback = (analysis.get('suggested_feedback') or '').lower()
    provider = (analysis.get('provider') or '').lower()
    if provider == 'local_analysis':
        return False
    legacy_markers = (
        'no ai api key',
        'automated draft: review the pdf carefully',
        'local heuristics because no ai',
    )
    return any(marker in feedback for marker in legacy_markers) or provider == 'heuristic'


def heuristic_report_analysis(
    report_title: str,
    extracted_text: str,
    criteria: list[dict],
) -> dict[str, Any]:
    """Generate summary, rubric scores, and teacher feedback from extracted report text."""
    text = (extracted_text or '').strip()
    words = _word_count(text)
    sections = _detect_sections(text)
    signals = _detect_signals(text)

    section_count = sum(1 for key in sections if sections[key])
    coverage = section_count / max(len(_SECTION_CHECKS), 1)

    suggested_scores: dict[str, int] = {}
    for row in criteria:
        cid = str(row.get('id'))
        max_score = int(row.get('max_score') or 0)
        name = row.get('name') or ''
        suggested_scores[cid] = _score_for_criterion(name, max_score, coverage, words)

    total_max = sum(int(row.get('max_score') or 0) for row in criteria) or 100
    total_suggested = sum(suggested_scores.values())
    suggested_marks = int(round((total_suggested / total_max) * 100)) if total_max else 60
    suggested_marks = max(0, min(100, suggested_marks))

    return {
        'summary': _build_summary(report_title, text, sections, words),
        'suggested_criterion_scores': suggested_scores,
        'suggested_feedback': _build_feedback(report_title, text, sections, signals, words, criteria),
        'suggested_teacher_marks': suggested_marks,
        'provider': 'local_analysis',
    }
