#!/usr/bin/env python3
"""Small OOXML writer. Strings are literal, money is Decimal, formulas cache values."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import math
import zipfile
from xml.sax.saxutils import escape

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def text(value):
    value = str(value)
    if any(not (c in "\t\n\r" or 32 <= ord(c) <= 0xD7FF
                or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF)
           for c in value):
        raise ValueError("Text contains a character XML cannot represent")
    return escape(value, {'"': '&quot;', "'": '&apos;'})


def column(n):
    result = ""
    while n:
        n, rest = divmod(n - 1, 26)
        result = chr(65 + rest) + result
    return result


def formula(expression, cached):
    return {"formula": expression, "value": cached}


def cell(value, ref, header=False, total=False, custom_style=None):
    style = custom_style if custom_style is not None else 1 if header else 4 if total else 0
    if isinstance(value, dict):
        cached = value["value"]
        if not isinstance(cached, (Decimal, int)) or not Decimal(cached).is_finite():
            raise ValueError("A formula requires a finite cached number")
        return (f'<c r="{ref}" s="{5 if total else 2}"><f>{text(value["formula"])}</f>'
                f'<v>{cached}</v></c>')
    if isinstance(value, date):
        serial = (value - date(1899, 12, 30)).days
        return f'<c r="{ref}" s="3"><v>{serial}</v></c>'
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite money")
        return f'<c r="{ref}" s="{5 if total else 2}"><v>{value}</v></c>'
    if isinstance(value, int):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    if isinstance(value, float):
        raise ValueError("Use Decimal, not floating point")
    return (f'<c r="{ref}" s="{style}" t="inlineStr"><is>'
            f'<t xml:space="preserve">{text(value)}</t></is></c>')


def sheet_xml(sheet):
    rows, widths = sheet["rows"], sheet["widths"]
    end = f'{column(len(widths))}{len(rows)}'
    cols = ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                   for i, w in enumerate(widths, 1))
    data = []
    for i, row in enumerate(rows, 1):
        headline = i in sheet.get('headline_rows', [])
        merged = i in sheet.get('merge_rows', [])
        font_size = 20 if headline else 11
        height = max([1] + [sum(max(1, math.ceil(len(line) / max(1, widths[j] - 3)))
                                for line in str(v).split('\n'))
                           for j, v in enumerate(row) if isinstance(v, str)]) * 15 + 10
        height = min(409, max(27, height))
        if merged:
            usable = (sum(widths)-5) * 11 / font_size
            height = max(30, sum(max(1, math.ceil(len(line)/usable)) for line in str(row[0]).split('\n'))
                         * (font_size+5) + 15)
        style = 6 if headline else 7 if i in sheet.get('fine_rows', []) else 8 if i in sheet.get('notice_rows', []) else None
        cells = ''.join(cell(v, f'{column(j)}{i}', i in sheet.get('header_rows', [1]),
                             i in sheet.get("totals", []), style) for j, v in enumerate(row, 1))
        data.append(f'<row r="{i}" ht="{height}" customHeight="1">{cells}</row>')
    auto = f'<autoFilter ref="A1:{end}"/>' if sheet.get("filter") else ''
    merges = sheet.get('merge_rows', [])
    merged_xml = ('<mergeCells count="' + str(len(merges)) + '">' + ''.join(
        f'<mergeCell ref="A{i}:{column(len(widths))}{i}"/>' for i in merges) + '</mergeCells>') if merges else ''
    pane = ('<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>') if sheet.get('freeze', True) else ''
    return (f'<worksheet xmlns="{NS}"><sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>'
            f'<dimension ref="A1:{end}"/><sheetViews><sheetView workbookViewId="0">'
            f'{pane}'
            '</sheetView></sheetViews><sheetFormatPr defaultRowHeight="27"/>'
            f'<cols>{cols}</cols><sheetData>{"".join(data)}</sheetData>{auto}{merged_xml}'
            '<pageMargins left="0.3" right="0.3" top="0.4" bottom="0.4" header="0.2" footer="0.2"/>'
            '<pageSetup paperSize="1" orientation="landscape" fitToWidth="1" fitToHeight="0"/>'
            '<headerFooter><oddFooter>&amp;CPage &amp;P of &amp;N</oddFooter></headerFooter>'
            '</worksheet>')


def styles_xml():
    xfs = []
    for font, fill, num in [(0, 0, 0), (1, 2, 0), (0, 0, 164),
                            (0, 0, 165), (2, 3, 0), (2, 3, 164), (3, 0, 0), (4, 0, 0), (5, 0, 0)]:
        xfs.append(f'<xf numFmtId="{num}" fontId="{font}" fillId="{fill}" borderId="0"'
                   ' xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyAlignment="1">'
                   '<alignment vertical="center" wrapText="1"/></xf>')
    return (f'<styleSheet xmlns="{NS}"><numFmts count="2">'
            '<numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00;[Red](&quot;$&quot;#,##0.00)"/>'
            '<numFmt numFmtId="165" formatCode="mmm d, yyyy"/></numFmts>'
            '<fonts count="6"><font><sz val="11"/><color rgb="FF243247"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><color rgb="FF243247"/><name val="Calibri"/></font>'
            '<font><b/><sz val="20"/><color rgb="FF243247"/><name val="Calibri"/></font>'
            '<font><sz val="10"/><color rgb="FF566579"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><color rgb="FF8A3B12"/><name val="Calibri"/></font></fonts>'
            '<fills count="4"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FF243247"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFE5F0EC"/><bgColor indexed="64"/></patternFill></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            f'<cellXfs count="9">{"".join(xfs)}</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '<dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>'
            '</styleSheet>')


def write_xlsx(output, sheets):
    names = [s["name"] for s in sheets]
    if len(set(names)) != len(names) or any(len(n) > 31 for n in names):
        raise ValueError("Invalid sheet names")
    declarations, rels, overrides = [], [], []
    parts = {"xl/styles.xml": styles_xml()}
    for i, sheet in enumerate(sheets, 1):
        declarations.append(f'<sheet name="{text(sheet["name"])}" sheetId="{i}" r:id="rId{i}"/>')
        rels.append(f'<Relationship Id="rId{i}" Type="{OFFICE}/worksheet" Target="worksheets/sheet{i}.xml"/>')
        overrides.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        parts[f'xl/worksheets/sheet{i}.xml'] = sheet_xml(sheet)
    rels.append(f'<Relationship Id="rId{len(sheets)+1}" Type="{OFFICE}/styles" Target="styles.xml"/>')
    parts["xl/workbook.xml"] = (f'<workbook xmlns="{NS}" xmlns:r="{OFFICE}">'
        '<workbookPr date1904="0"/><bookViews><workbookView activeTab="0"/></bookViews>'
        f'<sheets>{"".join(declarations)}</sheets><definedNames>' + ''.join(
            f'<definedName name="_xlnm.Print_Titles" localSheetId="{i}">{text(chr(39)+n+chr(39))}!$1:$1</definedName>'
            for i, n in enumerate(names)) + '</definedNames>'
        '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    parts['xl/_rels/workbook.xml.rels'] = f'<Relationships xmlns="{REL}">{"".join(rels)}</Relationships>'
    parts['_rels/.rels'] = (f'<Relationships xmlns="{REL}"><Relationship Id="rId1"'
        f' Type="{OFFICE}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    parts['[Content_Types].xml'] = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + ''.join(overrides) + '</Types>')
    # Build every XML part first; no half-written file on validation errors.
    parts = {name: (XML + content).encode('utf-8') for name, content in parts.items()}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_STORED) as archive:
        for name, content in sorted(parts.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 15, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return Path(output)
