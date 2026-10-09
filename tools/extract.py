"""Read PDF/HTML/DOCX/text as attributable text; never execute source content."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


def extract(path):
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return '\n\n'.join(f'[Page {i+1}]\n{page.extract_text() or "[No extractable text; visual/OCR review needed]"}' for i, page in enumerate(pdf.pages))
    if path.suffix.lower() == '.docx':
        with ZipFile(path) as z:
            doc = ET.fromstring(z.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        return '\n\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in doc.findall('.//w:p', ns))
    if path.suffix.lower() in {'.html', '.htm'}:
        from html.parser import HTMLParser
        class TextReader(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.parts, self.hidden = [], 0
            def handle_starttag(self, tag, attrs):
                if tag in {'script','style','noscript','ix:header'}: self.hidden += 1
                if not self.hidden and tag in {'p','div','tr','br','h1','h2','h3'}: self.parts.append('\n')
                if not self.hidden and tag in {'td','th'}: self.parts.append('\t')
            def handle_endtag(self, tag):
                if tag in {'script','style','noscript','ix:header'} and self.hidden: self.hidden -= 1
                if not self.hidden and tag in {'p','div','tr','h1','h2','h3'}: self.parts.append('\n')
            def handle_data(self, data):
                if not self.hidden: self.parts.append(data)
        parser = TextReader()
        parser.feed(path.read_text(encoding='utf-8', errors='replace'))
        import re
        return '\n'.join(re.sub(r'[ \t]+',' ',line).strip() for line in ''.join(parser.parts).splitlines() if line.strip())
    return path.read_text(encoding='utf-8-sig')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    parser.add_argument('--output')
    args = parser.parse_args()
    text = extract(args.path)
    if args.output:
        dest = Path(args.output)
        if dest.exists():
            raise ValueError('Extraction output already exists')
        dest.write_text(text, encoding='utf-8')
    else:
        print(text)
