# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from crew import RealEstateFlow, Bahria
import streamlit as st
import warnings, os
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Load prompt from prompt.txt
prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
try:
    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt_template = file.read()
except FileNotFoundError:
    st.error("Prompt file not found at project/src/bahria/prompt.txt. Please create the file with the prompt content.")
    st.stop()
    

def run():
    """
    Run the crew.
    """
    st.title("🏠 AI Real-Estate Agent")

    # Initialize session state for messages and flow
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "flow" not in st.session_state:
        # Initialize Bahria crew and RealEstateFlow once
        bahria_crew = Bahria()
        st.session_state.flow = RealEstateFlow(crew=bahria_crew)

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input
    if user_input := st.chat_input("How can I assist you with properties in Bahria Town, DHA, Gulberg, etc?"):
        # Append user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Use the persistent flow instance
        flow = st.session_state.flow

        # Check for exit condition
        if user_input.lower() in ["exit", "quit"]:
            response = "Goodbye."
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
            st.stop()

        # Run the flow to get the response
        try:
            response = flow.kickoff(inputs={"user_input": user_input, "prompt": prompt_template})
            if not response:  # Debug: Check if response is empty
                response = "Error: No response returned from the agent."
        except Exception as e:
            response = f"Error processing your request: {str(e)}"

        # Append and display assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)


if __name__ == "__main__":
    # Check environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        st.error("OpenAI API key not found. Please set the 'OPENAI_API_KEY' environment variable.")
        st.stop()
    run()
    
    # gemini_api_key = os.getenv("GEMINI_API_KEY")
    # if not gemini_api_key:
    #     st.error("Gemini API key not found. Please set the 'GEMINI_API_KEY' environment variable.")
    #     st.stop()
    
    # Run the Streamlit app
    #run()



