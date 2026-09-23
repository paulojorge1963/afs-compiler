"""Generates the AFS .docx pack (Section 8 of the spec) from a ReportData object.

Reproduces the reference compilation-engagement AFS pack's layout, section order,
numbering style and boilerplate wording, with bracketed fields replaced by the
entity/financial-year data. Every figure here comes from app.reporting.build_report /
app.calc - never recomputed independently.
"""
from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor

from app.calc import _dir as normalize_direction
from app.models import ReportType
from app.reporting import ReportData, applicable_policies

BODY_FONT = "Calibri"
WATERMARK_TEXT = "FOR REVIEW BEFORE ISSUE - NOT YET APPROVED BY THE DIRECTOR"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt(n: float | None, dash_on_zero: bool = False) -> str:
    if n is None:
        return ""
    n = round(n)
    if n == 0:
        return "-" if dash_on_zero else "0"
    sign = n < 0
    s = f"{abs(n):,.0f}".replace(",", " ")
    return f"({s})" if sign else s


def fmt_date_long(d) -> str:
    if d is None:
        return "[date]"
    return d.strftime("%d %B %Y").lstrip("0")


def fmt_date_full(d) -> str:
    if d is None:
        return "[date]"
    return d.strftime("%A, %d %B %Y").replace(" 0", " ")


def fmt_date_upper(d) -> str:
    if d is None:
        return "[DATE]"
    return d.strftime("%-d %B %Y").upper() if hasattr(d, "strftime") else str(d)


# ---------------------------------------------------------------------------
# Low-level docx helpers
# ---------------------------------------------------------------------------


