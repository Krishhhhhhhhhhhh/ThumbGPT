import asyncio
import logging

from sqlmodel import Session,select
from database import engine
from models import Job, Thumbnail
from services.openai_service import generate_thumbnail
from services.imagekit_service import upload_file

logger=logging.getLogger(__name__)

STYLES = {
	"bold_dramatic": (
		"Create a cinematic, high-contrast thumbnail with intense lighting, strong emotions, "
		"dynamic composition, and a sense of tension or urgency. Use deep shadows, punchy highlights, "
		"and bold visual elements that feel larger than life."
	),
	"clean-minimal": (
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

STYLE_ORDER=["bold_dramatic","clean_minimal","vibrant_energetic"]

async def generate_single_thumbnail(thumbnail_id:str,prompt:str,style_prompt:str,headshot_url:str): 
    #DB mark -> generating
    #Ai call

