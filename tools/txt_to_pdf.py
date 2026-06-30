"""Convert BizOS_Feature_Test.txt to a branded PDF."""
from fpdf import FPDF
from pathlib import Path

SRC = Path(__file__).parent.parent / "BizOS_Feature_Test.txt"
DST = Path(__file__).parent.parent / "BizOS_Feature_Test.pdf"

GREEN = (64, 126, 60)
WHITE = (255, 255, 255)
DARK  = (26, 26, 26)
LIGHT = (244, 250, 244)
RULE  = (200, 230, 200)

SECTION_MARKER = "SECTION "
SEPARATOR      = "=" * 20
THIN_RULE      = "-" * 20
TEST_MARKER    = "TEST "


def safe(text: str) -> str:
    """Replace non-Latin-1 characters with ASCII equivalents."""
    return (
        text
        .replace("—", "--")
        .replace("–", "-")
        .replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("…", "...")
        .replace(" ", " ")
        .encode("latin-1", errors="replace").decode("latin-1")
    )


class BizOSPDF(FPDF):
    def header(self):
        self.set_fill_color(*GREEN)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.set_y(3)
        self.cell(0, 6, safe("BizOS -- Feature Test Document"), align="C")
        self.set_text_color(*DARK)
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def classify(line: str) -> str:
    s = line.strip()
    if s.startswith(SEPARATOR[:10]) and len(s) > 20:
        return "rule_heavy"
    if s.startswith(THIN_RULE[:8]) and len(s) > 10:
        return "rule_thin"
    if s.startswith(SECTION_MARKER):
        return "section"
    if s.startswith(TEST_MARKER):
        return "test_header"
    if s.startswith("  ") and s.lstrip().startswith(
        ("Steps:", "Expected:", "Note:", "File:", "Check:")
    ):
        return "label"
    if s.startswith("    ") or (
        s.startswith("  ")
        and not s.lstrip().startswith(("-", "Steps", "Expected", "Note", "File", "Check"))
    ):
        return "code"
    if not s:
        return "blank"
    return "body"


def make_pdf(src: Path, dst: Path) -> None:
    pdf = BizOSPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    lines = src.read_text(encoding="utf-8").splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        kind = classify(line)

        if kind == "rule_heavy":
            i += 1
            continue

        if kind == "rule_thin":
            pdf.set_draw_color(*RULE)
            pdf.set_line_width(0.3)
            pdf.line(18, pdf.get_y(), 192, pdf.get_y())
            pdf.ln(3)
            i += 1
            continue

        if kind == "blank":
            pdf.ln(2)
            i += 1
            continue

        if kind == "section":
            pdf.ln(3)
            pdf.set_fill_color(*GREEN)
            pdf.set_text_color(*WHITE)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 9, safe(f"  {line.strip()}"), ln=True, fill=True)
            pdf.set_text_color(*DARK)
            pdf.ln(2)
            i += 1
            continue

        if kind == "test_header":
            pdf.ln(2)
            pdf.set_fill_color(*LIGHT)
            pdf.set_text_color(*GREEN)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 7, safe(f"  {line.strip()}"), ln=True, fill=True)
            pdf.set_text_color(*DARK)
            i += 1
            continue

        if kind == "label":
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.set_x(22)
            pdf.cell(0, 5, safe(line.strip()), ln=True)
            pdf.set_text_color(*DARK)
            i += 1
            continue

        if kind == "code":
            code_lines = []
            while i < len(lines) and classify(lines[i]) == "code":
                code_lines.append(lines[i])
                i += 1
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Courier", "", 7.5)
            pdf.set_text_color(40, 40, 40)
            for cl in code_lines:
                pdf.set_x(24)
                pdf.cell(0, 4.5, safe(cl.rstrip()), ln=True, fill=True)
            pdf.set_text_color(*DARK)
            pdf.ln(1)
            continue

        # body
        text = line.strip()
        if not text:
            i += 1
            continue

        is_title = (
            (text.isupper() and len(text) > 8)
            or text.startswith("PREREQUISITES")
            or text.startswith("END OF TEST")
        )

        if is_title:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*GREEN)
        elif text.startswith("Optional") or text.startswith("All tests"):
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
        else:
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*DARK)

        pdf.set_x(18)
        pdf.multi_cell(0, 5, safe(text))
        pdf.set_text_color(*DARK)
        i += 1

    pdf.output(str(dst))
    size_kb = dst.stat().st_size // 1024
    print(f"PDF written: {dst}")
    print(f"Size: {size_kb} KB  |  Pages: {pdf.page_no()}")


if __name__ == "__main__":
    make_pdf(SRC, DST)
