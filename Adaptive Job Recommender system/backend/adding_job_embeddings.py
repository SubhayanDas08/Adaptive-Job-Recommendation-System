import pymongo
import numpy as np
from langchain_community.embeddings.ollama import OllamaEmbeddings
from pymongo import UpdateOne
import os
from dotenv import load_dotenv
from bson import ObjectId
from tqdm import tqdm  # for the progress bar

# Load environment variables
load_dotenv()

# MongoDB setup
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DATABASE_NAME")]

# Collections
job_collection = db.jobs
embedding_collection = db.job_embeddings

# Ollama model for generating embeddings
def get_embedding_function():
    """Returns the embedding function for vector storage."""
    return OllamaEmbeddings(model="mxbai-embed-large")

# Initialize embedding function
embedding_function = get_embedding_function()

def extract_embedding(text):
    """Generate embedding for combined job text."""
    try:
        if not text.strip():
            return np.array([])
            
        embedding = embedding_function.embed_documents([text])
        return np.array(embedding[0]) if embedding else np.array([])
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return np.array([])

def create_job_embedding(job):
    """Create embedding for a job document."""
    try:
        # Validate required fields
        if not all(key in job for key in ['job_title', 'job_overview']):
            print(f"Skipping job {job.get('_id', '')} - missing required fields")
            return None

        # Combine all relevant text fields
        combined_text = f"""
        Job Title: {job['job_title']}
        Overview: {job['job_overview']}
        Hard Skills: {' '.join([skill['skill'] for skill in job.get('hard_skills', [])])}
        Soft Skills: {' '.join([skill['skill'] for skill in job.get('soft_skills', [])])}
        Company: {job.get('company_name', '')}
        Industry: {job.get('company_industry', '')}
        """

        # Generate single embedding for combined text
        job_embedding = extract_embedding(combined_text)
        if job_embedding.size == 0:
            return None

        # Prepare embedding document
        return {
            "job_id": job["_id"],
            "embedding": job_embedding.tolist(),
            "metadata": {
                "url": job.get("url", ""),
                "company_name": job.get("company_name", ""),
                "job_title": job["job_title"],
                "location": job.get("job_location", ""),
                "rating": job.get("company_rating", None),
                "industry": job.get("company_industry", ""),
                "size": job.get("company_size", ""),
                "type": job.get("company_type", ""),
            }
        }

    except Exception as e:
        print(f"Error processing job {job.get('_id', '')}: {e}")
        return None

def generate_and_store_job_embeddings():
    """Process each job individually and store embeddings right away."""
    try:
        total_jobs = job_collection.count_documents({})
        print(f"Processing {total_jobs} jobs...")

        cursor = job_collection.find({})

        # Use tqdm for a progress bar
        with tqdm(total=total_jobs, desc="Generating Embeddings") as pbar:
            for job in cursor:
                embedding_doc = create_job_embedding(job)
                if embedding_doc:
                    # Insert/update immediately (no batching)
                    embedding_collection.update_one(
                        {"job_id": job["_id"]},
                        {"$set": embedding_doc},
                        upsert=True
                    )
                pbar.update(1)

        print("Embedding generation completed successfully")

    except Exception as e:
        print(f"Fatal error in embedding generation: {e}")

if __name__ == "__main__":
    generate_and_store_job_embeddings()
