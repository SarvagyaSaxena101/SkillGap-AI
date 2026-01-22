import streamlit as st
import PyPDF2
import docx2txt
import os
from groq import Groq
import re
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# Function to parse resume
def parse_resume(file):
    if file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return docx2txt.process(file)
    elif file.type == "text/plain":
        return file.getvalue().decode("utf-8")
    return None

# Function to generate learning plan using Groq API
def generate_learning_plan(goal, current_skills, resume_text, time_availability, groq_api_key, completed_topics):
    client = Groq(api_key=groq_api_key)
    
    completed_topics_str = ", ".join(completed_topics)
    prompt = f"""
    You are an expert career coach and learning planner.
    Your task is to create a personalized weekly learning plan for a user with a specific career goal.
    The user has already completed the following topics: {completed_topics_str}.
    Do not include the completed topics in the new plan.

    User's Goal: {goal}
    User's Current Skills:
    {current_skills}
    User's Resume:
    {resume_text}
    Time Commitment: {time_availability} hours/week

    Instructions:
    1.  **Analyze the user's goal, current skills, and resume to identify the skill gaps.**
    2.  **Generate a week-by-week learning plan to bridge these gaps.**
    3.  **The plan should be realistic given the user's time commitment.**
    4.  **Provide specific resources (e.g., online courses, books, projects) for each topic.**
    5.  **The output should be in a structured format, with each week's plan as a separate section.**
    6.  **Each week should have a 'Topic', 'Resources', and 'Weekly Goal'.**
    7.  **Start each week with '### Week' followed by the week number.**

    Example Output:
    ### Week 1: Foundational Skills
    *   **Topic:** Python Programming
    *   **Resources:**
        *   Coursera: Python for Everybody
        *   Book: "Automate the Boring Stuff with Python"
    *   **Weekly Goal:** Complete the first 5 chapters of the book and the first 2 weeks of the course.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    
    plan_text = chat_completion.choices[0].message.content
    
    # Parse the plan_text into a structured format
    plan = []
    weeks = re.split(r'### Week ', plan_text)[1:]
    for i, week_content in enumerate(weeks):
        week_data = {'week': i + 1}
        lines = week_content.split('\n')
        week_data['title'] = lines[0].strip()
        
        for line in lines[1:]:
            if '*   **Topic:**' in line:
                week_data['topic'] = line.split('**Topic:**')[1].strip()
            elif '*   **Resources:**' in line:
                week_data['resources'] = []
            elif '*   **Weekly Goal:**' in line:
                week_data['goal'] = line.split('**Weekly Goal:**')[1].strip()
            elif week_data.get('resources') is not None and '*   ' in line:
                week_data['resources'].append(line.split('*   ')[1].strip())
        plan.append(week_data)
        
    return plan


def main():
    st.title("SkillGap AI: From Goal to Weekly Learning Plan")

    # Initialize session state
    if 'learning_plan' not in st.session_state:
        st.session_state.learning_plan = None
    if 'completed_topics' not in st.session_state:
        st.session_state.completed_topics = []

    # User inputs
    st.header("Your Information")
    goal = st.text_input("Your Goal (e.g., 'ML Engineer at FAANG')")
    time_availability = st.slider("How many hours can you commit per week?", 1, 40, 10)
    
    # Groq API Key
    groq_api_key = os.getenv("GROQ_API_KEY")

    current_skills = st.text_area("Your Current Skills (one per line)")

    # Resume upload
    st.header("Upload Your Resume")
    resume = st.file_uploader("Upload your resume (PDF, TXT, or DOCX)", type=["pdf", "txt", "docx"])

    if st.button("Generate Learning Plan"):
        if goal and current_skills and resume:
            with st.spinner("Generating your personalized learning plan..."):
                resume_text = parse_resume(resume)
                if resume_text:
                    st.session_state.learning_plan = generate_learning_plan(goal, current_skills, resume_text, time_availability, groq_api_key, st.session_state.completed_topics)
                    st.success("Learning plan generated successfully!")
                else:
                    st.error("Could not parse the resume. Please try a different file format.")
        else:
            st.error("Please fill in all the fields and upload your resume.")

    if st.session_state.learning_plan:
        st.header("Your Weekly Learning Plan")
        for week in st.session_state.learning_plan:
            st.subheader(f"Week {week['week']}: {week['title']}")
            if 'topic' in week:
                completed = st.checkbox(f"Mark as completed: {week['topic']}", key=f"week_{week['week']}_{week['topic']}")
                if completed and week['topic'] not in st.session_state.completed_topics:
                    st.session_state.completed_topics.append(week['topic'])
                
                st.write(f"**Topic:** {week['topic']}")
            if 'resources' in week:
                st.write("**Resources:**")
                for resource in week['resources']:
                    st.write(f"*   {resource}")
            if 'goal' in week:
                st.write(f"**Weekly Goal:** {week['goal']}")

        if st.button("Regenerate Plan Based on Progress"):
            with st.spinner("Regenerating your learning plan..."):
                st.session_state.learning_plan = generate_learning_plan(goal, current_skills, "", time_availability, groq_api_key, st.session_state.completed_topics)
                st.success("Learning plan regenerated successfully!")


if __name__ == "__main__":
    main()
