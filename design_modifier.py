import os
import re
import traceback
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict
import asyncio
import json
from dotenv import load_dotenv
from openai import OpenAI
import logging
from utils import LlamaAPIClient

logger = logging.getLogger(__name__)

class HTMLModifier:
    def __init__(self):
        self.executor = ThreadPoolExecutor()
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))         
        self.llamaclient = LlamaAPIClient()
        self.auth_token = os.getenv('AUTH_TOKEN')
        self.api_url = "https://infer.e2enetworks.net/project/p-4333/endpoint/is-3236/v1/chat/completions"

    #def generate_design_prompt(self, brand_config, carousel_content):
    #        """
    #        Generate a design prompt based on the brand configuration and content.
    #    
    #        Args:
    #            brand_config (dict): Dictionary containing branding details, including:
    #                - color_palette (list): List of color hex codes.
    #                - logo (str): Path to the uploaded logo (optional).
    #                - font_style (str): Font style to use.
    #                - include_images (bool): Whether to include images.
    #            carousel_content (str): Carousel content data.
    #    
    #        Returns:
    #            dict: Generated design prompt in JSON format or an empty dict if an error occurs.
    #        """
    #        design_json = None
    #
    #        try:
    #            color_palette = brand_config.get("color_palette", [])
    #            logo = brand_config.get("logo", None)
    #            font_style = brand_config.get("font_style", "Default")
    #            include_images = brand_config.get("include_images", True)
    #    
    #            if not color_palette:
    #                print("No color palette provided. Proceeding with default settings.")
    #                color_palette = [] 
    #    
    #            elif not all(isinstance(color, str) and color.startswith("#") for color in color_palette):
    #                print("Invalid color palette provided.")
    #                return {}
    #    
    #            color_palette_str = ", ".join(color_palette)
