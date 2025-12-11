from pypdf import PdfReader

def extract_pdf_pages(path):
    try:
        r = PdfReader(path)
        out=[]
        for p in r.pages:
            try: out.append(p.extract_text() or '')
            except: out.append('')
        return out
    except:
        return []
