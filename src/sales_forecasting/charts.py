from __future__ import annotations

import struct
import zlib
from pathlib import Path


PALETTE = ["#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#17becf", "#8c564b", "#d62728"]


def svg_line_chart(
        path: Path,
        actual_points: list[tuple[str, float]],
        models_forecasts: dict[str, list[tuple[str, float]]],
        title: str,
        width: int = 1100,
        height: int = 450,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    margin_left, margin_right, margin_top, margin_bottom = 70, 40, 50, 80
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    # ვაგროვებთ ყველა მნიშვნელობას მაქსიმუმისა და მინიმუმის დასადგენად
    all_values = [v for _, v in actual_points]
    for pts in models_forecasts.values():
        all_values.extend([v for _, v in pts if v is not None])

    if not all_values:
        return

    min_v, max_v = min(all_values), max(all_values)
    if max_v == min_v:
        max_v += 1

    total_len = len(actual_points)

    def get_coords(points):
        coords = []
        for idx, (_, value) in enumerate(points):
            if value is None:
                continue
            x = margin_left + (idx / max(1, total_len - 1)) * plot_w
            y = margin_top + (max_v - value) / (max_v - min_v) * plot_h
            coords.append(f"{x:.1f},{y:.1f}")
        return coords

    # Actual ხაზის კოორდინატები
    actual_coords = get_coords(actual_points)

    # ფერების პალიტრა მოდელებისთვის
    colors = ["#ff7f0e", "#2ca02c", "#9467bd", "#17becf"]

    lines_svg = []
    legend_svg = []

    # Actual-ის დამატება ლეგენდაში
    legend_svg.append(
        f'<text x="{margin_left}" y="{height - 25}" fill="#1f77b4" font-weight="bold" font-size="12">● Actual</text>')

    # მოდელების ხაზების გენერაცია
    for c_idx, (model_name, points) in enumerate(models_forecasts.items()):
        if not points:
            continue
        coords = get_coords(points)
        color = colors[c_idx % len(colors)]

        # ვხატავთ წყვეტილ (dashed) ხაზს მოდელებისთვის
        lines_svg.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="5 3" points="{" ".join(coords)}"/>'
        )

        # ლეგენდის პოზიციის გამოთვლა (ჰორიზონტალურად ჩამწკრივება)
        leg_x = margin_left + 120 + (c_idx * 180)
        legend_svg.append(
            f'<text x="{leg_x}" y="{height - 25}" fill="{color}" font-weight="bold" font-size="12">● {model_name}</text>'
        )

    # ბადისა (Grid) და თიქების დამზადება
    grid = []
    for i in range(5):
        y = margin_top + i * plot_h / 4
        val = max_v - i * (max_v - min_v) / 4
        grid.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        grid.append(f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11">${val:,.0f}</text>')

    tick_labels = []
    tick_indices = [0, total_len // 4, total_len // 2, (total_len * 3) // 4, total_len - 1]
    for idx in sorted(list(set(tick_indices))):
        if idx < total_len:
            x = margin_left + (idx / max(1, total_len - 1)) * plot_w
            tick_labels.append(
                f'<text x="{x:.1f}" y="{height - 55}" text-anchor="middle" font-size="11">{actual_points[idx][0]}</text>')

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
        <rect width="100%" height="100%" fill="white"/>
        <text x="{margin_left}" y="30" font-size="18" font-family="Arial" font-weight="700">{title}</text>
        {''.join(grid)}
        <polyline fill="none" stroke="#1f77b4" stroke-width="3" points="{' '.join(actual_coords)}"/>
        {''.join(lines_svg)}
        <line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#333"/>
        <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" stroke="#333"/>
        {''.join(tick_labels)}
        {''.join(legend_svg)}
    </svg>
    """
    path.write_text(svg, encoding="utf-8")


def svg_bar_chart(
    path: Path,
    data: list[tuple[str, float]],
    title: str = "",
    width: int = 1000,
    height: int = 500,
) -> None:
    if not data:
        return

    # ჩარჩოსა და ველების (Padding) განსაზღვრა
    padding_top = 60
    padding_bottom = 80
    padding_left = 100
    padding_right = 50

    chart_width = width - padding_left - padding_right
    chart_height = height - padding_top - padding_bottom

    max_val = max(val for _, val in data) if data else 1.0
    if max_val == 0:
        max_val = 1.0

    # SVG ფაილის დაწყება
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="background:#fff; font-family:sans-serif;">'
    ]

    # სათაურის დამატება
    if title:
        svg.append(f'<text x="{width // 2}" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#333">{title}</text>')

    # Y ღერძის ბადე (Grid Lines) და თიქები
    grid_lines = 5
    for i in range(grid_lines + 1):
        val = (max_val / grid_lines) * i
        y = height - padding_bottom - (chart_height / grid_lines) * i
        svg.append(f'<line x1="{padding_left}" y1="{y}" x2="{width - padding_right}" y2="{y}" stroke="#e0e0e0" stroke-width="1"/>')
        svg.append(f'<text x="{padding_left - 10}" y="{y + 4}" text-anchor="end" font-size="12" fill="#666">${val:,.0f}</text>')

    # სვეტების (Bars) გამოთვლა და დახატვა
    num_bars = len(data)
    bar_gap_ratio = 0.3  # დაშორება სვეტებს შორის
    total_bar_width = chart_width / num_bars
    bar_width = total_bar_width * (1 - bar_gap_ratio)
    gap_width = total_bar_width * bar_gap_ratio

    # ფერების პალიტრა სვეტებისთვის
    colors = ["#3182bd", "#6baed6", "#9ecae1", "#c6dbef", "#e6550d", "#fd8d3c", "#fdae6b", "#fdd0a2", "#31a354", "#74c476"]

    for idx, (label, val) in enumerate(data):
        x = padding_left + idx * total_bar_width + gap_width / 2
        bar_h = (val / max_val) * chart_height
        y = height - padding_bottom - bar_h
        color = colors[idx % len(colors)]

        # სვეტის დახატვა
        svg.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_h}" fill="{color}" rx="3"/>')

        # მნიშვნელობის დაწერა სვეტის თავზე
        if bar_h > 20:
            svg.append(f'<text x="{x + bar_width / 2}" y="{y - 5}" text-anchor="middle" font-size="11" font-weight="bold" fill="#333">${val:,.0f}</text>')

        # კატეგორიის სახელის (X წარწერის) დახატვა დახრილად, რომ ტექსტები ერთმანეთს არ გადაედოს
        svg.append(
            f'<text x="{x + bar_width / 2}" y="{height - padding_bottom + 20}" '
            f'text-anchor="end" font-size="11" fill="#444" '
            f'transform="rotate(-25, {x + bar_width / 2}, {height - padding_bottom + 20})">{label}</text>'
        )

    # მთავარი ღერძების ხაზები
    svg.append(f'<line x1="{padding_left}" y1="{height - padding_bottom}" x2="{width - padding_right}" y2="{height - padding_bottom}" stroke="#888" stroke-width="2"/>')
    svg.append(f'<line x1="{padding_left}" y1="{padding_top}" x2="{padding_left}" y2="{height - padding_bottom}" stroke="#888" stroke-width="2"/>')

    svg.append("</svg>")

    # ფაილში ჩაწერა
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

def svg_scatter_chart(
            path: Path,
            points: list[tuple[float, float]],
            title: str,
            x_label: str,
            y_label: str,
            width: int = 900,
            height: int = 500
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        margin_left, margin_right = 70, 30
        margin_top, margin_bottom = 50, 60

        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        if max_x == min_x:
            max_x += 1

        if max_y == min_y:
            max_y += 1

        circles = []

        for x, y in points:
            cx = margin_left + (x - min_x) / (max_x - min_x) * plot_w
            cy = margin_top + (max_y - y) / (max_y - min_y) * plot_h

            circles.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#1f77b4" opacity="0.7"/>'
            )

        svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg"
         width="{width}"
         height="{height}">

    <rect width="100%" height="100%" fill="white"/>

    <text x="{margin_left}" y="30"
          font-size="20"
          font-weight="bold">
    {title}
    </text>

    <line x1="{margin_left}"
          y1="{height - margin_bottom}"
          x2="{width - margin_right}"
          y2="{height - margin_bottom}"
          stroke="black"/>

    <line x1="{margin_left}"
          y1="{margin_top}"
          x2="{margin_left}"
          y2="{height - margin_bottom}"
          stroke="black"/>

    {''.join(circles)}

    <text x="{width // 2}"
          y="{height - 15}"
          text-anchor="middle">
    {x_label}
    </text>

    <text transform="translate(20,{height // 2}) rotate(-90)"
          text-anchor="middle">
    {y_label}
    </text>

    </svg>
    """

        path.write_text(svg, encoding="utf-8")
