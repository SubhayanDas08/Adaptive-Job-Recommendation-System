from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt
import os
from bson import ObjectId
from langchain import PromptTemplate, LLMChain
from langchain.llms.ollama import Ollama
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from langchain_community.embeddings.ollama import OllamaEmbeddings
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import random
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DATABASE_NAME")]
users_collection = db.users
user_embedding_collection = db.user_embeddings
job_embedding_collection = db.job_embeddings

# Create indexes
db.users.create_index([("email", 1)], unique=True)

# Pydantic models
class Skill(BaseModel):
    skill: str
    influence: int = Field(..., ge=0, le=100)

class ResumeSkills(BaseModel):
    soft_skills: List[Skill]
    hard_skills: List[Skill]

# Ollama setup
output_parser = PydanticOutputParser(pydantic_object=ResumeSkills)
format_instructions = output_parser.get_format_instructions()
escaped_format_instructions = format_instructions.replace("{", "{{").replace("}", "}}")

prompt_template = f"""
You are given resume text extracted from a PDF file. Your task is to extract the soft skills and hard skills mentioned in the resume.
Soft skills include communication, teamwork, adaptability, problem-solving, leadership, emotional intelligence, and time management.
Hard skills include the following:
- Programming and Software Development
- Data Analysis and Statistical Analysis
- Project Management
- Financial Analysis and Forecasting
- Technical Writing and Documentation
- Machine Learning and Artificial Intelligence
- Graphic Design and Visual Communication
- Digital Marketing and SEO/SEM
- Web Development
- Database Management and SQL
- Cybersecurity and Information Security
- IT Networking and Infrastructure Management
- Quality Assurance and Software Testing
- Computer-Aided Design (CAD) and 3D Modeling
- Engineering Design and Simulation
- Scientific Research and Laboratory Skills
- Legal Research and Compliance
- Social Media Management and Analytics
- Content Creation and Copywriting
- Multimedia Production and Video Editing
- Technical Support and Troubleshooting
- Operating Systems Administration
- DevOps and Continuous Integration/Deployment
- Agile and Scrum Methodologies
- Data Visualization
- Business Intelligence and Analytics
- Supply Chain Management and Logistics
- Sales and Negotiation Techniques
- Advanced Excel and Data Modeling
- Statistical Software Proficiency (R, SAS, SPSS)
- Cloud Computing (AWS, Azure, Google Cloud)
- Mobile Application Development
- Robotics and Automation Engineering
- Virtual Reality (VR) and Augmented Reality (AR) Development
- E-commerce Platform Management
- Digital Forensics and Incident Response
- Network Security Monitoring and Penetration Testing
- Biotechnology Techniques and Laboratory Procedures
- Geographic Information Systems (GIS) and Spatial Analysis
- Foreign Language Proficiency
- Medical Diagnosis and Patient Care
- Mechanical Engineering Design and Analysis
- Electronics Engineering and Circuit Design
- Management Consulting and Strategic Advisory

For each skill you extract, assign a percentage influence (from 0 to 100) that reflects how prominently the skill is represented in the resume.
Return the output in JSON format following this schema:
{escaped_format_instructions}

Resume:
{{resume_text}}
"""

skill_template = PromptTemplate(
    input_variables=["resume_text"],
    template=prompt_template,
)

llm = Ollama(model="llama3:8b", temperature=0, base_url="http://localhost:11434")
skill_chain = LLMChain(llm=llm, prompt=skill_template, output_parser=output_parser)

# Password helper functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

# Embedding setup
embedding_function = OllamaEmbeddings(model="mxbai-embed-large")

def extract_embedding(text):
    try:
        if not text.strip():
            return np.array([])
        embedding = embedding_function.embed_documents([text])
        return np.array(embedding[0]) if embedding else np.array([])
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return np.array([])

# Helper function to create/update user embeddings
def create_user_embeddings_helper(user_id):
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None

        combined_text = f"""
        Resume: {user.get('resume', '')}
        Hard Skills: {' '.join([s['skill'] for s in user.get('hard_skills', [])])}
        Soft Skills: {' '.join([s['skill'] for s in user.get('soft_skills', [])])}
        """
        
        embedding = extract_embedding(combined_text)
        if embedding.size == 0:
            return None

        user_embedding_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": {
                "user_id": ObjectId(user_id),
                "embedding": embedding.tolist(),
                "email": user['email']
            }},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Embedding creation error: {e}")
        return False

