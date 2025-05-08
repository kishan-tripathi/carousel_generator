import os
import json
import random
import time
import base64
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from openai import OpenAI
import fal_client
#from template_processor_old import HTMLTemplateProcessor
import logging

logger = logging.getLogger(__name__)
load_dotenv()

# class FluxImageGeneratorAPI:
#     def __init__(self, api_url="https://ead1-2401-4900-8842-395a-69a1-ea1f-354-55b.ngrok-free.app/generate"):
#         """
#         Initialize the FluxImageGeneratorAPI class.

#         Args:
#             api_url (str): The base URL of the Flux Flask API.
#         """
#         self.api_url = api_url

#     def generate_image(self, prompt, height, width, output_path, seed=None):
#         """
#         Generate an image via the Flux Flask API.
        
#         Args:
#             prompt (str): Image generation prompt.
#             height (int): Image height.
#             width (int): Image width.
#             output_path (str): Path to save the generated image.
#             seed (int): Random seed for reproducibility.
        
#         Returns:
#             str: Path to the generated image or None on failure.
#         """
#         try:
#             payload = {
#                 "prompt": prompt,
#                 "height": height,
#                 "width": width,
#                 "seed": seed
#             }
#             response = requests.post(self.api_url, json=payload)
#             response.raise_for_status()
            
#             image_base64 = response.json().get("response")
#             if image_base64:
#                 with open(output_path, "wb") as f:
#                     f.write(base64.b64decode(image_base64))
#                 return output_path
#             else:
#                 logger.error("Error: No image data in API response.")
#                 return None
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error calling Flux API: {e}")
#             return None


