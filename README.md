🤖 TalentScout Hiring Assistant Chatbot
Project Overview
The TalentScout Hiring Assistant is an intelligent chatbot designed to automate the initial screening phase for technical candidates at the fictional TalentScout recruitment agency. Leveraging the power of Large Language Models (LLMs), the chatbot efficiently gathers essential candidate data and dynamically generates a preliminary technical assessment based on the candidate's declared tech stack.

Goal: Streamline the recruitment workflow, reduce manual screening time for recruiters, and ensure a professional, consistent candidate experience.

Installation Instructions
Prerequisites
Python 3.8+

Streamlit

Requests (for API calls)

Setup Steps
Clone the Repository:

This step retrieves the entire project repository, including the core application file (talent_scout_assistant.py) and all folders (e.g., the local .git folder) and custom components like pri-cpu.

git clone [your_git_repository_link]
cd talent-scout-hiring-assistant



Create a Virtual Environment (Recommended):

python -m venv venv
source venv/bin/activate  # On Windows, use `. venv\Scripts\activate`



Install Dependencies:

pip install streamlit requests



Run the Application Locally:

streamlit run talent_scout_assistant.py



This command will open the application in your default web browser (usually at http://localhost:8501).

Usage Guide
The chatbot follows a structured, sequential conversational flow:

Greeting: The assistant introduces itself and asks for the Full Name.

Information Gathering: The candidate is prompted for their Email, Phone Number, Years of Experience, Desired Position(s), and Current Location.

Tech Stack Declaration: The candidate is asked to list their core technologies (e.g., Python, AWS, React, SQL).

Technical Screening: The LLM dynamically generates three tailored, open-ended questions based on the declared tech stack. The candidate responds to each question sequentially.

Conclusion: The chatbot provides a final summary and sets expectations for follow-up from a human recruiter.

To End the Conversation Early: The candidate can use conversation-ending keywords like "goodbye," "exit," or "thank you" at any point.

Technical Details
Libraries Used
Library

Purpose

streamlit

Frontend UI development and session state management.

requests

Handling secure, synchronous HTTP POST requests to the Gemini API.

json

Parsing and constructing API payloads and responses.

time

Implementing exponential backoff logic for API reliability.

Model Details
Model: gemini-2.5-flash-preview-05-20

Function: Used for text generation, dynamic question generation, and technical answer evaluation.

Architectural Decisions
State Management:

Streamlit st.session_state is used to maintain the entire conversational context, track the current step, store candidate_data, and hold the tech_questions and candidate_results. This is crucial for a single-session, multi-stage interaction.

LLM Utility:

A robust function, call_gemini_api_with_backoff, is implemented to handle API calls. This includes exponential backoff and retries to ensure resilience against temporary network or rate-limiting issues.

Firebase Integration:

Mandatory environment variables (__app_id, __firebase_config, __initial_auth_token) are included and processed. Placeholder functions for Firebase initialization and a path constructor for secure data storage (/artifacts/{appId}/users/{userId}/candidate_profiles/initial_screening) are defined, satisfying the platform's requirements for secure data handling, even though the primary demonstration uses session state.

Prompt Design
Effective prompt engineering is central to this project's intelligence.

Phase

Prompt Strategy

Purpose

System Instruction

Defines the professional, friendly, and concise persona of the "TalentScout Hiring Assistant."

Ensures consistent tone and adherence to the core task (screening).

Information Gathering

Simple, sequential questions (e.g., "What is your Full Name?").

Guarantees all six critical data points are collected systematically.

Technical Question Generation

Dynamic Prompt: Inserts the candidate's exact tech stack into the prompt (get_question_generation_prompt(tech_stack)). Instructs the LLM to generate exactly 3 open-ended, practical questions.

Generates relevant, non-trivial questions to assess real-world proficiency.

Answer Evaluation

Evaluation Prompt: Inserts both the question and the candidate's answer. Instructs the LLM to provide a concise summary and assign a formal Proficiency Rating (e.g., 'Excellent', 'Good').

Ensures objective, structured assessment of technical responses for recruiter review.

Fallback/Context

The fallback logic instructs the LLM to politely redirect the user back to the required input for the current step.

Maintains conversation coherence and prevents deviation from the screening purpose.

Challenges & Solutions
Challenge

Solution

Maintaining Context Across Steps

Used st.session_state to store conversation history and explicitly passed the history to the LLM utility function, enabling context-aware responses and follow-ups.

Ensuring LLM Reliability

Implemented call_gemini_api_with_backoff with retry logic to handle transient API errors, ensuring the screening process is robust.

Dynamic Question Relevance

Carefully crafted the get_question_generation_prompt to be highly specific, forcing the LLM to focus on practical, open-ended questions for the provided tech stack, rather than generic knowledge checks.

Data Privacy & Compliance

Integrated the required Firebase setup for secure pathing and included clear documentation and warnings on the UI, emphasizing that in a production environment, sensitive data must be encrypted and stored securely (meeting GDPR/privacy requirements).

Candidate Profile & Technical Results Example
All candidate inputs and LLM-generated technical assessments are logged in the sidebar for demonstration purposes. This log simulates the data that would be saved to a secure database for a human recruiter to review.
