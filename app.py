from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse
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

#class FontStyle(str, Enum):
#    ARIAL = "Arial"
#    HELVETICA = "Helvetica"
#    TIMES_NEW_ROMAN = "Times New Roman"
#    GEORGIA = "Georgia"
#    VERDANA = "Verdana"
#
class ColorPaletteType(str, Enum):
    MANUAL = "MANUAL"
    URL = "URL"

class ArticleRequest(BaseModel):
    article_input: str = Field(..., description="URL or text of the article")
    num_pages: int = Field(..., ge=1, le=9, description="Number of pages to generate")
    color_palette_type: ColorPaletteType
    color_palette_input: Union[List[str], str] = Field(..., description="List of colors or URL")
    include_images: bool = Field(True, description="Whether to include images")
    font_style:str = Field(..., description="Font Style")
    brand_name: Optional[str] = Field(None, description="Brand name if logo is provided")

async def create_download_zip(user_id: str) -> BytesIO:
    """
    Creates a ZIP file containing all generated images for a specific user_id.
    Returns a BytesIO object containing the ZIP file.
    
    Args:
        user_id (str): The user ID to search for in image filenames
        
    Returns:
        BytesIO: A buffer containing the ZIP file with all matching images
        
    Raises:
        HTTPException: If no images are found for the given user ID
    """
    zip_buffer = BytesIO()
    
    base_dir = os.path.abspath("final_images")
  
    search_pattern = os.path.join(base_dir, f"*{user_id}*.png")
    
    image_files = glob.glob(search_pattern)

    print(f"Searching for pattern: {search_pattern}")
    print(f"Found files: {image_files}")
    
    if not image_files:
        raise HTTPException(status_code=404, detail=f"No images found for user ID: {user_id}")
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for image_path in image_files:
            
            image_name = os.path.basename(image_path)
            
            try:
                zip_file.write(image_path, image_name)
                print(f"Successfully added {image_name} to ZIP")
            except Exception as e:
                print(f"Error adding {image_name} to ZIP: {str(e)}")
    
    zip_buffer.seek(0)
    return zip_buffer

@app.post("/generate-article/")
async def generate_article(
    request: str = Form(...),
    logo: Optional[UploadFile] = File(None)
):
    user_id = None
    uploaded_logo = None
    try:
       
        user_id = uid_generator.generate_uuid()
        user_dir = os.path.join("final_images", user_id)
        os.makedirs(user_dir, exist_ok=True)
        os.makedirs("images", exist_ok=True)
        os.makedirs("logos", exist_ok=True)

      
        request_data = json.loads(request)
        article_request = ArticleRequest(**request_data)

     
        if logo and not article_request.brand_name:
            raise HTTPException(
                status_code=400, 
                detail="Brand name is required if a logo is uploaded."
            )

        if logo:
            logo_filename = f"{user_id}_logo_{logo.filename}"
            logo_path = os.path.join("logos", logo_filename)
            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)
            uploaded_logo = logo_path

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
        )


        zip_buffer = await create_download_zip(user_id)

    
        async def cleanup_user_files():
            try:
               
                user_dir = os.path.join("final_images", user_id)
                if os.path.exists(user_dir):
                    shutil.rmtree(user_dir)
                
                
                for file in glob.glob(os.path.join("images", f"{user_id}*")):
                    os.remove(file)
               
                for file in glob.glob(os.path.join("logos", f"{user_id}*")):
                    os.remove(file)
            except Exception as e:
                print(f"Error during cleanup: {e}")

       
        asyncio.create_task(cleanup_user_files())

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=images_{user_id}.zip"
            }
        )

    except Exception as e:
        
        if user_id:
            await asyncio.to_thread(cleanup_files, "images", "logos", user_id)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        
        if uploaded_logo and os.path.exists(uploaded_logo):
            os.remove(uploaded_logo)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)





