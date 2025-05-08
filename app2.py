from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field
import shutil
import time
from pathlib import Path
import glob
import os
import json
import asyncio
import base64
from main import main as main_module
from utils import cleanup_files, UserIDGenerator
from extract_colors import ColorPaletteInput

app = FastAPI()
uid_generator = UserIDGenerator()

class ColorPaletteType(str, Enum):
    MANUAL = "MANUAL"
    URL = "URL"

class ArticleRequest(BaseModel):
    article_input: str = Field(..., description="URL or text of the article")
    num_pages: int = Field(..., ge=1, le=9, description="Number of pages to generate")
    color_palette_type: ColorPaletteType
    color_palette_input: Union[List[str], str] = Field(..., description="List of colors or URL")
    include_images: bool = Field(True, description="Whether to include images")
    font_style: str = Field(..., description="Font Style")
    brand_name: Optional[str] = Field(None, description="Brand name if logo is provided")

def encode_images_to_base64(user_id: str, timestamp: str) -> List[str]:
    base_dir = os.path.abspath("final_images")
    user_dir = os.path.join(base_dir, user_id, f"generation_{timestamp}")

    if not os.path.exists(user_dir):
        raise HTTPException(status_code=404, detail=f"No directory found for user ID: {user_id} and timestamp: {timestamp}")

    image_files = glob.glob(os.path.join(user_dir, "*.png"))

    if not image_files:
        raise HTTPException(status_code=404, detail="No images found.")

    encoded_images = []
    for image_path in image_files:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            encoded_images.append(encoded)
    return encoded_images

@app.post("/generate-article/")
async def generate_article(
    request: str = Form(...),
    logo: Optional[UploadFile] = File(None)
):
    print(f"request is {request}")
    user_id = None
    uploaded_logo = None
    try:
        user_id = uid_generator.generate_uuid()
        timestamp = int(time.time() * 1000)
        user_dir = os.path.join("final_images", user_id, f"generation_{timestamp}")
        os.makedirs(user_dir, exist_ok=True)
        os.makedirs("images", exist_ok=True)
        os.makedirs("logos", exist_ok=True)

        request_data = json.loads(request)
        article_request = ArticleRequest(**request_data)
        # print("request data ", request_data)
        print("article request ", article_request)

        print(f"logo and brand_name{logo}{article_request.brand_name}")

        if logo and not article_request.brand_name:
            raise HTTPException(
                status_code=400, 
                detail="Brand name is required if a logo is uploaded."
            )
    ##### changing error handling
        if logo:
            logo_filename = f"{user_id}{timestamp}_logo_{logo.filename}"
            logo_path = os.path.join("logos", logo_filename)
            print("Logo path is ", logo_path)
            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)
            uploaded_logo = logo_path
            print(f"logo path {logo_path}")

        # print(f"logo path{logo_path}") 
        else:
            print("No logo provided.")   

        color_palette_type = (
            ColorPaletteInput.MANUAL
            if article_request.color_palette_type == ColorPaletteType.MANUAL
            else ColorPaletteInput.URL
        )

        await asyncio.to_thread(
            main_module,
            article_input=article_request.article_input,
            num_pages=article_request.num_pages,
            color_palette_type=color_palette_type,
            color_palette_input=article_request.color_palette_input,
            uploaded_logo=uploaded_logo,
            include_images=article_request.include_images,
            font_style=article_request.font_style,
            user_id=user_id,
            brand_name=article_request.brand_name,
            time_stamp=timestamp
        )

        encoded_images = encode_images_to_base64(user_id, str(timestamp))

        # Cleanup async
        async def cleanup_user_files(user_id: str, timestamp: int):
            try:
                user_dir = os.path.join("final_images", user_id, f"generation_{timestamp}")
                if os.path.exists(user_dir):
                    shutil.rmtree(user_dir)
                images_dir = os.path.join("images", user_id, f"generation_{timestamp}")
                if os.path.exists(images_dir):
                    shutil.rmtree(images_dir)
                #for file in glob.glob(os.path.join("logos", f"{user_id}{timestamp}*")):
                #    os.remove(file)
            except Exception as e:
                print(f"Error during cleanup: {e}")  

        asyncio.create_task(cleanup_user_files(user_id, timestamp))

        return JSONResponse(content={"images": encoded_images})

    except Exception as e:
        if user_id:
            await asyncio.to_thread(cleanup_files, "images", "logos", user_id)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if uploaded_logo and os.path.exists(uploaded_logo):
            os.remove(uploaded_logo)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000)
