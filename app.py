from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, StreamingResponse
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl
import shutil
import os
from pathlib import Path
import glob
import json
import asyncio
import zipfile
from io import BytesIO
from main import main as main_module
from utils import ColorPaletteInput, cleanup_files, UserIDGenerator

app = FastAPI()
uid_generator = UserIDGenerator()

class FontStyle(str, Enum):
    ARIAL = "Arial"
    HELVETICA = "Helvetica"
    TIMES_NEW_ROMAN = "Times New Roman"
    GEORGIA = "Georgia"
    VERDANA = "Verdana"

class ColorPaletteType(str, Enum):
    MANUAL = "MANUAL"
    URL = "URL"

class ArticleRequest(BaseModel):
    article_input: str = Field(..., description="URL or text of the article")
    num_pages: int = Field(..., ge=1, le=6, description="Number of pages to generate")
    color_palette_type: ColorPaletteType
    color_palette_input: Union[List[str], HttpUrl] = Field(..., description="List of colors or URL")
    include_images: bool = Field(True, description="Whether to include images")
    font_style: FontStyle

@app.post("/generate-article/")
async def generate_article(
    request: str = Form(...),
    logo: Optional[UploadFile] = File(None)
):
    user_id = None
    uploaded_logo = None
    try:
        # Generate unique user ID and create necessary directories
        user_id = uid_generator.generate_uuid()
        user_dir = os.path.join("final_images", user_id)
        os.makedirs(user_dir, exist_ok=True)
        os.makedirs("images", exist_ok=True)
        os.makedirs("logos", exist_ok=True)

        # Parse request data
        request_data = json.loads(request)
        article_request = ArticleRequest(**request_data)

        # Handle logo upload if provided
        if logo:
            logo_filename = f"{user_id}_logo_{logo.filename}"
            logo_path = os.path.join("logos", logo_filename)
            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)
            uploaded_logo = logo_path

        # Process the main module in a non-blocking way
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
        )

        # Return success response
        return {
            "status": "success",
            "user_id": user_id,
            "message": "Images generated successfully"
        }

    except Exception as e:
        # Clean up files in case of error
        if user_id:
            await asyncio.to_thread(cleanup_files, "images", "logos", user_id)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up uploaded logo
        if uploaded_logo and os.path.exists(uploaded_logo):
            os.remove(uploaded_logo)

@app.get("/download/{user_id}")
async def download_images(user_id: str):
    try:
        # Create a ZIP file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all images with matching user_id to the ZIP
            for image in glob.glob(os.path.join("final_images", f"{user_id}*.png")):
                image_name = os.path.basename(image)
                zip_file.write(image, image_name)
        
        # Reset buffer position
        zip_buffer.seek(0)
        
        # Clean up files immediately after adding them to ZIP
        async def cleanup_user_files():
            try:
                # Clean up images in final_images directory
                for file in glob.glob(os.path.join("final_images", f"{user_id}*.png")):
                    os.remove(file)
                
                # Clean up images in images directory
                for file in glob.glob(os.path.join("images", f"{user_id}*")):
                    os.remove(file)
                
                # Clean up logos
                for file in glob.glob(os.path.join("logos", f"{user_id}*")):
                    os.remove(file)
            except Exception as e:
                print(f"Error during cleanup: {e}")
        
        # Schedule cleanup
        asyncio.create_task(cleanup_user_files())
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=images_{user_id}.zip"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)