class FluxImageGeneratorAPI:
    def __init__(self, api_key=None):
        """
        Initialize the FluxImageGeneratorAPI class.

        Args:
            api_key (str, optional): The FAL API key. If not provided, it will try to use the FAL_KEY environment variable.
        """
        if api_key:
            os.environ["FAL_KEY"] = api_key
        # Verify that FAL_KEY is available in environment
        if "FAL_KEY" not in os.environ:
            print("Warning: FAL_KEY environment variable not set. Please set it or provide an API key.")

    def generate_image(self, prompt, height, width, output_path, seed=None):
        """
        Generate an image via the fal-client API.
        
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
            # Prepare arguments for the fal-ai/flux/dev model
            arguments = {
                "prompt": prompt,
                "image_size": {
                    "width": width,
                    "height": height
                },
                "num_images": 1,
                "enable_safety_checker": True,
            }
            
            # Add seed if provided
            if seed is not None:
                arguments["seed"] = seed
                
            # Call the API and wait for the result
            result = fal_client.subscribe(
                "fal-ai/flux/dev",
                arguments=arguments,
                with_logs=True
            )
            
            # Save the image to the specified output path
            if result and "images" in result and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]
                
                # If the image URL is empty but we have a base64 content (sync_mode=True case)
                if not image_url and "content" in result["images"][0]:
                    image_base64 = result["images"][0]["content"]
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(image_base64))
                    return output_path
                
                # Otherwise, download from URL
                elif image_url:
                    import requests
                    image_response = requests.get(image_url)
                    image_response.raise_for_status()
                    
                    with open(output_path, "wb") as f:
                        f.write(image_response.content)
                    return output_path
                
            print("Error: No image data in API response.")
            return None
            
        except Exception as e:
            print(f"Error generating image with Flux API: {e}")
            return None
            
    def generate_image_stream(self, prompt, height, width, callback=None, seed=None):
        """
        Stream image generation results via the fal-client API.
        
        Args:
            prompt (str): Image generation prompt.
            height (int): Image height.
            width (int): Image width.
            callback (function): Callback function to process streaming events.
            seed (int): Random seed for reproducibility.
        
        Returns:
            Generator yielding stream events.
        """
        try:
            # Prepare arguments for the fal-ai/flux/dev model
            arguments = {
                "prompt": prompt,
                "image_size": {
                    "width": width,
                    "height": height
                },
                "num_images": 1
            }
            
            # Add seed if provided
            if seed is not None:
                arguments["seed"] = seed
                
            # Start streaming
            stream = fal_client.stream(
                "fal-ai/flux/dev",
                arguments=arguments
            )
            
            # Process streaming events
            for event in stream:
                if callback:
                    callback(event)
                yield event
                
        except Exception as e:
            print(f"Error streaming image with Flux API: {e}")
            yield {"error": str(e)}


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
            logger.error(f"Network-related error: {req_err}")
        except Exception as e:
            logger.error(f"Error fetching article: {e}")
        
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
            Generate carousel content using OpenAI API with retry logic for errors
            """
            constraints_details = []
            for i, template in enumerate(template_info, 1):
                constraints_details.append(
                    f"Page {i}:\n"
                    f"- Title: Write a title under {int(template['title_length'])} characters\n"
                    f"- Content: Write {int(template['content_length'])} characters or less using short, complete sentences"
                )
    
            constraints_str = "\n".join(constraints_details)
    
            prompt = f"""
            You are tasked with breaking down this article into {len(template_info)} well-developed pages.
    
            CRITICAL LENGTH RULES:
            {constraints_str}
    
            WRITING GUIDELINES:
            1. Titles: Create IMPACTFUL UPPERCASE titles using EXACTLY the maximum allowed characters
            2. Content: Write FULL-LENGTH content that uses 90-100% of the character limit
            3. Content must be detailed and comprehensive, using complete sentences
            4. Each page should contain:
               - A primary message or concept
               - Supporting details or examples
               - Clear connection to the overall narrative
            5. Maintain natural flow and readability
            6. Use professional, engaging language
            7. Each content section MUST use at least 90% of its maximum character limit
            8. NO short, fragmentary content allowed
    
            Output Format:
            {{
                "pages": [
                    {{
                        "title": "UPPERCASE TITLE (USING FULL CHARACTER LIMIT)",
                        "content": "Detailed, comprehensive content that uses 90-100% of the character limit. Must contain complete thoughts and proper context. No abbreviated or truncated content allowed.",
                        "template_path": "Path to template",
                        "image": "Path to image",
                        "logo": "Path to logo"
                    }}
                ]
            }}
    
            Article Text:
            {article_text[:4500]}
            Respond only with the JSON.
            """
    
            retries = 3
            for attempt in range(retries):
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
    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Attempt {attempt + 1}: JSON parsing error: {str(e)}")
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1}: Error generating carousel content: {str(e)}")
    
                time.sleep(2)
    
            logger.error("Failed to generate valid carousel content after multiple retries")
            return None       
        

    def generate_image_prompts(self, article_text, carousel_content):
        """
        Generate image prompts for each page based on the article and content with retry mechanism
        
        Args:
            article_text (str): The original article text
            carousel_content (dict): The generated carousel content
            
        Returns:
            dict: Updated carousel content with image prompts or None if all retries fail
        """
        max_retries = 3
        retry_count = 0
        
        prompt = f"""
        Based on the following article and generated carousel content, create appropriate image prompts for each page.
        Each prompt should be descriptive and relate to the page's content and don't use text in the image.
    
        Article Text:
        {article_text}
    
        Carousel Content:
        {json.dumps(carousel_content, indent=2)}
    
        Generate an image prompt very detailed  for each page in the following format And no comments in the JSON:
        {{
            "pages": [
                {{
                    "page_number": 1,
                    "image_prompt": "a very Detailed description for image generation."
                }}
            ]
        }}
        """
    
        while retry_count < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating detailed image generation prompts."},
                        {"role": "user", "content": prompt}
                    ]
                )
                logger.info(f"Attempt {retry_count + 1} response: {response}")
                
                response_content = response.choices[0].message.content
                
                if response_content.startswith('```json'):
                    response_content = response_content.replace('```json\n', '').replace('\n```', '')
                
                try:
                    image_prompts = json.loads(response_content)
                    logger.info(f"Successfully parsed image prompts on attempt {retry_count + 1}: {image_prompts}")
                    if 'pages' in image_prompts and isinstance(image_prompts['pages'], list):
                        for page_prompt in image_prompts['pages']:
                            page_idx = page_prompt['page_number'] - 1
                            carousel_content['pages'][page_idx]['image_prompt'] = page_prompt['image_prompt']
                        
                        return carousel_content
                    else:
                        logger.error(f"Invalid response structure on attempt {retry_count + 1}")
                        retry_count += 1
                        
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON decode error on attempt {retry_count + 1}: {json_error}")
                    retry_count += 1
                    
            except Exception as e:
                logger.error(f"Error on attempt {retry_count + 1}: {e}")
                retry_count += 1
            if retry_count < max_retries:
                time.sleep(1)
        
        logger.error(f"Failed to generate image prompts after {max_retries} attempts")
        return None

    #def generate_image_prompts(self, article_text, carousel_content):
    #    """
    #    Generate image prompts for each page based on the article and content
    #    
    #    Args:
    #        article_text (str): The original article text
    #        carousel_content (dict): The generated carousel content
    #        
    #    Returns:
    #        dict: Updated carousel content with image prompts
    #    """
    #    prompt = f"""
    #    Based on the following article and generated carousel content, create appropriate image prompts for each page.
    #    Each prompt should be descriptive and relate to the page's content and don't use text in the image.
