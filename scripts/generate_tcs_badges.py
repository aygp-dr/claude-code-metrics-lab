#!/usr/bin/env python3
"""
Generate SVG badges for TCS (Trailer Consistency Score) metrics.
Reads from reports/tcs.json and creates badge SVG files.
"""

import json
import os
from pathlib import Path


def create_badge_svg(label: str, value: str, color: str) -> str:
    """Create an SVG badge with given label, value, and color."""
    # Calculate text widths (rough approximation)
    label_width = len(label) * 7 + 10
    value_width = len(value) * 7 + 10
    total_width = label_width + value_width
    
    # Color mapping
    color_map = {
        'brightgreen': '#4c1',
        'green': '#97ca00',
        'yellow': '#dfb317',
        'orange': '#fe7d37',
        'red': '#e05d44',
        'blue': '#007ec6',
        'lightgrey': '#9f9f9f'
    }
    
    badge_color = color_map.get(color, color)
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h{label_width}v20H0z"/>
    <path fill="{badge_color}" d="M{label_width} 0h{value_width}v20H{label_width}z"/>
    <path fill="url(#b)" d="M0 0h{total_width}v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_width/2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_width/2}" y="14">{label}</text>
    <text x="{label_width + value_width/2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_width + value_width/2}" y="14">{value}</text>
  </g>
</svg>"""
    
    return svg


def main():
    """Generate badges from TCS report data."""
    # Paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    reports_dir = repo_root / "reports"
    badges_dir = repo_root / "static" / "badges"
    
    # Ensure badges directory exists
    badges_dir.mkdir(parents=True, exist_ok=True)
    
    # Read TCS data
    tcs_file = reports_dir / "tcs.json"
    if not tcs_file.exists():
        print(f"Error: {tcs_file} not found. Run tcs-report-generator.sh first.")
        return
    
    with open(tcs_file, 'r') as f:
        tcs_data = json.load(f)
    
    # Generate overall TCS badge
    overall = tcs_data['overall']
    tcs_badge = create_badge_svg(
        "TCS",
        f"{overall['tcs']}%",
        overall['color']
    )
    
    with open(badges_dir / "tcs-badge.svg", 'w') as f:
        f.write(tcs_badge)
    
    print(f"Generated: tcs-badge.svg ({overall['tcs']}%, {overall['color']})")
    
    # Generate individual trailer badges
    for trailer_name, trailer_data in tcs_data['trailers'].items():
        badge = create_badge_svg(
            trailer_name,
            f"{trailer_data['percentage']}%",
            trailer_data['color']
        )
        
        badge_filename = f"{trailer_name}-badge.svg"
        with open(badges_dir / badge_filename, 'w') as f:
            f.write(badge)
        
        print(f"Generated: {badge_filename} ({trailer_data['percentage']}%, {trailer_data['color']})")
    
    print(f"\nAll badges generated in: {badges_dir}")


if __name__ == "__main__":
    main()