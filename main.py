from article_contentgen import ArticleCarouselGenerator
from template_processor import TemplateSelector
from design_modifier import  HTMLModifier ,process_templates 
from html_png import async_html_to_png
from utils import UserIDGenerator
import asyncio
import json
import os
from io import BytesIO
import time 
import time
from io import BytesIO
from extract_colors import ColorPaletteInput,handle_color_palette
from utils import setup_logging, handle_logo_upload, cleanup_files
import logging


def main(
    article_input, 
    num_pages, 
    color_palette_type: ColorPaletteInput,
    color_palette_input=None,
    uploaded_logo=None, 
    include_images=True, 
    font_style=None,
    user_id=None,
    brand_name=None,
):
    """
    Main function to process article content and generate designed templates
    Parameters:
    article_input (str): URL, topic, or complete article text
    num_pages (int): Number of pages to generate
    color_palette_type: ColorPaletteInput enum indicating type of color input
    color_palette_input: URL string or list of color strings based on color_palette_type
    uploaded_logo: File object from upload or None
    include_images (bool): Whether to include images in the output
    font_style (str): Selected font style from dropdown
    """
   
    user_id=user_id
    setup_logging(user_id)  
    logger = logging.getLogger(__name__)
    
    logger.info("Logging setup complete.")

    generator = ArticleCarouselGenerator()
    processor = TemplateSelector()
    modifier = HTMLModifier()
    logger.info("Components initialized successfully")


    
    logo_path = handle_logo_upload(uploaded_logo,user_id)

    processed_colors = handle_color_palette(color_palette_type, color_palette_input)
    logger.info("Logo and color palette processed")
    
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
    
    output_dir = 'final_output9'

    brand_config = {
        'color_palette': processed_colors,
        'logo': logo_path,
        'font_style': font_style,
        'include_images': include_images,
        'user_id':user_id,
        'brand_name':brand_name
    }
    print(brand_config)
        

    template_info = processor.select_templates(num_pages,brand_config)
    if not template_info:
        logger.info("Template selection failed")
        return None

    carousel_content = generator.process_article(article_text, template_info, brand_config, include_images=include_images)
    if not carousel_content:
        logger.info("Failed to process articcle content")

        return None
    #print(carousel_content)

    filename = 'template_info.txt'
    with open(filename, 'w', encoding='utf-8') as f:
            
        json.dump(template_info, f, indent=4)  

    #print(f"template_info: {template_info}")      

    logging.info("replacing content in templates")
    populated_templates = asyncio.run(processor.populate_templates(
    carousel_content=carousel_content,
    template_info=template_info,
    brand_config=brand_config
    
))
    logging.info("content replaced done")
    selected_layouts = [
        {"collection": "layouts_lit", "layout": "layout1"},
        {"collection": "layouts_lit", "layout": "layout5"},
        {"collection": "layouts_it", "layout": "layout1"},
        {"collection": "layouts_it", "layout": "layout5"},
        {"collection": "layouts_lit", "layout": "layout6"},
        {"collection": "layouts_it", "layout": "layout6"}

    ]
    
    # check if any templates match the selected layouts
    layout_found = False
    matching_template = None
    
    for info in template_info:
        for selected in selected_layouts:
            if (info['collection'] == selected['collection'] and 
                info['layout'] == selected['layout']):
                layout_found = True
                matching_template = info
                break
        if layout_found:
            logger.info(f"Selected layout matches: {matching_template['collection']}/{matching_template['layout']}")
            break
    
    if layout_found:
        font_style = brand_config.get("font_style", "Default")
        design_json = {
            "font-style": font_style 
        } 
        print(design_json)


        modified_files = asyncio.run(process_templates(
            populated_templates=populated_templates,
            color_mapping=design_json,
            output_dir=output_dir
        ))


        logger.info("Started conversion of html to png")
        results = asyncio.run(async_html_to_png(modified_files, "container", 'final_images2', brand_config))

        successful = sum(1 for r in results if r['success'])
        print(f"\nProcessing Summary:")
        print(f"Total processed: {len(results)}")
        logger.info(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        
        failed = [r for r in results if not r['success']]
        if failed:
            print("\nFailed conversions:")
            for f in failed:
                print(f"HTML {f['index']}: {f['error']}")
        
        return modified_files, results   
          
    else:
        logger.info("No matching layouts found. Proceeding with design modification process.")
        print("Populated templates:")
        #for template in populated_templates:
        #    print(template)
        
        design_json = modifier.generate_design_prompt(brand_config,carousel_content)
        
        print(design_json)
        logger.info("prompt json generated")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "final_output9")
        os.makedirs(output_dir, exist_ok=True)

        logger.info("Started color modification")
        modified_files = asyncio.run(process_templates(
            populated_templates=populated_templates,
            color_mapping=design_json,
            output_dir=output_dir
        ))
        logger.info("Files modified sucessfully")
        
        logger.info(" converting the html to png files.")
        
        results = asyncio.run(async_html_to_png(modified_files, "container", 'final_images2', brand_config))
        
        successful = sum(1 for r in results if r['success'])
        print(f"\nProcessing Summary:")
        print(f"Total processed: {len(results)}")
        logger.info(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        

        failed = [r for r in results if not r['success']]
        if failed:
            logger.info("\nFailed conversions:")
            for f in failed:
                print(f"HTML {f['index']}: {f['error']}")
        
        return modified_files, results   




if __name__ == "__main__":
    

    start_time = int(time.time())    

    
    with open("C:\\Users\\shash\\OneDrive\\Documents\\new_carousel_gen\\uploads\\logos\\lexLogo.svg.svg", "rb") as logo_file: 
        uploaded_logo_simulation = BytesIO(logo_file.read())
        uploaded_logo_simulation.name = "test_logo.svg"  

    example_config = {
        'article_input': "https://aeon.co/essays/why-do-i-let-myself-sabotage-my-own-best-laid-plans",
        'num_pages' : 6,
        'color_palette_type': ColorPaletteInput.URL,
        'color_palette_input':  "https://aeon.co/essays/why-do-i-let-myself-sabotage-my-own-best-laid-plans",
        'uploaded_logo': uploaded_logo_simulation,  
        'include_images': True,
        'font_style': "Verdana",
        'brand_name':"@legalwires"
    }



    output_files,results  = main(**example_config)
    #print("Generated Files:", output_files)    
    #print("Generated Files:", results)
    

    end_time = int(time.time())  
    total_time = end_time-start_time

    images_directory = 'images'  
    logos_directory = 'logos'    
    #cleanup_files(images_directory, logos_directory, user_id)
    #print('files deleted')
    print(f'total time: {total_time}')


