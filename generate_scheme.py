import xml.etree.ElementTree as ET
import json
import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
import xml.dom.minidom as minidom
import html
import random
import argparse
import math
import subprocess

"""
run from terminal:
python3 generate_scheme.py --path /path/to/manifest.json --name output.xml
examples:
"""

def main():
    parser = argparse.ArgumentParser(description="Export dbt dependency graph to draw.io format.")
    parser.add_argument('--path', type=str, required=True, help='Path to dbt manifest.json')
    parser.add_argument('--name', type=str, default='raw_graph.xml', help='Raw XML output file name')
    args = parser.parse_args()
    manifest = load_manifest(args.path)
    if manifest:
        graph = build_graph(manifest)
        export_to_drawio(graph, manifest, raw_graph_xml=args.name)
        subprocess.run(["drawio", args.name])

def model_has_tests(model_id, manifest):
    test_nodes = {k: v for k, v in manifest["nodes"].items() if v["resource_type"] == "test"}
    for test_id, test in test_nodes.items():
        if model_id in test.get("depends_on", {}).get("nodes", []):
            return True
    return False

def escape_xml(text):
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text, quote=True)

def load_manifest(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading manifest: {e}")
        return None

def build_graph(manifest):
    graph = nx.DiGraph()
    nodes = manifest.get("nodes", {})
    sources = manifest.get("sources", {})
    for node_id, node in nodes.items():
        if node.get("resource_type") != "model":
            continue
        model_name = node["name"]
        graph.add_node(model_name, type="model", file_path=node.get("original_file_path", ""),
                       description=node.get("description", ""), node_id=node_id,
                       package_name=node.get("package_name", ""),
                       materialized=node.get("config", {}).get("materialized", "unknown"))  # Исправлено
        for dep in node.get("depends_on", {}).get("nodes", []):
            if dep in nodes and nodes[dep]["resource_type"] == "model":
                dep_name = nodes[dep]["name"]
                graph.add_edge(dep_name, model_name, type="ref")
            elif dep in sources:
                source_name = sources[dep]["name"]
                graph.add_node(source_name, type="source", node_id=dep)
                graph.add_edge(source_name, model_name, type="source")
    return graph

def get_layout_positions(graph):
    try:
        A = to_agraph(graph)
        A.graph_attr.update({
            'rankdir': 'LR',
            'nodesep': '4.0',
            'ranksep': '5.0',
            'splines': 'true',
            'overlap': 'false',
            'pack': 'true',
            'pad': '3.0',
            'dpi': '300',
            'fontsize': '11',
            'size': '100,100',
            'ratio': 'compress',
        })
        A.layout(prog='dot')
        positions = {}
        sizes = {}
        for n in A.nodes():
            name = n.get_name()
            pos = n.attr.get("pos")
            if pos:
                x_str, y_str = pos.split(",")
                positions[name] = (float(x_str), float(y_str))
                width = max(150, min(350, len(name) * 10))
                height = 40
                sizes[name] = (width, height)
        return positions, sizes
    except Exception as e:
        print(f"❌ Error in layout calculation: {e}")
        return {}, {}

def get_attachment_sides_with_variation(src_pos, dst_pos):
    dx = dst_pos[0] - src_pos[0]
    dy = dst_pos[1] - src_pos[1]
    delta = 0.15
    def random_offset(base):
        return min(1.0, max(0.0, base + random.uniform(-delta, delta)))
    if abs(dx) > abs(dy):
        if dx > 0:
            exit_x, exit_y = 1.0, random_offset(0.5)
            entry_x, entry_y = 0.0, random_offset(0.5)
        else:
            exit_x, exit_y = 0.0, random_offset(0.5)
            entry_x, entry_y = 1.0, random_offset(0.5)
    else:
        if dy > 0:
            exit_x, exit_y = random_offset(0.5), 1.0
            entry_x, entry_y = random_offset(0.5), 0.0
        else:
            exit_x, exit_y = random_offset(0.5), 0.0
            entry_x, entry_y = random_offset(0.5), 1.0
    return (exit_x, exit_y), (entry_x, entry_y)

def point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    projection_x = x1 + t * dx
    projection_y = y1 + t * dy
    return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)

