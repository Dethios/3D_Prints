"""Rasterize the project's path-only SVG at 2x and downsample the edges."""

from pathlib import Path
import math
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw
from svgpathtools import parse_path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "artwork" / "mulan-illustration.svg"
    graphic = ET.parse(source).getroot()
    scale = 2
    w, h = (int(graphic.get(k)) for k in ("width", "height"))
    image = Image.new("RGBA", (w*scale, h*scale))
    brush = ImageDraw.Draw(image)
    for item in graphic.findall("{*}path"):
        fill = item.get("fill", "black")
        stroke = item.get("stroke")
        width = round(float(item.get("stroke-width", "1"))*scale)
        for contour in parse_path(item.attrib["d"]).continuous_subpaths():
            points = []
            for piece in contour:
                count = max(2, math.ceil(piece.length()/1.2))
                points.extend((p.real*scale, p.imag*scale)
                              for p in (piece.point(j/count) for j in range(count)))
            end = contour[-1].end
            points.append((end.real*scale, end.imag*scale))
            if fill != "none":
                brush.polygon(points, fill=fill)
            if stroke:
                brush.line(points, stroke, width=width, joint="curve")
    image.resize((w,h), Image.Resampling.LANCZOS).save(source.with_suffix(".png"))


if __name__ == "__main__":
    main()
