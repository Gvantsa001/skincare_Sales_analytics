from __future__ import annotations

import struct
import zlib
from pathlib import Path


PALETTE = ["#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#17becf", "#8c564b", "#d62728"]


def svg_line_chart(path: Path, points: list[tuple[str, float]], title: str, width: int = 1100, height: int = 420) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    margin_left, margin_right, margin_top, margin_bottom = 70, 24, 48, 54
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    values = [value for _, value in points]
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        max_v += 1
    coords = []
    for idx, (_, value) in enumerate(points):
        x = margin_left + (idx / max(1, len(points) - 1)) * plot_w
        y = margin_top + (max_v - value) / (max_v - min_v) * plot_h
        coords.append(f"{x:.1f},{y:.1f}")
    tick_labels = []
    for idx in [0, len(points) // 4, len(points) // 2, (len(points) * 3) // 4, len(points) - 1]:
        label = points[idx][0]
        x = margin_left + (idx / max(1, len(points) - 1)) * plot_w
        tick_labels.append(f'<text x="{x:.1f}" y="{height - 20}" text-anchor="middle" font-size="11">{label}</text>')
    grid = []
    for i in range(5):
        y = margin_top + i * plot_h / 4
        value = max_v - i * (max_v - min_v) / 4
        grid.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        grid.append(f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11">${value:,.0f}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{margin_left}" y="28" font-size="20" font-family="Arial" font-weight="700">{title}</text>
{''.join(grid)}
<polyline fill="none" stroke="{PALETTE[0]}" stroke-width="2.4" points="{' '.join(coords)}"/>
<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#333"/>
<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" stroke="#333"/>
{''.join(tick_labels)}
</svg>
'''
    path.write_text(svg, encoding="utf-8")


def svg_bar_chart(path: Path, bars: list[tuple[str, float]], title: str, width: int = 900, height: int = 430) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    margin_left, margin_right, margin_top, margin_bottom = 86, 24, 52, 104
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_v = max(value for _, value in bars) or 1
    bar_gap = 10
    bar_w = (plot_w - bar_gap * (len(bars) - 1)) / len(bars)
    rects = []
    labels = []
    for idx, (label, value) in enumerate(bars):
        x = margin_left + idx * (bar_w + bar_gap)
        h = (value / max_v) * plot_h
        y = margin_top + plot_h - h
        color = PALETTE[idx % len(PALETTE)]
        rects.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}"/>')
        labels.append(f'<text transform="translate({x + bar_w / 2:.1f},{height - 82}) rotate(-35)" text-anchor="end" font-size="11">{label}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{margin_left}" y="30" font-size="20" font-family="Arial" font-weight="700">{title}</text>
<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#333"/>
<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" stroke="#333"/>
<text x="{margin_left - 8}" y="{margin_top + 4}" text-anchor="end" font-size="11">${max_v:,.0f}</text>
{''.join(rects)}
{''.join(labels)}
</svg>
'''
    path.write_text(svg, encoding="utf-8")


def png_bar_chart(path: Path, bars: list[tuple[str, float]], width: int = 900, height: int = 520) -> None:
    """Write a simple RGB PNG bar chart without third-party dependencies."""
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = bytearray([255, 255, 255] * width * height)

    def pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            canvas[offset : offset + 3] = bytes(color)

    def rect(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y0), min(height, y1)):
            row_offset = (y * width) * 3
            for x in range(max(0, x0), min(width, x1)):
                offset = row_offset + x * 3
                canvas[offset : offset + 3] = bytes(color)

    def line(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            pixel(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    left, right, top, bottom = 90, 40, 60, 90
    plot_w = width - left - right
    plot_h = height - top - bottom
    axis = (40, 40, 40)
    grid = (225, 225, 225)
    for i in range(6):
        y = top + int(i * plot_h / 5)
        line(left, y, width - right, y, grid)
    line(left, top, left, height - bottom, axis)
    line(left, height - bottom, width - right, height - bottom, axis)

    max_value = max([value for _, value in bars] or [1.0])
    bar_count = max(1, len(bars))
    gap = 34
    bar_w = max(24, int((plot_w - gap * (bar_count + 1)) / bar_count))
    colors = [(31, 119, 180), (44, 160, 44), (255, 127, 14), (148, 103, 189), (214, 39, 40)]
    for idx, (_, value) in enumerate(bars):
        x0 = left + gap + idx * (bar_w + gap)
        h = int((value / max_value) * (plot_h - 8)) if max_value else 0
        y0 = height - bottom - h
        rect(x0, y0, x0 + bar_w, height - bottom, colors[idx % len(colors)])
        rect(x0, y0, x0 + bar_w, y0 + 4, (20, 20, 20))

    # A small color key in the upper-left makes the image recognizable even without text rendering.
    for idx, _ in enumerate(bars):
        rect(24, 22 + idx * 18, 42, 34 + idx * 18, colors[idx % len(colors)])

    raw = b"".join(b"\x00" + canvas[y * width * 3 : (y + 1) * width * 3] for y in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