def get_closest_edge_points(text_x, text_y, text_width, text_height, node_x, node_y, node_width, node_height):
    text_points = [
        (text_x + text_width / 2, text_y, 0.5, 0.0),
        (text_x + text_width / 2, text_y + text_height, 0.5, 1.0),
        (text_x, text_y + text_height / 2, 0.0, 0.5),
        (text_x + text_width, text_y + text_height / 2, 1.0, 0.5)
    ]
    node_points = [
        (node_x + node_width / 2, node_y, 0.5, 0.0),
        (node_x + node_width / 2, node_y + node_height, 0.5, 1.0),
        (node_x, node_y + node_height / 2, 0.0, 0.5),
        (node_x + node_width, node_y + node_height / 2, 1.0, 0.5)
    ]
    min_distance = float('inf')
    best_text_point = None
    best_node_point = None
    for tx, ty, t_exit_x, t_exit_y in text_points:
        for nx, ny, n_entry_x, n_entry_y in node_points:
            distance = math.sqrt((tx - nx) ** 2 + (ty - ny) ** 2)
            if distance < min_distance:
                min_distance = distance
                best_text_point = (t_exit_x, t_exit_y)
                best_node_point = (n_entry_x, n_entry_y)
    return best_text_point, best_node_point

def get_safe_description_position(node_x, node_y, node_width, node_height, positions, sizes, text_width, text_height, current_node, graph):
    buffer = 40
    description = escape_xml(graph.nodes[current_node].get("description", ""))
    description_length = len(description)
    adjusted_text_width = min(250, max(150, 150 + (description_length // 20) * 10))
    adjusted_text_height = min(120, max(50, 50 + (description_length // 25) * 5 + description.count("\n") * 12))
    directions = [
        ('top', node_x, node_y - adjusted_text_height - buffer) if description_length > 50 else ('right', node_x + node_width + buffer, node_y),
        ('bottom', node_x, node_y + node_height + buffer) if description_length > 50 else ('left', node_x - adjusted_text_width - buffer, node_y),
        ('right', node_x + node_width + buffer, node_y),
        ('left', node_x - adjusted_text_width - buffer, node_y),
        ('top', node_x, node_y - adjusted_text_height - buffer),
        ('bottom', node_x, node_y + node_height + buffer)
    ]
    best_score = -1
    best_position = None
    best_direction = None
    best_arrow_params = None
    for direction, text_x, text_y in directions:
        node_overlap = False
        min_node_distance = float('inf')
        for other_node, (other_x, other_y) in positions.items():
            if other_node == current_node:
                continue
            if other_node in sizes:
                other_width, other_height = sizes[other_node]
                if not (text_x + adjusted_text_width + buffer < other_x or
                        text_x > other_x + other_width + buffer or
                        text_y + adjusted_text_height + buffer < other_y or
                        text_y > other_y + other_height + buffer):
                    node_overlap = True
                    break
                node_distance = math.sqrt((text_x + adjusted_text_width / 2 - (other_x + other_width / 2)) ** 2 +
                                          (text_y + adjusted_text_height / 2 - (other_y + other_height / 2)) ** 2)
                min_node_distance = min(min_node_distance, node_distance)
        if node_overlap:
            continue
        min_edge_distance = float('inf')
        text_center_x = text_x + adjusted_text_width / 2
        text_center_y = text_y + adjusted_text_height / 2
        for src, dst in graph.edges():
            if current_node in (src, dst) and src in positions and dst in positions:
                src_x, src_y = positions[src]
                dst_x, dst_y = positions[dst]
                edge_distance = point_to_segment_distance(text_center_x, text_center_y, src_x, src_y, dst_x, dst_y)
                min_edge_distance = min(min_edge_distance, edge_distance)
        score = min(min_node_distance, min_edge_distance * 2 if min_edge_distance < 80 else min_edge_distance)
        (exit_x, exit_y), (entry_x, entry_y) = get_closest_edge_points(
            text_x, text_y, adjusted_text_width, adjusted_text_height,
            node_x, node_y, node_width, node_height
        )
        if score > best_score:
            best_score = score
            best_position = (text_x, text_y)
            best_direction = direction
            best_arrow_params = (exit_x, exit_y, entry_x, entry_y)
    if best_position is None:
        text_x = node_x
        text_y = node_y + node_height + buffer * 1.5
        (exit_x, exit_y), (entry_x, entry_y) = get_closest_edge_points(
            text_x, text_y, adjusted_text_width, adjusted_text_height,
            node_x, node_y, node_width, node_height
        )
        return text_x, text_y, 'bottom', exit_x, exit_y, entry_x, entry_y
    return *best_position, best_direction, *best_arrow_params

def export_to_drawio(graph, manifest, raw_graph_xml="raw_graph.xml"):
    positions, sizes = get_layout_positions(graph)
    if not positions:
        print("⚠️ can't find positions for graph")
        return
    canvas_width = 12000
    canvas_height = 10000
    margin = 500
    all_x = [pos[0] for pos in positions.values()]
    all_y = [pos[1] for pos in positions.values()]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    scale_x = (canvas_width - 2 * margin) / (max_x - min_x) if (max_x - min_x) > 0 else 1
    scale_y = (canvas_height - 2 * margin) / (max_y - min_y) if (max_y - min_y) > 0 else 1
    scale_x *= 1.2
    scale_y *= 1.2
    mxfile = ET.Element("mxfile")
    diagram = ET.SubElement(mxfile, "diagram", id="diagram1", name="Page-1")
    mxgraph = ET.SubElement(diagram, "mxGraphModel", dx="0", dy="0", grid="1", gridSize="10",
                            guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1")
    root = ET.SubElement(mxgraph, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    # Add legend group in the top-left corner
    legend_group_id = "legend_group"
    legend_group = ET.SubElement(root, "mxCell", id=legend_group_id, vertex="1", parent="1")
    legend_x = 50
    legend_y = 50
    legend_width = 200
    legend_height = 360
    ET.SubElement(legend_group, "mxGeometry", x=str(legend_x), y=str(legend_y),
                  width=str(legend_width), height=str(legend_height), **{"as": "geometry"})
    # Legend frame
    legend_frame_style = (
        "shape=rectangle;fillColor=#f5f5f5;opacity=70;strokeColor=#000000;strokeWidth=1;"
        "fontSize=10;whiteSpace=wrap;html=1;"
    )
    legend_frame = ET.SubElement(root, "mxCell", id="legend_frame", value="",
                                 style=legend_frame_style, vertex="1", parent=legend_group_id)
    ET.SubElement(legend_frame, "mxGeometry", x="0", y="0",
                  width=str(legend_width), height=str(legend_height), **{"as": "geometry"})
    # Legend title
    legend_title = ET.SubElement(root, "mxCell", id="legend_title", value="<b>Легенда:</b>",
                                 style="text;fontSize=12;html=1;align=left;", vertex="1", parent=legend_group_id)
    ET.SubElement(legend_title, "mxGeometry", x="10", y="10", width="100", height="20", **{"as": "geometry"})
    # Legend node examples
    node_width = 80
    node_height = 30
    vertical_spacing = 40
    # Source node
    source_style = "shape=step;fillColor=#ffcc00;fontSize=10;whiteSpace=wrap;html=1;align=center;"
    source_node = ET.SubElement(root, "mxCell", id="legend_source", value="Источник",
                                style=source_style, vertex="1", parent=legend_group_id)
    ET.SubElement(source_node, "mxGeometry", x="10", y="40", width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # int_ model
    int_style = "shape=rectangle;rounded=1;fillColor=#99ccff;fontSize=10;whiteSpace=wrap;html=1;align=center;"
    int_node = ET.SubElement(root, "mxCell", id="legend_int", value="int_ модель",
                             style=int_style, vertex="1", parent=legend_group_id)
    ET.SubElement(int_node, "mxGeometry", x="10", y=str(40 + vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # stg_ model
    stg_style = "shape=rectangle;rounded=1;fillColor=#afbab3;fontSize=10;whiteSpace=wrap;html=1;align=center;"
    stg_node = ET.SubElement(root, "mxCell", id="legend_stg", value="stg_ модель",
                             style=stg_style, vertex="1", parent=legend_group_id)
    ET.SubElement(stg_node, "mxGeometry", x="10", y=str(40 + 2 * vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # Regular green node
    green_style = "shape=rectangle;rounded=1;fillColor=#c2f0c2;fontSize=10;whiteSpace=wrap;html=1;align=center;"
    green_node = ET.SubElement(root, "mxCell", id="legend_green", value="Обычная модель",
                               style=green_style, vertex="1", parent=legend_group_id)
    ET.SubElement(green_node, "mxGeometry", x="10", y=str(40 + 3 * vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # Node with no tests
    no_tests_style = "shape=rectangle;rounded=1;fillColor=#c2f0c2;strokeColor=#ff0000;strokeWidth=2;fontSize=10;whiteSpace=wrap;html=1;align=center;"
    no_tests_node = ET.SubElement(root, "mxCell", id="legend_no_tests", value="Модель без тестов",
                                  style=no_tests_style, vertex="1", parent=legend_group_id)
    ET.SubElement(no_tests_node, "mxGeometry", x="10", y=str(40 + 4 * vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # Description node
    desc_style = (
        "shape=rectangle;fillColor=#D3D3D3;opacity=50;strokeColor=#FFFF00;strokeWidth=1.5;"
        "fontSize=10;whiteSpace=wrap;html=1;align=center;"
    )
    desc_node = ET.SubElement(root, "mxCell", id="legend_desc", value="Описание модели",
                              style=desc_style, vertex="1", parent=legend_group_id)
    ET.SubElement(desc_node, "mxGeometry", x="10", y=str(40 + 5 * vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # Package model
    package_style = "shape=rectangle;fillColor=#c2f0c2;fontSize=10;whiteSpace=wrap;html=1;align=center;"
    package_node = ET.SubElement(root, "mxCell", id="legend_package", value="Модель из dbt_packages",
                                style=package_style, vertex="1", parent=legend_group_id)
    ET.SubElement(package_node, "mxGeometry", x="10", y=str(40 + 6 * vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    # Table name for models and sources
    table_name_style = "text;fontSize=10;html=1;align=left;verticalAlign=top;strokeColor=none;"
    table_name_node = ET.SubElement(root, "mxCell", id="legend_table_name", value="(schema.name / db.dataset.table)",
                                    style=table_name_style, vertex="1", parent=legend_group_id)
    ET.SubElement(table_name_node, "mxGeometry", x="10", y=str(40 + 7 * vertical_spacing), width=str(node_width), height=str(node_height), **{"as": "geometry"})
    node_ids = {}
    label_counter = 0  # Counter for unique package label IDs
    for idx, (node, pos) in enumerate(positions.items()):
        node_id = f"id{idx}"
        node_ids[node] = node_id
        attrs = graph.nodes[node]
        n_type = attrs.get("type", "model")
        description = escape_xml(attrs.get("description", ""))
        model_path = escape_xml(attrs.get("file_path", ""))
        package_name = escape_xml(attrs.get("package_name", ""))
        materialization = escape_xml(attrs.get("materialized", "unknown"))
        project_name = manifest.get("metadata", {}).get("project_name", "")
        is_package_model = "dbt_packages" in model_path or (package_name and package_name != project_name)
        if is_package_model:
            print(f"📍 Identified package model: {node}, package: {package_name}, path: {model_path}, materialization: {materialization}")
        label = f"{escape_xml(node)}<br>{model_path}"
        num_lines = label.count("<br>") + 1
        line_height = 8
        base_height = 25
        height = base_height + num_lines * line_height
        width = max(150, min(350, len(node) * 10))
        x = margin + (pos[0] - min_x) * scale_x * 0.85
        y = margin + (pos[1] - min_y) * scale_y * 0.85
        shape = "step" if n_type == "source" else ("rectangle" if is_package_model else "rectangle;rounded=1")
        color = "#c2f0c2"
        if n_type == "source":
            color = "#ffcc00"
        elif node.startswith("stg_") or "/stg_" in model_path:
            color = "#afbab3"
        elif node.startswith("int_") or "/int_" in model_path:
            color = "#99ccff"
        has_tests = model_has_tests(attrs.get("node_id", ""), manifest) if n_type != "source" else True
        border_style = "" if has_tests else "strokeColor=#ff0000;strokeWidth=2;"
        style = f"shape={shape};fillColor={color};strokeColor=#000000;{border_style}fontSize=10;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
        cell = ET.SubElement(root, "mxCell", id=node_id, value=label,
                             style=style, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(width), height=str(height),
                      **{"as": "geometry"})
        # Determine actual table name
        table_name = ""
        if n_type == "model":
            node_id_manifest = attrs.get("node_id", "")
            node_data = manifest["nodes"].get(node_id_manifest, {})
            schema_name = node_data.get("schema", "")
            table_alias = node_data.get("name", node)
            print(f"🔍 Model: {node}, node_id: {node_id_manifest}, schema: {schema_name}, name: {table_alias}")
            table_name = f"{schema_name}.{table_alias}" if schema_name else table_alias
        elif n_type == "source":
            source_id = attrs.get("node_id", "")
            source_data = manifest["sources"].get(source_id, {})
            database_name = source_data.get("database", "")
            dataset_name = source_data.get("schema", "")
            identifier = source_data.get("identifier", node)
            print(f"🔍 Source: {node}, source_id: {source_id}, database: {database_name}, dataset: {dataset_name}, identifier: {identifier}")
            if database_name and dataset_name:
                table_name = f"{database_name}.{dataset_name}.{identifier}"
            elif database_name:
                table_name = f"{database_name}.{identifier}"
            else:
                table_name = identifier
        table_name = escape_xml(table_name)
        # Add table name label in bottom-right corner
        if table_name:
            table_name_label_id = f"table_name_label{idx}"
            table_name_label_style = "text;fontSize=10;html=1;align=right;verticalAlign=bottom;strokeColor=none;"
            table_name_label_value = f'<span style="background-color:#E6E6FA;padding:2px;">{table_name}</span>'
            table_name_label_width = min(150, max(50, len(table_name) * 6))
            table_name_label_height = 15
            table_name_label_x = x + width - table_name_label_width  # Align to right edge
            table_name_label_y = y + height  # Position below node
            table_name_label_cell = ET.SubElement(root, "mxCell", id=table_name_label_id, value=table_name_label_value,
                                                 style=table_name_label_style, vertex="1", parent="1")
            ET.SubElement(table_name_label_cell, "mxGeometry", x=str(table_name_label_x), y=str(table_name_label_y),
                          width=str(table_name_label_width), height=str(table_name_label_height), **{"as": "geometry"})
        # Add package name label for dbt_packages models
        if is_package_model and package_name:
            label_counter += 1
            package_label_id = f"package_label_{label_counter}"
            package_label_style = "text;fontSize=10;html=1;align=left;verticalAlign=top;strokeColor=none;"
            package_label_value = f'<span style="background-color:#EEC231;padding:2px;">{package_name}</span>'
            label_width = min(150, max(50, len(package_name) * 6))
            label_x = x
            label_y = y - 20
            package_label_cell = ET.SubElement(root, "mxCell", id=package_label_id, value=package_label_value,
                                               style=package_label_style, vertex="1", parent="1")
            ET.SubElement(package_label_cell, "mxGeometry", x=str(label_x), y=str(label_y), width=str(label_width), height="15",
                          **{"as": "geometry"})
        # Add materialization label for all models
        if materialization and n_type != "source":
            materialization_label_id = f"materialization_label{idx}"
            materialization_label_style = "text;fontSize=10;html=1;align=left;verticalAlign=top;strokeColor=none;"
            materialization_label_value = f'<span style="background-color:#D3D3D3;padding:2px;">{materialization}</span>'
            materialization_label_width = min(150, max(50, len(materialization) * 6))
            materialization_label_x = x
            materialization_label_y = y + height + 5
            materialization_label_cell = ET.SubElement(root, "mxCell", id=materialization_label_id, value=materialization_label_value,
                                                       style=materialization_label_style, vertex="1", parent="1")
            ET.SubElement(materialization_label_cell, "mxGeometry", x=str(materialization_label_x), y=str(materialization_label_y),
                          width=str(materialization_label_width), height="15", **{"as": "geometry"})
        if description:
            text_id = f"text{idx}"
            description_length = len(description)
            text_lines = description.count("\n") + 1
            text_width = min(250, max(150, 150 + (description_length // 20) * 10))
            text_height = min(120, max(50, 50 + text_lines * 12 + (description_length // 25) * 5))
            text_x, text_y, direction, exit_x, exit_y, entry_x, entry_y = get_safe_description_position(
                x, y, width, height, positions, sizes, text_width, text_height, node, graph)
            text_style = (
                "shape=rectangle;fillColor=#D3D3D3;opacity=50;strokeColor=#FFFF00;strokeWidth=1.5;"
                "fontSize=10;whiteSpace=wrap;html=1;align=left;verticalAlign=top;"
            )
            text_cell = ET.SubElement(root, "mxCell", id=text_id, value=description,
                                      style=text_style, vertex="1", parent="1")
            ET.SubElement(text_cell, "mxGeometry", x=str(text_x), y=str(text_y), width=str(text_width),
                          height=str(text_height), **{"as": "geometry"})
            arrow_id = f"desc_arrow{idx}"
            arrow_style = (
                f"edgeStyle=elbowEdgeStyle;rounded=1;html=1;strokeColor=#FFFF00;endArrow=block;"
                f"exitX={exit_x:.2f};exitY={exit_y:.2f};entryX={entry_x:.2f};entryY={entry_y:.2f};"
                f"jettySize=auto;orthogonal=1"
            )
            arrow_cell = ET.SubElement(root, "mxCell", id=arrow_id, edge="1",
                                       source=text_id, target=node_id, parent="1", style=arrow_style)
            ET.SubElement(arrow_cell, "mxGeometry", relative="1", **{"as": "geometry"})
    edge_id = 1000
    for src, dst in graph.edges():
        if src in node_ids and dst in node_ids:
            edge_type = graph.edges[src, dst].get("type", "ref")
            stroke_color = "#0000FF" if edge_type == "source" else "#000000"
            src_center = positions[src]
            dst_center = positions[dst]
            (exit_x, exit_y), (entry_x, entry_y) = get_attachment_sides_with_variation(src_center, src_center)
            arrow_style = (
                f"edgeStyle=orthogonalEdgeStyle;curved=1;html=1;jettySize=auto;"
                f"entryX={entry_x:.2f};entryY={entry_y:.2f};"
                f"exitX={exit_x:.2f};exitY={exit_y:.2f};"
                f"strokeColor={stroke_color};arrow=block;orthogonal=1;"
            )
            edge = ET.SubElement(root, "mxCell", id=f"e{edge_id}", edge="1",
                             source=node_ids[src], target=node_ids[dst], parent="1", style=arrow_style)
            ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})
            edge_id += 1
    try:
        xml_str = minidom.parseString(ET.tostring(mxgraph, encoding="unicode")).toprettyxml(indent="  ")
        with open(raw_graph_xml, "w", encoding="utf-8") as f:
            f.write(xml_str)
        print(f"📝 Raw graph XML saved to: {raw_graph_xml}")
    except Exception as e:
        print(f"❌ Error saving raw graph XML: {e}")

if __name__ == "__main__":
    main()