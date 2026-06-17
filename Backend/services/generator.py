import asyncio
import logging

from sqlmodel import Session, select
from database import engine
from models import Job, Thumbnail
from services.openai_service import generate_thumbnail
from services.imagekit_service import upload_file

logger = logging.getLogger(__name__)

STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]


async def generate_single_thumbnail(thumbnail_id: str, prompt: str, headshot_url: str):
    # Mark as generating
    with Session(engine) as session:
        thumb = session.get(Thumbnail, thumbnail_id)
        thumb.status = "generating"
        style_name = thumb.style_name
        job_id = thumb.job_id          # ← grab job_id here, avoids extra DB call later
        session.add(thumb)
        session.commit()

    logger.info(f"[job={job_id}] Generating thumbnail {thumbnail_id} (style={style_name})")

    try:
        # Generate image via Ideogram
        image_bytes = await generate_thumbnail(
            prompt=prompt,
            style_name=style_name,
            headshot_url=headshot_url,
        )

        # Upload to ImageKit
        url = upload_file(
            file_bytes=image_bytes,         
            file_name=f"{thumbnail_id}.png",
            folder=f"thumbnails/{job_id}/",
            content_type="image/png",
        )

        # Save URL and mark as uploaded
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.image_kit_url = url
            thumb.status = "uploaded"
            session.add(thumb)
            session.commit()

        logger.info(f"[job={job_id}] Thumbnail {thumbnail_id} uploaded successfully.")

    except Exception as e:
        logger.error(f"[job={job_id}] Thumbnail {thumbnail_id} failed: {str(e)}")
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.status = "error"
            thumb.error_message = str(e)[:500]
            session.add(thumb)
            session.commit()


async def process_job(job_id: str):
    # Mark job as processing
    with Session(engine) as session:
        job = session.get(Job, job_id)
        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.add(job)
        session.commit()

    logger.info(f"[job={job_id}] Processing started.")

    # Load all thumbnail IDs for this job
    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        thumbnail_ids = [t.id for t in thumbnails]

    # Run all three style variants concurrently
    tasks = [
        generate_single_thumbnail(tid, prompt, headshot_url)
        for tid in thumbnail_ids
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Determine final job status
    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()

        total = len(thumbnails)
        failed = sum(1 for t in thumbnails if t.status == "error")
        uploaded = sum(1 for t in thumbnails if t.status == "uploaded")

        if failed == total:
            final_status = "failed"
        elif failed > 0:
            final_status = "partial_failure"   # some succeeded, some didn't
        else:
            final_status = "completed"

        job = session.get(Job, job_id)
        job.status = final_status
        session.add(job)
        session.commit()

    logger.info(
        f"[job={job_id}] Done. status={final_status} "
        f"uploaded={uploaded}/{total} failed={failed}/{total}"
    )