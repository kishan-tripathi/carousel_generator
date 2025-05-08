import os
import json
from pymongo import MongoClient

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")  
db = client['layouts_database']

template_specs_file = "template_specifications.json" 
with open(template_specs_file, "r", encoding="utf-8") as f:
    template_specs = json.load(f)

base_dir = r"C:\Users\Abbas Rizvi\Desktop\buxa ai content\carousalbackend\carousal\carousel_generator"

for main_dir in ["layouts_it", "layouts_lit", "layouts_lt", "layouts_t"]:
    collection = db[main_dir]  
    print(f"Using collection: {main_dir}")
    
    main_dir_path = os.path.join(base_dir, main_dir)
   
    for layout in os.listdir(main_dir_path):
        layout_path = os.path.join(main_dir_path, layout)
        if os.path.isdir(layout_path):
            layout_data = {"layout": layout, "files": []}
            for html_file in os.listdir(layout_path):
                file_path = os.path.join(layout_path, html_file)
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                image_height = template_specs.get(html_file, {}).get("image_height")
                image_width = template_specs.get(html_file, {}).get("image_width")

                file_data = {"file_name": html_file, "content": content}
                if image_height and image_width:
                    file_data["image_height"] = image_height
                    file_data["image_width"] = image_width
                
                layout_data["files"].append(file_data)
            
            try:
                result = collection.insert_one(layout_data)
                print(f"Inserted layout data for {layout} with id: {result.inserted_id}")
            except Exception as e:
                print(f"Error inserting data into {main_dir}: {e}")

print("layouts stored in MongoDB successfully.")






#import os
#from pymongo import MongoClient
#
## MongoDB setup
#client = MongoClient("mongodb://localhost:27017/")  # Update with your MongoDB URI if needed
#db = client['layouts_database']
#
## Base directory (update this to the path where your layout directories are stored)
#base_dir = "C:\\Users\\shash\\OneDrive\\Documents\\Carousel_generator"
#
## Loop through each main layout directory
#for main_dir in ["layouts_it", "layouts_lit", "layouts_lt", "layouts_t"]:
#    collection = db[main_dir]  # Create a collection for each main directory
#    print(collection)
#    
#    # Path to the main directory
#    main_dir_path = os.path.join(base_dir, main_dir)
#    
#    # Loop through each layout subdirectory
#    for layout in os.listdir(main_dir_path):
#        layout_path = os.path.join(main_dir_path, layout)
#        if os.path.isdir(layout_path):
#            layout_data = {"layout": layout, "files": []}
#            
#            # Loop through HTML files in the subdirectory
#            for html_file in os.listdir(layout_path):
#                file_path = os.path.join(layout_path, html_file)
#                
#                # Read the content of the HTML file
#                with open(file_path, 'r', encoding='utf-8') as file:
#                    content = file.read()
#                
#                # Add the file's name and content to the layout data
#                layout_data["files"].append({"file_name": html_file, "content": content})
#            
#            try:
#                # Insert the layout data into the collection
#                result = collection.insert_one(layout_data)
#                print(f"Inserted layout data with id: {result.inserted_id}")  # Print the inserted ID
#            except Exception as e:
#                print(f"Error inserting data into {main_dir}: {e}")  # Print any errors
#
#print("Layouts have been stored in MongoDB successfully.")
#