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
    # Configure headless browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Proper headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU for compatibility
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize the Selenium WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)

        # Extract tag names and inline colors
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
    # Extract colors from the website
    extracted_data = extract_colors_from_website(url)

    # Find top dominant colors
    dominant_colors = find_dominant_colors(extracted_data, n_colors=5)

    # Return the list of dominant colors
    return dominant_colors
