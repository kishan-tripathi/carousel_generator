import os
import json
import random
import base64
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from openai import OpenAI
import re
import traceback
from template_processor import TemplateSelector 
#from template_processor_old import HTMLTemplateProcessor
import logging
from utils import LlamaAPIClient



logger = logging.getLogger(__name__)
load_dotenv()

class FluxImageGeneratorAPI:
    def __init__(self, api_url="https://ead1-2401-4900-8842-395a-69a1-ea1f-354-55b.ngrok-free.app/generate"):
        """
        Initialize the FluxImageGeneratorAPI class.

        Args:
            api_url (str): The base URL of the Flux Flask API.
        """
        self.api_url = api_url

    def generate_image(self, prompt, height, width, output_path, seed=None):
        """
        Generate an image via the Flux Flask API.
        
        Args:
            prompt (str): Image generation prompt.
            height (int): Image height.
            width (int): Image width.
            output_path (str): Path to save the generated image.
            seed (int): Random seed for reproducibility.
        
        Returns:
            str: Path to the generated image or None on failure.
        """
        try:
            payload = {
                "prompt": prompt,
                "height": height,
                "width": width,
                "seed": seed
            }
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            # Decode the image from the base64 response
            image_base64 = response.json().get("response")
            if image_base64:
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(image_base64))
                return output_path
            else:
                print("Error: No image data in API response.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error calling Flux API: {e}")
            return None


