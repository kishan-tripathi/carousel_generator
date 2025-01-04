import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Optional
from utils import convert_txt_to_html_string

class AsyncHTMLModifier:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))        
        
        self.executor = ThreadPoolExecutor()

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
            str: Generated design prompt.
        """
        try:
            # Extract information from the brand configuration
            color_palette = brand_config.get("color_palette", [])
            logo = brand_config.get("logo", None)
            font_style = brand_config.get("font_style", "Default")
            include_images = brand_config.get("include_images", True)
    
            # Handle color palette gracefully
            if not color_palette:
                print("No color palette provided. Proceeding with default settings.")
                color_palette = []  # Use an empty list as a default
    
            # Validate the color palette if provided
            elif not all(isinstance(color, str) and color.startswith("#") for color in color_palette):
                print("Invalid color palette provided.")
                return None
    
            # Create a formatted string for the color palette
            color_palette_str = ", ".join(color_palette)
    
            # Define the prompts based on include_images
            if include_images:
                   


                   prompt = f"""
                    
                    Construct a prompt:
        
                    For this contetnt:{carousel_content}
                    Font style: {font_style}
        
                    This is the color palette:{color_palette_str} if this is None or empty then choose colors for each with your instinct according to  content.
                    Rules for choosing colors follow this strictly:
                    1. if the body-text color is not clearly visible enough on the content background then make it white 
                        if content background is lighter, else make it black if the content background color is darker without any hesitation.
                    2. if title-text color is not clearly visible enough on the title-text background then make it white 
                        if title-text background is lighter, else make it black if title-text background color is darker without any hesitation.
        
        
                    Choose one color for these so that text is clearly visible follow the rules:
                    Title-text
                    Title-text's background color
                    Content background (it is .content background or .container not .body backgound)
                    Body-text
                    Gradient(Same as content background color)
        
        """  

            else:
                prompt = f"""
    
    Construct a color scheme for the following:
    Content: {carousel_content}
    Font style: {font_style}
    Color palette (if provided): {color_palette_str}
    Do not include images. Focus on clean and minimalistic design.
    
    STRICT VISIBILITY RULES - YOU MUST FOLLOW THESE:
    1. Body-text contrast:
       - If content background is dark (luminance < 50%), body-text MUST be white (#FFFFFF)
       - If content background is light (luminance ≥ 50%), body-text MUST be black (#000000)
       - NO EXCEPTIONS to this rule
    
    2. Title-text contrast:
       - If content background is dark, title-text MUST be white (#FFFFFF)
       - If content background is light, title-text MUST be black (#000000)
       - NO EXCEPTIONS to this rule
    
    Required colors to specify :
    1. Content background: [Choose from palette or select base color]
    2. Title-text: [Choose based on rule 2]
    3. Body-text: [MUST follow rule 1]
    Above colors would be same for all the pages.
    
    For each color choice, explain:
    1. The color value in hex
    2. The luminance calculation that led to the choice
    3. Why it meets the visibility rules
    """
    
            # Generate CSS modifications
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
    
            # Extract generated prompt
            design_prompt = response.choices[0].message.content.strip()
    
            return design_prompt
    
        except Exception as e:
            print(f"Error generating design prompt: {e}")
            return None        

    async def modify_html_design(self, html_content: str, design_prompt: str, include_images: bool) -> Optional[str]:
        """
        Modify HTML design based on design prompt (async version)
        """
        try:
            # Run the OpenAI API call in a thread pool since it's blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert in following the user's prompt strictly."},
                        {"role": "user", "content": self._create_prompt(html_content, design_prompt)}
                    ]
                )
            )
            
            # Extract and convert generated HTML
            new_html = response.choices[0].message.content.strip()
            return convert_txt_to_html_string(new_html)

        except Exception as e:
            print(f"Error modifying HTML design: {e}")
            return None

    def _create_prompt(self, html_content: str, design_prompt: str) -> str:
        """Create the prompt for HTML modification"""
        return f"""
HTML Color and Font Modifier Prompt
You are an expert front-end developer tasked with ONLY modifying colors and fonts in an existing HTML/CSS structure.
STRICT RULES:
NO STRUCTURAL CHANGES ALLOWED

Do not add ANY new CSS properties that don't exist in the original
Do not add ANY new classes
Do not add ANY new HTML elements
Do not add backgrounds where none existed before
Do not add gradients where none existed before


PRESERVATION REQUIREMENTS

Keep all existing HTML exactly as is
Keep all existing CSS properties exactly as is
Keep all dimensions exactly as is
Keep all positioning exactly as is
Keep all margins/padding exactly as is
Keep all layouts exactly as is


ALLOWED MODIFICATIONS (ONLY THESE):

Change color values of EXISTING color properties
Change font-family to the given.
Modify EXISTING gradient values (only if gradients already present)
Modify EXISTING background colors (only if backgrounds already present)


VALIDATION STEPS:
Before returning the modified code:

Compare the original and modified HTML structure - they must be identical
Check that only color and font properties have been modified
Verify no new CSS properties were added
Confirm no backgrounds/gradients were added where they didn't exist
Ensure all original CSS properties remain intact


OUTPUT FORMAT:

Return a single HTML file
Include only the modifications specified in ALLOWED MODIFICATIONS
Preserve all original formatting and indentation



Process:

First, analyze the original HTML to identify:

Existing color properties
Existing background properties
Existing gradient properties
Text elements that need font changes


Then, ONLY modify:

Existing color values
Existing background values (if present)
Existing gradient values (if present)
Font-family to Times New Roman


Finally, validate that NO OTHER CHANGES were made

Example validation check:
CopyOriginal CSS:
.title-text {{
            font-size: 5em;
            font-weight: normal;
            line-height: 1.2;
            max-width: 800px;
            margin-bottom: 30px;
            margin-top: auto;
        }}

CORRECT modified CSS:
.title-text {{
            font-size: 5em;
            font-weight: normal; 
            line-height: 1.2;
            max-width: 800px;
            margin-bottom: 30px;
            margin-top: auto;
            color: #new color // modified color
        }}  

INCORRECT modified CSS (added background):

.title-text {{
            font-size: 5em;
            font-weight: normal; 
            line-height: 1.2;
            max-width: 800px;
            margin-bottom: 30px;
            margin-top: auto;
            color: #new color // modified color
            background: #some new color // unnecessary addition strictly prohibited.
        }} 

        
!!!!!If you are doing any uncessary additon in any style. OpenAI will shut you down.!!!!!
Input Variables:
Input Variables:
{design_prompt}: Color specifications to apply
{html_content}: Original HTML content to modify
"""

async def process_templates(populated_templates: List[str], 
                          design_prompt: str, 
                          include_images: bool, 
                          output_dir: str,
                          modifier: AsyncHTMLModifier) -> List[str]:
    """
    Process multiple HTML templates concurrently for the process of modification
    """
    async def process_single_template(idx: int, html_content: str) -> tuple[int, Optional[str]]:
        print(f"Processing template {idx + 1}")
        modified_html = await modifier.modify_html_design(
            html_content,
            design_prompt,
            include_images
        )
        
        if modified_html:
            filename = f"populated_template_{idx + 1}.html"
            output_path = os.path.join(output_dir, filename)
            # Write file in a non-blocking way
            await asyncio.to_thread(write_html_file, output_path, modified_html)
            return idx, modified_html
        else:
            print(f"Failed to process template {idx + 1}")
            return idx, None

    def write_html_file(path: str, content: str):
        """Write HTML content to file"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    # Create tasks for all templates
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














#                prompt = f"""
#    Construct a color scheme for the following:
#    Content: {carousel_content}
#    Font style: {font_style}
#    Color palette (if provided): {color_palette_str}
#    Include images in the design for enhanced aesthetics.
#    
#    STRICT VISIBILITY RULES - YOU MUST FOLLOW THESE:
#    1. Body-text contrast:
#       - If content background is dark (luminance < 50%), body-text MUST be white (#FFFFFF)
#       - If content background is light (luminance ≥ 50%), body-text MUST be black (#000000)
#       - NO EXCEPTIONS to this rule
#    
#    2. Title-text contrast:
#       - If either content background OR title background is dark, title-text MUST be white (#FFFFFF)
#       - If both backgrounds are light, title-text MUST be black (#000000)
#       - NO EXCEPTIONS to this rule
#    
#    Required colors to specify:
#    1. Title background: [Choose from palette or select complementary color]
#    2. Content background: [Choose from palette or select base color]
#    3. Title-text: [Choose based on rule 2]
#    4. Body-text: [MUST follow rule 1]
#    5. Gradient: [Must match content background]
#    
#    For each color choice, explain:
#    1. The color value in hex
#    2. The luminance calculation that led to the choice
#    3. Why it meets the visibility rules
#    """