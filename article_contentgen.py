import os
import json
import random
import base64
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from openai import OpenAI
from template_processor_old import HTMLTemplateProcessor
import logging

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
        # self.auth_token = os.getenv('AUTH_TOKEN')

    def fetch_article_content(url):
        """
        Fetches the main article content from a given URL.
        
        Args:
            url (str): The URL of the web page to extract content from.
    
        Returns:
            str: The extracted article content, or None if extraction fails.
        """
        try:
            # Fetch the webpage
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content
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
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a content generation assistant specializing in creating engaging, well-structured carousel content."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content
        return content


    def generate_carousel_content(self, article_text, template_info):
        """
        Generate carousel content using OpenAI API
        
        Args:
            article_text (str): The article text to base content on
            template_info (list): List of template information
        
        Returns:
            dict: Parsed JSON content for carousel
        """
        # removing 'content'
        sanitized_template_info = [
            {key: value for key, value in template.items() if key != "content"}
            for template in template_info
        ]
    
        prompt = f"""
        Break down the following article into {len(sanitized_template_info)} pages.
        Each page must adhere to the title and body text length constraints provided. And try to generate text a little less than the constraint. Length is the number of characters.
    
        Constraints:
        {json.dumps(sanitized_template_info, indent=2)}
    
        Output Format:
        {{
            "pages": [
                {{
                    "title": "Page title (adhering to constraints) should be all in uppercase",
                    "content": "Page body text (adhering to constraints) generate text half size of given size constraint i.e., number of characters",
                    "template_path": "Path to template",
                    "image": "Path to image",
                    "logo": "Path to logo"
                }}
            ]
        }}
    
        Create engaging and meaningful content that flows naturally across pages while maintaining the article's core message and narrative structure. Each page should work both independently and as part of the sequence.
    
        Article Text:
        {article_text[:4500]}

        Give the json man"""
    
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a content generation assistant specializing in creating engaging, well-structured carousel content."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            print("Generated content:", content)
           
            if content.startswith('```json'):
                content = content.replace('```json\n', '').replace('\n```', '')
           
            json_content = json.loads(content)
        
            if not isinstance(json_content, dict) or 'pages' not in json_content:
                raise ValueError("Invalid JSON structure")
            
           
            for i, page in enumerate(json_content['pages']):
                if i < len(template_info):
                    page['template_path'] = template_info[i]['path']
                    
            return json_content
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating carousel content: {str(e)}")
            return None       

    def generate_image_prompts(self, article_text, carousel_content):
        """
        Generate image prompts for each page based on the article and content
        
        Args:
            article_text (str): The original article text
            carousel_content (dict): The generated carousel content
            
        Returns:
            dict: Updated carousel content with image prompts
        """
        prompt = f"""
        Based on the following article and generated carousel content, create appropriate image prompts for each page.
        Each prompt should be descriptive and relate to the page's content and don't use text in the image.

        Article Text:
        {article_text}

        Carousel Content:
        {json.dumps(carousel_content, indent=2)}

        Generate an image prompt very detailed  for each page in the following format:
        {{
            "pages": [
                {{
                    "page_number": 1,
                    "image_prompt": "a very Detailed description for image generation."
                }}
            ]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at creating detailed image generation prompts."},
                    {"role": "user", "content": prompt}
                ]
            )
            print( f"this is response {response}")
            response_content = response.choices[0].message.content
            
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json\n', '').replace('\n```', '')
            
            image_prompts = json.loads(response_content)

            print(f"this is image prompt{image_prompts}")
            
            # update carousel content with image prompts
            for page_prompt in image_prompts['pages']:
                page_idx = page_prompt['page_number'] - 1
                carousel_content['pages'][page_idx]['image_prompt'] = page_prompt['image_prompt']
            
            return carousel_content
            
        except Exception as e:
            logger.error(f"Error generating image prompts: {e}")
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
                HTMLTemplateProcessor().template_specs
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

