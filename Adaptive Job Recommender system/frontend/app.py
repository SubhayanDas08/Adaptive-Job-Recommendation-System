import streamlit as st
import requests
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import json  # Add import at the top of your file instead for better practice
import streamlit.components.v1 as components

load_dotenv()  # Load environment variables

# Configure API URL (should point to your Flask backend)
API_URL = os.getenv("API_URL", "http://localhost:5000")

def dashboard_page():
    """Dashboard after login"""
    st.title("Dashboard")
    
    if 'user' not in st.session_state:
        st.error("Please login first")
        return
    
    user_data = st.session_state.user
    
    tab1, tab2, tab3 = st.tabs(["Evaluate Skills", "My Resume", "Job Recommendations"])
    
    with tab1:
        st.header("Skill Evaluation")
        if st.button("Evaluate My Skills"):
            with st.spinner("Analyzing your resume..."):
                try:
                    response = requests.post(
                        f"{API_URL}/update-skills",
                        json={"_id": user_data.get('id')}
                    )
                    if response.status_code == 200:
                        st.session_state.user = response.json().get('user')
                        st.success("Skills updated successfully!")
                        st.experimental_rerun()
                    else:
                        st.error(f"Error: {response.json().get('error')}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
    
    with tab2:
        st.header("My Resume Profile")
        display_user_profile(st.session_state.user)
        
    with tab3:
        job_recommendations_page()

def job_recommendations_page():
    """Display job recommendations"""
    st.header("Job Recommendations")
    
    if 'user' not in st.session_state:
        st.error("Please login first")
        return
    
    # Layout columns for header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### Personalized Job Matches")
        st.write("Get recommendations based on your skills and experience")
    with col2:
        if st.button("🔄 Refresh Recommendations"):
            st.session_state.recommendations = None
    
    # Fetch recommendations if not already available
    if st.button("Get Recommendations") or 'recommendations' in st.session_state:
        with st.spinner("Finding the best matches for you..."):
            try:
                response = requests.post(
                    f"{API_URL}/get-job-recommendations",
                    json={"_id": st.session_state.user['id']}
                )
                if response.status_code == 200:
                    st.session_state.recommendations = response.json().get('recommendations', [])
                else:
                    st.error(f"Error: {response.json().get('error')}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")
    
    if 'recommendations' in st.session_state and st.session_state.recommendations:
        display_job_recommendations()
    else:
        st.info("Click 'Get Recommendations' to see personalized job matches")

def display_job_recommendations():
    """Display job cards and open job site on Apply Now"""
    for job in st.session_state.recommendations:
        with st.expander(f"{job['title']} - {job['company']}", expanded=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                match_type = job.get('match_type', 'low').lower()
                if match_type == 'high':
                    st.markdown("**Match:** 🌟🌟🌟 Excellent Fit")
                elif match_type == 'medium':
                    st.markdown("**Match:** 🌟🌟 Good Fit")
                else:
                    st.markdown("**Match:** 🌟 Potential Fit")
                
                st.markdown(f"**Location:** {job.get('location', 'Not specified')}")
                
            with col2:
                if job.get('rating'):
                    st.markdown(f"**Rating:** {job['rating']}/5")
                
                if st.button("Apply Now", key=f"apply_{job['job_id']}"):
                    try:
                        response = requests.post(
                            f"{API_URL}/track-application",
                            json={
                                "user_id": st.session_state.user['id'],
                                "job_id": job['job_id'],
                                "match_type": job['match_type']
                            }
                        )
                        if response.status_code == 200:
                            res_data = response.json()
                            st.success(res_data.get('notification', 'Application recorded!'))
                            # The notification now can include a message about the skills update.
                            job_link = job.get('job_application_link')
                            if job_link:
                                js = f"""
                                <script>
                                    window.open({json.dumps(job_link)}, "_blank");
                                </script>
                                """
                                components.html(js, height=0)
                        else:
                            st.error("Failed to record application")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")



def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def registration_form():
    """Display registration form"""
    st.title("Registration Form")
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password")
        with col2:
            resume_pdf = st.file_uploader("Upload Resume (PDF)", type="pdf")
        submitted = st.form_submit_button("Register")
        
        if submitted:
            if not all([email, password, resume_pdf]):
                st.error("Please fill all fields")
                return
            resume_text = extract_text_from_pdf(resume_pdf)
            if not resume_text:
                return
            data = {
                "email": email,
                "password": password,
                "resume": resume_text
            }
            try:
                response = requests.post(
                    f"{API_URL}/register",
                    json=data
                )
                if response.status_code == 201:
                    user_id = response.json().get("id")
                    update_skills(user_id)
                    st.success("Registration successful! Skills extracted.")
                    st.markdown("[Proceed to Login](#login)")
                else:
                    st.error(f"Registration failed: {response.json().get('error')}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

def update_skills(user_id):
    """Trigger skills update for new user"""
    try:
        response = requests.post(
            f"{API_URL}/update-skills",
            json={"_id": user_id}
        )
        if response.status_code != 200:
            st.warning("Registration succeeded but skills extraction failed")
    except Exception as e:
        st.warning("Skills update failed - try manually later")

def login_page():
    """Login form"""
    st.title("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    
    if st.button("Login"):
        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                user_data = response.json().get("user")
                user_data['id'] = response.json().get("user", {}).get("id")
                st.session_state.user = user_data
                st.experimental_rerun()
            else:
                st.error(response.json().get("error"))
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

def display_user_profile(user_data):
    """Display user profile in My Resume tab"""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Hard Skills")
        if not user_data.get('hard_skills'):
            st.info("No hard skills analyzed yet")
        else:
            for skill in user_data.get("hard_skills", []):
                if isinstance(skill, dict):
                    st.write(f"- {skill['skill']} ({skill['influence']}%)")
                else:
                    st.write(f"- {skill}")
    with col2:
        st.markdown("### Soft Skills")
        if not user_data.get('soft_skills'):
            st.info("No soft skills analyzed yet")
        else:
            for skill in user_data.get("soft_skills", []):
                if isinstance(skill, dict):
                    st.write(f"- {skill['skill']} ({skill['influence']}%)")
                else:
                    st.write(f"- {skill}")
    st.markdown("### Resume Text")
    st.text_area("Resume Content", value=user_data.get("resume", ""), height=300, disabled=True)
    st.markdown("---")
    if st.button("Create User Embeddings"):
        with st.spinner("Generating embeddings..."):
            try:
                response = requests.post(
                    f"{API_URL}/create-embeddings",
                    json={"_id": user_data.get('id')}
                )
                if response.status_code == 200:
                    st.success("Embeddings created successfully!")
                else:
                    st.error(f"Error: {response.json().get('error')}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

def main():
    """Main app flow"""
    st.set_page_config(
        page_title="Career Assistant",
        page_icon="💼",
        layout="wide"
    )
    if 'user' in st.session_state:
        dashboard_page()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Register", "Login"])
        if page == "Register":
            registration_form()
        elif page == "Login":
            login_page()

if __name__ == '__main__':
    main()
