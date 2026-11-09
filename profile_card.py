"""Render profile details into both SVG themes without accessing the network.

Run `python profile_card.py` after editing profile.json. GitHub stats are
preserved; today.py refreshes them separately using the GitHub API.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
LINE_WIDTH = 59
TEXT_X = 390
STAT_IDS = (
    "repo_data", "star_data", "commit_data",
    "follower_data", "loc_data", "loc_add", "loc_del",
)
THEMES = {
    "dark_mode.svg": {
        "background": "#161b22", "text": "#c9d1d9", "key": "#ffa657",
        "value": "#a5d6ff", "muted": "#616e7f", "add": "#3fb950", "del": "#f85149",
    },
    "light_mode.svg": {
        "background": "#f6f8fa", "text": "#24292f", "key": "#953800",
        "value": "#0a3069", "muted": "#6e7781", "add": "#1a7f37", "del": "#cf222e",
    },
}


def load_profile():
    return json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))


def node(parent, tag, text=None, **attributes):
    element = ET.SubElement(parent, f"{{{SVG_NS}}}{tag}", attributes)
    element.text = text
    return element


def render_cards(age=None):
    profile = load_profile()
    for filename, colors in THEMES.items():
        path = ROOT / filename
        tree = ET.parse(path)
        root = tree.getroot()
        # Preserve the existing artwork and the most recently fetched stats.
        stats = {
            key: root.find(f".//*[@id='{key}']").text
            for key in STAT_IDS
        }
        dots = {}
        for key in STAT_IDS:
            previous = root.find(f".//*[@id='{key}_dots']")
            dots[key] = previous.text if previous is not None else " ... "
        for text in list(root.findall(f"{{{SVG_NS}}}text")):
            if text.get("class") != "ascii":
                root.remove(text)
        root.set("viewBox", "0 0 985 530")
        root.set("font-family", "Menlo,Consolas,Liberation Mono,monospace")
        root.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        root.set("role", "img")
        root.set("aria-labelledby", "profile_title profile_description")
        for tag in ("title", "desc"):
            for old in root.findall(f"{{{SVG_NS}}}{tag}"):
                root.remove(old)
        node(root, "title", f"{profile['username']} — GitHub profile", id="profile_title")
        node(root, "desc", "; ".join(
            f"{label}: {value}"
            for section in profile["sections"] for label, value in section
        ), id="profile_description")
        root.find(f"{{{SVG_NS}}}style").text = (
            f".key {{fill: {colors['key']};}}\n"
            f".value {{fill: {colors['value']};}}\n"
            f".cc {{fill: {colors['muted']};}}\n"
            f".addColor {{fill: {colors['add']};}}\n"
            f".delColor {{fill: {colors['del']};}}\n"
            "text, tspan {white-space: pre;}\n"
        )
        panel = node(root, "text", fill=colors["text"])
        y = 30

        def line():
            nonlocal y
            row = node(panel, "tspan", x=str(TEXT_X), y=str(y))
            y += 20
            return row

        def heading(title):
            node(line(), "tspan", f"{title} ".ljust(LINE_WIDTH, "-"))

        def field(label, value, value_id=None):
            if len(label) + len(value) + 6 > LINE_WIDTH:
                raise ValueError(f"Profile row is too long: {label}. Split it into two rows.")
            row = line()
            node(row, "tspan", ". ", **{"class": "cc"})
            node(row, "tspan", label, **{"class": "key"}).tail = ":"
            padding = LINE_WIDTH - len(label) - len(value) - 5
            attrs = {"class": "cc"}
            if value_id:
                attrs["id"] = f"{value_id}_dots"
            node(row, "tspan", " " + "." * padding + " ", **attrs)
            attrs = {"class": "value"}
            if value_id:
                attrs["id"] = value_id
            node(row, "tspan", value, **attrs)

        heading(profile["username"])
        for index, section in enumerate(profile["sections"]):
            for label, value in section:
                field(label, value)
            if index == 0 and age:
                field("Uptime", age, "age_data")
            y += 20
        heading("- Contact")
        for label, value in profile["contacts"]:
            field(label, value)
        y += 20
        heading("- GitHub Stats")

        # Fixed positions keep the second column aligned as counts grow.
        for left_label, left_id, right_label, right_id in (
            ("Repos", "repo_data", "Stars", "star_data"),
            ("Commits", "commit_data", "Followers", "follower_data"),
        ):
            row = line()
            node(row, "tspan", ". ", **{"class": "cc"})
            node(row, "tspan", left_label, **{"class": "key"}).tail = ":"
            node(row, "tspan", dots[left_id], id=f"{left_id}_dots", **{"class": "cc"})
            node(row, "tspan", stats[left_id], id=left_id, **{"class": "value"})
            node(row, "tspan", "| ", x="720", **{"class": "cc"})
            node(row, "tspan", right_label, **{"class": "key"}).tail = ":"
            node(row, "tspan", dots[right_id], id=f"{right_id}_dots", **{"class": "cc"})
            node(row, "tspan", stats[right_id], id=right_id, **{"class": "value"})
        row = line()
        node(row, "tspan", ". ", **{"class": "cc"})
        node(row, "tspan", "GitHub LOC", **{"class": "key"}).tail = ":"
        node(row, "tspan", dots["loc_data"], id="loc_data_dots", **{"class": "cc"})
        node(row, "tspan", stats["loc_data"], id="loc_data", **{"class": "value"}).tail = " ( "
        node(row, "tspan", "+", **{"class": "addColor"})
        node(row, "tspan", stats["loc_add"], id="loc_add", **{"class": "addColor"}).tail = ", "
        node(row, "tspan", "-", **{"class": "delColor"})
        node(row, "tspan", stats["loc_del"], id="loc_del", **{"class": "delColor"}).tail = " )"
        height = max(530, y)
        root.set("height", str(height))
        root.set("viewBox", f"0 0 985 {height}")
        root.find(f"{{{SVG_NS}}}rect").set("height", str(height))
        tree.write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    render_cards()
