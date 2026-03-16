import time
import uuid
from dataclasses import dataclass

from app.schemas.analysis import AnalysisResult
from app.schemas.common import DomainLabel
from app.schemas.diagram_plan import DiagramPlan
from app.schemas.websocket import AudioChunkEvent
from app.services.analysis.diagram_planner_service import DiagramPlannerService
from app.services.analysis.domain_filter_service import DomainFilterService
from app.services.analysis.quality_check_service import QualityCheckService
from app.services.analysis.text_normalizer import TextNormalizer
from app.services.analysis.visualization_decision_service import VisualizationDecisionService
from app.services.generation.svg_generator_service import SVGGeneratorService
from app.services.generation.svg_sanitizer import SVGSanitizer
from app.services.storage.pipeline_logger import PipelineLogger
from app.services.stt.stt_service import STTService


@dataclass
class PipelineResult:
    transcript_text: str
    normalized_text: str
    analysis: AnalysisResult
    diagram_plan: DiagramPlan | None
    svg: str | None
    diagram_id: str | None
    latency_ms: int


class RealtimePipeline:
    def __init__(
        self,
        *,
        stt_service: STTService,
        normalizer: TextNormalizer,
        domain_filter: DomainFilterService,
        viz_decision: VisualizationDecisionService,
        planner: DiagramPlannerService,
        svg_generator: SVGGeneratorService,
        svg_sanitizer: SVGSanitizer,
        quality_checker: QualityCheckService,
        pipeline_logger: PipelineLogger,
        provider_name: str,
    ) -> None:
        self._stt = stt_service
        self._normalizer = normalizer
        self._domain_filter = domain_filter
        self._viz_decision = viz_decision
        self._planner = planner
        self._svg_generator = svg_generator
        self._svg_sanitizer = svg_sanitizer
        self._quality_checker = quality_checker
        self._logger = pipeline_logger
        self._provider_name = provider_name

    async def process_utterance(
        self,
        *,
        session_id: str,
        utterance_id: str,
        chunks: list[AudioChunkEvent],
    ) -> PipelineResult:
        started = time.perf_counter()

        transcript_text = await self._stt.transcribe_final(chunks)
        normalized_text = await self._normalizer.normalize(transcript_text)
        domain_decision = await self._domain_filter.classify(normalized_text)
        viz_decision = await self._viz_decision.decide(normalized_text, domain_decision)

        analysis = AnalysisResult(
            session_id=session_id,
            utterance_id=utterance_id,
            programming_relevance_score=domain_decision.score,
            domain_label=domain_decision.label,
            visualization_needed=viz_decision.needed,
            visualization_reason=viz_decision.reason,
            diagram_type=viz_decision.diagram_type,
        )

        start_ms = 0
        end_ms = sum(chunk.duration_ms for chunk in chunks)
        await self._logger.log_transcript(
            session_id=session_id,
            utterance_id=utterance_id,
            raw_text=transcript_text,
            normalized_text=normalized_text,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        await self._logger.log_analysis(analysis)

        if analysis.domain_label != DomainLabel.PROGRAMMING or not analysis.visualization_needed:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return PipelineResult(
                transcript_text=transcript_text,
                normalized_text=normalized_text,
                analysis=analysis,
                diagram_plan=None,
                svg=None,
                diagram_id=None,
                latency_ms=latency_ms,
            )

        diagram_id = f"diag-{uuid.uuid4().hex[:12]}"
        diagram_plan = await self._planner.plan(normalized_text, analysis)

        svg_output: str | None = None
        try:
            raw_svg = self._svg_generator.generate(diagram_plan)
            sanitized_svg = self._svg_sanitizer.sanitize(raw_svg)
            valid, error_reason = self._quality_checker.validate_svg(sanitized_svg)
            if valid:
                svg_output = sanitized_svg
            else:
                raise ValueError(f"SVG_QUALITY_FAILED:{error_reason}")
        except Exception:
            # Fallback policy: keep diagram_plan even if SVG generation/validation fails.
            svg_output = None

        latency_ms = int((time.perf_counter() - started) * 1000)
        await self._logger.log_diagram(
            diagram_id=diagram_id,
            plan=diagram_plan,
            svg=svg_output,
            provider=self._provider_name,
            latency_ms=latency_ms,
        )

        return PipelineResult(
            transcript_text=transcript_text,
            normalized_text=normalized_text,
            analysis=analysis,
            diagram_plan=diagram_plan,
            svg=svg_output,
            diagram_id=diagram_id,
            latency_ms=latency_ms,
        )