#
    #    Article Text:
    #    {article_text}
#
    #    Carousel Content:
    #    {json.dumps(carousel_content, indent=2)}
#
    #    Generate an image prompt very detailed  for each page in the following format:
    #    {{
    #        "pages": [
    #            {{
    #                "page_number": 1,
    #                "image_prompt": "a very Detailed description for image generation."
    #            }}
    #        ]
    #    }}
    #    """
#
    #    try:
    #        response = self.client.chat.completions.create(
    #            model="gpt-4o-mini",
    #            messages=[
    #                {"role": "system", "content": "You are an expert at creating detailed image generation prompts."},
    #                {"role": "user", "content": prompt}
    #            ]
    #        )
    #        print( f"this is response {response}")
    #        response_content = response.choices[0].message.content
    #        
    #        if response_content.startswith('```json'):
    #            response_content = response_content.replace('```json\n', '').replace('\n```', '')
    #        
    #        image_prompts = json.loads(response_content)
#
    #        print(f"this is image prompt{image_prompts}")
    #        
    #        # update carousel content with image prompts
    #        for page_prompt in image_prompts['pages']:
    #            page_idx = page_prompt['page_number'] - 1
    #            carousel_content['pages'][page_idx]['image_prompt'] = page_prompt['image_prompt']
    #        
    #        return carousel_content
    #        
    #    except Exception as e:
    #        logger.error(f"Error generating image prompts: {e}")
    #        return None

    #def update_content_with_dimensions(self, carousel_content, template_specs):
    #    """
    #    Update carousel content with image dimensions from template specifications
    #    """
    #    for page in carousel_content['pages']:
    #        template_path = page['template_path']
    #        template_name = os.path.basename(template_path)
    #        
    #        if template_name in template_specs:
    #            specs = template_specs[template_name]
    #            page['image_height'] = specs['image_height']
    #            page['image_width'] = specs['image_width']
    #    
    #    return carousel_content
    
    def update_content_with_dimensions(self, carousel_content, template_info):
        """
        Update carousel content with image dimensions from template specifications
        """
        template_map = {item['filename']: item for item in template_info}
        for page in carousel_content['pages']:
            template_path = page.get('template_path', '')
            template_name = os.path.basename(template_path)
            if template_name in template_map:
                specs = template_map[template_name]
                page['image_height'] = specs.get('image_height')
                page['image_width'] = specs.get('image_width')
            else:
                page['image_height'] = None
                page['image_width'] = None
        
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
    
        user_id = brand_config['user_id']
        timestamp = brand_config['time_stamp']
        generation_folder = os.path.join("images", user_id, f"generation_{timestamp}")
    
        os.makedirs(generation_folder, exist_ok=True)
    
        carousel_content = self.generate_carousel_content(article_text, template_info)
        if not carousel_content:
            print("Failed to generate carousel content")
            return None
    
        if include_images:
            carousel_content = self.generate_image_prompts(article_text, carousel_content)
    
            if not carousel_content:
                logger.error("Failed to generate image prompts")
                return None
            logger.info("Image prompts generated successfully!")
    
            carousel_content = self.update_content_with_dimensions(
                carousel_content, 
                template_info
            )
            logger.info("Carousel content updated successfully with dimensions!")
    
            logger.info("Started Image generation")
            for page in carousel_content['pages']:
                os.makedirs('images', exist_ok=True)
                
                image_path = self.flux_generator.generate_image(
                    prompt=page['image_prompt'],
                    height=page['image_height'],
                    width=page['image_width'],
                    output_path=os.path.abspath(
                        os.path.join(generation_folder, f"{user_id}_page_{carousel_content['pages'].index(page) + 1}.jpg")
                    )
                )
                print(image_path)
    
                if image_path:
                    page['image'] = image_path
                else:
                    logger.error(f"Warning: Failed to generate image for page {carousel_content['pages'].index(page) + 1}")
                    page['image'] = os.path.join('images', 'placeholder.jpg')
    
            logger.info("Images generated successfully")
        logo_path = brand_config.get('logo', None)
        for page in carousel_content['pages']:
            if logo_path:
                page['logo'] = logo_path
            else:
                logger.error("Warning: No logo path provided in brand_config.")
                page['logo'] = None  
        try:
            content_file_path = os.path.join(generation_folder, "content.json")
            with open(content_file_path, "w", encoding="utf-8") as json_file:
                json.dump(carousel_content, json_file, indent=4, ensure_ascii=False)
            logger.info(f"Content saved to {content_file_path}")
            return carousel_content
        except Exception as e:
            logger.error(f"Error saving JSON file: {e}")
            return None    
    
      
    #def process_article(self, article_text, template_info, brand_config,include_images):
    #    """
    #    Process an article and generate carousel content.
    #    
    #    If include_images is False, skip image generation and related tasks.
    #    Use the logo path from brand_config.
    #    
    #    Parameters:
    #    - article_text (str): Text of the article to process
    #    - template_info (dict): Template-specific information
    #    - include_images (bool): Flag to include image generation
    #    - brand_config (dict): Dictionary containing brand configurations
    #    """
