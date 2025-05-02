#!/usr/bin/env python3
from pymongo import MongoClient
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Replace with your actual MongoDB connection string and database name
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DATABASE_NAME")
    

    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[db_name]
        print("Connected to MongoDB.")
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        sys.exit(1)
    
    # Define the collections
    job_embeddings_collection = db['job_embeddings']
    jobs_collection = db['jobs']

    # Retrieve distinct job IDs from the job_embeddings collection
    try:
        job_ids_with_embeddings = job_embeddings_collection.distinct("job_id")
        print(f"Found {len(job_ids_with_embeddings)} job embeddings corresponding to jobs.")
    except Exception as e:
        print(f"Error retrieving job_ids: {e}")
        client.close()
        sys.exit(1)
    
    # Count the jobs that do not have a corresponding embedding
    try:
        jobs_to_remove_count = jobs_collection.count_documents({"_id": {"$nin": job_ids_with_embeddings}})
        print(f"Jobs to be removed (without embeddings): {jobs_to_remove_count}")
    except Exception as e:
        print(f"Error counting jobs to remove: {e}")
        client.close()
        sys.exit(1)
    
    # Request user confirmation before deletion
    confirm = input("Do you want to proceed with deletion? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Deletion aborted by user.")
        client.close()
        return

    # Delete jobs without embeddings
    try:
        result = jobs_collection.delete_many({"_id": {"$nin": job_ids_with_embeddings}})
        print(f"Deletion complete. {result.deleted_count} job(s) removed.")
    except Exception as e:
        print(f"Error deleting jobs: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
