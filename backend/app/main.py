from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.websocket.audio_ws import router as websocket_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.services.analysis.diagram_planner_service import DiagramPlannerService
from app.services.analysis.domain_filter_service import DomainFilterService
from app.services.analysis.quality_check_service import QualityCheckService
from app.services.analysis.text_normalizer import TextNormalizer
from app.services.analysis.visualization_decision_service import VisualizationDecisionService
from app.services.generation.svg_generator_service import SVGGeneratorService
from app.services.generation.svg_sanitizer import SVGSanitizer
from app.services.llm.openai_provider import OpenAIProvider
from app.services.orchestration.realtime_pipeline import RealtimePipeline
from app.services.storage.pipeline_logger import PipelineLogger
from app.services.stt.stt_service import STTService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_db()

    settings = get_settings()
    provider = OpenAIProvider(settings)
    stt_service = STTService(settings)
    pipeline_logger = PipelineLogger(SessionLocal)

    app.state.stt_service = stt_service
    app.state.pipeline_logger = pipeline_logger
    app.state.realtime_pipeline = RealtimePipeline(
        stt_service=stt_service,
        normalizer=TextNormalizer(provider),
        domain_filter=DomainFilterService(provider),
        viz_decision=VisualizationDecisionService(provider),
        planner=DiagramPlannerService(),
        svg_generator=SVGGeneratorService(),
        svg_sanitizer=SVGSanitizer(),
        quality_checker=QualityCheckService(),
        pipeline_logger=pipeline_logger,
        provider_name=provider.provider_name,
    )

    yield


app = FastAPI(title="audio-to-diagram-backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
