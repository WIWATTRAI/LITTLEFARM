"""Build index.html (Three.js 4D viewer for dorm building A) from elements.json + schedule.json.

Usage: python3 build.py [data_dir]   (default: ./data)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data"

elements = json.loads((data / "elements.json").read_text(encoding="utf-8"))
schedule = json.loads((data / "schedule.json").read_text(encoding="utf-8"))


def js(obj):
    # keep "</script>" from closing the inline script
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


html = (HERE / "viewer.html").read_text(encoding="utf-8")
html = html.replace("/*__ELEMENTS__*/null", js(elements)).replace("/*__SCHEDULE__*/null", js(schedule))
(HERE / "index.html").write_text(html, encoding="utf-8")
print(f"index.html: {len(elements['elements'])} elements, {len(schedule['tasks'])} tasks")
