import streamlit as st
import requests
import json
import time
from typing import Dict, Any, List

# --- 1. FIREBASE CONFIGURATION & INITIALIZATION (Mandatory Setup) ---

# Global variables provided by the Canvas environment
__app_id = "talent-scout-hiring-assistant"
__firebase_config = '{}' # Placeholder for config
__initial_auth_token = None

# Using global constants for the Firebase environment variables
APP_ID = __app_id
FIREBASE_CONFIG = json.loads(__firebase_config)
INITIAL_AUTH_TOKEN = __initial_auth_token

# Firebase Imports (simulated as we cannot import external JS modules directly in python)
# In a real environment, you would use these imports:
# from firebase_admin import initialize_app, credentials, firestore
# In this environment, we'll use a placeholder function.

def initialize_firebase_placeholder():
    """
    Placeholder for mandatory Firebase initialization.
    In a true Python environment, this would set up Firestore and Auth.
    """
    try:
        if FIREBASE_CONFIG:
            # Simulate initial connection log
            # For demonstration, we just return a status
            return {"status": "initialized", "db": f"firestore-db-{APP_ID}"}
        else:
            return {"status": "uninitialized", "error": "Firebase config missing."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Initialize Firebase placeholder
FIREBASE_STATUS = initialize_firebase_placeholder()

# Firestore path construction (as required)
def get_candidate_data_path(user_id):
    """Returns the Firestore path for private candidate data."""
    # Note: We are using a simulated user_id in this demo, which is the session ID.
    return f"/artifacts/{APP_ID}/users/{user_id}/candidate_profiles/initial_screening"

# --- 2. GEMINI API UTILITY FUNCTIONS ---

# Use the recommended model for text generation
MODEL_NAME = "gemini-2.5-flash-preview-05-20"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
API_KEY = "" # The key is injected by the environment

def call_gemini_api_with_backoff(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles LLM API call with exponential backoff for reliability."""
    max_retries = 5
    initial_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            headers = {'Content-Type': 'application/json'}
            # The API key is injected by the Canvas environment if not explicitly set
            response = requests.post(f"{API_URL}?key={API_KEY}", headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            # Check for specific API error codes related to rate limiting
            if response.status_code in [429, 500, 503]:
                raise requests.exceptions.RequestException(f"Retriable error: {response.status_code}")

            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                # print(f"API call failed ({e}). Retrying in {delay}s...") # Suppressed console log
                time.sleep(delay)
            else:
                st.error(f"Error communicating with the AI service after {max_retries} attempts. Please try again later. Details: {e}")
                raise

def generate_content(user_query: str, system_prompt: str, history: List[Dict[str, Any]] = None, use_search: bool = False) -> str:
    """Constructs payload and calls the Gemini API."""
    
    # Initialize chat history if not provided
    if history is None:
        history = []
    
    # Append current user query
    history.append({"role": "user", "parts": [{"text": user_query}]})
    
    payload = {
        "contents": history,
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "config": {
            "temperature": 0.4 # Use a moderate temperature for professional, focused responses
        }
    }
    
    if use_search:
        payload["tools"] = [{"google_search": {}}]

    try:
        response_json = call_gemini_api_with_backoff(payload)
        
        # Extract the text content from the response
        # Using .get for safe dictionary access
        candidate = response_json.get('candidates', [{}])[0]
        generated_text = candidate.get('content', {}).get('parts', [{}])[0].get('text', 'Error: Could not retrieve response text.')
        
        # Add the assistant's response to the history for context maintenance
        history.append({"role": "assistant", "parts": [{"text": generated_text}]})
        
        return generated_text

    except Exception as e:
        return f"An internal error occurred during AI processing: {e}"


# --- 3. CHATBOT STATE MANAGEMENT AND PROMPTS ---

# Define the conversational steps and the prompt to guide the LLM for that step
CONVERSATION_STEPS = {
    0: {"prompt": "Welcome! I'm the TalentScout Hiring Assistant. I'll guide you through a quick initial screening. To start, what is your **Full Name**?", "key": "full_name"},
    1: {"prompt": "Great, thanks, {full_name}. What is your **Email Address** for our records?", "key": "email"},
    2: {"prompt": "And what is your primary **Phone Number**?", "key": "phone"},
    3: {"prompt": "How many **Years of Professional Experience** do you have in the tech industry? (e.g., 5 years)", "key": "years_of_experience"},
    4: {"prompt": "What **Desired Position(s)** are you currently seeking? (e.g., Senior Frontend Developer, Data Scientist)", "key": "desired_position"},
    5: {"prompt": "What is your **Current Location** (City, State/Country)?", "key": "location"},
    6: {"prompt": "Thank you for that information. Now, please list your primary **Tech Stack**. Include programming languages, frameworks, databases, and tools you are proficient in (e.g., Python, React, SQL, AWS, Docker).", "key": "tech_stack"},
    7: {"prompt": "Tech Screening: Please answer the following technical questions based on your stack:", "key": "technical_screening"},
    8: {"prompt": "Conclusion: Thank you for your time. Reviewing final summary.", "key": "conclusion"},
}

SYSTEM_PROMPT = (
    "You are the TalentScout Hiring Assistant, a professional, friendly, and concise chatbot. "
    "Your primary role is to gather information and screen candidates for technical roles. "
    "Follow the specific instructions for each step. DO NOT provide extra conversational filler. "
    "If the user deviates, gently guide them back to the required information for the current step. "
    "Maintain the context of the conversation and refer to the user's name when appropriate."
)

# Prompts for specific LLM tasks
def get_question_generation_prompt(tech_stack: str) -> str:
    """Generates the dynamic prompt for creating technical questions."""
    return (
        f"The candidate has declared the following tech stack: {tech_stack}. "
        "Generate exactly 3 open-ended technical questions. The questions must be tailored to assess "
        "practical, real-world proficiency in these technologies (e.g., a question about state management in a framework, "
        "or a design pattern). Ensure the questions are relevant to the provided stack. "
        "Present the questions clearly as a numbered list."
    )

def get_answer_evaluation_prompt(question: str, answer: str) -> str:
    """Generates the prompt for evaluating a technical answer."""
    return (
        f"Act as a Senior Technical Recruiter. Evaluate the candidate's answer based on the question. "
        f"Question: '{question}'. "
        f"Candidate Answer: '{answer}'. "
        "Provide a concise, professional assessment summary (max 3 sentences) and assign a proficiency rating: "
        "'Excellent', 'Good', 'Adequate', or 'Needs Improvement'. Do not add any conversational filler, only the summary and rating."
    )


# --- 4. STREAMLIT APPLICATION LOGIC ---

def init_session_state():
    """Initializes all necessary session state variables."""
    if 'conversation_history' not in st.session_state:
        st.session_state['conversation_history'] = []
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 0
    if 'candidate_data' not in st.session_state:
        st.session_state['candidate_data'] = {}
    if 'tech_questions' not in st.session_state:
        st.session_state['tech_questions'] = []
    if 'current_q_index' not in st.session_state:
        st.session_state['current_q_index'] = 0
    if 'candidate_results' not in st.session_state:
        st.session_state['candidate_results'] = []
    if 'is_finished' not in st.session_state:
        st.session_state['is_finished'] = False
    
    # Initialize the first message
    if not st.session_state.conversation_history:
        first_prompt = CONVERSATION_STEPS[0]["prompt"]
        st.session_state.conversation_history.append(
            {"role": "assistant", "content": first_prompt}
        )

def process_user_input(user_input: str):
    """Processes user input based on the current conversational step."""
    step = st.session_state['current_step']
    data_key = CONVERSATION_STEPS.get(step, {}).get("key")

    # 1. Check for conversation-ending keywords
    if any(keyword in user_input.lower() for keyword in ["goodbye", "exit", "thank you", "that's all"]):
        st.session_state.conversation_history.append({"role": "user", "content": user_input})
        st.session_state.conversation_history.append({
            "role": "assistant", 
            "content": "Understood. Thank you for your time. A human recruiter will still review the information we gathered. Have a great day!"
        })
        st.session_state.is_finished = True
        return

    # 2. Handle information gathering steps (Steps 0-6)
    if 0 <= step <= 6:
        
        # Store user input
        st.session_state.candidate_data[data_key] = user_input
        
        # Prepare the next assistant message
        next_step_index = step + 1
        
        if next_step_index == 7:
            # Special handling for Tech Stack step to generate questions
            try:
                with st.spinner("Analyzing tech stack and generating questions..."):
                    tech_stack = st.session_state.candidate_data['tech_stack']
                    question_prompt = get_question_generation_prompt(tech_stack)
                    
                    # Create a new history list to send, starting from the last 2-3 turns for context
                    # of *who* they are, but ensuring the question generation isn't too chatty.
                    llm_history = st.session_state.conversation_history[-3:]
                    
                    # Call LLM to generate questions
                    questions_text = generate_content(
                        user_query=question_prompt,
                        system_prompt=SYSTEM_PROMPT,
                        history=llm_history 
                    )
                    
                    # Simple parsing (assuming LLM returns a numbered list)
                    raw_questions = [q.strip() for q in questions_text.split('\n') if q.strip() and q[0].isdigit()]
                    
                    if not raw_questions:
                        # Fallback if parsing fails or LLM gives a poor response
                        raw_questions = ["Explain the concept of immutability in programming and why it's beneficial."] 

                    st.session_state.tech_questions = raw_questions
                    st.session_state.current_q_index = 0
                    
                    # Set the next question prompt
                    q_index = st.session_state.current_q_index
                    question = st.session_state.tech_questions[q_index]
                    assistant_response = f"{CONVERSATION_STEPS[7]['prompt']}\n\n**Question {q_index + 1}:** {question}"
            
            except Exception as e:
                assistant_response = f"I encountered an error while generating questions ({e}). Let's skip to the conclusion for now."
                next_step_index = 8 # Skip directly to conclusion
        
        elif next_step_index <= 6:
            # Standard info gathering next step
            next_prompt_template = CONVERSATION_STEPS[next_step_index]["prompt"]
            # Format the prompt with the candidate's name if available
            formatted_prompt = next_prompt_template.format(
                full_name=st.session_state.candidate_data.get('full_name', 'candidate')
            )
            assistant_response = formatted_prompt
            
        else: # Reached conclusion (Step 8)
            assistant_response = generate_conclusion_summary()
            st.session_state.is_finished = True


        # Update chat history and step
        st.session_state.conversation_history.append({"role": "user", "content": user_input})
        st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})
        st.session_state['current_step'] = next_step_index
    
    # 3. Handle Technical Screening step (Step 7)
    elif step == 7 and st.session_state.tech_questions:
        current_q_index = st.session_state.current_q_index
        current_question = st.session_state.tech_questions[current_q_index]
        
        # 3a. Call LLM to evaluate the answer
        try:
            with st.spinner(f"Evaluating answer for Question {current_q_index + 1}..."):
                evaluation_prompt = get_answer_evaluation_prompt(current_question, user_input)
                
                # Pass an empty history here, as requested by the prompt engineering section,
                # to keep the evaluation focused and prevent chat history noise.
                evaluation_text = generate_content(
                    user_query=evaluation_prompt,
                    system_prompt="You are a Technical Evaluator. Strictly follow the prompt instructions and output only the summary and rating.",
                    history=[] 
                )
                
                # Store the result
                st.session_state.candidate_results.append({
                    "question": current_question,
                    "answer": user_input,
                    "evaluation": evaluation_text
                })
                
            st.session_session.conversation_history.append({"role": "user", "content": user_input})

            # 3b. Advance to next question or conclusion
            next_q_index = current_q_index + 1
            if next_q_index < len(st.session_state.tech_questions):
                st.session_state.current_q_index = next_q_index
                next_question = st.session_state.tech_questions[next_q_index]
                assistant_response = (
                    f"**Assessment for Q{current_q_index + 1} Recorded:**\n\n"
                    f"Let's move to **Question {next_q_index + 1}:** {next_question}"
                )
                st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})

            else:
                # All questions answered, move to conclusion
                st.session_state['current_step'] = 8
                assistant_response = generate_conclusion_summary()
                st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})
                st.session_state.is_finished = True
                
        except Exception:
            assistant_response = "I couldn't process your technical answer right now. Moving to the final step."
            st.session_state['current_step'] = 8
            st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})
            st.session_state.is_finished = True
        
    # 4. Handle Fallback (if step or logic is missed)
    else:
        # LLM-powered fallback response
        fallback_query = f"I am currently on step {step} where I need to ask about {data_key}. The user responded with: '{user_input}'. Please provide a polite, single-sentence response guiding them back to the required input."
        try:
            fallback_response = generate_content(
                user_query=fallback_query,
                system_prompt="You are a helpful and polite chatbot assistant. Do not deviate from the current task.",
                history=st.session_state.conversation_history
            )
        except Exception:
            fallback_response = "I didn't quite catch that. Could you please provide the information I requested?"
            
        st.session_state.conversation_history.append({"role": "user", "content": user_input})
        st.session_state.conversation_history.append({"role": "assistant", "content": fallback_response})


def generate_conclusion_summary():
    """Generates the final summary and next steps for the candidate."""
    name = st.session_state.candidate_data.get('full_name', 'Candidate')
    position = st.session_state.candidate_data.get('desired_position', 'a technical role')
    
    summary_text = (
        f"Thank you, {name}, for completing the initial screening for {position}. "
        "Your responses have been recorded."
        "\n\n---"
        "\n\n**Candidate Profile Summary:**"
        f"\n- **Experience:** {st.session_state.candidate_data.get('years_of_experience')}"
        f"\n- **Tech Stack:** {st.session_state.candidate_data.get('tech_stack')}"
        f"\n- **Total Questions Answered:** {len(st.session_state.candidate_results)}"
        "\n\n---"
        "\n\nA TalentScout recruiter will carefully review your information and the technical screening results. "
        "We aim to follow up with you via email at "
        f"{st.session_state.candidate_data.get('email', 'the provided email address')} within 2-3 business days. "
        "We appreciate your interest in finding a great role through TalentScout!"
    )
    
    # Simulate data saving (In a real app, this would be a Firestore setDoc call)
    user_id = st.session_state.get('user_id', 'simulated_user')
    data_path = get_candidate_data_path(user_id)
    
    # Simulate logging the data save location
    summary_text += f"\n\n*(For Recruiter Review: Data logged to simulated path: {data_path})*"
    
    return summary_text


# --- 5. STREAMLIT UI RENDER ---

st.set_page_config(
    page_title="TalentScout Hiring Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (UI Enhancement Bonus)
st.markdown("""
<style>
    .main {
        background-color: #f7f9fc;
        padding: 10px;
    }
    .stChatFloatingInputContainer {
        border-top: 1px solid #e0e0e0;
        padding: 10px 0;
        background-color: white;
    }
    .stChatMessage {
        border-radius: 12px;
        padding: 12px 15px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stChatMessage.st-lc .st-emotion-cache-12ms9r9 { 
        background-color: #d1e7dd !important; /* Assistant: Green/Success Tone */
        color: #155724;
    }
    .stChatMessage.st-ee .st-emotion-cache-12ms9r9 { 
        background-color: #e9ecef !important; /* User: Light Gray */
        color: #212529;
    }
    .title-text {
        color: #1f77b4;
        font-weight: 700;
    }
    .st-emotion-cache-1wivap2 {
        padding: 0px 1rem 0px 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Main Title and Sidebar
st.markdown('<h1 class="title-text">🤖 TalentScout Hiring Assistant</h1>', unsafe_allow_html=True)
st.subheader("Your AI-Powered Initial Screening")

with st.sidebar:
    st.markdown("### 📋 Screening Progress")
    current_step = st.session_state.get('current_step', 0)
    
    # Display the steps
    for idx, (step_key, step_data) in enumerate(CONVERSATION_STEPS.items()):
        status = "✅" if idx < current_step else ("➡️" if idx == current_step else "⬜")
        st.write(f"{status} {step_data.get('key').replace('_', ' ').title()}")

    st.markdown("---")
    st.markdown("### Candidate Data Log (Simulated)")
    st.json(st.session_state.get('candidate_data', {}))
    
    st.markdown("---")
    st.markdown("### Technical Results")
    st.json(st.session_state.get('candidate_results', []))
    
    st.markdown("---")
    st.info(f"App ID: `{APP_ID}`")
    st.warning("Note: Data is simulated/stored in session state for this demo. In production, this data would be secured in Firestore.")
    if st.button("Start New Screening"):
        st.session_state.clear()
        st.rerun()


# --- Chat Interface ---

init_session_state()

# Inject a unique ID for the session to simulate a user_id for Firestore pathing
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = f"user-{int(time.time() * 1000)}"


# Display chat messages
for message in st.session_state.conversation_history:
    with st.chat_message(message["role"]):
        # Special formatting for technical questions/results
        content = message["content"]
        if "Assessment for Q" in content or "Question " in content:
            st.markdown(content)
        else:
            st.write(content)

# Handle user input
if not st.session_state.is_finished:
    user_input = st.chat_input("Type your response here...")
    if user_input:
        with st.spinner("Assistant is processing..."):
            process_user_input(user_input)
            st.rerun()
else:
    st.info("Screening completed. Click 'Start New Screening' in the sidebar to begin again.")