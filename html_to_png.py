
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


def local_html_to_png(html_path, class_name, output_folder="output_images"):
    """
    Converts HTML elements with specific class names from a local HTML file to PNG images.

    Parameters:
    html_path (str): Path to the local HTML file
    class_name (str): The class name to target
    output_folder (str): Folder to save the PNG files (default: 'output_images')
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Convert local path to file URL
    file_url = 'file://' + os.path.abspath(html_path)

    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Load the local HTML file
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

            # Save the image with a unique name
            timestamp = int(time.time() * 1000)
            output_path = os.path.join(output_folder, f"{class_name}_{idx}_{timestamp}.png")
            image.save(output_path, 'PNG')
            print(f"Saved: {output_path}")

    except Exception as e:
        print(f"An error occurred while processing {html_path}: {str(e)}")

    finally:
        driver.quit()


# Main execution
if __name__ == "__main__":
    final_output_dir = "final_output9"
    output_folder = "final_images"
    class_name = "container"

    # Ensure the output directory exists
    os.makedirs(output_folder, exist_ok=True)

    # Iterate over all HTML files in the final_output directory
    for file_name in os.listdir(final_output_dir):
        if file_name.endswith('.html'):
            file_path = os.path.join(final_output_dir, file_name)
            print(f"Processing: {file_name}")

            # Convert the HTML to PNG
            try:
                local_html_to_png(file_path, class_name, output_folder)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
