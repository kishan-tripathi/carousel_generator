from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
from sklearn.cluster import KMeans
import webcolors
from enum import Enum

class ColorPaletteInput(Enum):
    URL = "url"
    MANUAL = "manual"


def handle_color_palette(input_type: ColorPaletteInput, color_input=None):
    """
    Process color palette based on input type selection
    
    Parameters:
    input_type: ColorPaletteInput enum indicating the type of input
    color_input: Either URL string or list of color strings, depending on input_type
    
    Returns:
    list: List of color codes
    """
    if not color_input:
        return None
        
    if input_type == ColorPaletteInput.URL:
        if isinstance(color_input, str) and color_input.startswith(('http://', 'https://')):
            return extract_colors_from_url(color_input)
        else:
            print("Invalid URL provided for color palette")
            return None
            
    elif input_type == ColorPaletteInput.MANUAL:
        if isinstance(color_input, list) and all(isinstance(color, str) for color in color_input):
            return color_input
        else:
            print("Invalid manual color list provided")
            return None

def extract_colors_from_website(url): 
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        tags = re.findall(r'<([a-zA-Z]+)', driver.page_source)
        unique_tags = list(set(tags))
        color_data = []

        for tag_name in unique_tags:
            try:
                elements = driver.find_elements(By.TAG_NAME, tag_name)
                for element in elements:
                    bg_color = element.value_of_css_property('background-color')
                    if bg_color and bg_color != "rgba(0, 0, 0, 0)": 
                        color_data.append(bg_color)
            except Exception as e:
                print(f"Error processing tag {tag_name}: {e}")

        return color_data

    finally:
        driver.quit()

def convert_to_rgb(color_string):
    match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_string)
    if match:
        return tuple(map(int, match.groups()))
    return None

def find_dominant_colors(color_list, n_colors=5):
    rgb_colors = [convert_to_rgb(color) for color in color_list if convert_to_rgb(color)]
    if not rgb_colors:
        print("No valid colors found for clustering.")
        return []
    try:
        kmeans = KMeans(n_clusters=min(n_colors, len(rgb_colors)), random_state=0, n_init=10)
        kmeans.fit(rgb_colors)
        dominant_colors = kmeans.cluster_centers_.astype(int)
        return [webcolors.rgb_to_hex(tuple(color)) for color in dominant_colors]
    except Exception as e:
        print(f"Error during clustering: {e}")
        return []

def extract_colors_from_url(url):
    extracted_data = extract_colors_from_website(url)

    dominant_colors = find_dominant_colors(extracted_data, n_colors=5)

    return dominant_colors

#colors = extract_colors_from_url("https://aeon.co/essays/why-do-i-let-myself-sabotage-my-own-best-laid-plans")
#print(colors)