#
    #            if include_images:
    #                prompt = f"""
    #                Construct a color mapping in JSON format:
    #                For this content: {carousel_content}
    #                Font style: {font_style}
    #                This is the color palette: {color_palette_str} if this is None or empty then choose colors for each with your instinct according to the content.
    #                Rules for choosing colors:
    #                1. If the body-text color is not clearly visible enough on the content background, make it white if content background is lighter, else make it black if the content background color is darker.
    #                2. If the title-text color is not clearly visible enough on the title-text background, make it white if the title-text background is lighter, else make it black if the title-text background color is darker.
    #                Provide a JSON object with the following structure:
    #                {{
    #                    "title-text": "#hex",
    #                    "title-text-background": "#hex",
    #                    "body-text": "#hex",
    #                    "brand-name": "#hex",
    #                    "container": "#hex",
    #                    "font-style":"Arial"
    #                }}
    #                """
    #            else:
    #                prompt = f"""
    #                Construct a color scheme in JSON format for the following:
    #                Content: {carousel_content}
    #                Font style: {font_style}
    #                Color palette (if provided): {color_palette_str}
    #                Do not include images. Focus on clean and minimalistic design.
    #                STRICT VISIBILITY RULES:
    #                1. Body-text contrast:
    #                   - If content background is dark (luminance < 40%), body-text MUST be white (#FFFFFF).
    #                   - If content background is light (luminance ≥ 60%), body-text MUST be black (#000000).
    #                2. Title-text contrast:
    #                   - If content background is dark, title-text MUST be white (#FFFFFF).
    #                   - If content background is light, title-text MUST be black (#000000).
    #                Provide a JSON object with the following structure:
    #                {{
    #                    "title-text": "#hex",
    #                    "title-text-background": "#hex",
    #                    "body-text": "#hex",
    #                    "brand-name": "#hex",
    #                    "container": "#hex",
    #                    "font-style": "Arial",
    #                    "number":"#hex"
    #                }}
    #                """
    #    
    #            response = self.client.chat.completions.create(
    #                model="gpt-4o-mini",
    #                messages=[
    #                    {"role": "system", "content": "You are a helpful assistant."},
    #                    {"role": "user", "content": prompt}
    #                ]
    #            )
    #    
    #
    #            if response:
    #                design_prompt = response.choices[0].message.content.strip()
    #                print(design_prompt)
    #                
    #                json_match = re.search(r'({.*})', design_prompt, re.DOTALL)
    #                
    #                if json_match:
    #                    json_str = json_match.group(0)  
    #                
    #                    try:
    #                        design_json = json.loads(json_str)
    #                        print("Parsed JSON:", design_json)
    #                    except json.JSONDecodeError:
    #                        print("Error parsing response as JSON.")
    #                else:
    #                    print("No valid json found in the reponse.!!")
    #            else:
    #                print("No valid choices found in the response.")
    #                
    #        except Exception as e:
    #            print(f"An error occurred: {e}")
    #
    #        return design_json if design_json is not None else {}  

    def generate_design_prompt(self, brand_config, carousel_content):
        """
        Generate a design prompt based on the brand configuration and content.
    
        Args:
            brand_config (dict): Dictionary containing branding details, including:
                - color_palette (list): List of color hex codes.
                - logo (str): Path to the uploaded logo (optional).
                - font_style (str): Font style to use.
                - include_images (bool): Whether to include images.
            carousel_content (str): Carousel content data.
    
        Returns:
            dict: Generated design prompt in JSON format or an empty dict if an error occurs.
        """
        design_json = None
        max_retries = 3
        retry_count = 0
    
        try:
            color_palette = brand_config.get("color_palette", [])
            logo = brand_config.get("logo", None)
            font_style = brand_config.get("font_style", "Default")
            include_images = brand_config.get("include_images", True)
    
            if not color_palette:
                print("No color palette provided. Proceeding with default settings.")
                color_palette = [] 
    
            elif not all(isinstance(color, str) and color.startswith("#") for color in color_palette):
                print("Invalid color palette provided.")
                return {}
    
            color_palette_str = ", ".join(color_palette)
    
            if include_images:
                prompt = f"""
                Construct a color mapping in JSON format:
                For this content: {carousel_content}
                Font style: {font_style}
                This is the color palette: {color_palette_str} if this is None or empty then choose colors for each with your instinct according to the content.
                Rules for choosing colors:
                1. If the body-text color is not clearly visible enough on the content background, make it white if content background is lighter, else make it black if the content background color is darker.
                2. If the title-text color is not clearly visible enough on the title-text background, make it white if the title-text background is lighter, else make it black if the title-text background color is darker.
                Provide a JSON object with the following structure:
                {{
                    "title-text": "#hex",
                    "title-text-background": "#hex",
                    "body-text": "#hex",
                    "brand-name": "#hex",
                    "container": "#hex",
                    "font-style":"Arial"
                }}
                """
            else:
                prompt = f"""
                Construct a color scheme in JSON format for the following:
                Content: {carousel_content}
                Font style: {font_style}
                Color palette (if provided): {color_palette_str}
                Do not include images. Focus on clean and minimalistic design.
                STRICT VISIBILITY RULES:
                1. Body-text contrast:
                   - If content background is dark (luminance < 40%), body-text MUST be white (#FFFFFF).
                   - If content background is light (luminance ≥ 60%), body-text MUST be black (#000000).
                2. Title-text contrast:
                   - If content background is dark, title-text MUST be white (#FFFFFF).
                   - If content background is light, title-text MUST be black (#000000).
                Provide a JSON object with the following structure:
                {{
                    "title-text": "#hex",
                    "title-text-background": "#hex",
                    "body-text": "#hex",
                    "brand-name": "#hex",
                    "container": "#hex",
                    "font-style": "Arial",
                    "number":"#hex"
                }}
                """
    
            while retry_count < max_retries:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
    
                if response:
                    design_prompt = response.choices[0].message.content.strip()
                    print(f"Attempt {retry_count + 1} response:", design_prompt)
                    
                    json_match = re.search(r'({.*})', design_prompt, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(0)  
                    
                        try:
                            design_json = json.loads(json_str)
                            print("Successfully parsed JSON:", design_json)
                            break  # Exit the loop if JSON parsing succeeds
                        except json.JSONDecodeError:
                            print(f"JSON decode error on attempt {retry_count + 1}")
                            retry_count += 1
                    else:
                        print(f"No valid JSON found in the response on attempt {retry_count + 1}")
                        retry_count += 1
                else:
                    print(f"No valid choices found in the response on attempt {retry_count + 1}")
                    retry_count += 1
    
                if retry_count == max_retries:
                    print(f"Failed to parse JSON after {max_retries} attempts")
    
        except Exception as e:
            print(f"An error occurred: {e}")
    
        return design_json if design_json is not None else {}    
    
        
    def update_class_styles(self, css_content: str, selector: str, updates: dict, is_body: bool = False) -> str:
        """
    Update the styles for a specific class or tag in the CSS content.
        
        If `is_body` is True, it updates the tag without a preceding dot.
        """
       
        pattern = rf'{selector}\s*{{[^}}]*}}' if is_body else rf'\.{selector}\s*{{[^}}]*}}'
        block = re.search(pattern, css_content, re.DOTALL)
        
        if block:
            block_content = block.group(0)
            new_block = block_content

            for property_name, value in updates.items():
                if property_name == 'background':
                    bg_pattern = r'background(?:-color)?:\s*[^;]+;'
                    new_block = re.sub(bg_pattern, f'background: {value};', new_block)
                elif property_name == 'color':
                    color_pattern = r'color:\s*[^;]+;'
                    new_block = re.sub(color_pattern, f'color: {value};', new_block)
                elif property_name == 'font-family':
                    font_pattern = r'font-family:\s*[^;]+;'
                    new_block = re.sub(font_pattern, f'font-family: {value};', new_block)

            css_content = css_content.replace(block_content, new_block)
        
        return css_content

    def modify_html_design(self, html_content: str, color_mapping: Dict[str, str]) -> Optional[str]:
        """Modify HTML design by applying style updates only for keys present in color_mapping."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
    
            style_tag = soup.find("style")
            if not style_tag:
                print("Style tag not found in HTML content.")
                return None
    
            css_content = style_tag.string
            print(f"Processing color mapping: {color_mapping}")
           
            if 'title-text' in color_mapping or 'title-text-background' in color_mapping:
                css_content = self.update_class_styles(css_content, 'title-text', {
                    'color': color_mapping.get('title-text'),
                    'background': color_mapping.get('title-text-background')
                })
            
            if 'body-text' in color_mapping:
                css_content = self.update_class_styles(css_content, 'body-text', {
                    'color': color_mapping.get('body-text')
                })

            if 'number' in color_mapping:
                css_content = self.update_class_styles(css_content, 'number', {
                    'color': color_mapping.get('number')
                })    
            
            if 'container' in color_mapping:
                css_content = self.update_class_styles(css_content, 'container', {
                    'background': color_mapping.get('container')
                })
                css_content = self.update_class_styles(css_content, 'content', {
                    'background': color_mapping.get('container')
                })

            if 'brand-name' in color_mapping:
                css_content = self.update_class_styles(css_content, 'brand-name', {
                    'color': color_mapping.get('brand-name')
                })
            
            if 'font-style' in color_mapping:
                print(f"Applying font style: {color_mapping['font-style']}")  
                css_content = self.update_class_styles(css_content, 'body', {
                    'font-family': color_mapping['font-style']
                }, is_body=True)
    
            style_tag.string = css_content
            return str(soup)
    
        except Exception as e:
            print(f"Error modifying HTML design: {e}")
            print(f"Color mapping was: {color_mapping}") 
            return None  

async def process_templates(
    populated_templates: List[str], 
    output_dir: str, 
    color_mapping: Dict[str, str]
) -> List[str]:
    """Process multiple HTML templates concurrently."""
    modifier = HTMLModifier()
    logger.info("Started processing templates")
    
    async def process_single_template(idx: int, html_content: str) -> tuple[int, Optional[str]]:
        print(f"Processing template {idx + 1}")
        modified_html = await asyncio.to_thread(modifier.modify_html_design, html_content, color_mapping)
        
        if modified_html:
            filename = f"populated_template_{idx + 1}.html"
            output_path = os.path.join(output_dir, filename)
            await asyncio.to_thread(write_html_file, output_path, modified_html)
            return idx, modified_html
        else:
            print(f"Failed to process template {idx + 1}")
            return idx, None

    def write_html_file(path: str, content: str):
        """Write HTML content to file."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

  
    tasks = [
        process_single_template(idx, html_content)
        for idx, html_content in enumerate(populated_templates)
    ]

    results = await asyncio.gather(*tasks)
    
    modified_files = []
    for idx, content in sorted(results, key=lambda x: x[0]):
        if content:
            modified_files.append(content)
    
    return modified_files