#
    #    user_id = brand_config['user_id']
    #    # Generate initial carousel content
    #    carousel_content = self.generate_carousel_content(article_text, template_info)
    #    if not carousel_content:
    #        print("Failed to generate carousel content")
    #        return None
    #
    #    if include_images:
    #        
    #       
    #        carousel_content = self.generate_image_prompts(article_text, carousel_content)
    #        
    #        if not carousel_content:
    #            logger.error("Failed to generate image prompts")
    #            return None
    #        logger.info("Image prompts generated sucessfully!!")
    #
    #       
    #        carousel_content = self.update_content_with_dimensions(
    #            carousel_content, 
    #            template_info
    #        )
    #        logger.info("carousel content updated sucessfully with dims!!")
    #        
    #
    #       
    #        logger.info("Started Image generation")
    #        for page in carousel_content['pages']:
    #           
    #            os.makedirs('images', exist_ok=True)
    #            image_path = self.flux_generator.generate_image(
    #                prompt=page['image_prompt'],
    #                height=page['image_height'],
    #                width=page['image_width'],
    #                #output_path=os.path.join('images', f"page_{carousel_content['pages'].index(page) + 1}.jpg")
    #                output_path = os.path.abspath(
    #                os.path.join('images', f"{user_id}_page_{carousel_content['pages'].index(page) + 1}.jpg")
    #                )
    #            )
    #            print(image_path)
    #            
    #            if image_path:
    #                page['image'] = image_path
    #            else:
    #                logger.error(f"Warning: Failed to generate image for page {carousel_content['pages'].index(page) + 1}")
    #                page['image'] = os.path.join('images', 'placeholder.jpg')
#
    #        logger.info("Images generated sucessfully")        
    #
    #    # Handle logo from brand_config
    #    logo_path = brand_config.get('logo', None)
    #    for page in carousel_content['pages']:
    #        if logo_path:
    #            page['logo'] = logo_path
    #        else:
    #            logger.error("Warning: No logo path provided in brand_config.")
    #            page['logo'] = None  # Or set a default logo path
    #
    #    # Save the final content
    #    try:
    #        with open("content.json", "w", encoding="utf-8") as json_file:
    #            json.dump(carousel_content, json_file, indent=4, ensure_ascii=False)
    #        return carousel_content
    #    except Exception as e:
    #        logger.error(f"Error saving JSON file: {e}")
    #        return None
#
#