#from selenium import webdriver
#from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.common.by import By
#from selenium.webdriver.support.ui import WebDriverWait
#from selenium.webdriver.support import expected_conditions as EC
#import numpy as np
#from sklearn.cluster import KMeans
#import re
#import logging
#import time
#from concurrent.futures import ThreadPoolExecutor
#from functools import lru_cache
#
#class OptimizedColorExtractor:
#    def __init__(self, max_colors=5, timeout=10):  # Reduced default timeout
#        self.max_colors = max_colors
#        self.timeout = timeout
#        self.chrome_options = self._setup_chrome_options()
#        logging.basicConfig(level=logging.WARNING)  # Changed to WARNING level
#        self.logger = logging.getLogger(__name__)
#        
#    @staticmethod
#    def _setup_chrome_options():
#        options = Options()
#        options.add_argument("--headless")
#        options.add_argument("--disable-gpu")
#        options.add_argument("--no-sandbox")
#        options.add_argument("--disable-dev-shm-usage")
#        # Additional performance optimizations
#        options.add_argument("--disable-extensions")
#        options.add_argument("--disable-logging")
#        options.add_argument("--disable-3d-apis")
#        options.add_argument("--disable-images")  # Disable image loading
#        options.page_load_strategy = 'eager'  # Changed to eager loading
#        return options
#
#    @lru_cache(maxsize=1024)
#    def _convert_to_rgb(self, color_string):
#        """Convert color string to RGB tuple with caching"""
#        if not color_string or color_string == 'transparent' or color_string == 'rgba(0, 0, 0, 0)':
#            return None
#            
#        try:
#            match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_string)
#            if match:
#                r, g, b = map(int, match.groups())
#                if (r, g, b) != (0, 0, 0) and (r, g, b) != (255, 255, 255):
#                    return (r, g, b)
#        except Exception:
#            pass
#        return None
#
#    def _process_element(self, element):
#        """Process a single element's colors"""
#        colors = set()
#        try:
#            bg_color = element.value_of_css_property('background-color')
#            color = element.value_of_css_property('color')
#            
#            if bg_color:
#                colors.add(bg_color)
#            if color:
#                colors.add(color)
#        except:
#            pass
#        return colors
#
#    def _extract_element_colors(self, driver):
#        """Extract colors from elements using parallel processing"""
#        colors = set()
#        try:
#            # Optimized selector list
#            selectors = [
#                "div[style]", "span[style]", "a[style]", 
#                "*[class*='bg-']", "*[class*='color-']",
#                "*[style*='background']", "*[style*='color']"
#            ]
#            
#            # Combine all selectors for a single query
#            combined_selector = ', '.join(selectors)
#            elements = driver.find_elements(By.CSS_SELECTOR, combined_selector)
#            
#            # Process elements in parallel
#            with ThreadPoolExecutor(max_workers=4) as executor:
#                element_colors = executor.map(self._process_element, elements)
#                
#            for color_set in element_colors:
#                colors.update(color_set)
#                
#        except Exception as e:
#            self.logger.error(f"Error extracting colors: {e}")
#            
#        return colors
#
#    def _cluster_colors(self, rgb_colors):
#        """Optimized color clustering"""
#        try:
#            if not rgb_colors:
#                return []
#            
#            rgb_array = np.array(rgb_colors)
#            n_colors = min(self.max_colors, len(rgb_colors))
#            
#            # Use mini-batch K-means for faster clustering
#            kmeans = KMeans(
#                n_clusters=n_colors,
#                random_state=42,
#                n_init=5,  # Reduced number of initializations
#                max_iter=100,  # Reduced maximum iterations
#                algorithm='elkan'  # Faster algorithm for lower dimensional data
#            )
#            kmeans.fit(rgb_array)
#            
#            return [f"#{int(r):02x}{int(g):02x}{int(b):02x}" 
#                   for r, g, b in kmeans.cluster_centers_]
#            
#        except Exception as e:
#            self.logger.error(f"Clustering error: {e}")
#            return []
#
#    def extract_colors(self, url):
#        """Main extraction method with timeout handling"""
#        driver = None
#        try:
#            driver = webdriver.Chrome(options=self.chrome_options)
#            driver.set_page_load_timeout(self.timeout)
#            
#            self.logger.info(f"Loading URL: {url}")
#            driver.get(url)
#            
#            # Reduced wait time with specific condition
#            WebDriverWait(driver, self.timeout).until(
#                EC.presence_of_element_located((By.TAG_NAME, "body"))
#            )
#            
#            raw_colors = self._extract_element_colors(driver)
#            rgb_colors = [rgb for color in raw_colors 
#                         if (rgb := self._convert_to_rgb(color))]
#            
#            if not rgb_colors:
#                return []
#                
#            return self._cluster_colors(rgb_colors)
#            
#        except Exception as e:
#            self.logger.error(f"Error in color extraction: {e}")
#            return []
#            
#        finally:
#            if driver:
#                driver.quit()
#
## Usage example
#if __name__ == "__main__":
#    url = "https://aeon.co/essays/why-do-i-let-myself-sabotage-my-own-best-laid-plans"
#    extractor = OptimizedColorExtractor(max_colors=10)
#    
#    start_time = time.time()
#    colors = extractor.extract_colors(url)
#    elapsed = time.time() - start_time
#    
#    print(f"Time taken: {elapsed:.2f} seconds")
#    print("Dominant colors:", colors if colors else "No colors extracted")