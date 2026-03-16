from html import escape

from app.schemas.diagram_plan import DiagramPlan


class SVGGeneratorService:
    def generate(self, diagram_plan: DiagramPlan) -> str:
        width = 1280
        height = 720
        node_width = 220
        node_height = 90
        h_gap = 90
        y = 220
        start_x = 80

        positions: dict[str, tuple[int, int]] = {}
        node_fragments: list[str] = []

        for idx, node in enumerate(diagram_plan.nodes):
            x = start_x + idx * (node_width + h_gap)
            positions[node.id] = (x, y)
            stroke = "#d64545" if node.visual.emphasis == "high" else "#1f2937"
            fill = "#fff5f5" if node.visual.emphasis == "high" else "#f8fafc"
            node_fragments.append(
                "\n".join(
                    [
                        f'<rect x="{x}" y="{y}" width="{node_width}" height="{node_height}" rx="10" '
                        f'fill="{fill}" stroke="{stroke}" stroke-width="2" />',
                        f'<text x="{x + 12}" y="{y + 30}" font-size="20" font-family="sans-serif" fill="#111827">{escape(node.label)}</text>',
                        f'<text x="{x + 12}" y="{y + 56}" font-size="15" font-family="sans-serif" fill="#374151">{escape(node.description[:36])}</text>',
                    ]
                )
            )

        edge_fragments: list[str] = []
        for edge in diagram_plan.edges:
            from_pos = positions.get(edge.from_node)
            to_pos = positions.get(edge.to_node)
            if from_pos is None or to_pos is None:
                continue

            x1 = from_pos[0] + node_width
            y1 = from_pos[1] + node_height // 2
            x2 = to_pos[0]
            y2 = to_pos[1] + node_height // 2
            dash = "6 4" if edge.visual.style == "dashed" else ""
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            label_x = (x1 + x2) // 2
            label_y = y1 - 10
            edge_fragments.append(
                "\n".join(
                    [
                        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0f172a" stroke-width="2" marker-end="url(#arrow)"{dash_attr} />',
                        f'<text x="{label_x}" y="{label_y}" font-size="14" font-family="sans-serif" fill="#334155">{escape(edge.label or edge.relation)}</text>',
                    ]
                )
            )

        annotation_fragments = []
        ann_y = 420
        for ann in diagram_plan.annotations[:3]:
            annotation_fragments.append(
                f'<text x="80" y="{ann_y}" font-size="16" font-family="sans-serif" fill="#065f46">- {escape(ann.text)}</text>'
            )
            ann_y += 28

        return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{escape(diagram_plan.topic)}\">\n  <defs>\n    <marker id=\"arrow\" markerWidth=\"10\" markerHeight=\"10\" refX=\"8\" refY=\"3\" orient=\"auto\" markerUnits=\"strokeWidth\">\n      <path d=\"M0,0 L0,6 L9,3 z\" fill=\"#0f172a\" />\n    </marker>\n  </defs>\n  <rect x=\"0\" y=\"0\" width=\"{width}\" height=\"{height}\" fill=\"#ffffff\" />\n  <text x=\"80\" y=\"90\" font-size=\"34\" font-family=\"sans-serif\" fill=\"#0f172a\">{escape(diagram_plan.topic)}</text>\n  <text x=\"80\" y=\"130\" font-size=\"18\" font-family=\"sans-serif\" fill=\"#334155\">{escape(diagram_plan.summary)}</text>\n  {'\n  '.join(edge_fragments)}\n  {'\n  '.join(node_fragments)}\n  {'\n  '.join(annotation_fragments)}\n</svg>"""
