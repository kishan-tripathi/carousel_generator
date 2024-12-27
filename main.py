from article_contentgen import ArticleCarouselGenerator
from template_processor import HTMLTemplateProcessor
from template_processorn import TemplateSelector
from design_modifier import AsyncHTMLModifier , process_templates 
from utils import UserIDGenerator
import asyncio
import json
from io import BytesIO
from html_to_png import local_html_to_png
import os
from html_png import parallel_html_to_png
import shutil
from pathlib import Path
import time
import requests
import time
from PIL import Image
from io import BytesIO
from enum import Enum
from utils import ColorPaletteInput, handle_color_palette,handle_logo_upload, cleanup_files




def main(
    article_input, 
    num_pages, 
    color_palette_type: ColorPaletteInput,
    color_palette_input=None,
    uploaded_logo=None, 
    include_images=True, 
    font_style=None
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


    generator = ArticleCarouselGenerator()
    processor = TemplateSelector()
    uidgenerator = UserIDGenerator()
    modifier_new = AsyncHTMLModifier()

    user_id = uidgenerator.generate_uuid()
    
    # Handle logo upload
    logo_path = handle_logo_upload(uploaded_logo,user_id)
    
    # Process color palette based on selected input type
    processed_colors = handle_color_palette(color_palette_type, color_palette_input)
    
    # Get article content based on input type
    article_text = ""
    if article_input.startswith(('http://', 'https://')):
        article_text = ArticleCarouselGenerator.fetch_article_content(article_input)
    elif len(article_input.split()) == 1:
        article_text = ArticleCarouselGenerator.generate_article(article_input)
    else:
        article_text = article_input
        
    if not article_text:
        print("Failed to get article content")
        return None
    

    brand_template_path = 'brand_template.json'
    output_dir = 'final_output9'



    # Updating brand template with user preferences
    brand_config = {
        'color_palette': processed_colors,
        'logo': logo_path,
        'font_style': font_style,
        'include_images': include_images,
        'user_id':user_id
    }
    print(brand_config)
    #processor.update_brand_template(brand_template_path, brand_config)    
        

    template_info = processor.select_templates(num_pages,brand_config)
    if not template_info:
        print("Template selection failed")
        return None

    carousel_content = generator.process_article(article_text, template_info, brand_config, include_images=include_images)
    if not carousel_content:
        print("Failed to process article content")
        return None
    print(carousel_content)

    filename = 'template_info.txt'
    with open(filename, 'w', encoding='utf-8') as f:
            
        json.dump(template_info, f, indent=4)  

    print(f"template_info: {template_info}")      
    
    populated_templates = processor.populate_templates(carousel_content,template_info,brand_config)
    if not populated_templates:
        print("Failed to populate templates")
        return None
    
    selected_layouts = [
        {"collection": "layouts_lit", "layout": "layout1"},
        {"collection": "layouts_lit", "layout": "layout5"},
        {"collection": "layouts_it", "layout": "layout1"},
        {"collection": "layouts_it", "layout": "layout5"}
    ]
    
    # Check if any templates match the selected layouts
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
            print(f"Selected layout matches: {matching_template['collection']}/{matching_template['layout']}")
            break
    
    if layout_found:
        # Write populated templates to files without modifying the design
        modified_files = []
        for idx, html_content in enumerate(populated_templates):
            filename = f"populated_template_{idx + 1}.html"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            modified_files.append(output_path)
            print(f"Populated template saved to: {output_path}")
        
        return modified_files
    else:
        print("No matching layouts found. Proceeding with design modification process.")
        print("Populated templates:")
        for template in populated_templates:
            print(template)
        
        design_prompt = modifier_new.generate_design_prompt(brand_config, carousel_content)
        if not design_prompt:
            print("Failed to generate design prompt")
            return None
        
        print(design_prompt)
        
        modified_files = asyncio.run(process_templates(
            populated_templates,
            design_prompt,
            include_images,
            output_dir,
            modifier_new
        ))
        
        #return modified_files 

        results = parallel_html_to_png(modified_files, "container", 'final_images')
        
        # Print conversion summary
        successful = sum(1 for r in results if r['success'])
        print(f"\nProcessing Summary:")
        print(f"Total processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        
        # Print details of failed conversions
        failed = [r for r in results if not r['success']]
        if failed:
            print("\nFailed conversions:")
            for f in failed:
                print(f"HTML {f['index']}: {f['error']}")
        
        return modified_files, results   
    



    ## Define the list of selected layouts
    #selected_layouts = ["layouts_lit/layout1", "layouts_lit/layout5", "layouts_it/layout1", "layouts_it/layout5"]
    #
    ## Check if any of the paths in template_info match the selected layouts
    #layout_found = False
    #matching_layout_path = None  # To keep track of the matched layout path
    #for info in template_info2:
    #    # Extract the layout from the path
    #    layout_path = info['path'].replace('\\', '/')  # Normalize path for comparison
    #    for layout in selected_layouts:
    #        if layout in layout_path:
    #            layout_found = True
    #            matching_layout_path = layout_path
    #            break  # Exit the inner loop if a match is found
    #    if layout_found:
    #        print(f"Selected layout matches: {matching_layout_path}")
    #        break  # Exit the outer loop if a match is found
    #
    #if layout_found:
    #    # Write populated templates to files without modifying the design
    #    modified_files = []
    #    for idx, html_content in enumerate(populated_templates):
    #        filename = f"populated_template_{idx + 1}.html"
    #        output_path = os.path.join(output_dir, filename)
    #        with open(output_path, "w", encoding="utf-8") as f:
    #            f.write(html_content)
    #        modified_files.append(output_path)
    #        print(f"Populated template saved to: {output_path}")
    #    
    #    return modified_files
    #else:
    #    print("No matching layouts found. Proceeding with design modification process.")
#
    #    print("Populated templates:")
    #    for template in populated_templates:
    #        print(template)
    #    
    #    #input_dir = 'populated_templates'
    #    #content_path = 'content.json'
    #    
    #    design_prompt = modifier.generate_design_prompt(brand_config, carousel_content)
    #    if not design_prompt:
    #        print("Failed to generate design prompt")
    #        return None
    #    
    #    print(design_prompt)
#
#
    #    modified_files = asyncio.run(process_templates(
    #    populated_templates,
    #    design_prompt,
    #    include_images,
    #    output_dir,
    #    modifier_new
    #    ))
    #
        # Proceed with the design modification process
        #modified_files = []
        #for idx, html_content in enumerate(populated_templates):
        #    print(f"Processing template {idx + 1}")
        #    
        #    modified_html = modifier.modify_html_design(
        #        html_content,  # Pass the HTML content directly
        #        design_prompt,
        #        include_images=include_images
        #    )
#
        #    filename = f"populated_template_{idx + 1}.html"
        #    output_path = os.path.join(output_dir, filename)
        #    # Write modified HTML
        #    with open(output_path, 'w', encoding='utf-8') as f:
        #        f.write(modified_html)
#
        #    if modified_html:
        #        modified_files.append(modified_html)
        #    else:
        #        print(f"Failed to process template {idx + 1}")
        #
        #return modified_files



if __name__ == "__main__":
    

    start_time = int(time.time())    

    # Simulating a file upload with a file-like object
    with open("C:\\Users\\shash\\OneDrive\\Documents\\new_carousel_gen\\uploads\\logos\\lexLogo.svg.svg", "rb") as logo_file:  # Replace with your actual logo file path
        uploaded_logo_simulation = BytesIO(logo_file.read())
        uploaded_logo_simulation.name = "test_logo.svg"  

    example_config = {
        'article_input': "https://legal-wires.com/buzz/sc-directs-police-to-complete-verification-of-govt-job-candidates-within-six-months-to-prevent-delays/",
        'num_pages': 5,
        'color_palette_type': ColorPaletteInput.MANUAL,
        'color_palette_input': ["#b0d2da","#cab29f","#7da1bf","#2f4a60"],
        'uploaded_logo': None,  # Simulated file upload
        'include_images': True,
        'font_style': "Arial"
    }



    # Run the main function
    output_files = main(**example_config)
    print("Generated Files:", output_files)    

    end_time = int(time.time())  
    total_time = end_time-start_time

    #user_id = example_config['user_id']

    images_directory = 'images'  
    logos_directory = 'logos'    
    #cleanup_files(images_directory, logos_directory, user_id)
    print('files deleted')
    print(f'total time: {total_time}')


    ## Check if the selected template is one of the specified layouts
    ##selected_layouts = ["layouts_lit/layout1", "layouts_lit/layout5", "layouts_it/layout1", "layouts_it/layout5"]
    ##if any(layout in template_info['selected_layout'] for layout in selected_layouts):
    ##    print("Selected layout does not require modification. Returning populated templates directly.")
    #selected_layouts = ["layouts_lit/layout1", "layouts_lit/layout5", "layouts_it/layout1", "layouts_it/layout5"]
    #
    ## Check if any of the paths in template_info match the selected layouts
    #layout_found = False
    #for info in template_info:
    #    # Extract the layout from the path
    #    layout_path = info['path'].replace('\\', '/')  # Normalize path for comparison
    #    for layout in selected_layouts:
    #        if layout in layout_path:
    #            layout_found = True
    #            break  # Exit the inner loop if a match is found
    #    if layout_found:
    #        print("Selected layout matches:", layout_path)
    #        break  # Exit the outer loop if a match is found
    #
    #if not layout_found:
    #    print("No matching layouts found.")    
    #
    #    # Write populated templates to files
    #    modified_files = []
    #    for idx, html_content in enumerate(populated_templates):
    #        filename = f"populated_template_{idx + 1}.html"
    #        output_path = os.path.join(output_dir, filename)
    #        with open(output_path, "w", encoding="utf-8") as f:
    #            f.write(html_content)
    #        modified_files.append(output_path)
    #        print(f"Populated template saved to: {output_path}")
    #    
    #    return modified_files
#
#
    #print("Populated templates:")
    #for template in populated_templates:
    #    print(template)
    #
    #input_dir = 'populated_templates'
    #content_path = 'content.json'
    #
    #design_prompt = modifier.generate_design_prompt(brand_config, carousel_content)
    #if not design_prompt:
    #    print("Failed to generate design prompt")
    #    return None
    #
    #print(design_prompt)
    #
    #modified_files = []
    #
    ## Process each HTML content in populated_templates
    #for idx, html_content in enumerate(populated_templates):
    #    print(f"Processing template {idx + 1}")
    #    
    #    output_path = modifier.modify_html_design(
    #        html_content,  # Pass the HTML content directly
    #        design_prompt,
    #        include_images=include_images
    #    )
    #    
    #    if output_path:
    #        print(f"Modified HTML saved to: {output_path}")
    #        modified_files.append(output_path)
    #    else:
    #        print(f"Failed to process template {idx + 1}")
    #
    #return modified_files
    #



#    carousel_content = generator.process_article(article_text, template_info, brand_config, include_images=include_images)
#    if not carousel_content:
#        print("Failed to process article content")
#        return None
#        
#    populated_templates = processor.populate_templates(carousel_content)
#    if not populated_templates:
#        print("Failed to populate templates")
#        return None
#        
#    print("Populated templates:")
#    for template in populated_templates:
#        print(template)
#        
#    input_dir = 'populated_templates'
#    content_path = 'content.json'
#
#    
#    design_prompt = modifier.generate_design_prompt(brand_config, carousel_content)
#    if not design_prompt:
#        print("Failed to generate design prompt")
#        return None
#        
#    print(design_prompt)
#
#    modified_files = []
#    
#    # Process each HTML content in populated_templates
#    for idx, html_content in enumerate(populated_templates):
#        print(f"Processing template {idx + 1}")
#        
#        output_path = modifier.modify_html_design(
#            html_content,  # Pass the HTML content directly
#            design_prompt,
#            include_images=include_images
#        )
#        
#        if output_path:
#            print(f"Modified HTML saved to: {output_path}")
#            modified_files.append(output_path)
#        else:
#            print(f"Failed to process template {idx + 1}")
#    
#    return modified_files    








    
    #modified_files = []
    #for file_name in os.listdir(input_dir):
    #    if file_name.endswith('.html'):
    #        file_path = os.path.join(input_dir, file_name)
    #        print(f"Processing: {file_name}")
    #        
    #        output_path = modifier.modify_html_design(
    #            file_path, 
    #            design_prompt,
    #            include_images=include_images
    #        )
    #        
    #        if output_path:
    #            print(f"Modified HTML saved to: {output_path}")
    #            modified_files.append(output_path)
    #        else:
    #            print(f"Failed to process: {file_name}")
    #
    #return modified_files






#
#if __name__ == "__main__":
#    # Example usage with URL-based color palette
#    example_url = {
#        'article_input': "https://legal-wires.com/buzz/mere-harassment-not-enough-for-suicide-abetment-conviction-supreme-court-clarifies-legal-standards-2/",
#        'num_pages': 5,
#        'color_palette_type': ColorPaletteInput.URL,
#        'color_palette_input': "https://legal-wires.com/buzz/mere-harassment-not-enough-for-suicide-abetment-conviction-supreme-court-clarifies-legal-standards-2/",
#        'uploaded_logo': None,
#        'include_images': True,
#        'font_style': "Arial"
#    }
#    
#    # Example usage with manual color list
#    example_manual = {
#        'article_input': "https://example.com/article",
#        'num_pages': 5,
#        'color_palette_type': ColorPaletteInput.MANUAL,
#        'color_palette_input': ["#FF0000", "#00FF00", "#0000FF"],
#        'uploaded_logo': None,
#        'include_images': True,
#        'font_style': "Arial"
#    }
#    
#    # Use either example_url or example_manual configuration
#    main(**example_url)


    