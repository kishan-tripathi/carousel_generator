import os
import json
import requests
import base64
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from template_processor import HTMLTemplateProcessor
import random

load_dotenv()

def image_file_to_base64(image_path):
    """Convert an image file to a Base64 string."""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    return base64.b64encode(image_data).decode('utf-8')

def image_url_to_base64(image_url):
    """Fetch an image from a URL and convert it to Base64."""
    response = requests.get(image_url)
    image_data = response.content
    return base64.b64encode(image_data).decode('utf-8')

class FluxImageGenerator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('FLUX_API_KEY')
        self.api_endpoint = "https://api.segmind.com/v1/flux-schnell"

    def generate_image(self, prompt, height, width, output_path):
        """
        Generate an image using Flux API and save it to the specified path.
        
        Args:
            prompt (str): Image generation prompt
            height (int): Desired image height
            width (int): Desired image width
            output_path (str): Path where the image should be saved
            
        Returns:
            str: Path to the saved image or None if generation fails
        """
        print("start")
        try:
            headers = {
                'x-api-key': self.api_key
            }

            payload = {
                "prompt": prompt+"Don't include any text in the generated image.",
                "steps": 4,
                "seed": random.randint(0, 2**32 - 1),
                "sampler_name": "euler",
                "scheduler": "normal",
                "samples": 1,
                "width": width,
                "height": height,
                "denoise": 1
            }

            # Make request to Flux API
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            print(response)

            # Save the response image
            with open(output_path, 'wb') as f:
                f.write(response.content)

            return output_path
        
        except Exception as e:
            print(f"Error generating image with Flux: {e}")
            return None
        
class ArticleCarouselGenerator:
    def __init__(self, openai_api_key=None, flux_api_key=None, default_pages=5):
        self.client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
        self.default_pages = default_pages
        self.flux_generator = FluxImageGenerator(api_key=flux_api_key)

    def fetch_article_content( url):
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
            
            # Define potential article containers in order of priority
            candidate_selectors = [
                'article',                      # Standard article tag
                'div.article-content',          # Common class for article content
                'div.main-content',             # Common class for main content
                'div.content',                  # General content class
                'body'                          # Fallback to the entire body if all else fails
            ]
            
            for selector in candidate_selectors:
                # Attempt to find content matching the current selector
                candidate = soup.select_one(selector)
                if candidate:
                    text = candidate.get_text(strip=True)
                    if len(text) > 50:  # Ensure content is substantial
                        return text
            
            # If no content is found, raise a custom exception
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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a content generation assistant specializing in creating engaging, well-structured carousel content."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the content from the response
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
    
        prompt = f"""
        Break down the following article into {len(template_info)} pages.
        Each page must adhere to the title and body text length constraints provided. And try to generate text a little less than the constraint. Length is the number of characters.
    
        Constraints:
        {json.dumps(template_info, indent=2)}
    
        Output Format:
        {{
            "pages": [
                {{
                    "title": "Page title (adhering to constraints) should be all in uppercase",
                    "content": "Page body text (optional) (adhering to constraints) generate text half size of given size constraint i.e., number of characters",
                    "template_path": "Path to template",
                    "image": "Path to image",
                    "logo": "Path to logo"
                }}
            ]
        }}
    
        Create engaging and meaningful content that flows naturally across pages while maintaining the article's core message and narrative structure. Each page should work both independently and as part of the sequence.
    
        Article Text:
        {article_text}"""
    
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a content generation assistant specializing in creating engaging, well-structured carousel content."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content
            print("Generated content:", content)
            
            # Remove markdown formatting if present
            if content.startswith('```json'):
                content = content.replace('```json\n', '').replace('\n```', '')
            
            # Parse the JSON content
            json_content = json.loads(content)
            
            # Validate the structure
            if not isinstance(json_content, dict) or 'pages' not in json_content:
                raise ValueError("Invalid JSON structure")
            
            # Match template paths from template_info to the generated content
            for i, page in enumerate(json_content['pages']):
                if i < len(template_info):
                    page['template_path'] = template_info[i]['path']
                    
            return json_content
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            return None
        except Exception as e:
            print(f"Error generating carousel content: {str(e)}")
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
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating detailed image generation prompts."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            image_prompts = json.loads(response.choices[0].message.content)
            
            # Update carousel content with image prompts
            for page_prompt in image_prompts['pages']:
                page_idx = page_prompt['page_number'] - 1
                carousel_content['pages'][page_idx]['image_prompt'] = page_prompt['image_prompt']
            
            return carousel_content
            
        except Exception as e:
            print(f"Error generating image prompts: {e}")
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

    def process_article(self, article_text, template_info, brand_config, include_images):
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
        user_id = brand_config["user_id"]
        # Generate initial carousel content
        carousel_content = self.generate_carousel_content(article_text, template_info)
        if not carousel_content:
            print("Failed to generate carousel content")
            return None
    
        if include_images:
            # Generate image prompts
            carousel_content = self.generate_image_prompts(article_text, carousel_content)
            if not carousel_content:
                print("Failed to generate image prompts")
                return None
    
            # Update content with image dimensions
            carousel_content = self.update_content_with_dimensions(
                carousel_content, 
                HTMLTemplateProcessor().template_specs
            )
    
            # Generate images using Flux
            for page in carousel_content['pages']:
                # Ensure images directory exists
                os.makedirs('images', exist_ok=True)
                
                # Generate and save image using Flux
                image_path = self.flux_generator.generate_image(
                    prompt=page['image_prompt'],
                    height=page['image_height'],
                    width=page['image_width'],
                    #output_path=os.path.join('images', f"page_{carousel_content['pages'].index(page) + 1}.jpg")
                    output_path = os.path.abspath(
                    os.path.join('images', f"{user_id}_page_{carousel_content['pages'].index(page) + 1}.jpg")
                    )
                )
                 
                if image_path:
                    page['image'] = image_path
                else:
                    print(f"Warning: Failed to generate image for page {carousel_content['pages'].index(page) + 1}")
                    # Default/placeholder image here
                    page['image'] = os.path.join('images', 'placeholder.jpg')
    
        # Handle logo from brand_config
        logo_path = brand_config.get('logo', None)
        for page in carousel_content['pages']:
            if logo_path:
                page['logo'] = logo_path
            else:
                print("Warning: No logo path provided in brand_config.")
                page['logo'] = None  # Or set a default logo path
    
        # Save the final content
        try:
            with open("content.json", "w", encoding="utf-8") as json_file:
                json.dump(carousel_content, json_file, indent=4, ensure_ascii=False)
            return carousel_content
        except Exception as e:
            print(f"Error saving JSON file: {e}")
            return None