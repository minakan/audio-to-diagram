import xml.etree.ElementTree as ET


class SVGSanitizer:
    def sanitize(self, svg: str) -> str:
        root = ET.fromstring(svg)
        self._remove_scripts(root)
        self._strip_event_attributes(root)
        if "viewBox" not in root.attrib:
            root.set("viewBox", "0 0 1280 720")
        return ET.tostring(root, encoding="unicode")

    def _remove_scripts(self, root: ET.Element) -> None:
        for parent in root.iter():
            remove_children = []
            for child in list(parent):
                if child.tag.lower().endswith("script"):
                    remove_children.append(child)
            for child in remove_children:
                parent.remove(child)

    def _strip_event_attributes(self, root: ET.Element) -> None:
        for elem in root.iter():
            for attr_name in list(elem.attrib.keys()):
                if attr_name.lower().startswith("on"):
                    del elem.attrib[attr_name]
