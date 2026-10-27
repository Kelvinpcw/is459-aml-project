#!/usr/bin/env python3
"""Regenerate the architecture PNG/PDF exports from the editable draw.io files.

Requirements: Python 3, PyMuPDF, and rsvg-convert (librsvg).
Run from any directory: python3 "Proposal 5/Architecture/render_architecture.py"

The supported draw.io shapes are deliberately limited to those in these diagrams:
groups, text, rectangles, ellipses, embedded images, and explicitly routed edges.
The separate proposal overview SVG is also rendered and embedded into the Word
proposal, without rebuilding or replacing the document's text or formatting.
"""

from __future__ import annotations

import html
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import pymupdf


HERE = Path(__file__).resolve().parent
PROPOSAL = HERE.parent
TEMP_ROOT = Path(os.environ.get("TMPDIR", tempfile.gettempdir())) / "opencode"
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)


def element(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{tag}", {k: str(v) for k, v in attrs.items()})


def style_map(cell):
    return dict(part.split("=", 1) for part in cell.get("style", "").split(";") if "=" in part)


def export_svg(model, destination):
    width = float(model.get("pageWidth"))
    height = float(model.get("pageHeight"))
    svg = ET.Element(f"{{{SVG}}}svg", {
        "width": f"{width / 2:g}pt", "height": f"{height / 2:g}pt",
        "viewBox": f"0 0 {width:g} {height:g}", "version": "1.1",
    })
    element(svg, "rect", x=0, y=0, width=width, height=height, fill="#FFFFFF")
    defs = element(svg, "defs")
    markers = {}
    cells = list(model.find("root"))
    by_id = {c.get("id"): c for c in cells}

    def offset(parent):
        if parent in (None, "0", "1"):
            return 0.0, 0.0
        cell = by_id[parent]
        px, py = offset(cell.get("parent"))
        geometry = cell.find("mxGeometry")
        return px + float(geometry.get("x", 0)), py + float(geometry.get("y", 0))

    def marker(color, arrow):
        key = color, arrow
        if key not in markers:
            name = f"arrow-{len(markers)}"
            markers[key] = name
            node = element(defs, "marker", id=name, viewBox="0 0 10 8", refX=9, refY=4,
                           markerWidth=10, markerHeight=8, markerUnits="userSpaceOnUse", orient="auto")
            element(node, "path", d="M0 0 L9 4 L0 8 Z", fill=color)
        return f"url(#{markers[key]})"

    for cell in cells:
        geometry = cell.find("mxGeometry")
        if geometry is None or cell.get("style") == "group;":
            continue
        style = style_map(cell)
        px, py = offset(cell.get("parent"))
        color = style.get("strokeColor", "none")
        stroke = {"stroke": color, "stroke-width": style.get("strokeWidth", "1.5")}
        if style.get("dashed") == "1":
            stroke["stroke-dasharray"] = style.get("dashPattern", "8 6")

        if cell.get("edge") == "1":
            for key in ("source", "target"):
                if cell.get(key) and cell.get(key) not in by_id:
                    raise ValueError(f"Unknown {key}: {cell.get(key)}")
            start = geometry.find("mxPoint[@as='sourcePoint']")
            end = geometry.find("mxPoint[@as='targetPoint']")
            if start is None or end is None:
                raise ValueError(f"Edge {cell.get('id')} requires explicit endpoints")
            points = [start, *geometry.findall("Array/mxPoint"), end]
            path = " ".join(f"{'M' if i == 0 else 'L'}{px + float(p.get('x')):g} {py + float(p.get('y')):g}"
                            for i, p in enumerate(points))
            attrs = {"d": path, "fill": "none", **stroke, "stroke-linejoin": "round"}
            if style.get("endArrow", "none") != "none":
                attrs["marker-end"] = marker(color, style["endArrow"])
            element(svg, "path", **attrs)
            continue

        x = px + float(geometry.get("x", 0))
        y = py + float(geometry.get("y", 0))
        w = float(geometry.get("width", 0))
        h = float(geometry.get("height", 0))
        if cell.get("style", "").startswith("text;"):
            value = re.sub(r"<br\s*/?>", "\n", cell.get("value", ""), flags=re.I)
            value = html.unescape(re.sub(r"<[^>]*>", "", value))
            lines = value.splitlines() or [""]
            size = float(style.get("fontSize", 22))
            bits = int(style.get("fontStyle", 0))
            attrs = {"x": x, "y": y + size * .94, "fill": style.get("fontColor", "#172B42"),
                     "font-family": "Arial, Helvetica, sans-serif", "font-size": size,
                     "font-weight": "bold" if bits & 1 else "normal"}
            if bits & 2:
                attrs["font-style"] = "italic"
            node = element(svg, "text", **attrs)
            spacing = h / len(lines) if len(lines) > 1 else size * 1.3
            for i, line in enumerate(lines):
                element(node, "tspan", x=x, y=y + size * .94 + i * spacing).text = line
            continue

        shape = style.get("shape")
        if shape == "image":
            data = style["image"].replace("data:image/png,", "data:image/png;base64,", 1)
            image = element(svg, "image", x=x, y=y, width=w, height=h, preserveAspectRatio="none")
            image.set(f"{{{XLINK}}}href", data)
        elif shape == "rectangle":
            attrs = {"x": x, "y": y, "width": w, "height": h,
                     "fill": style.get("fillColor", "none"), **stroke}
            if style.get("rounded") == "1":
                attrs["rx"] = min(10, min(w, h) * .035)
            element(svg, "rect", **attrs)
        elif shape == "ellipse":
            element(svg, "ellipse", cx=x + w / 2, cy=y + h / 2, rx=w / 2, ry=h / 2,
                    fill=style.get("fillColor", "none"), **stroke)
        else:
            raise ValueError(f"Unsupported draw.io shape: {shape!r} ({cell.get('id')})")
    ET.ElementTree(svg).write(destination, encoding="utf-8", xml_declaration=True)


def render(source, destination, fmt, width=None):
    command = ["rsvg-convert", "--format", fmt, "--output", str(destination)]
    if width:
        command.extend(["--width", str(width)])
    subprocess.run([*command, str(source)], check=True)


def refresh_word_image(image):
    document = PROPOSAL / "Project_Proposal_5.docx"
    namespaces = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
                  "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    pix = pymupdf.Pixmap(str(image))
    with zipfile.ZipFile(document) as source:
        names = [n for n in source.namelist() if n.startswith("word/media/")]
        if names != ["word/media/image1.png"]:
            raise ValueError("Expected exactly one existing proposal image; refusing an ambiguous replacement")
        xml = source.read("word/document.xml")
        # Keep all original XML namespace prefixes and formatting. Only the
        # existing image's two extent attributes need an updated aspect ratio.
        tree = ET.fromstring(xml)
        extent = tree.find(".//wp:inline/wp:extent", namespaces)
        if extent is None:
            raise ValueError("Expected an inline proposal image")
        cx = int(extent.get("cx"))
        old_cy = extent.get("cy")
        cy = str(round(cx * pix.height / pix.width))
        xml = re.sub(rb'(<wp:extent\b[^>]*\bcy=")' + old_cy.encode() + rb'(")',
                     lambda m: m[1] + cy.encode() + m[2], xml, count=1)
        xml = re.sub(rb'(<a:ext\b[^>]*\bcy=")' + old_cy.encode() + rb'(")',
                     lambda m: m[1] + cy.encode() + m[2], xml, count=1)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as target:
            for entry in source.infolist():
                content = image.read_bytes() if entry.filename == names[0] else (
                    xml if entry.filename == "word/document.xml" else source.read(entry.filename))
                target.writestr(entry, content)
    document.write_bytes(data.getvalue())


def main():
    if not shutil.which("rsvg-convert"):
        raise SystemExit("Install librsvg / rsvg-convert before rendering")
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aml-diagram-render-", dir=TEMP_ROOT) as temp:
        temp = Path(temp)
        outputs = []
        for kind in ("Detailed", "Simplified"):
            folder = HERE / kind
            source = ET.parse(folder / "AWS_Architecture.drawio")
            pack = pymupdf.open()
            for i, diagram in enumerate(source.getroot().findall("diagram")):
                name = ("01_Shared_AWS_Architecture", "02_BQ1_Monitoring", "03_BQ2_Investigation")[i]
                svg, png, pdf = (temp / f"{kind}-{name}.{ext}" for ext in ("svg", "png", "pdf"))
                export_svg(diagram.find("mxGraphModel"), svg)
                render(svg, png, "png", width=3600)
                render(svg, pdf, "pdf")
                with pymupdf.open(pdf) as page:
                    pack.insert_pdf(page)
                outputs.append((png, folder / f"{name}.png"))
            pdf = temp / f"{kind}-AWS_Architecture_Pack.pdf"
            pack.save(pdf, garbage=4, deflate=True)
            pack.close()
            outputs.append((pdf, folder / "AWS_Architecture_Pack.pdf"))
        overview = temp / "Proposed_AWS_Architecture.png"
        render(PROPOSAL / "assets/Proposed_AWS_Architecture.svg", overview, "png", width=2880)
        outputs.append((overview, PROPOSAL / "assets/Proposed_AWS_Architecture.png"))
        for temporary, destination in outputs:
            os.replace(temporary, destination)
            print(destination.relative_to(PROPOSAL))
        refresh_word_image(PROPOSAL / "assets/Proposed_AWS_Architecture.png")
        print("Project_Proposal_5.docx: refreshed architecture image")


if __name__ == "__main__":
    main()
