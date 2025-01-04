#import random
#import asyncio
#from pymongo import MongoClient
#from bs4 import BeautifulSoup
#import traceback
#import os
#import logging
#from typing import List, Dict, Optional
#
#
#logger = logging.getLogger(__name__)
#
#class TemplateSelector:
#    def __init__(self, db_url="mongodb://localhost:27017/", db_name="layouts_database"):
#        logger.info("Initializing TemplateSelector with database: %s", db_name)
#        self.client = MongoClient(db_url)
#        self.db = self.client[db_name]
#
#    def calculate_div_length(self, html_content, div_class):
#        try:
#            template_soup = BeautifulSoup(html_content, 'html.parser')
#            div = template_soup.find(class_=div_class)
#            if not div:
#                return 0
#
#            text_content = div.get_text(strip=True)
#            return len(text_content) / 1.2 if text_content else 0
#        except Exception as e:
#            logger.error("Error calculating div length for %s: %s", div_class, e, exc_info=True)
#            return 0
#
#    def select_templates(self, num_pages, brand_config):
#        try:
#            logo_path = brand_config.get("logo")
#            include_images = brand_config.get("include_images", True)
#
#            main_layout_collection = (
#                "layouts_lit" if logo_path and include_images else
#                "layouts_lt" if logo_path else
#                "layouts_it" if include_images else
#                "layouts_t"
#            )
#
#            if main_layout_collection not in self.db.list_collection_names():
#                logger.warning("Collection '%s' not found in database.", main_layout_collection)
#                return None
#
#            collection = self.db[main_layout_collection]
#            layouts = list(collection.find({}, {"_id": 0, "layout": 1, "files": 1}))
#
#            if not layouts:
#                logger.warning("No layouts found in collection '%s'.", main_layout_collection)
#                return None
#
#            selected_layout = random.choice(layouts)
#            html_files = selected_layout.get("files", [])
#            if not html_files:
#                logger.warning("No files found in the selected layout.")
#                return None
#
#            selected_files = html_files[:min(len(html_files), num_pages)]
#            result = [
#                {
#                    "collection": main_layout_collection,
#                    "layout": selected_layout["layout"],
#                    "filename": file.get("file_name", "default_filename.html"),
#                    "title_length": self.calculate_div_length(file.get("content", ""), "title-text"),
#                    "body_length": self.calculate_div_length(file.get("content", ""), "body-text"),
#                    "content": file.get("content", ""),
#                    "path": file.get("file_name", "default_filename.html")
#                }
#                for file in selected_files if file.get("content")
#            ]
#
#            if len(result) < num_pages:
#                logger.warning("Requested %d pages, but only %d templates are available.", num_pages, len(result))
#                return None
#
#            return result
#        except Exception as e:
#            logger.error("Error in select_templates: %s", e, exc_info=True)
#            return None
#        
#          
#
#    def populate_templates(self, carousel_content, template_info, brand_config):
#        try:
#            pages = carousel_content if isinstance(carousel_content, list) else carousel_content.get('pages', [])
#            template_map = {
#                t.get('filename', '').replace('.html', ''): t.get('content', '')
#                for t in template_info if isinstance(t, dict) and t.get('filename') and t.get('content')
#            }
#
#            populated_templates = []
#            for i, page in enumerate(pages):
#                try:
#                    template_path = page.get('template_path', '')
#                    template_name = os.path.basename(template_path).replace('.html', '')
#                    template_content = template_map.get(template_name)
#
#                    if not template_content:
#                        logger.warning("Template '%s' not found for page %d.", template_name, i + 1)
#                        continue
#
#                    template_soup = BeautifulSoup(template_content, 'html.parser')
#                    if (title_div := template_soup.find(class_='title-text')) and 'title' in page:
#                        title_div.string = page['title']
#                    if (body_div := template_soup.find(class_='body-text')) and 'content' in page:
#                        body_div.string = page['content']
#                    if (brand_div := template_soup.find(class_='brand-name')) and 'brand_name' in brand_config:
#                        brand_div.string = brand_config['brand_name']
#                    if (logo_div := template_soup.find(class_='logo')) and (logo_img := logo_div.find('img')):
#                        logo_img['src'] = page.get('logo', '')
#                    if (content_img := template_soup.find(class_='image')) and (img_tag := content_img.find('img')):
#                        img_tag['src'] = page.get('image', '')
#
#                    populated_templates.append(str(template_soup))
#                except Exception as e:
#                    logger.error("Error populating page %d: %s", i + 1, e, exc_info=True)
#
#            if not populated_templates:
#                logger.warning("No templates were successfully populated.")
#                return None
#
#            return populated_templates
#        except Exception as e:
#            logger.error("Error populating templates: %s", e, exc_info=True)
#            return None
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

    def calculate_div_length(self, html_content, div_class):
        try:
            template_soup = BeautifulSoup(html_content, 'html.parser')
            div = template_soup.find(class_=div_class)
            if not div:
                return 0

            text_content = div.get_text(strip=True)
            return len(text_content) / 1.2 if text_content else 0
        except Exception as e:
            logger.error("Error calculating div length for %s: %s", div_class, e, exc_info=True)
            return 0

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
                    "path": file.get("file_name", "default_filename.html")
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
                logger.warning("No templates were successfully populated.")
                return None

            return populated_templates

        except Exception as e:
            logger.error(f"Error populating templates: {str(e)}", exc_info=True)
            return None



