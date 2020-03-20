import argparse
import construct as ct
from pathlib import Path
import sys
import yaml
import enum

from jktool.layout import *


def build_layout(layout: dict) -> bytes:
    widget_ids_to_idx_map = dict()
    pane_names_to_idx_map = dict()

    layout["panesNames"] = []
    for i, pane in enumerate(layout["panes"]):
        if pane["name"] in pane_names_to_idx_map:
            raise ValueError("Duplicate pane name: " + pane["name"])
        pane_names_to_idx_map[pane["name"]] = i
        layout["panesNames"].append(pane["name"])

    layout["widgets"] = []
    layout["widgetsNames"] = []

    def build_widget_list(widget: dict) -> None:
        if widget["id"] in widget_ids_to_idx_map:
            raise ValueError(f"Duplicate widget ID: {widget['id']}")
        widget_ids_to_idx_map[widget["id"]] = len(layout["widgets"])
        layout["widgets"].append(widget)
        layout["widgetsNames"].append(widget["name"])

        # Fix the type field
        widget["flags"] &= ~0x30
        widget["flags"] |= widget["type"] << 4

        if "numChildWidgets" not in widget:
            widget["numChildWidgets"] = 0

        if widget["type"] == WidgetType.Layout:
            widget["numChildWidgets"] = len(widget["widgets"])
        elif widget["type"] == WidgetType.Pane:
            widget["objectIdx"] = pane_names_to_idx_map[widget["pane"]]
        elif widget["type"] == WidgetType.Group:
            widget["objectIdx"] = len(widget["widgets"])

        for child in widget["widgets"]:
            build_widget_list(child)
        del widget["widgets"]

    build_widget_list(layout["rootWidget"])

    layout["animsNames"] = []
    for anim in layout["anims"]:
        layout["animsNames"].append(anim["name"])
        for entry in anim["entries"]:
            entry["widgetIdx"] = widget_ids_to_idx_map[entry["widget"]]

    return Layout.build(layout)


def build_project(project: dict) -> bytes:
    project["packages"] = [x["name"] for x in project["packages"]]
    project["layouts"] = [x["name"] for x in project["layouts"]]
    return Project.build(project)


def remove_io(v):
    if isinstance(v, ct.core.EnumIntegerString) or isinstance(v, enum.IntEnum):
        return int(v)

    if isinstance(v, dict):
        if "_io" in v:
            del v["_io"]
        d = dict()
        # Put these keys first
        for key in ("name", "id", "widget"):
            if key in v:
                d[key] = v[key]
        d.update({k: remove_io(vv) for k, vv in v.items() if not k.startswith("_")})
        return d
    elif isinstance(v, list):
        return [remove_io(x) for x in v]
    else:
        return v


def dump(data) -> None:
    parsed = remove_io(data)
    yaml.dump(parsed, stream=sys.stdout, Dumper=yaml.CSafeDumper,
              sort_keys=False, default_flow_style=None)


def parse_widget_tree(layout, idx, parent) -> int:
    next_idx = idx + 1
    widget = layout.widgets[idx]
    name = layout.widgetsNames[idx]

    widget["name"] = name
    widget["id"] = f'{widget["name"]}-{widget["widgetIdx"]}'
    del widget["widgetIdx"]
    widget["widgets"] = []
    if parent:
        parent["widgets"].append(widget)

    if widget.type == WidgetType.Layout:
        for _ in range(widget.numChildWidgets):
            next_idx = parse_widget_tree(layout, next_idx, widget)
    elif widget.type == WidgetType.Pane:
        widget["pane"] = layout.panes[widget.objectIdx]["name"]
        del widget["objectIdx"]
    elif widget.type == WidgetType.Group:
        for _ in range(widget.objectIdx):
            next_idx = parse_widget_tree(layout, next_idx, widget)
        del widget["objectIdx"]

    return next_idx


def dump_layout(layout) -> None:
    for pane, name in zip(layout.panes, layout.panesNames):
        pane["name"] = name

    parse_widget_tree(layout, 0, None)
    layout["rootWidget"] = layout.widgets[0]

    for anim, name in zip(layout.anims, layout.animsNames):
        anim["name"] = name
        del anim["numEntries"]
        for entry in anim["entries"]:
            widget = layout["widgets"][entry.widgetIdx]
            entry["widget"] = widget["id"]
            del entry["widgetIdx"]

    del layout["widgets"]
    del layout["widgetsNames"]
    del layout["panesNames"]
    del layout["animsNames"]

    del layout["numWidgets"]
    del layout["numMainWidgets"]
    del layout["numPanes"]
    del layout["numPlayers"]
    del layout["numAnims"]
    del layout["panesOffset"]
    del layout["animsOffset"]
    del layout["namesOffset"]

    dump(layout)


def dump_project(project) -> None:
    project.packages = [{"id": i, "name": x} for i, x in enumerate(project.packages)]
    project.layouts = [{"id": i, "name": x} for i, x in enumerate(project.layouts)]
    dump(project)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--type", help="File type (automatically detected using file extension), e.g. mfl, mfpk", default="")
    parser.add_argument("file", type=Path)

    args = parser.parse_args()
    type = args.type
    path = args.file

    if not type:
        type = path.suffixes[0][1:]

    if path.suffix == ".yml":
        # convert to binary
        data = yaml.load(path.read_text(), Loader=yaml.CSafeLoader)
        if type == "mfl":
            sys.stdout.buffer.write(build_layout(data))
        elif type == "mfpk":
            sys.stdout.buffer.write(Package.build(data))
        elif type == "mfpj":
            sys.stdout.buffer.write(build_project(data))
        else:
            raise ValueError("unknown type: " + type)
    else:
        # convert to text
        data = path.read_bytes()
        if type == "mfl":
            dump_layout(Layout.parse(data))
        elif type == "mfpk":
            dump(Package.parse(data))
        elif type == "mfpj":
            dump_project(Project.parse(data))
        else:
            raise ValueError("unknown type: " + type)


if __name__ == '__main__':
    main()