class ArticleCarouselGenerator:

    def __init__(self, openai_api_key=None, flux_api_key=None, default_pages=5):
        self.client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
        self.default_pages = default_pages
        self.flux_generator = FluxImageGeneratorAPI()
        self.llamaclient = LlamaAPIClient()
        self.auth_token = os.getenv('AUTH_TOKEN')
        
        self.api_url = os.getenv('API_URL')

    def fetch_article_content(url):
        """
        Fetches the main article content from a given URL.
        
        Args:
            url (str): The URL of the web page to extract content from.
    
        Returns:
            str: The extracted article content, or None if extraction fails.
        """
        try:
           
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            
            candidate_selectors = [
                'article',                      
                'div.article-content',         
                'div.main-content',             
                'div.content',                 
                'body'                         
            ]
            for selector in candidate_selectors:

                candidate = soup.select_one(selector)
                if candidate:
                    text = candidate.get_text(strip=True)
                    if len(text) > 50: 
                        return text
            
            raise ValueError("Article content could not be extracted from the provided URL.")
        
        except requests.RequestException as req_err:
            print(f"Network-related error: {req_err}")
        except Exception as e:
            print(f"Error fetching article: {e}")
        
        return None
    

    def generate_article(self, topic):
        prompt = f"""
        Generate an article on this topic in around 3000 words. Topic:{topic}
        """
        response = self.llamaclient.generate(
        prompt,
        system_prompt="You are a content generation assistant specializing in creating engaging, well-structured carousel content."
        )
        print(response)
    
    
    def generate_carousel_content(self, article_text, template_info):
        """
        Generate carousel content using LLaMA API with strict length constraints
        
        Args:
            article_text (str): The article text to base content on
            template_info (list): List of template information
        
        Returns:
            dict: Parsed JSON content for carousel, or None if parsing fails
        """
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                constraints_details = []
                for i, template in enumerate(template_info, 1):
                    constraints_details.append(
                        f"Page {i}:\n"
                        f"- Title: Write a title under {int(template['title_length'])} characters\n"
                        f"- Content: Write {int(template['content_length'])} characters or less using short, complete sentences"
                    )
                
                constraints_str = "\n".join(constraints_details)
    
                prompt = f"""
                You are tasked with breaking down this article into {len(template_info)} extremely concise pages.
                
                CRITICAL LENGTH RULES:
                {constraints_str}
    
                WRITING GUIDELINES:
                1. Titles: Use length constraint IMPACTFUL words in UPPERCASE
                2. Content: Write in length constraint, complete sentences
                3. Focus on ONE key point per page
                4. Remove unnecessary words and modifiers
                5. Use active voice for brevity
                6. Break complex ideas into simpler statements
                7. Skip transitions and get straight to the point
                8. Count characters carefully before finalizing
    
                Output Format:
                {{
                    "pages": [
                        {{
                            "title": "Title with lenght constraints",
                            "content": "Content with specifed length constraints",
                            "template_path": "Path to template",
                            "image": "Path to image",
                            "logo": "Path to logo"
                        }}
                    ]
                }}
    
                Article Text:
                {article_text[:4500]}
    
                COUNT CHARACTERS CAREFULLY. Respond only with the JSON."""
    
                content = self.llamaclient.generate(
                    prompt,
                    system_prompt="""You are an expert content editor skilled at conveying information in the fewest possible words 
                    while maintaining clarity and completeness. Never exceed character limits. 
                    Respond only with valid JSON."""
                )
                
                content = content.strip()
                if content.startswith('```'):
                    start = content.find('\n', content.find('```')) + 1
                    end = content.rfind('```')
                    content = content[start:end].strip()
                
                content = re.sub(r'^json\n', '', content, flags=re.IGNORECASE)
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                json_content = json.loads(content)
                
                if not isinstance(json_content, dict) or 'pages' not in json_content:
                    raise ValueError("Invalid JSON structure")
                
                
                for i, (page, template) in enumerate(zip(json_content['pages'], template_info)):
                    title_len = len(page['title'])-10
                    content_len = len(page['content'])-50
                    
                    if title_len > template['title_length']:
                        raise ValueError(f"Title length {title_len} exceeds limit {template['title_length']} for page {i+1}")
                    
                    if content_len > template['content_length']:
                        raise ValueError(f"Content length {content_len} exceeds limit {template['content_length']} for page {i+1}")
                    
                    page['template_path'] = template['filename']
                
                return json_content
    
            except json.JSONDecodeError as e:
                logger.warning(f"Retry {current_retry + 1}/{max_retries}: JSON parsing error")
                current_retry += 1
                if current_retry == max_retries:
                    logger.error(f"JSON parsing error after {max_retries} attempts: {str(e)}")
                    return None
    
            except Exception as e:
                logger.warning(f"Retry {current_retry + 1}/{max_retries}: {str(e)}")
                current_retry += 1
                if current_retry == max_retries:
                    logger.error(f"Error generating carousel content after {max_retries} attempts: {str(e)}")
                    return None
                
        return None
   
    def generate_image_prompts(self, article_text, carousel_content):
        """
        Generate image prompts for each page based on the article and content with retry mechanism
        
        Args:
            article_text (str): The original article text
            carousel_content (dict): The generated carousel content
        
        Returns:
            dict: Updated carousel content with image prompts, or None if all retries fail
        """
        MAX_RETRIES = 3
        
        def generate_llm_response():
            """Helper function to generate and clean LLM response"""
            prompt = f"""
            Based on the following article and carousel content, create precise and detailed image prompts.
            Each prompt must describe a clear, generation-ready image that relates to the page's content.
            DO NOT include any text or words in the image descriptions.
            
            Article Text:
            {article_text}
            
            Carousel Content:
            {json.dumps(carousel_content, indent=2)}
          
            number of prompts = {len(carousel_content["pages"])}
            
            
            Requirements for image prompts:
            1. Be highly detailed and specific
            2. Focus on visual elements only - no text
            3. Match the theme and tone of each page
            4. Include style, composition, and lighting details
            5. Be suitable for image generation
            
            Generate prompts in this exact format:
            {{
                "pages": [
                    {{
                        "page_number": 1,
                        "image_prompt": "Detailed visual description for image generation"
                    }}
                ]
            }}
            
            Respond only with the JSON, no additional text or markdown."""
            print(carousel_content)
            
            response = self.llamaclient.generate(
                prompt,
                system_prompt="""You are an expert at creating detailed, generation-ready image prompts.
                Focus on visual elements only, never include text in images.
                Respond only with valid JSON data."""
            )
            
            response = response.strip()
            if response.startswith('```'):
                start = response.find('\n', response.find('```')) + 1
                end = response.rfind('```')
                response = response[start:end].strip()
            
            response = re.sub(r'^json\n', '', response, flags=re.IGNORECASE)
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
                
            return response
    
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Attempting to generate image prompts (attempt {attempt + 1}/{MAX_RETRIES})")
                
                content = generate_llm_response()
                
                try:
                    image_prompts = json.loads(content)
                except json.JSONDecodeError as json_error:
                    logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {str(json_error)}")
                    if attempt == MAX_RETRIES - 1:
                        logger.error("All JSON parsing attempts failed")
                        return None
                    continue
             
                if not isinstance(image_prompts, dict) or 'pages' not in image_prompts:
                    logger.warning(f"Invalid JSON structure on attempt {attempt + 1}")
                    if attempt == MAX_RETRIES - 1:
                        logger.error("All attempts produced invalid JSON structure")
                        return None
                    continue
              
                expected_pages = len(carousel_content['pages'])
                received_pages = len(image_prompts['pages'])
                if received_pages != expected_pages:
                    logger.warning(f"Mismatch in page count: expected {expected_pages}, got {received_pages}")
                    if attempt == MAX_RETRIES - 1:
                        logger.error("Failed to generate correct number of image prompts")
                        return None
                    continue
           
                try:
                    for page_prompt in image_prompts['pages']:
                        page_idx = page_prompt['page_number'] - 1
                        if page_idx < 0 or page_idx >= len(carousel_content['pages']):
                            raise ValueError(f"Invalid page number: {page_prompt['page_number']}")
                        carousel_content['pages'][page_idx]['image_prompt'] = page_prompt['image_prompt']
                    
                    logger.info("Successfully generated and integrated image prompts")
                    return carousel_content
                    
                except (KeyError, IndexError, ValueError) as e:
                    logger.warning(f"Error updating carousel content on attempt {attempt + 1}: {str(e)}")
                    if attempt == MAX_RETRIES - 1:
                        logger.error("Failed to update carousel content with image prompts")
                        return None
                    continue
                    
            except Exception as e:
                logger.warning(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                logger.debug(f"Error details: {traceback.format_exc()}")
                if attempt == MAX_RETRIES - 1:
                    logger.error("All attempts failed with unexpected errors")
                    return None
                continue
        
        return None
        
    def update_content_with_dimensions(self, carousel_content, template_specs):
        """
        Update carousel content with image dimensions from template specifications
        """
        for page in carousel_content['pages']:
            template_path = page['template_path']
            template_name = os.path.basename(template_path)
            
            if template_name in template_specs:
                specs = template_specs[template_name]
                page['image_height'] = specs['image_height']
                page['image_width'] = specs['image_width']
        
        return carousel_content

    def process_article(self, article_text, template_info, brand_config,include_images):
        """
        Process an article and generate carousel content.
        
        If include_images is False, skip image generation and related tasks.
        Use the logo path from brand_config.
        
        Parameters:
        - article_text (str): Text of the article to process
        - template_info (dict): Template-specific information
        - include_images (bool): Flag to include image generation
        - brand_config (dict): Dictionary containing brand configurations
        """

        user_id = brand_config['user_id']
        # Generate initial carousel content
        carousel_content = self.generate_carousel_content(article_text, template_info)
        if not carousel_content:
            print("Failed to generate carousel content")
            return None
    
        if include_images:
           
            carousel_content = self.generate_image_prompts(article_text, carousel_content)
            
            if not carousel_content:
                logger.error("Failed to generate image prompts")
                return None
            logger.info("Image prompts generated sucessfully!!")
    
           
            carousel_content = self.update_content_with_dimensions(
                carousel_content, 
                TemplateSelector().template_specs
                #HTMLTemplateProcessor().template_specs
            )
            logger.info("carousel content updated sucessfully with dims!!")
            
    
           
            logger.info("Started Image generation")
            for page in carousel_content['pages']:
               
                os.makedirs('images', exist_ok=True)
                image_path = self.flux_generator.generate_image(
                    prompt=page['image_prompt'],
                    height=page['image_height'],
                    width=page['image_width'],
                    #output_path=os.path.join('images', f"page_{carousel_content['pages'].index(page) + 1}.jpg")
                    output_path = os.path.abspath(
                    os.path.join('images', f"{user_id}_page_{carousel_content['pages'].index(page) + 1}.jpg")
                    )
                )
                print(image_path)
                
                if image_path:
                    page['image'] = image_path
                else:
                    logger.error(f"Warning: Failed to generate image for page {carousel_content['pages'].index(page) + 1}")
                    page['image'] = os.path.join('images', 'placeholder.jpg')

            logger.info("Images generated sucessfully")        
    
        # Handle logo from brand_config
        logo_path = brand_config.get('logo', None)
        for page in carousel_content['pages']:
            if logo_path:
                page['logo'] = logo_path
            else:
                logger.error("Warning: No logo path provided in brand_config.")
                page['logo'] = None  # Or set a default logo path
    
        # Save the final content
        try:
            with open("content.json", "w", encoding="utf-8") as json_file:
                json.dump(carousel_content, json_file, indent=4, ensure_ascii=False)
            return carousel_content
        except Exception as e:
            logger.error(f"Error saving JSON file: {e}")
            return None

