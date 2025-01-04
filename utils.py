import os
import shutil
from pathlib import Path
from enum import Enum
import uuid
import time
import hashlib
import random
import json
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from sklearn.cluster import KMeans
import numpy as np
import webcolors
import logging
import logging.config



class ColorPaletteInput(Enum):
    URL = "url"
    MANUAL = "manual"

class UserIDGenerator:
    def __init__(self):
        self._counter = 0
    
    def generate_uuid(self):
        """Generate a UUID-based user ID"""
        return str(uuid.uuid4())
    
    def generate_timestamp_based(self):
        """Generate a timestamp-based user ID with counter to ensure uniqueness"""
        self._counter += 1
        timestamp = int(time.time() * 1000)  # millisecond timestamp
        return f"user_{timestamp}_{self._counter}"
    
    def generate_hash_based(self):
        """Generate a hash-based user ID using timestamp and random number"""
        timestamp = str(time.time())
        random_num = str(random.randint(1, 1000000))
        combined = (timestamp + random_num).encode('utf-8')
        return hashlib.sha256(combined).hexdigest()[:16]      

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



def cleanup_files(images_dir, logos_dir, user_id):
    """
    Deletes all images in the images directory and
    SVG files in the logos directory that start with the user_id.

    Parameters:
    images_dir (str): Path to the images directory.
    logos_dir (str): Path to the logos directory.
    user_id (str): User ID to match SVG files for deletion.
    """
    try:
        # Delete all files in the images directory
        for file_name in os.listdir(images_dir):
            file_path = os.path.join(images_dir, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")

        # Delete SVG files in the logos directory that start with the user_id
        for file_name in os.listdir(logos_dir):
            if file_name.startswith(user_id) and file_name.endswith('.svg'):
                file_path = os.path.join(logos_dir, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error during cleanup: {e}")    
    

def handle_logo_upload(uploaded_logo,user_id):
    """
    Handle logo file upload and save to logos directory
    """
    if not uploaded_logo:
        return None
        
    logos_dir = Path('logos')
    logos_dir.mkdir(exist_ok=True)
    
    #timestamp = int(time.time())
    logo_filename = f"{user_id}logo_.svg"
    logo_path = os.path.abspath(logos_dir / logo_filename)
    
    try:
        with open(logo_path, 'wb') as f:
            if hasattr(uploaded_logo, 'read'):
                shutil.copyfileobj(uploaded_logo, f)
            else:
                shutil.copy(uploaded_logo, logo_path)
        return str(logo_path)
    except Exception as e:
        print(f"Error saving logo: {e}")
        return None
    

def convert_txt_to_html_string(input_text: str) -> str:
    """
    Convert a string containing HTML content from .txt format to .html format.

    Parameters:
        input_text (str): String input containing HTML content.

    Returns:
        str: Extracted HTML content if valid tags are found, else an empty string.
    """
    try:
        # Extract the content between <!DOCTYPE html> or <!doctype html> and </html>
        start_tags = ["<!DOCTYPE html>", "<!doctype html>"]
        end_tag = "</html>".lower()

        start_index = -1
        for tag in start_tags:
            start_index = input_text.lower().find(tag.lower())
            if start_index != -1:
                break

        end_index = input_text.lower().find(end_tag) + len(end_tag)

        if start_index != -1 and end_index != -1:
            html_content = input_text[start_index:end_index]
            return html_content
        else:
            raise ValueError("HTML tags not found in the input text.")
    except Exception as e:
        print(f"An error occurred: {e}")
        return "" 


def extract_colors_from_website(url):
    # Configure headless browser
    chrome_options = Options()
    chrome_options.headless = True

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
        kmeans.fit(rgb_colors)  # Fit the model to the color data
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

def setup_logging(user_id):
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'carousel1_{user_id}_{int(time.time())}.log')
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'formatter': 'detailed',
                'level': 'DEBUG',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
            },
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'level': 'INFO',
            },
        },
        'root': {
            'handlers': ['file', 'console'],
            'level': 'INFO',  # Adjusted to reduce noise
        },
        'loggers': {
            'my_logger': {
                'handlers': ['file', 'console'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'requests': {  # Silencing specific libraries
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'urllib3': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False,
            },
        }
    }

    logging.config.dictConfig(logging_config)