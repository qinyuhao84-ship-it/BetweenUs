from app.services.pipeline import ProcessingPipeline
from app.workers.celery_app import celery_app


@celery_app.task(name="betweenus.pipeline.process")
def process_session_task(session_id: str) -> str:
    ProcessingPipeline.run_sync(session_id)
    return session_id
