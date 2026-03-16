from pydantic import BaseModel


class SVGResult(BaseModel):
    session_id: str
    utterance_id: str
    diagram_id: str
    svg: str
    prompt_version: str = "svg_v1"