#import random
#from pymongo import MongoClient
#from bs4 import BeautifulSoup
#import traceback
#import os
#import logging
#
#logger = logging.getLogger(__name__)
#
#
#
#
#class TemplateSelector:
#    def __init__(self, db_url="mongodb://localhost:27017/", db_name="layouts_database"):
#        
#        self.client = MongoClient(db_url)
#        self.db = self.client[db_name]
#
#
#    def calculate_div_length(self, html_content, div_class):
#        try:
#            template_soup = BeautifulSoup(html_content, 'html.parser')
#            
#            div = template_soup.find(class_=div_class)
#            if not div:
#                return 0
#            
#            text_content = div.get_text(strip=True)
#            if text_content:
#                return len(text_content) / 1.2
#            
#            default_lengths = {
#                'title-text': 60,
#                'body-text': 150
#            }
#            return default_lengths.get(div_class, 100)
#        except Exception as e:
#            print(f"Error calculating div length for {div_class}: {e}")
#            return 0
#        
#
#    
#    def select_templates(self, num_pages, brand_config):
#        """
#        Select templates from MongoDB: Randomly selects a layout, then picks the required number of templates (HTML files).
#        """
#        try:
#            
#            logo_path = brand_config.get("logo")
#            include_images = brand_config.get("include_images", True)
#    
#            if logo_path and include_images:
#                main_layout_collection = "layouts_lit"
#            elif logo_path and not include_images:
#                main_layout_collection = "layouts_lt"
#            elif not logo_path and include_images:
#                main_layout_collection = "layouts_it"
#            else:
#                main_layout_collection = "layouts_t"
#    
#            if main_layout_collection not in self.db.list_collection_names():
#                print(f"Main layout collection does not exist: {main_layout_collection}")
#                return None
#    
#            collection = self.db[main_layout_collection]
#            layouts = list(collection.find({}, {"_id": 0, "layout": 1, "files": 1}))
#    
#            if not layouts:
#                print(f"No layouts found in collection: {main_layout_collection}")
#                return None
#    
#            selected_layout = random.choice(layouts)
#    
#            if "files" not in selected_layout or not selected_layout["files"]:
#                print(f"No files found in the selected layout: {selected_layout}")
#                return None
#    
#            html_files = selected_layout["files"]
#            selected_files = html_files[:min(len(html_files), num_pages)]
#            print(len(selected_files))
#    
#            result = []
#            for file in selected_files:
#                content = file.get("content", None)
#                if content is None:
#                    print(f"File missing 'content': {file}")
#                    continue
#    
#                title_length = self.calculate_div_length(content, "title-text")
#                body_length = self.calculate_div_length(content, "body-text")
#                result.append({
#                    "collection":main_layout_collection,
#                    "layout": selected_layout["layout"],
#                    "filename": file.get("file_name", "default_filename.html"),
#                    "title_length": title_length,
#                    "body_length": body_length,
#                    "content": content,
#                    "path": file.get("file_name", "default_filename.html")
#                })
#    
#            if len(result) < num_pages:
#                print("Not enough templates available to meet the requested number of pages.")
#                return None
#    
#            return result
#    
#        except Exception as e:
#            print(f"Error in select_templates: {e}")
#            return None
#        
#    def populate_templates(self, carousel_content, template_info, brand_config):
#        try:
#            print("Initial carousel_content type:", type(carousel_content))
#            print("Initial template_info type:", type(template_info))
#            
#            pages = carousel_content if isinstance(carousel_content, list) else carousel_content.get('pages', [])
#            print(f"Found {len(pages)} pages to process")
#
#            template_map = {}
#            if isinstance(template_info, list):
#                for template in template_info:
#                    if isinstance(template, dict):
#                        filename = template.get('filename', '')
#                        content = template.get('content', '')
#                        if filename and content:
#                            base_name = filename.replace('.html', '')
#                            template_map[filename] = content
#                            template_map[base_name] = content
#                            template_map[f"{base_name}.html"] = content
#    
#            if not template_map:
#                print("Warning: No valid template content found in template_info")
#                return None
#    
#            print(f"Available templates: {list(template_map.keys())}")
#    
#            populated_templates = []
#            for i, page in enumerate(pages):
#                try:
#                    template_path = page.get('template_path', '')
#                    if not template_path:
#                        print(f"Warning: No template path found for page {i+1}")
#                        continue
#    
#                    template_name = os.path.basename(template_path)
#                    template_content = template_map.get(template_name)
#                    
#                    if not template_content:
#                        print(f"Warning: Template {template_name} not found in template_info")
#                        template_name = template_name.replace('.html', '')
#                        template_content = template_map.get(template_name)
#                        if not template_content:
#                            continue
#    
#                    print(f"Processing template: {template_name}")
#                    
#                    template_soup = BeautifulSoup(template_content, 'html.parser')
#    
#                    title_div = template_soup.find(class_='title-text')
#                    if title_div and 'title' in page:
#                        title_div.string = page['title']
#    
#                    body_div = template_soup.find(class_='body-text')
#                    if body_div and 'content' in page:
#                        body_div.string = page['content'] 
#
#                    brand_name_div = template_soup.find(class_='brand-name')
#                    if brand_name_div:
#                        brand_name = brand_config['brand_name']
#                        brand_name_div.string = brand_name
#                    else:
#                        print("Brand-name div not found, continuing without updating.")                        
#                    
#                    logo_div = template_soup.find(class_='logo')
#                    if logo_div:
#                        logo_img = logo_div.find('img')
#                        if logo_img and 'logo' in page:
#                            logo_img['src'] = page['logo']
#    
#                    content_img = template_soup.find(class_='image')
#                    if content_img:
#                        img_tag = content_img.find('img')
#                        if img_tag and 'image' in page:
#                            img_tag['src'] = page['image']
#    
#                    populated_templates.append(str(template_soup))
#                    print(f"Successfully processed page {i+1}")
#    
#                except Exception as e:
#                    print(f"Error processing page {i+1}: {e}")
#                    traceback.print_exc()
#                    continue
#    
#            if not populated_templates:
#                print("Warning: No templates were successfully populated")
#                return None
#    
#            return populated_templates
#    
#        except Exception as e:
#            print(f"Error populating templates: {e}")
#            traceback.print_exc()
#            return None          
#
#






























    #print(selected_templates)           

    #def select_templates(self, num_pages, brand_config):
    #    """
    #    Select templates from MongoDB based on brand configuration.
    #    """
    #    try:
    #        # Extract logo and include_images from the brand configuration
    #        logo_path = brand_config.get("logo")
    #        include_images = brand_config.get("include_images", True)  # Default to True if not provided
