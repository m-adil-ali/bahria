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
Your task is to generate a **single valid plain MongoDB query string without markdown format** based on a **natural language question** provided above in single quotation. 
Do **not** include any explanations, comments, or additional markdown format e.g(``` json) only the query itself(always remember).
Do **not** generate any deletion, trimming, cutting or update queries, only `find()` or `aggregate()` queries without markdown format.
You have 7 collections in the database names are enlisted below use only these valid collections while generating query:
Total_Collections : ["CommercialPlot", "ResidentialPlot", "FarmHouse", "Plaza", "Apartment", "Home", "Shop"]
And here is the schema of each collection, use only these valid fields while generating query:
"CommercialPlot": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","main_road_access","road_width","corner_plot"],
"ResidentialPlot": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","plot_number","road_width","corner_plot"],
"FarmHouse": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","bedrooms","garden","pool","parking"],
"Plaza": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","floors","shops","parking"],
"Apartment": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","bedrooms","bathrooms","floor_level"],
"Home": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","bedrooms","bathrooms","floor_level","parking","furnished"],
"Shop": ["_id","purpose","property_type","payment_type","title","description","price","area_size","owner_contact","city","society","phase","floor_level","shop_number","furnished","corner_shop"]
**Ignore the `_id` field and "property_type" in all collections while generating mongoDB queries.**
**Use find() filter when the `user_input` is a simple query(querying about one collection) and always use aggregate() pipeline when the `user_input` is complex query(querying about two or more collections).**

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
'''

def run():
    """
    Run the crew.
    """
    st.title("🏡Bahria Town Real Estate Chatbot")

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



