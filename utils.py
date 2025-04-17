import os
import shutil
from pathlib import Path
from enum import Enum
import uuid
import time
import hashlib
import random
import json
from typing import List, Dict, Optional, Union
import requests
import logging
from time import sleep
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
from dotenv import load_dotenv

load_dotenv()


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
    
class LlamaAPIClient:
    """
    A simplified client for interacting with the Llama API.
    Handles API calls, retries, and error management in a clean interface.
    """
    def __init__(
        self,
        model_path: str = "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4",
        api_url: str = os.getenv('BASE_URL'), 
        auth_token: str = os.getenv('AUTH_TOKEN'),
        max_retries: int = 3,
        base_delay: float = 1.0
    ):
        self.model_path = model_path
        self.api_url = api_url
        self.auth_token = auth_token
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)

    def _make_request(self, messages: List[Dict[str, str]], max_tokens: int = 4096) -> dict:
        """
        Makes the actual API request with retry logic.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }
        
        data = {
            "model": self.model_path,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "top_p": 0.9,
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    verify=False,
                    timeout=30
                )
                
                if response.status_code in [400, 429]:
                    self.logger.warning(f"Attempt {attempt + 1}: HTTP {response.status_code}")
                    sleep(self.base_delay * (2 ** attempt))  # Exponential backoff
                    continue
                
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                sleep(self.base_delay * (2 ** attempt))
                
        raise Exception("Max retries exceeded")

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response from the model using either a simple string prompt
        or a list of message dictionaries.
        
        Args:
            prompt: Either a string prompt or a list of message dictionaries
            max_tokens: Maximum tokens in the response
            system_prompt: Optional system prompt to prepend
            
        Returns:
            The model's response as a string
        """
        # Convert string prompt to proper message format
        if isinstance(prompt, str):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        try:
            response = self._make_request(messages, max_tokens)
            return response['choices'][0]['message']['content']
        except Exception as e:
            self.logger.error(f"Generation failed: {str(e)}")
            return ""  


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
        for file_name in os.listdir(logos_dir):
            if file_name.startswith(user_id) and file_name.endswith('.svg'):
                file_path = os.path.join(logos_dir, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error during cleanup: {e}")    
    

def handle_logo_upload(uploaded_logo,user_id,time_stamp):
    """
    Handle logo file upload and save to logos directory
    """
    if not uploaded_logo:
        return None
        
    logos_dir = Path('logos')
    logos_dir.mkdir(exist_ok=True)
    
    #timestamp = int(time.time())
    logo_filename = f"{user_id}{time_stamp}logo_.svg"
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
            'level': 'INFO', 
        },
        'loggers': {
            'my_logger': {
                'handlers': ['file', 'console'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'requests': {  
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