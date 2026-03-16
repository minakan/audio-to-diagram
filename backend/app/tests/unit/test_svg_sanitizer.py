from app.services.generation.svg_sanitizer import SVGSanitizer


def test_svg_sanitizer_removes_script_and_event_handler() -> None:
    sanitizer = SVGSanitizer()
    raw = """<svg xmlns=\"http://www.w3.org/2000/svg\" onclick=\"alert(1)\"><script>alert(1)</script><rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" /></svg>"""
    sanitized = sanitizer.sanitize(raw)

    assert "<script" not in sanitized.lower()
    assert "onclick" not in sanitized.lower()
    assert "viewBox" in sanitized
