import json
import random
import asyncio
from pymongo import MongoClient
from bs4 import BeautifulSoup
import traceback
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TemplateSelector:
    def __init__(self, db_url="mongodb://localhost:27017/", db_name="layouts_database"):
        logger.info("Initializing TemplateSelector with database: %s", db_name)
        self.client = MongoClient(db_url)
        self.db = self.client[db_name]
        self.template_specs_file='template_specifications.json'
        self.template_specs = self.load_template_specifications()

    def calculate_div_length(self, html_content, div_class):
        try:
            template_soup = BeautifulSoup(html_content, 'html.parser')
            div = template_soup.find(class_=div_class)
            if not div:
                return 0

            text_content = div.get_text(strip=True)
            return len(text_content) / 1.8 if text_content else 0                           ###########changed
            #return len(text_content)*0.8 if text_content else 0
        except Exception as e:
            logger.error("Error calculating div length for %s: %s", div_class, e, exc_info=True)
            return 0
        

    def load_template_specifications(self):
        try:
            with open(self.template_specs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading template specifications: {e}")
            return {}    

    def select_templates(self, num_pages, brand_config):
        try:
            logo_path = brand_config.get("logo")
            include_images = brand_config.get("include_images", True)

            main_layout_collection = (
                "layouts_lit" if logo_path and include_images else
                "layouts_lt" if logo_path else
                "layouts_it" if include_images else
                "layouts_t"
            )

            if main_layout_collection not in self.db.list_collection_names():
                logger.warning("Collection '%s' not found in database.", main_layout_collection)
                return None

            collection = self.db[main_layout_collection]
            layouts = list(collection.find({}, {"_id": 0, "layout": 1, "files": 1}))

            if not layouts:
                logger.warning("No layouts found in collection '%s'.", main_layout_collection)
                return None

            selected_layout = random.choice(layouts)
            html_files = selected_layout.get("files", [])
            if not html_files:
                logger.warning("No files found in the selected layout.")
                return None

            selected_files = html_files[:min(len(html_files), num_pages)]
            result = [
                {
                    "collection": main_layout_collection,
                    "layout": selected_layout["layout"],
                    "filename": file.get("file_name", "default_filename.html"),
                    "title_length": self.calculate_div_length(file.get("content", ""), "title-text"),
                    "content_length": self.calculate_div_length(file.get("content", ""), "body-text"),
                    "content": file.get("content", ""),
                    "path": file.get("file_name", "default_filename.html"),
                    "image_height" : file.get("image_height"),
                    "image_width": file.get("image_width")
                }
                for file in selected_files if file.get("content")
            ]

            if len(result) < num_pages:
                logger.warning("Requested %d pages, but only %d templates are available.", num_pages, len(result))
                return None

            return result
        except Exception as e:
            logger.error("Error in select_templates: %s", e, exc_info=True)
            return None

    async def populate_single_template(
        self,
        page: Dict,
        template_content: str,
        brand_config: Dict,
        index: int
    ) -> Optional[str]:
        try:
            template_soup = await asyncio.to_thread(BeautifulSoup, template_content, 'html.parser')

            if (title_div := template_soup.find(class_='title-text')) and 'title' in page:
                title_div.string = page['title']

            if (body_div := template_soup.find(class_='body-text')) and 'content' in page:
                body_div.string = page['content']

            if (brand_div := template_soup.find(class_='brand-name')) and 'brand_name' in brand_config:
                brand_div.string = brand_config['brand_name']

            if (logo_div := template_soup.find(class_='logo')) and (logo_img := logo_div.find('img')):
                logo_img['src'] = page.get('logo', '')

            if (content_img := template_soup.find(class_='image')) and (img_tag := content_img.find('img')):
                img_tag['src'] = page.get('image', '')

            result = await asyncio.to_thread(str, template_soup)
            return result

        except Exception as e:
            logger.error(f"Error populating page {index + 1}: {str(e)}", exc_info=True)
            return None

    async def populate_templates(
        self,
        carousel_content: Dict,
        template_info: List[Dict],
        brand_config: Dict
    ) -> Optional[List[str]]:
        try:
            pages = (carousel_content if isinstance(carousel_content, list)
                     else carousel_content.get('pages', []))

            template_map = {
                t.get('filename', '').replace('.html', ''): t.get('content', '')
                for t in template_info
                if isinstance(t, dict) and t.get('filename') and t.get('content')
            }

            

            tasks = []
            for i, page in enumerate(pages):
                template_path = page.get('template_path', '')
                template_name = os.path.basename(template_path).replace('.html', '')
                template_content = template_map.get(template_name)

                if not template_content:
                    logger.warning(f"Template '{template_name}' not found for page {i + 1}.")
                    continue

                task = self.populate_single_template(
                    page=page,
                    template_content=template_content,
                    brand_config=brand_config,
                    index=i
                )
                tasks.append(task)

            if not tasks:
                logger.warning("No valid templates to process.")
                return None

            results = await asyncio.gather(*tasks)
            populated_templates = [r for r in results if r is not None]

            if not populated_templates:
                logger.error("No templates were successfully populated.")
                return None

            return populated_templates

        except Exception as e:
            logger.error(f"Error populating templates: {str(e)}", exc_info=True)
            return None