@app.route('/create-embeddings', methods=['POST'])
def create_user_embeddings():
    try:
        data = request.get_json()
        user_id = data.get('_id')

        if not user_id:
            return jsonify({"error": "Missing user ID"}), 400

        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        combined_text = f"""
        Resume: {user.get('resume', '')}
        Hard Skills: {' '.join([s['skill'] for s in user.get('hard_skills', [])])}
        Soft Skills: {' '.join([s['skill'] for s in user.get('soft_skills', [])])}
        """
        
        embedding = extract_embedding(combined_text)
        if embedding.size == 0:
            return jsonify({"error": "Failed to generate embedding"}), 500

        user_embedding_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": {
                "user_id": ObjectId(user_id),
                "embedding": embedding.tolist(),
                "email": user['email']
            }},
            upsert=True
        )

        return jsonify({"message": "Embeddings created successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-job-recommendations', methods=['POST'])
def get_job_recommendations():
    try:
        data = request.get_json()
        user_id = data.get('_id')
        
        if not user_id:
            return jsonify({"error": "Missing user ID"}), 400

        # Get user embedding
        user_embedding = user_embedding_collection.find_one({"user_id": ObjectId(user_id)})
        if not user_embedding or 'embedding' not in user_embedding:
            return jsonify({"error": "User embeddings not found. Please create embeddings first."}), 404
            
        user_vector = np.array(user_embedding['embedding']).reshape(1, -1)
        
        # Get all job embeddings
        jobs = list(job_embedding_collection.find({}))
        if not jobs:
            return jsonify({"error": "No jobs available"}), 404

        # Calculate similarities for each job
        recommendations = []
        for job in jobs:
            if 'embedding' not in job:
                continue
            job_vector = np.array(job['embedding']).reshape(1, -1)
            similarity = cosine_similarity(user_vector, job_vector)[0][0]
            recommendations.append({
                "job_id": str(job['job_id']),
                "title": job.get('metadata', {}).get('job_title', ''),
                "company": job.get('metadata', {}).get('company_name', ''),
                "location": job.get('metadata', {}).get('location', ''),
                "job_application_link": job.get('metadata', {}).get('url', 'https://www.glassdoor.ie/Community/index.htm'),
                "rating": job.get('metadata', {}).get('rating', None),
                "similarity": similarity
            })

        # Sort recommendations by descending similarity score
        recommendations.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Deduplicate recommendations by job_title
        unique_recs = []
        seen_titles = set()
        for rec in recommendations:
            title = rec.get('title', '').strip()
            if title and title.lower() not in seen_titles:
                unique_recs.append(rec)
                seen_titles.add(title.lower())
            if len(unique_recs) >= 20:
                break

        # If fewer than 20 unique, add more from sorted list
        if len(unique_recs) < 20:
            for rec in recommendations:
                title = rec.get('title', '').strip()
                if title.lower() not in seen_titles:
                    unique_recs.append(rec)
                    seen_titles.add(title.lower())
                if len(unique_recs) >= 20:
                    break

        final_recs = unique_recs[:20]

        # Assign match types based on positions (for display purposes):
        # 0-11: high, 12-17: medium, 18-19: low
        for idx, rec in enumerate(final_recs):
            if idx < 12:
                rec['match_type'] = 'high'
            elif idx < 18:
                rec['match_type'] = 'medium'
            else:
                rec['match_type'] = 'low'
        
        return jsonify({"recommendations": final_recs}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        resume = data.get('resume', '')

        if not all([email, password]):
            return jsonify({"error": "Missing required fields"}), 400

        if users_collection.find_one({"email": email}):
            return jsonify({"error": "User already exists"}), 409

        # Create user without tracking fields as adaptive functionality is removed
        user_data = {
            "email": email,
            "password": hash_password(password),
            "resume": resume,
            "hard_skills": [],
            "soft_skills": []
        }

        result = users_collection.insert_one(user_data)

        return jsonify({
            "message": "User created successfully",
            "id": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/track-application', methods=['POST'])
def track_application():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        job_id = data.get("job_id")
        match_type = data.get("match_type")  # still useful for logging or further processing

        if not all([user_id, job_id]):
            return jsonify({"error": "Missing user_id or job_id"}), 400

        # Record the job application by updating the user's document
        # This pushes the job_id into the "applied_jobs" list
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"applied_jobs": job_id}},
            upsert=True  # In case the field doesn't exist yet
        )

        # Retrieve the current user to check the number of applications
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        applied_jobs = user.get("applied_jobs", [])
        response_message = "Application recorded"

        # Check if the count is a multiple of 3
        if len(applied_jobs) % 3 == 0:
            # Retrieve details for the last 3 applied jobs from the job collection
            last_three_job_ids = applied_jobs[-3:]
            last_three_jobs = []
            for jid in last_three_job_ids:
                # Here we assume that your job data (with required soft and hard skills)
                # resides in the job_embedding_collection and that the job identifier is stored under "job_id"
                job = job_embedding_collection.find_one({"job_id": jid})
                if job:
                    last_three_jobs.append(job)

            if last_three_jobs:
                # Merge/update the user's skills based on the required skills of the last three jobs
                new_soft, new_hard = update_user_skills_from_jobs(user, last_three_jobs)

                # Update the user's soft and hard skills in the database
                users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"soft_skills": new_soft, "hard_skills": new_hard}}
                )
                response_message += ". Your skill set has been updated based on your recent applications."

        return jsonify({"notification": response_message}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def update_user_skills_from_jobs(user, jobs):
    """
    Merge the required skills from a list of job documents with the user's current skills.
    For any matching skill, update its influence as the average of the current influence and the
    job's required influence (capped at 100). New skills are simply added.
    """
    # Convert user's current skills to dictionaries for quick lookup.
    current_soft = {skill['skill']: skill['influence'] for skill in user.get("soft_skills", [])}
    current_hard = {skill['skill']: skill['influence'] for skill in user.get("hard_skills", [])}

    # Process each job's required skills.
    for job in jobs:
        for skill in job.get("soft_skills", []):
            skill_name = skill.get("skill")
            job_influence = skill.get("influence", 0)
            if skill_name in current_soft:
                # Update via a simple averaging rule (or any other logic you prefer)
                current_soft[skill_name] = min(100, int((current_soft[skill_name] + job_influence) / 2))
            else:
                current_soft[skill_name] = job_influence

        for skill in job.get("hard_skills", []):
            skill_name = skill.get("skill")
            job_influence = skill.get("influence", 0)
            if skill_name in current_hard:
                current_hard[skill_name] = min(100, int((current_hard[skill_name] + job_influence) / 2))
            else:
                current_hard[skill_name] = job_influence

    # Convert the dictionaries back to the list of dicts format.
    updated_soft = [{"skill": k, "influence": v} for k, v in current_soft.items()]
    updated_hard = [{"skill": k, "influence": v} for k, v in current_hard.items()]

    return updated_soft, updated_hard


@app.route('/update-skills', methods=['POST'])
def update_skills():
    try:
        data = request.get_json()
        user_id = data.get('_id')

        if not user_id:
            return jsonify({"error": "Missing user ID"}), 400

        try:
            obj_id = ObjectId(user_id)
        except:
            return jsonify({"error": "Invalid user ID format"}), 400

        user = users_collection.find_one({"_id": obj_id})
        if not user:
            return jsonify({"error": "User not found"}), 404

        resume_text = user.get('resume', '')
        if not resume_text:
            return jsonify({"error": "No resume found for this user"}), 400

        try:
            skills = skill_chain.run(resume_text=resume_text)
        except Exception as e:
            return jsonify({"error": f"Skill extraction failed: {str(e)}"}), 500

        update_data = {
            "hard_skills": [{"skill": s.skill, "influence": s.influence} for s in skills.hard_skills],
            "soft_skills": [{"skill": s.skill, "influence": s.influence} for s in skills.soft_skills]
        }

        users_collection.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )

        updated_user = users_collection.find_one({"_id": obj_id})

        return jsonify({
            "message": "Skills updated successfully",
            "user": {
                "email": updated_user['email'],
                "resume": updated_user.get('resume', ''),
                "hard_skills": updated_user.get('hard_skills', []),
                "soft_skills": updated_user.get('soft_skills', [])
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({"error": "Missing credentials"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "User not found"}), 404

        if check_password(user['password'], password):
            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": str(user["_id"]),
                    "email": user['email'],
                    "resume": user.get('resume', ''),
                    "hard_skills": user.get('hard_skills', []),
                    "soft_skills": user.get('soft_skills', [])
                }
            }), 200
            
        return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
