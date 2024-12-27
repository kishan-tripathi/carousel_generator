import os
import json
import traceback
import random
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from openai import OpenAI
#from flux import FluxImageGenerator  # Import the FluxImageGenerator class

# Load environment variables
load_dotenv()

class HTMLTemplateProcessor:
    def __init__(self, 
                 templates_dir='new_carousel_gen', 
                 logos_dir='logos', 
                 images_dir='images', 
                 output_dir='populated_templates',
                 template_specs_file='template_specifications.json'):
        self.templates_dir = templates_dir
        self.logos_dir = logos_dir
        self.images_dir = images_dir
        self.output_dir = output_dir
        self.template_specs_file = template_specs_file
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load template specifications
        self.template_specs = self.load_template_specifications()

    def load_template_specifications(self):
        try:
            with open(self.template_specs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading template specifications: {e}")
            return {}

    def calculate_div_length(self, template_path, div_class):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_soup = BeautifulSoup(f, 'html.parser')
            
            div = template_soup.find(class_=div_class)
            if not div:
                return 0
            
            text_content = div.get_text(strip=True)
            if text_content:
                return len(text_content)/1.2
            
            default_lengths = {
                'title-text': 60,
                'body-text': 150
            }
            return default_lengths.get(div_class, 100)
        except Exception as e:
            print(f"Error calculating div length for {div_class} in {template_path}: {e}")
            return 0
        
    def update_brand_template(self ,template_path: str, brand_config: dict):
        """
        Overwrite the brand template file with the provided configuration.
        
        Parameters:
        template_path (str): Path to the brand template file
        brand_config (dict): Dictionary containing brand configuration data
        """
        try:
            # Overwrite the file with the new brand configuration
            with open(template_path, 'w') as file:
                json.dump(brand_config, file, indent=4)
            print("Brand template overwritten successfully.")
        except Exception as e:
            print(f"Error overwriting template: {e}")       


    def select_templates(self, num_pages, brand_config):
        """
        Select templates based on brand configuration.
        """
        try:
            # Extract logo and include_images from the brand configuration
            logo_path = brand_config.get('logo')
            include_images = brand_config.get('include_images', True)  # Default to True if not provided
    
            # Determine which main layout directory to use
            if logo_path and include_images:
                main_layout_dir = 'layouts_lit'
            elif logo_path and not include_images:
                main_layout_dir = 'layouts_lt'
            elif not logo_path and include_images:
                main_layout_dir = 'layouts_it'
            else:
                main_layout_dir = 'layouts_t'
    
            # Ensure the main layout directory exists
            if not os.path.isdir(main_layout_dir):
                print(f"Main layout directory does not exist: {main_layout_dir}")
                return None
    
            # Get all subdirectories (layout1 to layout5) within the chosen main layout directory
            subdirs = [
                os.path.join(main_layout_dir, d) 
                for d in os.listdir(main_layout_dir) 
                if os.path.isdir(os.path.join(main_layout_dir, d)) and d.startswith('layout') and d[6:].isdigit() and 1 <= int(d[6:]) <= 5
            ]
    
            if not subdirs:
                print(f"No subdirectories found in main layout directory: {main_layout_dir}")
                return None
    
            # Randomly select one subdirectory
            selected_subdir = random.choice(subdirs)
    
            # Get all HTML templates from the selected subdirectory
            templates = []
            for root, _, files in os.walk(selected_subdir):
                templates.extend([
                    os.path.join(root, f) 
                    for f in files 
                    if f.endswith('.html')
                ])
    
            if not templates:
                print(f"No templates found in subdirectory: {selected_subdir}")
                return None
    
            # Select templates and calculate metadata
            selected_templates = []
            for template in templates[:min(len(templates), num_pages)]:  # Sequential selection
                title_length = self.calculate_div_length(template, 'title-text')
                body_length = self.calculate_div_length(template, 'body-text')
                selected_templates.append({
                    'path': template,
                    'title_length': title_length,
                    'body_length': body_length
                })
                
            if len(selected_templates) < num_pages:
                print("Not enough templates available to meet the requested number of pages.")
                return None
    
            return selected_templates
    
        except Exception as e:
            print(f"Error in select_templates: {e}")
            return None    


    def populate_templates(self, carousel_content, template_info):
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
    
    
### For retrieving the templates from local dir.   
    
    #def populate_templates(self, carousel_content):
    #    try:
    #        
    #        content_data = carousel_content
#
    #        pages = content_data['pages']
    #        populated_templates = []
#
    #        for i, page in enumerate(pages):
    #            # Get the template path from the content
    #            template_path = page['template_path']
    #            
    #            # If the path doesn't exist, try to find the template in the layout directory
    #            if not os.path.exists(template_path):
    #                template_name = os.path.basename(template_path)
    #                layout_dir = os.path.dirname(template_path)
    #                if not os.path.exists(layout_dir):
    #                    # Try to find the template in any layout directory
    #                    for layout in os.listdir(self.templates_dir):
    #                        possible_path = os.path.join(self.templates_dir, layout, template_name)
    #                        if os.path.exists(possible_path):
    #                            template_path = possible_path
    #                            break
#
    #            with open(template_path, 'r', encoding='utf-8') as f:
    #                template_soup = BeautifulSoup(f, 'html.parser')
#
    #            title_div = template_soup.find(class_='title-text')
    #            if title_div:
    #                title_div.string = page['title']
#
    #            body_div = template_soup.find(class_='body-text')
    #            if body_div and 'content' in page:
    #                body_div.string = page['content']
#
#
    #            logo_div = template_soup.find(class_='logo')
    #            if logo_div:
    #                logo_img = logo_div.find('img')
    #                if logo_img:
    #                    if os.path.exists(page['logo']):
    #                        # Update the src attribute of the <img> tag
    #                        logo_img['src'] = page['logo']
    #                    else:
    #                        print(f"Warning: Logo file not found at {page['logo']}")
    #                else:
    #                    print("Warning: <img alt='Logo'> tag not found within .logo class")
    #            else:
    #                print("Warning: .logo class not found")                
    #            
#
    #            content_img = template_soup.find(class_='image')
    #            if content_img:
    #                img_tag = content_img.find('img')
    #                if img_tag:
    #                    img_tag['src'] = page['image']
#
    #            output_path = os.path.join(self.output_dir, f'populated_template_{i + 1}.html')
    #            with open(output_path, 'w', encoding='utf-8') as f:
    #                f.write(str(template_soup))
#
    #            #populated_templates.append(output_path)
    #            populated_templates.append(str(template_soup))
#
    #        return populated_templates
    #    except Exception as e:
    #        print(f"Error populating templates: {e}")
    #        return None


