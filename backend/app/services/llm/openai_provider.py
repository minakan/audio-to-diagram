import json
import logging
import re

from app.core.config import Settings
from app.schemas.analysis import DomainDecision, VisualizationDecision
from app.schemas.common import DomainLabel

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore[assignment]


class OpenAIProvider:
    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key and AsyncOpenAI is not None
            else None
        )

    async def normalize_text(self, text: str) -> str:
        if not text.strip():
            return ""
        if self._client is None:
            return self._heuristic_normalize(text)

        prompt = (
            "次の音声文字起こしを、意味を変えずに簡潔で自然な日本語へ正規化してください。"
            " 句読点を補い、不要なフィラーを除去してください。"
        )
        try:
            response = await self._client.responses.create(
                model=self._settings.openai_model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0,
            )
            normalized = (response.output_text or "").strip()
            return normalized or self._heuristic_normalize(text)
        except Exception as exc:  # pragma: no cover
            logger.warning("normalize_text fallback due to OpenAI error: %s", exc)
            return self._heuristic_normalize(text)

    async def classify_domain(self, text: str) -> DomainDecision:
        if self._client is None:
            return self._heuristic_domain(text)

        schema_hint = {
            "score": 0.0,
            "label": "programming or irrelevant",
            "reason": "string",
        }
        prompt = (
            "発話がプログラミング実習の内容か判定し、JSONのみで返してください。"
            f" 形式例: {json.dumps(schema_hint, ensure_ascii=False)}"
        )
        try:
            response = await self._client.responses.create(
                model=self._settings.openai_model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0,
            )
            payload = json.loads(response.output_text)
            label = DomainLabel.PROGRAMMING if payload.get("label") == "programming" else DomainLabel.IRRELEVANT
            return DomainDecision(
                score=float(payload.get("score", 0.0)),
                label=label,
                reason=str(payload.get("reason", "model_response")),
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("classify_domain fallback due to OpenAI error: %s", exc)
            return self._heuristic_domain(text)

    async def decide_visualization(self, text: str) -> VisualizationDecision:
        if self._client is None:
            return self._heuristic_visualization(text)

        schema_hint = {"needed": True, "reason": "string", "diagram_type": "string or null"}
        prompt = (
            "発話を図示すべきか判定し、JSONのみで返してください。"
            f" 形式例: {json.dumps(schema_hint, ensure_ascii=False)}"
        )
        try:
            response = await self._client.responses.create(
                model=self._settings.openai_model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0,
            )
            payload = json.loads(response.output_text)
            return VisualizationDecision(
                needed=bool(payload.get("needed", False)),
                reason=str(payload.get("reason", "model_response")),
                diagram_type=payload.get("diagram_type"),
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("decide_visualization fallback due to OpenAI error: %s", exc)
            return self._heuristic_visualization(text)

    def _heuristic_normalize(self, text: str) -> str:
        normalized = text
        for filler in ["えー", "あの", "その", "えっと"]:
            normalized = normalized.replace(filler, "")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _heuristic_domain(self, text: str) -> DomainDecision:
        keywords = [
            "変数",
            "関数",
            "配列",
            "ポインタ",
            "アルゴリズム",
            "ループ",
            "再帰",
            "スタック",
            "キュー",
            "木",
            "binary",
            "search",
            "python",
            "java",
            "c言語",
        ]
        lowered = text.lower()
        hit_count = sum(1 for keyword in keywords if keyword.lower() in lowered)
        if hit_count > 0:
            score = min(0.55 + 0.1 * hit_count, 0.99)
            return DomainDecision(
                score=score,
                label=DomainLabel.PROGRAMMING,
                reason="programming_keywords_detected",
            )
        return DomainDecision(score=0.08, label=DomainLabel.IRRELEVANT, reason="no_programming_signal")

    def _heuristic_visualization(self, text: str) -> VisualizationDecision:
        lowered = text.lower()
        positive = [
            "状態",
            "遷移",
            "流れ",
            "比較",
            "探索",
            "木",
            "配列",
            "スタック",
            "キュー",
            "ポインタ",
            "if",
            "for",
            "while",
        ]
        negative = ["提出", "締切", "休憩", "連絡", "課題を出す"]

        if any(word in lowered for word in negative):
            return VisualizationDecision(
                needed=False,
                reason="administrative_or_procedural_content",
                diagram_type=None,
            )
        if any(word in lowered for word in positive):
            diagram_type = "array_state_transition" if "配列" in lowered or "探索" in lowered else "process_flow"
            return VisualizationDecision(
                needed=True,
                reason="contains_structure_or_state_change",
                diagram_type=diagram_type,
            )
        return VisualizationDecision(needed=False, reason="not_visualizable_enough", diagram_type=None)
