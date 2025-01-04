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
import asyncio
import aiofiles
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class ImageProcessor:
    def __init__(self, max_concurrent: int = 5):
        """
        Initialize the async HTML processor.
        
        Parameters:
        max_concurrent (int): Maximum number of concurrent tasks
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)
    
    async def process_single_html(self, html_content: str, class_name: str, 
                                output_folder: str, index: int, 
                                brand_config: Dict) -> Dict:
        """
        Process a single HTML string to PNG conversion asynchronously.
        """
        async with self.semaphore:  # Limit concurrent executions
            result = {
                'index': index,
                'success': False,
                'files': [],
                'error': None
            }
            
            # Create unique process folder
            process_folder = os.path.join(output_folder, f"process_{index}")
            os.makedirs(process_folder, exist_ok=True)
            
            # Create temporary HTML file
            temp_html_path = os.path.join(process_folder, f"temp_{uuid.uuid4()}.html")
            
            try:
                # Write HTML content asynchronously
                async with aiofiles.open(temp_html_path, "w", encoding="utf-8") as f:
                    await f.write(html_content)
                
                # Run Selenium operations in thread pool (since Selenium is not async-native)
                result = await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    self._selenium_process,
                    temp_html_path,
                    class_name,
                    output_folder,
                    index,
                    brand_config
                )
                
            except Exception as e:
                result['error'] = str(e)
            
            finally:
                # Clean up temporary files
                try:
                    if os.path.exists(temp_html_path):
                        os.remove(temp_html_path)
                    os.rmdir(process_folder)
                except:
                    pass
            
            return result
    
    def _selenium_process(self, temp_html_path: str, class_name: str,
                         output_folder: str, index: int,
                         brand_config: Dict) -> Dict:
        """
        Handle Selenium operations in a separate thread.
        """
        result = {
            'index': index,
            'success': False,
            'files': [],
            'error': None
        }
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Load the HTML file
            file_url = 'file://' + os.path.abspath(temp_html_path)
            driver.get(file_url)
            
            # Wait for elements
            elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
            )
            
            # Process each element
            for idx, element in enumerate(elements):
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                driver.implicitly_wait(1)
                
                screenshot = element.screenshot_as_base64
                image_data = base64.b64decode(screenshot)
                image = Image.open(io.BytesIO(image_data))
                
                timestamp = int(time.time() * 1000)
                output_path = os.path.join(
                    output_folder,
                    f"{brand_config['user_id']}_{index}_{idx}_{timestamp}.png"
                )
                
                image.save(output_path, 'PNG')
                result['files'].append(output_path)
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            
        finally:
            driver.quit()
        
        return result

async def async_html_to_png(html_list: List[str], class_name: str,
                           output_folder: str = "output_images",
                           brand_config: Dict = None,
                           max_concurrent: int = 5) -> List[Dict]:
    """
    Convert multiple HTML strings to PNG images using async processing.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    processor = ImageProcessor(max_concurrent)
    
    # Create tasks for all HTML files
    tasks = [
        processor.process_single_html(
            html, class_name, output_folder, idx, brand_config
        )
        for idx, html in enumerate(html_list)
    ]
    
    # Run all tasks concurrently
    print(f"Starting async processing with max {max_concurrent} concurrent tasks...")
    results = await asyncio.gather(*tasks)
    
    # Print summary
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    print(f"Processing complete: {successful} successful, {failed} failed")
    
    return results














