"""Shared report upload constraints."""

ALLOWED_REPORT_EXTENSIONS = ('pdf', 'docx')

REPORT_FILE_ACCEPT = (
    '.pdf,.docx,application/pdf,'
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
)

REPORT_FILE_LABEL = 'PDF or DOCX document'

REPORT_FILE_TYPES_LABEL = 'PDF or DOCX'

REPORT_FILE_REQUIRED_MESSAGE = 'Report file is required (PDF or DOCX).'

REPORT_FILE_INVALID_MESSAGE = (
    f'Invalid file type. Allowed formats: {", ".join(ext.upper() for ext in ALLOWED_REPORT_EXTENSIONS)}.'
)


def report_file_extension(filename: str) -> str:
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[-1].lower()


def is_allowed_report_extension(filename: str) -> bool:
    return report_file_extension(filename) in ALLOWED_REPORT_EXTENSIONS


def report_content_type(filename: str) -> str:
    ext = report_file_extension(filename)
    if ext == 'pdf':
        return 'application/pdf'
    if ext == 'docx':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    return 'application/octet-stream'
