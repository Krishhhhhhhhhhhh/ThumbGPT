import os
import logging
from fastapi import APIRouter, Depends,HTTPException,UploadFile,File
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from sqlmodel import Session,select

from database import  get_session
from models import Job, Thumbnail
from services.generator import process_job,STYLE_ORDER
from services.imagekit import upload_file,get_variants

logger=logging.getLogger(__name__)

router=APIRouter(prefix="/api")

#request response schemas

class CreateJobRequest(BaseModel): 
    prompt:str
    num_thumbnails:int=1
    headshot_url:str

class CreateJobResponse(BaseModel): 
    job_id:str

class ThumbnailResponse(BaseModel):
    id:int 
    style_name:str
    status:str
    image_kit_url:str|None=None
    error_message:str|None=None
    variants:dict|None=None
    
@router.post("/upload-headshot")
async def upload_headshot(file: UploadFile = File(...)): 
    contents = await file.read()
    url=upload_file(
        file_bytes=contents,
        file_name=file.filename,
        folder="/headshots",
        content_type=file.content_type or "image/png",
    )
    
    return {"url":url}