def _set_cell_border(cell, **kwargs):
    """kwargs: top/bottom/left/right = {"sz": int, "val": "single"/"double", "color": "000000"}"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kwargs:
            spec = kwargs[edge]
            el = tcBorders.find(qn(f"w:{edge}"))
            if el is None:
                el = OxmlElement(f"w:{edge}")
                tcBorders.append(el)
            el.set(qn("w:val"), spec.get("val", "single"))
            el.set(qn("w:sz"), str(spec.get("sz", 4)))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), spec.get("color", "000000"))


def _no_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)


def _set_col_widths(table, widths_cm):
    table.autofit = False
    for row in table.rows:
        for cell, w in zip(row.cells, widths_cm):
            cell.width = Cm(w)


def _cell_text(cell, text, bold=False, align=None, size=10, italic=False):
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = BODY_FONT
    return p


def add_page_break(doc):
    doc.add_page_break()


def add_heading_rule(doc, text, size=13):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.underline = True
    run.font.size = Pt(size)
    run.font.name = BODY_FONT
    p.paragraph_format.space_after = Pt(10)
    return p


def add_page_header_block(doc, entity, year_end_date, subtitle: str):
    p = doc.add_paragraph()
    r = p.add_run(entity.company_name)
    r.bold = True
    r.font.size = Pt(11)
    r.font.name = BODY_FONT
    p.paragraph_format.space_after = Pt(0)

    p2 = doc.add_paragraph()
    r2 = p2.add_run(f"(Registration number: {entity.registration_number})")
    r2.font.size = Pt(10)
    r2.font.name = BODY_FONT
    p2.paragraph_format.space_after = Pt(0)

    p3 = doc.add_paragraph()
    r3 = p3.add_run(f"Annual Financial Statements for the year ended {fmt_date_long(year_end_date)}")
    r3.font.size = Pt(10)
    r3.font.name = BODY_FONT
    p3.paragraph_format.space_after = Pt(8)

    add_heading_rule(doc, subtitle)


def add_body_paragraph(doc, text, size=10, space_after=8, bold=False, align=None):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.name = BODY_FONT
    run.bold = bold
    p.paragraph_format.space_after = Pt(space_after)
    return p


def add_watermark_banner(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(WATERMARK_TEXT)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    p.paragraph_format.space_after = Pt(12)
    return p


# ---------------------------------------------------------------------------
# Statement table builder
# ---------------------------------------------------------------------------


def add_statement_table(doc, rows, col_widths_cm=(9.0, 1.5, 3.0, 3.0), header=("", "Note(s)", "", "")):
    """rows: list of dicts:
        {"label": str, "note": str, "current": float|str|None, "prior": float|str|None,
         "style": "normal"|"subtotal"|"grandtotal"|"section"|"blank", "dash_zero": bool}
    """
    table = doc.add_table(rows=0, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _no_table_borders(table)
    _set_col_widths(table, col_widths_cm)

    hdr = table.add_row()
    _cell_text(hdr.cells[0], header[0], bold=True, size=9)
    _cell_text(hdr.cells[1], header[1], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
    _cell_text(hdr.cells[2], header[2], bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
    _cell_text(hdr.cells[3], header[3], bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)

    for r in rows:
        style = r.get("style", "normal")
        if style == "blank":
            table.add_row()
            continue
        row = table.add_row()
        bold = style in ("subtotal", "grandtotal", "section")
        _cell_text(row.cells[0], r["label"], bold=bold, size=10)
        _cell_text(row.cells[1], r.get("note") or "", align=WD_ALIGN_PARAGRAPH.CENTER, size=10)

        dash_zero = r.get("dash_zero", False)
        cur = r.get("current")
        pri = r.get("prior")
        cur_text = cur if isinstance(cur, str) else (fmt(cur, dash_zero) if cur is not None else "")
        pri_text = pri if isinstance(pri, str) else (fmt(pri, dash_zero) if pri is not None else "")

        _cell_text(row.cells[2], cur_text, bold=bold, align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        _cell_text(row.cells[3], pri_text, bold=bold, align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)

        if style == "subtotal":
            for c in (row.cells[2], row.cells[3]):
                _set_cell_border(c, top={"sz": 6, "val": "single"})
        elif style == "grandtotal":
            for c in (row.cells[2], row.cells[3]):
                _set_cell_border(c, top={"sz": 6, "val": "double"}, bottom={"sz": 6, "val": "double"})
    return table


# ---------------------------------------------------------------------------
# Cover page (8.1)
# ---------------------------------------------------------------------------


def build_cover_page(doc, report: ReportData):
    entity = report.entity
    fy = report.fy

    for _ in range(4):
        doc.add_paragraph()

    add_watermark_banner(doc)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(entity.company_name.upper())
    run.bold = True
    run.font.size = Pt(18)
    run.font.name = BODY_FONT
    p.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"(REGISTRATION NUMBER {entity.registration_number})")
    run.bold = True
    run.font.size = Pt(13)
    run.font.name = BODY_FONT
    p.paragraph_format.space_after = Pt(40)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("ANNUAL FINANCIAL STATEMENTS")
    run.bold = True
    run.font.size = Pt(14)
    run.font.name = BODY_FONT

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"FOR THE YEAR ENDED {fmt_date_upper(fy.year_end_date)}")
    run.bold = True
    run.font.size = Pt(14)
    run.font.name = BODY_FONT


# ---------------------------------------------------------------------------
# General information (8.2)
# ---------------------------------------------------------------------------


def build_general_information(doc, report: ReportData):
    entity = report.entity
    fy = report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "General Information")

    director_names = "\n".join(d.full_name for d in entity.directors if d.date_resigned is None) or "[none]"

    rows = [
        ("Country of incorporation and domicile", entity.country_of_incorporation or ""),
        ("Company registration number", entity.registration_number or ""),
        ("Tax reference number", entity.tax_reference_number or ""),
        ("Director(s)", director_names),
        ("Nature of business and principal activities", entity.nature_of_business or ""),
        ("Registered office", entity.registered_office_address or ""),
        ("Business address", entity.business_address or ""),
        ("Postal address", entity.postal_address or ""),
        ("Bankers", entity.bankers or ""),
        ("Practitioner", entity.practitioner_firm or entity.practitioner_name or ""),
    ]

    table = doc.add_table(rows=0, cols=2)
    _no_table_borders(table)
    _set_col_widths(table, (5.5, 10.5))
    for label, value in rows:
        row = table.add_row()
        _cell_text(row.cells[0], label, bold=False, size=10)
        _cell_text(row.cells[1], str(value), size=10)


# ---------------------------------------------------------------------------
# Contents page (8.3)
# ---------------------------------------------------------------------------


def build_contents_page(doc, report: ReportData, page_map: list[tuple[str, int]]):
    entity = report.entity
    add_page_header_block(doc, entity, report.fy.year_end_date, "Index")

    table = doc.add_table(rows=0, cols=2)
    _no_table_borders(table)
    _set_col_widths(table, (13.0, 3.0))
    for title, page in page_map:
        row = table.add_row()
        _cell_text(row.cells[0], title, size=10)
        _cell_text(row.cells[1], str(page), align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)


# ---------------------------------------------------------------------------
# Director's Responsibilities and Approval (8.4)
# ---------------------------------------------------------------------------


def build_directors_responsibilities(doc, report: ReportData, next_year_end_label: str, approval_director_name: str,
                                      first_page: int, last_page: int):
    entity = report.entity
    fy = report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Director's Responsibilities and Approval")

    paras = [
        "The director is required by the Companies Act of South Africa, to maintain adequate accounting records "
        "and is responsible for the content and integrity of the annual financial statements and related "
        "financial information included in this report. It is his/her responsibility to ensure that the annual "
        "financial statements fairly present the state of affairs of the company as at the end of the financial "
        "year and the results of its operations and cash flows for the period then ended, in conformity with "
        "the International Financial Reporting Standard for Small and Medium-sized Entities.",
        "The annual financial statements are prepared in accordance with the International Financial Reporting "
        "Standard for Small and Medium-sized Entities and are based upon appropriate accounting policies "
        "consistently applied and supported by reasonable and prudent judgements and estimates.",
        "The director acknowledges that he/she is ultimately responsible for the system of internal financial "
        "control established by the company and places considerable importance on maintaining a strong control "
        "environment. To enable the director to meet these responsibilities, the director sets standards for "
        "internal control aimed at reducing the risk of error or loss in a cost effective manner. The standards "
        "include the proper delegation of responsibilities within a clearly defined framework, effective "
        "accounting procedures and adequate segregation of duties to ensure an acceptable level of risk. These "
        "controls are monitored throughout the company and all employees are required to maintain the highest "
        "ethical standards in ensuring the company's business is conducted in a manner that in all reasonable "
        "circumstances is above reproach. The focus of risk management in the company is on identifying, "
        "assessing, managing and monitoring all known forms of risk across the company. While operating risk "
        "cannot be fully eliminated, the company endeavours to minimise it by ensuring that appropriate "
        "infrastructure, controls, systems and ethical behaviour are applied and managed within predetermined "
        "procedures and constraints.",
        "The director is of the opinion, based on the information and explanations given by management, that "
        "the system of internal control provides reasonable assurance that the financial records may be relied "
        "on for the preparation of the annual financial statements. However, any system of internal financial "
        "control can provide only reasonable, and not absolute, assurance against material misstatement or "
        "loss.",
        f"The director has reviewed the company's cash flow forecast for the year to {next_year_end_label} and, "
        "in the light of this review and the current financial position, he/she is satisfied that the company "
        "has or has access to adequate resources to continue in operational existence for the foreseeable "
        "future.",
        f"The annual financial statements set out on pages {first_page} to {last_page}, which have been prepared "
        f"on the going concern basis, were approved by the director on {fmt_date_long(fy.date_approved)} and "
        "were signed on its behalf by:",
    ]
    for text in paras:
        add_body_paragraph(doc, text)

    add_body_paragraph(doc, "Approval of annual financial statements", bold=True, size=10)
    doc.add_paragraph()
    add_body_paragraph(doc, "_______________________________")
    add_body_paragraph(doc, approval_director_name)


# ---------------------------------------------------------------------------
# Director's Report (8.5)
# ---------------------------------------------------------------------------


def build_directors_report(doc, report: ReportData, sfp_page: int, approval_director_name: str):
    entity = report.entity
    fy = report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Director's Report")

    signing_directors = [d for d in entity.directors if d.date_resigned is None]

    add_body_paragraph(
        doc,
        f"The director has pleasure in submitting his/her report on the annual financial statements of "
        f"{entity.company_name} for the year ended {fmt_date_long(fy.year_end_date)}.",
    )

    add_body_paragraph(doc, "1.  Incorporation", bold=True, space_after=4)
    incorp = fmt_date_long(entity.incorporation_date) if entity.incorporation_date else "[incorporation date]"
    cert = (
        fmt_date_long(entity.certificate_to_commence_business_date)
        if entity.certificate_to_commence_business_date
        else incorp
    )
    add_body_paragraph(
        doc,
        f"The company was incorporated on {incorp} and obtained its certificate to commence business on {cert}.",
    )

    add_body_paragraph(doc, "2.  Nature of business", bold=True, space_after=4)
    add_body_paragraph(
        doc,
        f"{entity.company_name} was incorporated in South Africa with interests in the "
        f"{entity.nature_of_business or '[industry]'} industry. The company operates in "
        f"{entity.country_of_incorporation}.\n"
        "There have been no material changes to the nature of the company's business from the prior year.",
    )

    add_body_paragraph(doc, "3.  Review of financial results and activities", bold=True, space_after=4)
    add_body_paragraph(
        doc,
        "The annual financial statements have been prepared in accordance with International Financial "
        "Reporting Standard for Small and Medium-sized Entities and the requirements of the Companies Act of "
        "South Africa. The accounting policies have been applied consistently compared to the prior year.\n"
        "Full details of the financial position, results of operations and cash flows of the company are set "
        "out in these annual financial statements.",
    )

    add_body_paragraph(doc, "4.  Share capital", bold=True, space_after=4)
    add_body_paragraph(
        doc, "There have been no changes to the authorised or issued share capital during the year under review."
    )

    add_body_paragraph(doc, "5.  Director", bold=True, space_after=4)
    table = doc.add_table(rows=0, cols=2)
    _no_table_borders(table)
    _set_col_widths(table, (10.0, 6.0))
    hdr = table.add_row()
    _cell_text(hdr.cells[0], "Director", bold=True, size=10)
    _cell_text(hdr.cells[1], "Nationality", bold=True, size=10)
    for d in entity.directors:
        row = table.add_row()
        _cell_text(row.cells[0], d.full_name, size=10)
        _cell_text(row.cells[1], d.nationality or "", size=10)
    add_body_paragraph(doc, "There have been no changes to the directorate for the period under review.")

    add_body_paragraph(doc, "6.  Events after the reporting period", bold=True, space_after=4)
    add_body_paragraph(
        doc,
        "The director is not aware of any material event which occurred after the reporting date and up to the "
        "date of this report.",
    )

    add_body_paragraph(doc, "7.  Going concern", bold=True, space_after=4)
    add_body_paragraph(
        doc,
        "The annual financial statements have been prepared on the basis of accounting policies applicable to a "
        "going concern. This basis presumes that funds will be available to finance future operations and that "
        "the realisation of assets and settlement of liabilities, contingent obligations and commitments will "
        "occur in the ordinary course of business.\n"
        "The director believes that the company has adequate financial resources to continue in operation for "
        "the foreseeable future and accordingly the annual financial statements have been prepared on a going "
        "concern basis.\n"
        "The director has satisfied himself/herself that the company is in a sound financial position and that "
        "it has access to sufficient borrowing facilities to meet its foreseeable cash requirements. The "
        "director is not aware of any new material changes that may adversely impact the company. The director "
        "is also not aware of any material non-compliance with statutory or regulatory requirements or of any "
        "pending changes to legislation which may affect the company.",
    )

    add_body_paragraph(doc, "8.  Liquidity and solvency", bold=True, space_after=4)
    add_body_paragraph(
        doc, "The director has performed the required liquidity and solvency tests required by the Companies "
        "Act of South Africa."
    )

    add_body_paragraph(
        doc,
        f"The annual financial statements set out on page {sfp_page}, which have been prepared on the going "
        f"concern basis, were approved by the director on {fmt_date_long(fy.date_approved)}, and were signed on "
        "its behalf by:",
    )
    add_body_paragraph(doc, "Approval of annual financial statements", bold=True, size=10)
    doc.add_paragraph()
    add_body_paragraph(doc, "_______________________________")
    add_body_paragraph(doc, approval_director_name)
    add_body_paragraph(doc, fmt_date_full(fy.date_approved))


# ---------------------------------------------------------------------------
# Practitioner's / Independent Review / Audit Report (8.6)
# ---------------------------------------------------------------------------

REPORT_TYPE_TITLES = {
    ReportType.COMPILATION: "Practitioner's Compilation Report",
    ReportType.REVIEW: "Independent Review Report",
    ReportType.AUDIT: "Independent Auditor's Report",
}


def build_practitioners_report(doc, report: ReportData, first_page: int, last_page: int):
    entity = report.entity
    fy = report.fy
    title = REPORT_TYPE_TITLES.get(entity.report_type, "Practitioner's Compilation Report")
    add_page_header_block(doc, entity, fy.year_end_date, title)

    if entity.report_type == ReportType.COMPILATION:
        add_body_paragraph(doc, f"To the Management of {entity.company_name}")
        add_body_paragraph(
            doc,
            f"I have compiled the annual financial statements of {entity.company_name}, as set out on pages "
            f"{first_page} to {last_page}, based on information you have provided. These annual financial "
            f"statements comprise the statement of financial position of {entity.company_name} as at "
            f"{fmt_date_long(fy.year_end_date)}, the statement of comprehensive income, statement of changes in "
            "equity and statement of cash flows for the year then ended, and a summary of significant accounting "
            "policies and other explanatory information.",
        )
        add_body_paragraph(
            doc,
            "I performed this compilation engagement in accordance with International Standard on Related "
            "Services 4410 (Revised), Compilation Engagements.",
        )
        add_body_paragraph(
            doc,
            "I have applied my expertise in accounting and financial reporting to assist you in the preparation "
            "and presentation of these annual financial statements in accordance with the International "
            "Financial Reporting Standard for Small and Medium-sized Entities. I have complied with relevant "
            "ethical requirements, including principles of integrity, objectivity, professional competence and "
            "due care.",
        )
        add_body_paragraph(
            doc,
            "These annual financial statements and the accuracy and completeness of the information used to "
            "compile them are your responsibility.",
        )
        add_body_paragraph(
            doc,
            "Since a compilation engagement is not an assurance engagement, I am not required to verify the "
            "accuracy or completeness of the information you provided to me to compile these annual financial "
            "statements. Accordingly, I do not express an audit opinion or a review conclusion on whether these "
            "annual financial statements are prepared in accordance with the International Financial Reporting "
            "Standard for Small and Medium-sized Entities.",
        )
        doc.add_paragraph()
        add_body_paragraph(doc, "_______________________________")
        add_body_paragraph(doc, entity.practitioner_name or "[Practitioner name]")
        add_body_paragraph(doc, entity.practitioner_firm or "[Practitioner firm]")
        doc.add_paragraph()
        add_body_paragraph(doc, fmt_date_long(fy.date_approved))
    elif entity.report_type == ReportType.REVIEW:
        add_body_paragraph(
            doc,
            "[Independent Review Report wording - out of scope to fully draft for v1 (ISRE 2400 (Revised)). "
            "Complete this section with your practitioner's standard review report wording before issuing "
            "annual financial statements prepared on this basis.]",
        )
    else:
        add_body_paragraph(
            doc,
            "[Independent Auditor's Report wording - out of scope to fully draft for v1 (ISA 700 (Revised)). "
            "Complete this section with your auditor's standard report wording before issuing annual financial "
            "statements prepared on this basis.]",
        )


# ---------------------------------------------------------------------------
# Primary statements (8.7)
# ---------------------------------------------------------------------------


def build_statement_of_financial_position(doc, report: ReportData):
    entity = report.entity
    fy = report.fy
    add_page_header_block(doc, entity, fy.year_end_date, f"Statement of Financial Position as at {fmt_date_long(fy.year_end_date)}")

    bsc, bsp = report.balance_sheet_current, report.balance_sheet_prior
    notes = report.notes
    rows = []
    rows.append({"label": "Assets", "style": "section"})
    rows.append({"label": "Non-Current Assets", "style": "section"})
    if notes.has("ppe"):
        rows.append({"label": "Property, plant and equipment", "note": str(notes.get("ppe")),
                     "current": bsc.ppe_carrying_value, "prior": bsp.ppe_carrying_value})
    if notes.has("loans"):
        rows.append({"label": "Loans to shareholders", "note": str(notes.get("loans")),
                     "current": bsc.loans_to_shareholders, "prior": bsp.loans_to_shareholders})
    rows.append({"label": "", "current": bsc.non_current_assets, "prior": bsp.non_current_assets, "style": "subtotal"})
    rows.append({"label": "Current Assets", "style": "section"})
    if notes.has("receivables"):
        rows.append({"label": "Trade and other receivables",
                     "current": bsc.trade_and_other_receivables, "prior": bsp.trade_and_other_receivables})
    if notes.has("inventory"):
        rows.append({"label": "Inventories", "current": bsc.inventory, "prior": bsp.inventory})
    rows.append({"label": "Cash and cash equivalents", "current": bsc.cash, "prior": bsp.cash})
    rows.append({"label": "", "current": bsc.current_assets, "prior": bsp.current_assets, "style": "subtotal"})
    rows.append({"label": "Total Assets", "current": bsc.total_assets, "prior": bsp.total_assets, "style": "grandtotal"})
    rows.append({"style": "blank"})
    rows.append({"label": "Equity and Liabilities", "style": "section"})
    rows.append({"label": "Equity", "style": "section"})
    rows.append({"label": "Share capital", "current": bsc.share_capital, "prior": bsp.share_capital})
    rows.append({"label": "Retained income", "current": bsc.retained_income, "prior": bsp.retained_income})
    rows.append({"label": "", "current": bsc.total_equity, "prior": bsp.total_equity, "style": "subtotal"})
    rows.append({"label": "Liabilities", "style": "section"})
    if notes.has("loans"):
        rows.append({"label": "Loans from shareholders", "note": str(notes.get("loans")),
                     "current": bsc.loans_from_shareholders, "prior": bsp.loans_from_shareholders})
    if notes.has("payables"):
        rows.append({"label": "Trade and other payables",
                     "current": bsc.trade_and_other_payables, "prior": bsp.trade_and_other_payables})
    if notes.has("current_tax_payable"):
        rows.append({"label": "Current tax payable",
                     "current": bsc.current_tax_payable, "prior": bsp.current_tax_payable})
    if bsc.other_current_liability or bsp.other_current_liability:
        rows.append({"label": "Other current liabilities",
                     "current": bsc.other_current_liability, "prior": bsp.other_current_liability})
    if bsc.other_non_current_liability or bsp.other_non_current_liability:
        rows.append({"label": "Other non-current liabilities",
                     "current": bsc.other_non_current_liability, "prior": bsp.other_non_current_liability})
    rows.append({"label": "", "current": bsc.total_liabilities, "prior": bsp.total_liabilities, "style": "subtotal"})
    rows.append({"label": "Total Equity and Liabilities", "current": bsc.total_equity_and_liabilities,
                 "prior": bsp.total_equity_and_liabilities, "style": "grandtotal"})

    add_statement_table(
        doc, rows,
        header=("Figures in Rand", "Note(s)", fmt_date_long(fy.year_end_date), fmt_date_long(fy.comparative_year_end_date)),
    )


def build_statement_of_comprehensive_income(doc, report: ReportData):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Statement of Comprehensive Income")
    ic, ip = report.income_current, report.income_prior
    notes = report.notes

    rows = [
        {"label": "Revenue", "current": ic.revenue, "prior": ip.revenue},
        {"label": "Cost of sales", "current": -ic.cost_of_sales, "prior": -ip.cost_of_sales},
        {"label": "Gross profit", "current": ic.gross_profit, "prior": ip.gross_profit, "style": "subtotal"},
        {"label": "Operating expenses", "current": -ic.total_operating_expenses, "prior": -ip.total_operating_expenses},
        {"label": "Operating profit (loss)", "current": ic.operating_profit, "prior": ip.operating_profit, "style": "subtotal"},
        {"label": "Investment revenue", "note": str(notes.get("investment_revenue") or ""),
         "current": ic.investment_revenue, "prior": ip.investment_revenue},
        {"label": "Finance costs", "current": -ic.finance_costs, "prior": -ip.finance_costs},
        {"label": "Profit for the year", "current": ic.profit_for_the_year, "prior": ip.profit_for_the_year, "style": "subtotal"},
        {"label": "Other comprehensive income", "current": ic.other_comprehensive_income, "prior": ip.other_comprehensive_income, "dash_zero": True},
        {"label": "Total comprehensive income for the year", "current": ic.total_comprehensive_income,
         "prior": ip.total_comprehensive_income, "style": "grandtotal"},
    ]
    add_statement_table(
        doc, rows,
        header=("Figures in Rand", "Note(s)", fmt_date_long(fy.year_end_date), fmt_date_long(fy.comparative_year_end_date)),
    )


def build_statement_of_changes_in_equity(doc, report: ReportData):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Statement of Changes in Equity")
    es = report.equity_statement

    table = doc.add_table(rows=0, cols=4)
    _no_table_borders(table)
    _set_col_widths(table, (9.0, 3.0, 3.0, 3.0))
    hdr = table.add_row()
    for i, text in enumerate(["Figures in Rand", "Share capital", "Retained income", "Total equity"]):
        _cell_text(hdr.cells[i], text, bold=True, align=(WD_ALIGN_PARAGRAPH.RIGHT if i else None), size=9)

    def add_row(label, r, style="normal"):
        row = table.add_row()
        bold = style in ("subtotal", "grandtotal")
        _cell_text(row.cells[0], label, bold=bold, size=10)
        _cell_text(row.cells[1], fmt(r.share_capital), bold=bold, align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        _cell_text(row.cells[2], fmt(r.retained_income), bold=bold, align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        _cell_text(row.cells[3], fmt(r.total), bold=bold, align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        if style == "grandtotal":
            for c in row.cells[1:]:
                _set_cell_border(c, top={"sz": 6, "val": "double"}, bottom={"sz": 6, "val": "double"})
        elif style == "subtotal":
            for c in row.cells[1:]:
                _set_cell_border(c, top={"sz": 6, "val": "single"})

    add_row(f"Balance at {fmt_date_long(_prior_year_start(fy))}", es.opening_prior_year)
    add_row("Profit for the year", es.prior_year_profit)
    add_row("Other comprehensive income", es.prior_year_oci)
    add_row("Total comprehensive income for the year",
            _sum_rows(es.prior_year_profit, es.prior_year_oci), style="subtotal")
    add_row(f"Balance at {fmt_date_long(fy.comparative_year_end_date)}", es.opening_current_year)
    add_row("Profit for the year", es.current_year_profit)
    add_row("Other comprehensive income", es.current_year_oci)
    add_row("Total comprehensive income for the year",
            _sum_rows(es.current_year_profit, es.current_year_oci), style="subtotal")
    add_row(f"Balance at {fmt_date_long(fy.year_end_date)}", es.closing_current_year, style="grandtotal")


def _prior_year_start(fy):
    try:
        return fy.comparative_year_end_date.replace(year=fy.comparative_year_end_date.year - 1)
    except Exception:
        return fy.comparative_year_end_date


def _sum_rows(a, b):
    from app.calc import EquityRow
    return EquityRow("", a.share_capital + b.share_capital, a.retained_income + b.retained_income)


def build_statement_of_cash_flows(doc, report: ReportData):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Statement of Cash Flows")
    cf = report.cash_flow
    notes = report.notes

    rows = [
        {"label": "Cash flows from operating activities", "style": "section"},
        {"label": "Cash receipts from customers", "current": cf.receipts_from_customers},
        {"label": "Cash paid to suppliers and employees", "current": cf.paid_to_suppliers_and_employees},
        {"label": "Cash generated from (used in) operations", "note": str(notes.get("cash_generated")),
         "current": cf.cash_generated_from_operations, "style": "subtotal"},
        {"label": "Interest income", "current": cf.interest_income_received},
        {"label": "Finance costs", "current": cf.finance_costs_paid},
        {"label": "Net cash from operating activities", "current": cf.net_cash_from_operating_activities, "style": "subtotal"},
        {"style": "blank"},
        {"label": "Cash flows from investing activities", "style": "section"},
        {"label": "Purchase of property, plant and equipment", "note": str(notes.get("ppe") or ""),
         "current": cf.purchase_of_ppe},
        {"label": "Loan advances to shareholders", "current": -cf.loan_advances},
        {"label": "Loan repayments from shareholders", "current": cf.loan_repayments},
        {"label": "Net cash from investing activities", "current": cf.net_cash_from_investing_activities, "style": "subtotal"},
        {"style": "blank"},
        {"label": "Total cash movement for the year", "current": cf.total_cash_movement, "style": "subtotal"},
        {"label": "Cash at the beginning of the year", "current": cf.cash_at_beginning_of_year},
        {"label": "Total cash at end of the year", "current": cf.cash_at_end_of_year, "style": "grandtotal"},
    ]
    add_statement_table(
        doc, rows, col_widths_cm=(10.0, 1.5, 3.0, 3.0),
        header=("Figures in Rand", "Note(s)", fmt_date_long(fy.year_end_date), ""),
    )


# ---------------------------------------------------------------------------
# Accounting Policies (8.8)
# ---------------------------------------------------------------------------


def build_accounting_policies(doc, report: ReportData):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "1. Basis of preparation and summary of significant accounting policies")

    edition_clause = ""
    if fy.ifrs_edition.value.startswith("Third"):
        edition_clause = " - Third Edition (2025), early adopted"

    add_body_paragraph(
        doc,
        "The annual financial statements have been prepared on a going concern basis in accordance with the "
        f"International Financial Reporting Standard for Small and Medium-sized Entities{edition_clause}, and "
        "the Companies Act of South Africa. The annual financial statements have been prepared on the "
        "historical cost basis, and incorporate the principal accounting policies set out below. They are "
        "presented in South African Rands.",
    )
    add_body_paragraph(doc, "These accounting policies are consistent with the previous period.")

    policies = applicable_policies(fy)
    for i, policy in enumerate(policies, start=1):
        add_body_paragraph(doc, f"1.{i}  {policy['heading']}", bold=True, space_after=4)
        if policy["policy_area"] == "Property, plant and equipment (Section 17)":
            build_ppe_policy_body(doc, report)
        else:
            for para in policy["body"].split("\n\n"):
                add_body_paragraph(doc, para)


def build_ppe_policy_body(doc, report: ReportData):
    from app.policy_library import PPE_USEFUL_LIFE_NOTE

    before, _, after = PPE_USEFUL_LIFE_NOTE.partition("{{ppe_useful_life_table}}")
    for para in before.strip("\n").split("\n\n"):
        add_body_paragraph(doc, para)

    table = doc.add_table(rows=0, cols=3)
    _no_table_borders(table)
    _set_col_widths(table, (7.0, 5.0, 5.0))
    hdr = table.add_row()
    _cell_text(hdr.cells[0], "Item", bold=True, size=10)
    _cell_text(hdr.cells[1], "Depreciation method", bold=True, size=10)
    _cell_text(hdr.cells[2], "Average useful life", bold=True, size=10)
    seen = {}
    for asset in report.fy.ppe_assets:
        key = (asset.asset_category, asset.depreciation_method)
        seen[key] = asset.useful_life_years
    for (category, method), life in seen.items():
        row = table.add_row()
        _cell_text(row.cells[0], category, size=10)
        _cell_text(row.cells[1], method, size=10)
        life_text = f"{int(life)} years" if life == int(life) else f"{life} years"
        _cell_text(row.cells[2], life_text, size=10)

    for para in after.strip("\n").split("\n\n"):
        add_body_paragraph(doc, para)


# ---------------------------------------------------------------------------
# Notes to the Annual Financial Statements (8.9)
# ---------------------------------------------------------------------------


def _notes_header(doc, report, heading):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Notes to the Annual Financial Statements")
    add_body_paragraph(doc, heading, bold=True, size=11, space_after=6)


def build_note_ppe(doc, report: ReportData):
    n = report.notes.get("ppe")
    _notes_header(doc, report, f"{n}. Property, plant and equipment")

    table = doc.add_table(rows=0, cols=6)
    _no_table_borders(table)
    _set_col_widths(table, (5.0, 2.3, 2.3, 2.3, 2.3, 2.3))
    hdr1 = table.add_row()
    for i, text in enumerate(["", "Cost", "Accumulated depreciation", "Carrying value", "Cost", "Accumulated depreciation"]):
        _cell_text(hdr1.cells[i], text, bold=True, size=8, align=(WD_ALIGN_PARAGRAPH.RIGHT if i else None))
    hdr2 = table.add_row()
    labels = ["", *([fmt_date_long(report.fy.year_end_date)] * 3), *([fmt_date_long(report.fy.comparative_year_end_date)] * 2)]
    for i, text in enumerate(labels):
        _cell_text(hdr2.cells[i], text, bold=True, size=8, align=(WD_ALIGN_PARAGRAPH.RIGHT if i else None))

    total_cost_c = total_acc_c = total_cv_c = total_cost_p = total_acc_p = 0.0
    for asset in report.fy.ppe_assets:
        row = table.add_row()
        prior_cost = asset.opening_cost
        prior_acc = asset.opening_accumulated_depreciation
        _cell_text(row.cells[0], asset.asset_category, size=9)
        _cell_text(row.cells[1], fmt(asset.closing_cost), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[2], fmt(asset.closing_accumulated_depreciation), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[3], fmt(asset.carrying_value), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[4], fmt(prior_cost), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[5], fmt(prior_acc), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        total_cost_c += asset.closing_cost
        total_acc_c += asset.closing_accumulated_depreciation
        total_cv_c += asset.carrying_value
        total_cost_p += prior_cost
        total_acc_p += prior_acc

    row = table.add_row()
    _cell_text(row.cells[0], "Total", bold=True, size=9)
    for idx, val in enumerate([total_cost_c, total_acc_c, total_cv_c, total_cost_p, total_acc_p], start=1):
        c = row.cells[idx]
        _cell_text(c, fmt(val), bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _set_cell_border(c, top={"sz": 6, "val": "single"})

    add_body_paragraph(doc, "", space_after=6)
    add_body_paragraph(
        doc,
        "Reconciliation of property, plant and equipment - " + fmt_date_long(report.fy.year_end_date),
        bold=True, size=9, space_after=4,
    )
    recon = doc.add_table(rows=0, cols=5)
    _no_table_borders(recon)
    _set_col_widths(recon, (5.0, 2.5, 2.5, 2.5, 2.5))
    hdr = recon.add_row()
    for i, text in enumerate(["", "Opening balance", "Additions", "Depreciation", "Closing balance"]):
        _cell_text(hdr.cells[i], text, bold=True, size=8, align=(WD_ALIGN_PARAGRAPH.RIGHT if i else None))
    for asset in report.fy.ppe_assets:
        row = recon.add_row()
        opening_cv = asset.opening_cost - asset.opening_accumulated_depreciation
        _cell_text(row.cells[0], asset.asset_category, size=9)
        _cell_text(row.cells[1], fmt(opening_cv), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[2], fmt(asset.additions), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[3], fmt(-asset.depreciation_charge), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[4], fmt(asset.carrying_value), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)


def build_note_loans(doc, report: ReportData):
    n = report.notes.get("loans")
    _notes_header(doc, report, f"{n}. Loans to (from) shareholders")

    table = doc.add_table(rows=0, cols=3)
    _no_table_borders(table)
    _set_col_widths(table, (10.0, 3.0, 3.0))
    hdr = table.add_row()
    for i, text in enumerate(["", fmt_date_long(report.fy.year_end_date), fmt_date_long(report.fy.comparative_year_end_date)]):
        _cell_text(hdr.cells[i], text, bold=True, size=9, align=(WD_ALIGN_PARAGRAPH.RIGHT if i else None))

    total_c = total_p = 0.0
    for loan in report.fy.shareholder_loans:
        sign = 1 if normalize_direction(loan.direction) == "To" else -1
        row = table.add_row()
        _cell_text(row.cells[0], loan.shareholder_name, size=10)
        _cell_text(row.cells[1], fmt(sign * loan.closing_balance), align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        _cell_text(row.cells[2], fmt(sign * loan.opening_balance), align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        total_c += sign * loan.closing_balance
        total_p += sign * loan.opening_balance

    row = table.add_row()
    _cell_text(row.cells[0], "Total", bold=True, size=10)
    for idx, val in ((1, total_c), (2, total_p)):
        c = row.cells[idx]
        _cell_text(c, fmt(val), bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, size=10)
        _set_cell_border(c, top={"sz": 6, "val": "single"})

    add_body_paragraph(doc, "", space_after=6)
    add_body_paragraph(
        doc,
        "A positive balance represents an amount owing to the company by the shareholder/director (an asset); "
        "a negative balance represents an amount owing by the company to the shareholder/director (a liability).",
        size=8,
    )

    for loan in report.fy.shareholder_loans:
        rate_text = "interest-free" if not loan.interest_rate_pa else f"at {loan.interest_rate_pa * 100:.2f}% per annum"
        add_body_paragraph(
            doc,
            f"The loan {'to' if normalize_direction(loan.direction) == 'To' else 'from'} {loan.shareholder_name} is "
            f"{loan.secured_or_unsecured.lower()}, {rate_text}, and {loan.repayment_terms or 'has no fixed terms of repayment'}. "
            "This loan account is disclosed as a related party transaction in terms of Section 33 of the IFRS "
            "for SME's, as the shareholder/director is a related party of the company.",
        )


def build_note_receivables(doc, report: ReportData):
    n = report.notes.get("receivables")
    _notes_header(doc, report, f"{n}. Trade and other receivables")
    bsc, bsp = report.balance_sheet_current, report.balance_sheet_prior
    rows = [{"label": "Trade receivables", "current": bsc.trade_and_other_receivables, "prior": bsp.trade_and_other_receivables}]
    add_statement_table(doc, rows, header=("", "", fmt_date_long(report.fy.year_end_date), fmt_date_long(report.fy.comparative_year_end_date)))


def build_note_payables(doc, report: ReportData):
    n = report.notes.get("payables")
    _notes_header(doc, report, f"{n}. Trade and other payables")
    bsc, bsp = report.balance_sheet_current, report.balance_sheet_prior
    rows = [{"label": "Trade payables", "current": bsc.trade_and_other_payables, "prior": bsp.trade_and_other_payables}]
    add_statement_table(doc, rows, header=("", "", fmt_date_long(report.fy.year_end_date), fmt_date_long(report.fy.comparative_year_end_date)))


def build_note_inventory(doc, report: ReportData):
    n = report.notes.get("inventory")
    _notes_header(doc, report, f"{n}. Inventories")
    bsc, bsp = report.balance_sheet_current, report.balance_sheet_prior
    rows = [{"label": "Inventories, at the lower of cost and net realisable value",
             "current": bsc.inventory, "prior": bsp.inventory}]
    add_statement_table(doc, rows, header=("", "", fmt_date_long(report.fy.year_end_date), fmt_date_long(report.fy.comparative_year_end_date)))


def build_note_current_tax_payable(doc, report: ReportData):
    n = report.notes.get("current_tax_payable")
    _notes_header(doc, report, f"{n}. Current tax payable")
    bsc, bsp = report.balance_sheet_current, report.balance_sheet_prior
    rows = [{"label": "Current tax payable", "current": bsc.current_tax_payable, "prior": bsp.current_tax_payable}]
    add_statement_table(doc, rows, header=("", "", fmt_date_long(report.fy.year_end_date), fmt_date_long(report.fy.comparative_year_end_date)))


def build_note_investment_revenue(doc, report: ReportData):
    n = report.notes.get("investment_revenue")
    _notes_header(doc, report, f"{n}. Investment revenue")
    ic, ip = report.income_current, report.income_prior
    rows = [{"label": "Interest income", "current": ic.investment_revenue, "prior": ip.investment_revenue}]
    add_statement_table(doc, rows, header=("", "", fmt_date_long(report.fy.year_end_date), fmt_date_long(report.fy.comparative_year_end_date)))


def build_note_cash_generated(doc, report: ReportData):
    n = report.notes.get("cash_generated")
    _notes_header(doc, report, f"{n}. Cash generated from (used in) operations")
    cf = report.cash_flow
    rows = [
        {"label": "Profit before taxation", "current": cf.profit_before_tax},
        {"label": "Adjustments for:", "style": "section"},
        {"label": "Depreciation", "current": cf.depreciation_addback},
        {"label": "Investment revenue", "current": cf.investment_revenue_deduction},
        {"label": "Finance costs", "current": cf.finance_costs_addback},
        {"label": "Changes in working capital:", "style": "section"},
        {"label": "Trade and other receivables", "current": cf.receivables_movement, "dash_zero": True},
        {"label": "Trade and other payables", "current": cf.payables_movement, "dash_zero": True},
        {"label": "", "current": cf.reconciliation_total, "style": "grandtotal"},
    ]
    add_statement_table(doc, rows, header=("", "", fmt_date_long(report.fy.year_end_date), ""))


NOTE_BUILDERS = {
    "ppe": build_note_ppe,
    "loans": build_note_loans,
    "receivables": build_note_receivables,
    "inventory": build_note_inventory,
    "payables": build_note_payables,
    "current_tax_payable": build_note_current_tax_payable,
    "investment_revenue": build_note_investment_revenue,
    "cash_generated": build_note_cash_generated,
}

NOTE_TITLES = {
    "ppe": "Property, plant and equipment",
    "loans": "Loans to (from) shareholders",
    "receivables": "Trade and other receivables",
    "inventory": "Inventories",
    "payables": "Trade and other payables",
    "current_tax_payable": "Current tax payable",
    "investment_revenue": "Investment revenue",
    "cash_generated": "Cash generated from (used in) operations",
}

NOTE_ORDER = ["ppe", "loans", "receivables", "inventory", "payables", "current_tax_payable", "investment_revenue", "cash_generated"]


# ---------------------------------------------------------------------------
# Detailed Income Statement (8.10)
# ---------------------------------------------------------------------------


def build_detailed_income_statement(doc, report: ReportData):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Detailed Income Statement")
    ic, ip = report.income_current, report.income_prior

    rows = [
        {"label": "Revenue", "current": ic.revenue, "prior": ip.revenue},
        {"label": "Cost of sales", "current": -ic.cost_of_sales, "prior": -ip.cost_of_sales},
        {"label": "Gross profit", "current": ic.gross_profit, "prior": ip.gross_profit, "style": "subtotal"},
        {"label": "Other income", "current": 0, "prior": 0, "dash_zero": True},
        {"label": "Investment revenue", "current": ic.investment_revenue, "prior": ip.investment_revenue},
        {"style": "blank"},
        {"label": "Operating expenses", "style": "section"},
    ]
    for name, cur, pri in report.detailed_opex_lines:
        rows.append({"label": name, "current": -cur, "prior": -pri})
    rows.append({"label": "Total operating expenses", "current": -ic.total_operating_expenses,
                 "prior": -ip.total_operating_expenses, "style": "subtotal"})
    rows.append({"label": "Operating profit (loss)", "current": ic.operating_profit, "prior": ip.operating_profit, "style": "subtotal"})
    rows.append({"label": "Finance costs", "current": -ic.finance_costs, "prior": -ip.finance_costs})
    rows.append({"label": "Profit for the year", "current": ic.profit_for_the_year, "prior": ip.profit_for_the_year, "style": "grandtotal"})

    add_statement_table(
        doc, rows, col_widths_cm=(9.0, 1.5, 3.0, 3.0),
        header=("Figures in Rand", "", fmt_date_long(fy.year_end_date), fmt_date_long(fy.comparative_year_end_date)),
    )


# ---------------------------------------------------------------------------
# Tax Computation (8.11)
# ---------------------------------------------------------------------------


def build_tax_computation(doc, report: ReportData):
    entity, fy = report.entity, report.fy
    add_page_header_block(doc, entity, fy.year_end_date, "Tax Computation")
    tax = report.tax

    rows = [
        {"label": "Net profit per income statement", "current": tax.net_profit_per_income_statement},
        {"style": "blank"},
        {"label": "Temporary differences", "style": "section"},
    ]
    for td in tax.temporary_differences:
        rows.append({"label": td.description, "current": td.amount})
    rows.append({"label": "Total temporary differences", "current": tax.total_temporary_differences, "style": "subtotal"})
    rows.append({"style": "blank"})
    rows.append({"label": "Calculated tax profit for the year", "current": tax.calculated_tax_profit})
    rows.append({"label": "Assessed loss brought forward", "current": tax.assessed_loss_brought_forward})
    rows.append({"label": "Assessed loss utilised", "current": tax.assessed_loss_utilised})
    rows.append({"label": "Taxable income for the year", "current": tax.taxable_income, "style": "subtotal"})
    rows.append({"label": "Assessed loss carried forward", "current": tax.assessed_loss_carried_forward})

    add_statement_table(
        doc, rows, col_widths_cm=(11.0, 1.5, 3.0, 1.5),
        header=("Figures in Rand", "", fmt_date_long(fy.year_end_date), ""),
    )

    add_body_paragraph(doc, "", space_after=6)
    add_body_paragraph(doc, "Tax bracket table applied", bold=True, size=10, space_after=4)
    table = doc.add_table(rows=0, cols=3)
    _no_table_borders(table)
    _set_col_widths(table, (5.0, 5.0, 3.0))
    hdr = table.add_row()
    for i, text in enumerate(["Lower limit", "Upper limit", "Rate"]):
        _cell_text(hdr.cells[i], text, bold=True, size=9, align=(WD_ALIGN_PARAGRAPH.RIGHT if i else None))
    for b in tax.bracket_breakdown:
        row = table.add_row()
        _cell_text(row.cells[0], fmt(b["lower_limit"]), align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[1], fmt(b["upper_limit"]) if b["upper_limit"] else "and above", align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)
        _cell_text(row.cells[2], f"{b['rate'] * 100:.0f}%", align=WD_ALIGN_PARAGRAPH.RIGHT, size=9)

    add_body_paragraph(doc, "", space_after=6)
    rows2 = [{"label": "Tax thereon @ rate determined in the table above", "current": tax.tax_thereon, "style": "grandtotal"}]
    add_statement_table(doc, rows2, col_widths_cm=(11.0, 1.5, 3.0, 1.5), header=("", "", "", ""))


# ---------------------------------------------------------------------------
# Page sequence / numbering (deterministic: one forced page break per chunk,
# so the numbers we print always match the physical pages Word renders, as
# long as no single chunk's content overflows one page - see README).
# ---------------------------------------------------------------------------


def compute_page_sequence(report: ReportData) -> list[str]:
    report_title = REPORT_TYPE_TITLES.get(report.entity.report_type, "Practitioner's Compilation Report")
    seq = [
        "Cover",
        "General Information",
        "Index",
        "Director's Responsibilities and Approval",
        "Director's Report",
        report_title,
        "Statement of Financial Position",
        "Statement of Comprehensive Income",
        "Statement of Changes in Equity",
        "Statement of Cash Flows",
        "Accounting Policies",
    ]
    for key in NOTE_ORDER:
        if report.notes.has(key):
            seq.append(NOTE_TITLES[key])
    seq.append("Detailed Income Statement")
    seq.append("Tax Computation")
    return seq


def _approval_director_name(report: ReportData) -> str:
    signers = [d.full_name for d in report.entity.directors if d.signs_approval and d.date_resigned is None]
    if signers:
        return "\n".join(signers)
    return "[Director name]"


def _next_year_end_label(report: ReportData) -> str:
    fy = report.fy
    try:
        next_end = fy.year_end_date.replace(year=fy.year_end_date.year + 1)
        return fmt_date_long(next_end)
    except Exception:
        return "[next year end]"


def generate_afs_docx(report: ReportData) -> BytesIO:
    """Builds the full AFS pack and returns it as an in-memory .docx file."""
    if not report.is_valid:
        raise ValueError("Cannot generate the AFS pack while validation checks are failing.")

    seq = compute_page_sequence(report)
    page_map = {title: i + 1 for i, title in enumerate(seq)}

    report_title = REPORT_TYPE_TITLES.get(report.entity.report_type, "Practitioner's Compilation Report")
    present_note_titles = [NOTE_TITLES[k] for k in NOTE_ORDER if report.notes.has(k)]
    first_statement_page = page_map["Statement of Financial Position"]
    last_note_page = page_map[present_note_titles[-1]] if present_note_titles else page_map["Accounting Policies"]
    sfp_page = page_map["Statement of Financial Position"]
    approval_director_name = _approval_director_name(report)
    next_year_end_label = _next_year_end_label(report)

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = Pt(10)
    for section in doc.sections:
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)

    build_cover_page(doc, report)
    add_page_break(doc)

    build_general_information(doc, report)
    add_page_break(doc)

    contents_entries = [
        ("Director's Responsibilities and Approval", page_map["Director's Responsibilities and Approval"]),
        ("Director's Report", page_map["Director's Report"]),
        (report_title, page_map[report_title]),
        ("Statement of Financial Position", page_map["Statement of Financial Position"]),
        ("Statement of Comprehensive Income", page_map["Statement of Comprehensive Income"]),
        ("Statement of Changes in Equity", page_map["Statement of Changes in Equity"]),
        ("Statement of Cash Flows", page_map["Statement of Cash Flows"]),
        ("Accounting Policies", page_map["Accounting Policies"]),
        ("Notes to the Annual Financial Statements", page_map[present_note_titles[0]] if present_note_titles else page_map["Accounting Policies"]),
        ("Detailed Income Statement", page_map["Detailed Income Statement"]),
        ("Tax Computation", page_map["Tax Computation"]),
    ]
    build_contents_page(doc, report, contents_entries)
    add_page_break(doc)

    build_directors_responsibilities(
        doc, report, next_year_end_label, approval_director_name, first_statement_page, last_note_page
    )
    add_page_break(doc)

    build_directors_report(doc, report, sfp_page, approval_director_name)
    add_page_break(doc)

    build_practitioners_report(doc, report, first_statement_page, last_note_page)
    add_page_break(doc)

    build_statement_of_financial_position(doc, report)
    add_page_break(doc)
    build_statement_of_comprehensive_income(doc, report)
    add_page_break(doc)
    build_statement_of_changes_in_equity(doc, report)
    add_page_break(doc)
    build_statement_of_cash_flows(doc, report)
    add_page_break(doc)

    build_accounting_policies(doc, report)
    add_page_break(doc)

    for i, key in enumerate(NOTE_ORDER):
        if report.notes.has(key):
            NOTE_BUILDERS[key](doc, report)
            add_page_break(doc)

    build_detailed_income_statement(doc, report)
    add_page_break(doc)

    build_tax_computation(doc, report)

    # Footer with page numbers on every page.
    for section in doc.sections:
        footer = section.footer
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(WATERMARK_TEXT)
        run.italic = True
        run.font.size = Pt(7)
        run.font.color.rgb = RGBColor(0xA0, 0xA0, 0xA0)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
