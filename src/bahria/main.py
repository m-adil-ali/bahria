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
3. If the user input contains **purpose** keywords like "buy", "sell", or "rent", ensure the query includes a filter for `list_type` based on the purpose:
   - For `"purpose":"buy"` or `"purpose":"rent"`, use `"list_type": "Sale"` or `"list_type": "Rent"`.
4. Choose the query method based solely on the number of **distinct collections** mentioned in the user input:
   - If the user is asking about properties from **only one collection**, use a simple `find()` filter.
   - If the user is querying across **two or more collections**, use an `aggregate()` pipeline with appropriate `$unionWith` stages.
   - Do **not** base this decision on the number of fields used this decision should be applied only on collections.
5. You may use only the following **valid collection names**:  
   `["apartments", "homes", "shops", "commercial_plots", "farmhouses", "residential_plots", "plazas", ]`
6. Use only the fields defined for each collection below. **Ignore the `_id` fields entirely when generating queries.**

Schemas:
- **apartments**: ["_id", "apartment_no", "bathrooms", "bedrooms", "building_name", "city", "commercialName", "contact_Number", "email", "floor_level", "full_Name", "furnished", "images", "installment", "is_living", "kitchen", "lift", "list_type", "office_Name", "parking", "payment_type", "phase", "pin_location", "possession", "price", "property_type", "size.unit", "size.value", "society", "tv_lounch", "utilities", "video_url"]
- **homes**: ["_id", "bathrooms", "bedrooms", "car_parking", "city", "construction_year", "contact_Number", "design", "email", "extra_land.unit", "extra_land.value", "floor_level", "full_Name", "furnished", "house", "images", "kitchen", "list_type", "living", "office_Name", "payment_type", "phase", "pin_location", "possession", "price", "property_type", "sector", "servent_room", "size.unit", "size.value", "society", "solar_panel", "store_room", "swimmingPool", "utilities", "video_url"]
- **shops**: ["_id", "building_name", "city", "commercialName", "contact_Number", "email", "floor_number", "full_Name", "installment", "list_type", "monthly_rent", "office_Name", "payment_type", "phase", "pin_location", "possession", "price", "property_type", "shop_number", "size.unit", "size.value", "society", "video_url", "washroom"]
- **commercial_plots**: ["_id", "allotment.details.category", "allotment.details.development_charges", "allotment.details.map_charges", "allotment.details.plot", "allotment.details.possessionUitilityCharges", "allotment.details.road_width", "allotment.details.street", "allotment.status", "city", "commercialName", "construction_allowed", "contact_Number", "earth_status", "email", "extra_land.unit", "extra_land.value", "full_Name", "images", "installment", "list_type", "note_for_result", "office_Name", "ownership", "payment_type", "phase", "pin_location", "plot_dimension", "price", "property_type", "size.unit", "size.value", "society", "video_url"]
- **farmhouses**: ["_id", "allotment.details.category", "allotment.details.development_charges", "allotment.details.map_charges", "allotment.details.plot", "allotment.details.possessionUitilityCharges", "allotment.details.road_width", "allotment.details.street", "allotment.status", "city", "construction_allowed", "contact_Number", "earth_status", "email", "extra_land.unit", "extra_land.value", "full_Name", "images", "installment", "layout_plan", "list_type", "note_for_result", "office_Name", "ownership", "payment_type", "phase", "pin_location", "plot_dimension", "price", "property_type", "sector", "size.unit", "size.value", "society", "video_url"]
- **residential_plots**: ["_id", "allotment.details.category", "allotment.details.development_charges", "allotment.details.map_charges", "allotment.details.plot", "allotment.details.possessionUitilityCharges", "allotment.details.road_width", "allotment.details.street", "allotment.status", "city", "contact_Number", "earth_status", "email", "extra_land.unit", "extra_land.value", "full_Name", "images", "installment", "layout_plan", "list_type", "note_for_result", "office_Name", "ownership", "payment_type", "phase", "pin_location", "price", "property_type", "sector", "size.unit", "size.value", "society", "video_url"]
- **plazas**: ["_id", "apartment_floors", "apartments", "building_name", "city", "commercialName", "commercial_floors", "construction_story", "contact_Number", "email", "full_Name", "height", "images", "lift", "list_type", "monthly_rent", "office_Name", "parking", "payment_type", "phase", "pin_location", "plot_dimension", "price", "property_type", "size.unit", "size.value", "society", "utilities", "video_url"]

---
<<Examples>>
- user_input: ```Find me a home in bahria town Lahore with more than 5 marla area for sale.```
    generated_query: db.Home.find({"list_type": "Sale", "society": "Bahria Town Lahore", "city": "Lahore", "area_size": {"$gt": 1361.255}})
- user_input: ```looking for any property either be home, apartment, plaza in bahria town lahore in any phase where area_size must be greater than 1000 sq ft```
    generated_query: db.Home.aggregate([
                { $match: { city: "Lahore", society: "Bahria Town Lahore", area_size: { $gt: 1000 } } },
                { $project: { _id: 0, title: 1, description: 1, price: 1, area_size: 1, city: 1, society: 1, phase: 1, bedrooms: 1, bathrooms: 1, parking: 1, furnished: 1 } },
                { $unionWith: {
                    coll: "Apartment",
                    pipeline: [
                      { $match: { city: "Lahore", society: "Bahria Town Lahore", area_size: { $gt: 1000 } } },
                      { $project: { _id: 0, title: 1, description: 1, price: 1, area_size: 1, city: 1, society: 1, phase: 1, bedrooms: 1, bathrooms: 1, floor_level: 1 } }
                    ]
                  }
                },
                { $unionWith: {
                    coll: "Plaza",
                    pipeline: [
                      { $match: { city: "Lahore", society: "Bahria Town Lahore", area_size: { $gt: 1000 } } },
                      { $project: { _id: 0, title: 1, description: 1, price: 1, area_size: 1, city: 1, society: 1, phase: 1, floors: 1, shops: 1, parking: 1 } }
                    ]
                  }
                }
              ]).toArray()
              
---

Remember:
- Always return **only** the valid MongoDB query string.
- Never return any surrounding explanations, markdown formatting, or JSON structures.
- Always choose the query type (`find()` or `aggregate()`) based on how many **collections** are involved — not on how many fields.
'''

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



