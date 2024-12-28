import logging
import time
from article_contentgen import ArticleCarouselGenerator
from template_processor import HTMLTemplateProcessor
from template_processorn import TemplateSelector
from design_modifier import AsyncHTMLModifier, process_templates 
from utils import UserIDGenerator
import asyncio
import json
from io import BytesIO
import os
from seq_html_png import sequential_html_to_png
from utils import ColorPaletteInput, handle_color_palette, handle_logo_upload, cleanup_files

def setup_logging(user_id):
    """Sets up basic logging configuration for the application."""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'carousel_{user_id}_{int(time.time())}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger()

def main(
    article_input, 
    num_pages, 
    color_palette_type: ColorPaletteInput,
    color_palette_input=None,
    uploaded_logo=None, 
    include_images=True, 
    font_style=None,
    user_id=None,
    brand_name=None
):
    """Main function to process article content and generate designed templates"""
    start_time = time.time()
    logger = setup_logging(user_id)
    logger.info(f"Starting content generation for user: {user_id}")

    try:
        # Initialize components
        generator = ArticleCarouselGenerator()
        processor = TemplateSelector()
        modifier_new = AsyncHTMLModifier()
        logger.info("Components initialized successfully")

        # Process logo and color palette
        logo_path = handle_logo_upload(uploaded_logo, user_id)
        processed_colors = handle_color_palette(color_palette_type, color_palette_input)
        logger.info("Logo and color palette processed")

        # Process article content
        article_text = ""
        if article_input.startswith(('http://', 'https://')):
            article_text = ArticleCarouselGenerator.fetch_article_content(article_input)
            logger.info("Article fetched from URL")
        elif len(article_input.split()) == 1:
            article_text = ArticleCarouselGenerator.generate_article(article_input)
            logger.info("Article generated from topic")
        else:
            article_text = article_input
            logger.info("Using provided article text")

        if not article_text:
            logger.error("Failed to get article content")
            return None

        # Configure brand settings
        brand_config = {
            'color_palette': processed_colors,
            'logo': logo_path,
            'font_style': font_style,
            'include_images': include_images,
            'user_id': user_id,
            'brand_name':brand_name
        }

        # Process templates
        template_info = processor.select_templates(num_pages, brand_config)
        logger.info("Templates selected")
        if not template_info:
            logger.error("Template selection failed")
            return None

        carousel_content = generator.process_article(
            article_text, template_info, brand_config, include_images=include_images
        )
        logger.info("Carousel content generated")
        if not carousel_content:
            logger.error("Article processing failed")
            return None

        # Save template information
        with open('template_info.txt', 'w', encoding='utf-8') as f:
            json.dump(template_info, f, indent=4)

        # Generate templates
        populated_templates = processor.populate_templates(
            carousel_content, template_info, brand_config
        )
        logger.info("Templates Populated")
        if not populated_templates:
            logger.error("Template population failed")
            return None

        # Process layouts
        output_dir = 'final_output9'
        if matches_predefined_layout(template_info):
            logger.info("Using predefined layout")
            modified_files = save_templates(populated_templates, output_dir)
        else:
            logger.info("Using custom layout")
            design_prompt = modifier_new.generate_design_prompt(brand_config, carousel_content)
            modified_files = asyncio.run(process_templates(
                populated_templates,
                design_prompt,
                include_images,
                output_dir,
                modifier_new
            ))
        logger.info("Done with modifications")
        # Convert to images
        results = sequential_html_to_png(modified_files, "container", 'final_images', brand_config)
        log_conversion_results(logger, results)
        
        logger.info(f"Process completed in {time.time() - start_time:.2f} seconds")
        return modified_files, results

    except Exception as e:
        logger.error(f"Process failed: {str(e)}")
        return None

def matches_predefined_layout(template_info):
    """Checks if template matches predefined layouts"""
    predefined_layouts = [
        {"collection": "layouts_lit", "layout": "layout1"},
        {"collection": "layouts_lit", "layout": "layout5"},
        {"collection": "layouts_it", "layout": "layout1"},
        {"collection": "layouts_it", "layout": "layout5"}
    ]
    
    return any(
        info['collection'] == layout['collection'] and 
        info['layout'] == layout['layout']
        for info in template_info
        for layout in predefined_layouts
    )

def save_templates(templates, output_dir):
    """Saves templates to files"""
    modified_files = []
    for idx, html_content in enumerate(templates):
        filename = f"populated_template_{idx + 1}.html"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        modified_files.append(output_path)
    return modified_files

def log_conversion_results(logger, results):
    """Logs the results of HTML to PNG conversion"""
    successful = sum(1 for r in results if r['success'])
    logger.info(f"Conversions: {successful} successful, {len(results) - successful} failed")
    
    failed = [r for r in results if not r['success']]
    if failed:
        for f in failed:
            logger.error(f"Failed conversion {f['index']}: {f['error']}")

if __name__ == "__main__":
    # Test configuration
    with open("C:\\Users\\shash\\OneDrive\\Documents\\new_carousel_gen\\uploads\\logos\\lexLogo.svg.svg", "rb") as logo_file:
        uploaded_logo_simulation = BytesIO(logo_file.read())
        uploaded_logo_simulation.name = "test_logo.svg"

    example_config = {
        'article_input': "https://aeon.co/videos/the-remarkable-innovations-inspired-by-our-need-to-know-the-night-sky",
        'num_pages': 6,
        'color_palette_type': ColorPaletteInput.URL,
        'color_palette_input': "https://aeon.co/videos/the-remarkable-innovations-inspired-by-our-need-to-know-the-night-sky",
        'uploaded_logo': uploaded_logo_simulation,
        'include_images': True,
        'font_style': "Verdana",
        'brand_name':"@legalwires"
    }

    # Run test
    logger = setup_logging('test_run')
    try:
        output_files, results = main(**example_config)
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")