#from selenium import webdriver
#from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.common.by import By
#from selenium.webdriver.support.ui import WebDriverWait
#from selenium.webdriver.support import expected_conditions as EC
#import time
#import os
#from PIL import Image
#import io
#import base64
#import uuid
#import multiprocessing
#from typing import List, Dict
#from concurrent.futures import ProcessPoolExecutor, as_completed
#
#def process_single_html(args: tuple) -> Dict:
#    """
#    Process a single HTML string to PNG conversion.
#    
#    Parameters:
#    args (tuple): (html_content, class_name, output_folder, index)
#    
#    Returns:
#    dict: Dictionary containing the processing results
#    """
#    html_content, class_name, output_folder, index, brand_config = args
#    user_id =brand_config['user_id']
#    
#    # Create unique subfolder for this process to avoid conflicts
#    process_folder = os.path.join(output_folder, f"process_{index}")
#    os.makedirs(process_folder, exist_ok=True)
#    
#    # Create a temporary HTML file with unique name
#    temp_html_path = os.path.join(process_folder, f"temp_{uuid.uuid4()}.html")
#    with open(temp_html_path, "w", encoding="utf-8") as f:
#        f.write(html_content)
#
#    # Convert local path to file URL
#    file_url = 'file://' + os.path.abspath(temp_html_path)
#    
#    # Configure Chrome options
#    chrome_options = Options()
#    chrome_options.add_argument('--headless')
#    chrome_options.add_argument('--start-maximized')
#    chrome_options.add_argument('--disable-gpu')
#    chrome_options.add_argument('--no-sandbox')
#    
#    # Initialize the driver
#    driver = webdriver.Chrome(options=chrome_options)
#    
#    result = {
#        'index': index,
#        'success': False,
#        'files': [],
#        'error': None
#    }
#    
#    try:
#        # Load the HTML content
#        driver.get(file_url)
#        
#        # Wait for elements with the specified class to be present
#        elements = WebDriverWait(driver, 10).until(
#            EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
#        )
#        
#        # Process each element
#        for idx, element in enumerate(elements):
#            # Scroll element into view
#            driver.execute_script("arguments[0].scrollIntoView(true);", element)
#            
#            # Add a small delay to ensure the element is fully rendered
#            driver.implicitly_wait(1)
#            
#            # Get screenshot as base64
#            screenshot = element.screenshot_as_base64
#            
#            # Convert base64 to image
#            image_data = base64.b64decode(screenshot)
#            image = Image.open(io.BytesIO(image_data))
#            
#            # Generate unique filename
#            timestamp = int(time.time() * 1000)
#            output_path = os.path.join(output_folder, f"{user_id}_{index}_{idx}_{timestamp}.png")
#            
#            # Save the image
#            image.save(output_path, 'PNG')
#            result['files'].append(output_path)
#        
#        result['success'] = True
#            
#    except Exception as e:
#        result['error'] = str(e)
#        
#    finally:
#        driver.quit()
#        # Clean up temporary files
#        if os.path.exists(temp_html_path):
#            os.remove(temp_html_path)
#        # Try to remove the process folder
#        try:
#            os.rmdir(process_folder)
#        except:
#            pass
#    
#    return result
#
#async def parallel_html_to_png(html_list: List[str], class_name: str, output_folder: str = "output_images", max_workers: int = None ,brand_config: Dict = None) -> List[Dict]:
#    """
#    Convert multiple HTML strings to PNG images in parallel.
#    
#    Parameters:
#    html_list (List[str]): List of HTML strings to convert
#    class_name (str): The class name to target in the HTML
#    output_folder (str): Folder to save the PNG files
#    max_workers (int): Maximum number of parallel processes (defaults to CPU count)
#    
#    Returns:
#    List[Dict]: List of dictionaries containing results for each HTML string
#    """
#    if max_workers is None:
#        max_workers = multiprocessing.cpu_count()
#    
#    # Create output directory if it doesn't exist
#    os.makedirs(output_folder, exist_ok=True)
#    
#    # Prepare arguments for parallel processing
#    process_args = [(html, class_name, output_folder, idx, brand_config) for idx, html in enumerate(html_list)]
#    
#    results = []
#    
#    # Use ProcessPoolExecutor for parallel processing
#    with ProcessPoolExecutor(max_workers=max_workers) as executor:
#        # Submit all tasks
#        future_to_idx = {executor.submit(process_single_html, args): args[3] for args in process_args}
#
#        
#        # Process completed tasks
#        for future in as_completed(future_to_idx):
#            idx = future_to_idx[future]
#            try:
#                result = future.result()
#                results.append(result)
#                if result['success']:
#                    print(f"Successfully processed HTML {idx} and generated {len(result['files'])} images")
#                else:
#                    print(f"Failed to process HTML {idx}: {result['error']}")
#            except Exception as e:
#                print(f"Error processing HTML {idx}: {str(e)}")
#                results.append({
#                    'index': idx,
#                    'success': False,
#                    'files': [],
#                    'error': str(e)
#                })
#    
#    # Sort results by original index
#    results.sort(key=lambda x: x['index'])
#    return results