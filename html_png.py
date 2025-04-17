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
    
    #def _selenium_process(self, temp_html_path: str, class_name: str,
    #                     output_folder: str, index: int,
    #                     brand_config: Dict) -> Dict:
    #    """
    #    Handle Selenium operations in a separate thread.
    #    """
    #    result = {
    #        'index': index,
    #        'success': False,
    #        'files': [],
    #        'error': None
    #    }
    #    
    #    # Configure Chrome options
    #    chrome_options = Options()
    #    chrome_options.add_argument('--headless')
    #    chrome_options.add_argument('--start-maximized')
    #    chrome_options.add_argument('--disable-gpu')
    #    chrome_options.add_argument('--no-sandbox')
    #    
    #    driver = webdriver.Chrome(options=chrome_options)
    #    
    #    try:
    #        # Load the HTML file
    #        file_url = 'file://' + os.path.abspath(temp_html_path)
    #        driver.get(file_url)
    #        
    #        # Wait for elements
    #        elements = WebDriverWait(driver, 10).until(
    #            EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
    #        )
    #        
    #        # Process each element
    #        for idx, element in enumerate(elements):
    #            driver.execute_script("arguments[0].scrollIntoView(true);", element)
    #            driver.implicitly_wait(1)
    #            
    #            screenshot = element.screenshot_as_base64
    #            image_data = base64.b64decode(screenshot)
    #            image = Image.open(io.BytesIO(image_data))
    #            
    #            timestamp = int(time.time() * 1000)
    #            output_path = os.path.join(
    #                output_folder,
    #                f"{brand_config['user_id']}_{index}_{idx}_{timestamp}.png"
    #            )
    #            
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
    #    
    #    return result

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
    
            # Get user_id and timestamp
            user_id = brand_config['user_id']
            timestamp = brand_config['time_stamp']
    
            # Create subfolder structure for the user and timestamp
            user_dir = os.path.join(output_folder, user_id, f"generation_{timestamp}")
            os.makedirs(user_dir, exist_ok=True)
    
            # Process each element
            for idx, element in enumerate(elements):
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                driver.implicitly_wait(1)
    
                screenshot = element.screenshot_as_base64
                image_data = base64.b64decode(screenshot)
                image = Image.open(io.BytesIO(image_data))
    
                # Save image with timestamp and user-specific folder
                output_path = os.path.join(user_dir, f"{user_id}_{index}_{idx}_{timestamp}.png")
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