#
    #        # Determine which collection (main layout) to use
    #        if logo_path and include_images:
    #            main_layout_collection = "layouts_lit"
    #        elif logo_path and not include_images:
    #            main_layout_collection = "layouts_lt"
    #        elif not logo_path and include_images:
    #            main_layout_collection = "layouts_it"
    #        else:
    #            main_layout_collection = "layouts_t"
#
    #        # Verify if the collection exists in the database
    #        if main_layout_collection not in self.db.list_collection_names():
    #            print(f"Main layout collection does not exist: {main_layout_collection}")
    #            return None
#
    #        # Query MongoDB to get all templates from the selected collection
    #        collection = self.db[main_layout_collection]
    #        templates = list(collection.find({}, {"_id": 0, "layout": 1, "filename": 1, "content": 1}))
#
    #        if not templates:
    #            print(f"No templates found in collection: {main_layout_collection}")
    #            return None
#
    #        # Randomly select templates
    #        selected_templates = random.sample(templates, min(len(templates), num_pages))
#
    #        # Calculate metadata for selected templates
    #        result = []
    #        for template in selected_templates:
    #            title_length = self.calculate_div_length(template["content"], "title-text")
    #            body_length = self.calculate_div_length(template["content"], "body-text")
    #            result.append({
    #                "layout": template["layout"],
    #                "filename": template["filename"],
    #                "title_length": title_length,
    #                "body_length": body_length,
    #                "content": template["content"],  # Include HTML content for reference
    #            })
#
    #        if len(result) < num_pages:
    #            print("Not enough templates available to meet the requested number of pages.")
    #            return None
#
    #        return result
#
    #    except Exception as e:
    #        print(f"Error in select_templates: {e}")
    #        return None
#