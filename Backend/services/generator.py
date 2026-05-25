import asyncio
import logging

from sqlmodel import Session, select
from database import engine
from models import Job, Thumbnail
from services.openai_service import generate_thumbnail
from services.imagekit_service import upload_file

logger = logging.getLogger(__name__)

STYLES = {
    "bold_dramatic": (
        "Create a cinematic, high-contrast thumbnail with intense lighting, strong emotions, "
        "dynamic composition, and a sense of tension or urgency. Use deep shadows, punchy highlights, "
        "and bold visual elements that feel larger than life."
    ),
    "clean_minimal": (
        "Create a restrained, modern thumbnail with lots of negative space, a simple composition, "
        "a limited color palette, and a polished editorial look. Prioritize clarity, balance, and "
        "a premium minimal aesthetic."
    ),
    "vibrant_energetic": (
        "Create a bright, colorful thumbnail with saturated hues, lively shapes, motion, and strong visual energy. "
        "Use eye-catching contrast, playful accents, and an upbeat composition that feels fast, exciting, "
        "and highly clickable."
    ),
}

STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]


async def generate_single_thumbnail(thumbnail_id: str, prompt: str, headshot_url: str):
    # DB mark -> generating
    with Session(engine) as session:
        thumb = session.get(Thumbnail, thumbnail_id)
        thumb.status = "generating"
        style_name = (
            thumb.style.name if getattr(thumb, "style", None) else STYLE_ORDER[0]
        )
        session.add(thumb)
        session.commit()
    style_prompt = STYLES[style_name]
    # Ai call
    try:
        image_byte = await generate_thumbnail(prompt, style_prompt, headshot_url)
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            job_id = thumb.job_id

        # upload image

        url = upload_file(
            file_bytes=image_byte,
            file_name=f"{thumbnail_id}.png",
            folder=f"thumbnails/{job_id}/",
            content_type="image/png",
        )
        # DB call save the url + mark -> done
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.image_kit_url = url
            thumb.status = "uploaded"
            session.add(thumb)
            session.commit()
        logger.info(f"Thumbnail {thumbnail_id} generated and uploaded successfully.")
    except Exception as e:
        logger.error(f"Error generating thumbnail {thumbnail_id}: {str(e)}")
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.status = "error"
            thumb.error_message = str(e)[:500]
            session.add(thumb)
            session.commit()


async def process_job(job_id: str):
    # make job as processing
    # find all thumbnails for the job
    # start one workeer per thumbnail
    # wait for all workers to finish
    # mark job as complete/failed
    with Session(engine) as session:
        job = session.get(Job, job_id)
        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url

        session.add(job)
        session.commit()

    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        thumbnail_ids = [t.id for t in thumbnails]

    tasks = [
        generate_single_thumbnail(tid, prompt, headshot_url) for tid in thumbnail_ids
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        all_failed = all(t.status == "error" for t in thumbnails)
        job = session.get(Job, job_id)
        job.status = "failed" if all_failed else "completed"
        session.add(job)
        session.commit()
