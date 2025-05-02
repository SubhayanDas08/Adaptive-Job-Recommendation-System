import json
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DATABASE_NAME")]
jobs_collection = db.jobs

def import_jobs_from_json(file_path):
    try:
        # Read JSON file
        with open(file_path, 'r', encoding='utf-8') as file:
            jobs_data = json.load(file)
        
        # Insert jobs into MongoDB
        if isinstance(jobs_data, list):
            result = jobs_collection.insert_many(jobs_data)
            print(f"Successfully inserted {len(result.inserted_ids)} jobs")
        else:
            result = jobs_collection.insert_one(jobs_data)
            print(f"Successfully inserted 1 job with ID: {result.inserted_id}")
            
        return True
    
    except Exception as e:
        print(f"Error importing jobs: {str(e)}")
        return False

if __name__ == "__main__":

    json_file_path = "./data/jobs_with_skills_new_checkpoint_8094.json"

    success = import_jobs_from_json(json_file_path)
    
    if success:
        print("Job import completed successfully")
    else:
        print("Job import failed")