import xml.etree.ElementTree as ET


class QualityCheckService:
    def validate_svg(self, svg: str) -> tuple[bool, str | None]:
        if "<script" in svg.lower():
            return False, "script_tag_detected"
        try:
            root = ET.fromstring(svg)
        except ET.ParseError:
            return False, "invalid_xml"

        if root.tag.split("}")[-1] != "svg":
            return False, "root_not_svg"
        if "viewBox" not in root.attrib:
            return False, "missing_viewbox"
        return True, None
