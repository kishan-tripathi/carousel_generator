import random
from pymongo import MongoClient
from bs4 import BeautifulSoup
import traceback
import os



class TemplateSelector:
    def __init__(self, db_url="mongodb://localhost:27017/", db_name="layouts_database"):
        # Initialize MongoDB connection
        self.client = MongoClient(db_url)
        self.db = self.client[db_name]


    def calculate_div_length(self, html_content, div_class):
        try:
            # Parse the HTML content string
            template_soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the div with the specified class
            div = template_soup.find(class_=div_class)
            if not div:
                return 0
            
            # Extract text content and calculate length
            text_content = div.get_text(strip=True)
            if text_content:
                return len(text_content) / 1.2
            
            # Default lengths for specific classes
            default_lengths = {
                'title-text': 60,
                'body-text': 150
            }
            return default_lengths.get(div_class, 100)
        except Exception as e:
            print(f"Error calculating div length for {div_class}: {e}")
            return 0
        

    
    def select_templates(self, num_pages, brand_config):
        """
        Select templates from MongoDB: Randomly selects a layout, then picks the required number of templates (HTML files).
        """
        try:
            # Extract logo and include_images from the brand configuration
            logo_path = brand_config.get("logo")
            include_images = brand_config.get("include_images", True)  # Default to True if not provided
    
            # Determine which collection (main layout) to use
            if logo_path and include_images:
                main_layout_collection = "layouts_lit"
            elif logo_path and not include_images:
                main_layout_collection = "layouts_lt"
            elif not logo_path and include_images:
                main_layout_collection = "layouts_it"
            else:
                main_layout_collection = "layouts_t"
    
            # Verify if the collection exists in the database
            if main_layout_collection not in self.db.list_collection_names():
                print(f"Main layout collection does not exist: {main_layout_collection}")
                return None
    
            # Query MongoDB to get all layouts (subdirectories like 'layout1', 'layout2', etc.) from the selected collection
            collection = self.db[main_layout_collection]
            layouts = list(collection.find({}, {"_id": 0, "layout": 1, "files": 1}))
    
            if not layouts:
                print(f"No layouts found in collection: {main_layout_collection}")
                return None
    
            # Randomly select one layout
            selected_layout = random.choice(layouts)
    
            if "files" not in selected_layout or not selected_layout["files"]:
                print(f"No files found in the selected layout: {selected_layout}")
                return None
    
            html_files = selected_layout["files"]
            selected_files = html_files[:min(len(html_files), num_pages)]
            print(len(selected_files))
    
            # Process selected templates to calculate metadata and return them
            result = []
            for file in selected_files:
                content = file.get("content", None)
                if content is None:
                    print(f"File missing 'content': {file}")
                    continue
    
                title_length = self.calculate_div_length(content, "title-text")
                body_length = self.calculate_div_length(content, "body-text")
                result.append({
                    "collection":main_layout_collection,
                    "layout": selected_layout["layout"],
                    "filename": file.get("file_name", "default_filename.html"),
                    "title_length": title_length,
                    "body_length": body_length,
                    "content": content,
                    "path": file.get("file_name", "default_filename.html")  # Include filename for reference
                })
    
            if len(result) < num_pages:
                print("Not enough templates available to meet the requested number of pages.")
                return None
    
            return result
    
        except Exception as e:
            print(f"Error in select_templates: {e}")
            return None
        
    def populate_templates(self, carousel_content, template_info, brand_config):
        try:
            print("Initial carousel_content type:", type(carousel_content))
            print("Initial template_info type:", type(template_info))
            
            # Extract pages from carousel_content
            pages = carousel_content if isinstance(carousel_content, list) else carousel_content.get('pages', [])
            print(f"Found {len(pages)} pages to process")
    
            # Create a mapping of template filenames to their content
            template_map = {}
            
            # Handle template_info as a list of template objects
            if isinstance(template_info, list):
                for template in template_info:
                    if isinstance(template, dict):
                        filename = template.get('filename', '')
                        content = template.get('content', '')
                        if filename and content:
                            base_name = filename.replace('.html', '')
                            template_map[filename] = content
                            template_map[base_name] = content
                            template_map[f"{base_name}.html"] = content
    
            if not template_map:
                print("Warning: No valid template content found in template_info")
                return None
    
            print(f"Available templates: {list(template_map.keys())}")
    
            populated_templates = []
            for i, page in enumerate(pages):
                try:
                    template_path = page.get('template_path', '')
                    if not template_path:
                        print(f"Warning: No template path found for page {i+1}")
                        continue
    
                    template_name = os.path.basename(template_path)
                    template_content = template_map.get(template_name)
                    
                    if not template_content:
                        print(f"Warning: Template {template_name} not found in template_info")
                        template_name = template_name.replace('.html', '')
                        template_content = template_map.get(template_name)
                        if not template_content:
                            continue
    
                    print(f"Processing template: {template_name}")
                    
                    # Parse and update template
                    template_soup = BeautifulSoup(template_content, 'html.parser')
    
                    # Update title
                    title_div = template_soup.find(class_='title-text')
                    if title_div and 'title' in page:
                        title_div.string = page['title']
    
                    # Update body content
                    body_div = template_soup.find(class_='body-text')
                    if body_div and 'content' in page:
                        body_div.string = page['content'] 
    
                    # Update logo
                    logo_div = template_soup.find(class_='logo')
                    if logo_div:
                        logo_img = logo_div.find('img')
                        if logo_img and 'logo' in page:
                            logo_img['src'] = page['logo']
    
                    # Update content image
                    content_img = template_soup.find(class_='image')
                    if content_img:
                        img_tag = content_img.find('img')
                        if img_tag and 'image' in page:
                            img_tag['src'] = page['image']
    
                    populated_templates.append(str(template_soup))
                    print(f"Successfully processed page {i+1}")
    
                except Exception as e:
                    print(f"Error processing page {i+1}: {e}")
                    traceback.print_exc()
                    continue
    
            if not populated_templates:
                print("Warning: No templates were successfully populated")
                return None
    
            return populated_templates
    
        except Exception as e:
            print(f"Error populating templates: {e}")
            traceback.print_exc()
            return None          






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