from pypdf import PdfReader

def extract_pdf_pages(path: str):
    try:
        reader = PdfReader(path)
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or '')
            except Exception:
                pages.append('')
        return pages
    except Exception:
        return []
