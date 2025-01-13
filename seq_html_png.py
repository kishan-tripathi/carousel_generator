from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from PIL import Image
import io
import base64
import uuid
from typing import List, Dict

def process_single_html(html_content: str, class_name: str, output_folder: str, index: int, brand_config: Dict) -> Dict:
    """
    Process a single HTML string to PNG conversion.
    
    Parameters:
    html_content (str): HTML content to process
    class_name (str): Target class name for screenshots
    output_folder (str): Directory to save the images
    index (int): Index of the HTML content in the sequence
    brand_config (Dict): Configuration dictionary with additional information
    
    Returns:
    dict: Dictionary containing the processing results
    """
    user_id = brand_config['user_id']
    
    # Create unique subfolder for this process to avoid conflicts
    process_folder = os.path.join(output_folder, f"process_{index}")
    os.makedirs(process_folder, exist_ok=True)
    
    # Create a temporary HTML file with unique name
    temp_html_path = os.path.join(process_folder, f"temp_{uuid.uuid4()}.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Convert local path to file URL
    file_url = 'file://' + os.path.abspath(temp_html_path)
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    result = {
        'index': index,
        'success': False,
        'files': [],
        'error': None
    }
    
    try:
        # Load the HTML content
        driver.get(file_url)
        
        # Wait for elements with the specified class to be present
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
        )
        
        # Process each element
        for idx, element in enumerate(elements):
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            
            # Add a small delay to ensure the element is fully rendered
            driver.implicitly_wait(1)
            
            # Get screenshot as base64
            screenshot = element.screenshot_as_base64
            
            # Convert base64 to image
            image_data = base64.b64decode(screenshot)
            image = Image.open(io.BytesIO(image_data))
            
            # Generate unique filename
            timestamp = int(time.time() * 1000)
            output_path = os.path.join(output_folder, f"{user_id}_{index}_{idx}_{timestamp}.png")
            
            # Save the image
            image.save(output_path, 'PNG')
            result['files'].append(output_path)
        
        result['success'] = True
            
    except Exception as e:
        result['error'] = str(e)
        
    finally:
        driver.quit()
        # Clean up temporary files
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
        # Try to remove the process folder
        try:
            os.rmdir(process_folder)
        except:
            pass
    
    return result

def sequential_html_to_png(html_list: List[str], class_name: str, output_folder: str = "output_images", brand_config: Dict = None) -> List[Dict]:
    """
    Convert multiple HTML strings to PNG images sequentially.
    
    Parameters:
    html_list (List[str]): List of HTML strings to convert
    class_name (str): The class name to target in the HTML
    output_folder (str): Folder to save the PNG files
    brand_config (Dict): Configuration dictionary with additional information
    
    Returns:
    List[Dict]: List of dictionaries containing results for each HTML string
    """
    os.makedirs(output_folder, exist_ok=True)
    
    results = []
    for idx, html_content in enumerate(html_list):
        print(f"Processing HTML {idx}...")
        result = process_single_html(html_content, class_name, output_folder, idx, brand_config)
        results.append(result)
        if result['success']:
            print(f"Successfully processed HTML {idx} and generated {len(result['files'])} images")
        else:
            print(f"Failed to process HTML {idx}: {result['error']}")
    
    return results
