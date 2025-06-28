__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from crew import RealEstateFlow, Bahria
import streamlit as st
import warnings, os
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

prompt_template='''
You are an expert MongoDB query engineer with over 10 years of hands-on experience writing advanced NoSQL queries, specifically for MongoDB.

Your task is to generate a **single valid plain MongoDB query string**, based on a user's **natural language input** (provided within single quotes). Follow the instructions below strictly:

1. Only return the **plain MongoDB query** — no comments, explanations, markdown formatting (e.g., ```json), or additional output. Just the query string.
2. Do **not** generate any queries related to deletion, updates, or data manipulation. Only `find()` and `aggregate()` queries are allowed.
3. Choose the query method based solely on the number of **distinct collections** mentioned in the user input:
   - If the user is asking about properties from **only one collection**, use a simple `find()` filter.
   - If the user is querying across **two or more collections**, use an `aggregate()` pipeline with appropriate `$unionWith` stages.
   - Do **not** base this decision on the number of fields used — only on collections.
4. You may use only the following **valid collection names**:  
   `["CommercialPlot", "ResidentialPlot", "FarmHouse", "Plaza", "Apartment", "Home", "Shop"]`
5. Use only the fields defined for each collection below. **Ignore the `_id` and `property_type` fields entirely when generating queries.**

Schemas:
- **CommercialPlot**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","main_road_access","road_width","corner_plot"]
- **ResidentialPlot**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","plot_number","road_width","corner_plot"]
- **FarmHouse**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","bedrooms","garden","pool","parking"]
- **Plaza**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","floors","shops","parking"]
- **Apartment**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","bedrooms","bathrooms","floor_level"]
- **Home**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","bedrooms","bathrooms","floor_level","parking","furnished"]
- **Shop**: ["purpose","payment_type","title","description","price","area_size","owner_contact","city","society","phase","floor_level","shop_number","furnished","corner_shop"]

---
<<Examples>>
- user_input: ```Find me a home in bahria town Lahore with more than 5 marla area for sale.```
    generated_query: db.Home.find({"purpose": "sale", "society": "Bahria Town", "city": "Lahore", "area_size": {"$gt": 1361.255}})
- user_input: ```looking for any property either be home, apartment, plaza in bahria town lahore in any phase where area_size must be greater than 1000 sq ft```
    generated_query: db.Home.aggregate([
                { $match: { city: "Lahore", society: "Bahria Town", area_size: { $gt: 1000 } } },
                { $project: { _id: 0, title: 1, description: 1, price: 1, area_size: 1, city: 1, society: 1, phase: 1, bedrooms: 1, bathrooms: 1, parking: 1, furnished: 1 } },
                { $unionWith: {
                    coll: "Apartment",
                    pipeline: [
                      { $match: { city: "Lahore", society: "Bahria Town", area_size: { $gt: 1000 } } },
                      { $project: { _id: 0, title: 1, description: 1, price: 1, area_size: 1, city: 1, society: 1, phase: 1, bedrooms: 1, bathrooms: 1, floor_level: 1 } }
                    ]
                  }
                },
                { $unionWith: {
                    coll: "Plaza",
                    pipeline: [
                      { $match: { city: "Lahore", society: "Bahria Town", area_size: { $gt: 1000 } } },
                      { $project: { _id: 0, title: 1, description: 1, price: 1, area_size: 1, city: 1, society: 1, phase: 1, floors: 1, shops: 1, parking: 1 } }
                    ]
                  }
                }
              ]).toArray()
              
---

Remember:
- Always return **only** the valid MongoDB query string.
- Never return any surrounding explanations, formatting, or JSON structures.
- Always choose the query type (`find()` or `aggregate()`) based on how many **collections** are involved — not on how many fields.
'''

def run():
    """
    Run the crew.
    """
    st.title("🏠 Bahria Town Real-Estate Agent")

    # Initialize session state for messages
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input
    if user_input := st.chat_input("How can I assist you with properties in Bahria Town?"):
        # Append user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Initialize Bahria crew first
        bahria_crew = Bahria()

        # Pass the crew instance to your flow
        flow = RealEstateFlow(crew=bahria_crew)

        # Prepare inputs for the crew
        inputs = {
            'user_input': user_input,
            'prompt': prompt_template
        }

        # Check for exit condition
        if user_input.lower() in ["exit", "quit"]:
            st.session_state.messages.append({"role": "assistant", "content": "Goodbye."})
            with st.chat_message("assistant"):
                st.markdown("Goodbye.")
            st.stop()

        # Run the crew to get the response
        try:
            response = flow.kickoff(inputs={"user_input": user_input, "prompt": prompt_template}) 
            if not response:  # Debug: Check if response is empty
                response = "Error: No response returned from the flow."
        except Exception as e:
            response = f"Error processing your request: {str(e)}"
            
        # Append and display assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)


if __name__ == "__main__":
    # Check environment variables
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        st.error("Gemini API key not found. Please set the 'GEMINI_API_KEY' environment variable.")
        st.stop()
    
    # Run the Streamlit app
    run()



