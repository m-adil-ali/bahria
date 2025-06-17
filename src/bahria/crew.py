from crewai import Agent, Crew, Process 
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Optional, Dict
from crewai import Flow, Agent, Task
from crewai.flow.flow import Flow, listen, start, router
import json, os, yaml, re
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
from tools.mongo_tool import MongoTool
from dotenv import load_dotenv
from pydantic import BaseModel
from crewai.memory.external.external_memory import ExternalMemory
from crewai.memory.storage.interface import Storage
import streamlit as st
import google.generativeai as genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
model = "gemini-1.5-flash"
#chat_llm = ChatGoogleGenerativeAI(model=modl, api_key=api_key)

genai.configure(api_key=api_key)
model = genai.GenerativeModel(model)
chat = model.start_chat(history=[])

@CrewBase
class Bahria():
    def __init__(self):
        super().__init__()
        self.agents_config = self._load_agents_config()
        self.tasks_config = self._load_tasks_config()
        
        #self.llm = chat_llm #os.getenv('MODEL') #self._init_llm() #

    def _load_agents_config(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "agents.yaml")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _load_tasks_config(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tasks_path = os.path.join(base_dir, "config", "tasks.yaml")
        with open(tasks_path, "r") as f:
            return yaml.safe_load(f)
        
    @agent
    def property_agent(self) -> Agent:
        agent_cfg = self.agents_config.get('property_agent', {})
        return Agent(
            config=agent_cfg,
            llm= os.getenv('MODEL'), #self.llm_agent, #os.getenv('MODEL'),
            tools=[MongoTool()],
            # memory=True,  
            #memory_storage=self.chat.history,
            verbose= True
        )

    @task
    def analyze_query_task(self) -> Task:
        task_cfg = self.tasks_config.get('analyze_query_task', {})
        return Task(
            description=task_cfg.get('description', ''),
            expected_output=task_cfg.get('expected_output', '')
        )

    @task
    def fetch_property_task(self) -> Task:
        task_cfg = self.tasks_config.get('fetch_property_task', {})
        return Task(
            description=task_cfg.get('description', ''),
            expected_output=task_cfg.get('expected_output', ''),
            agent=self.property_agent()
        )
    

# class CustomStorage(Storage):
#     def __init__(self):
#         #self.memories = []
#         self.messages: List[Dict] = []

#     def save(self, value):
#         #self.memories.append(value)
#         """Parse and store messages in Gemini's conversation format"""
#         if value.startswith("User: "):
#             role = "user"
#             text = value[len("User: "):]
#         elif value.startswith("Assistant: "):
#             role = "model"
#             text = value[len("Assistant: "):]
#         else:
#             role = "user"
#             text = value

#         self.messages.append({
#             "role": role,
#             "parts": [{"text": text}]
#         })

#     # def search(self, query=None, limit=None, score_threshold=None): #optional
#     #     # Return full conversation history as-is
#     #     return self.memories

#     def reset(self):
#         self.messages = []

# external_memory = ExternalMemory(storage=CustomStorage())

class FlowState(BaseModel):
    user_input: str = ""
    prompt: str = ""
    analysis_dict: Optional[Dict] = None
    error: str = ""
    iteration: int = 0
    max_iterations: int = 5

class RealEstateFlow(Flow[FlowState]):
    def __init__(self, crew: Bahria):
        super().__init__(state=FlowState().model_dump())
        self.crew = crew    
        self.property_agent = crew.property_agent()
        self.analyze_query_task = crew.analyze_query_task()
        self.fetch_property_task = crew.fetch_property_task()
        self.llm = os.getenv('MODEL')
        self.chat = chat
        #self.history = chat.history   # Initialize chat history

        #self.memory = external_memory
    
    def _update_last_user_message(self, clean_user_input: str):
        """
        Traverse chat history in reverse to find the last user message
        and update its parts with the cleaned user input.
        Supports both dict and object types for compatibility.
        """
        for i in range(len(self.chat.history) - 1, -1, -1):
            msg = self.chat.history[i]
            # Determine the role for both dict and object types
            role = msg["role"] if isinstance(msg, dict) else getattr(msg, "role", None)
            if role == "user":
                if isinstance(msg, dict):
                    msg["parts"] = [{"text": clean_user_input}]
                else:
                    msg.parts = [{"text": clean_user_input}]
                break
    
    def _update_last_model_message(self, new_text: str):
    # Traverse history in reverse to find the last model message
        for i in range(len(self.chat.history) - 1, -1, -1):
            msg = self.chat.history[i]
            # For dict-based or attribute-based access
            role = msg["role"] if isinstance(msg, dict) else getattr(msg, "role", None)
            if role == "model":
                # Update the parts with the cleaned text
                if isinstance(msg, dict):
                    msg["parts"] = [{"text": new_text}]
                else:
                    msg.parts = [{"text": new_text}]
                break

    def _add_agent_response_to_history(self, agent_response: str):
        for i in range(len(self.chat.history) - 1, -1, -1):
            msg = self.chat.history[i]
            # Support both dict and object types
            role = msg["role"] if isinstance(msg, dict) else getattr(msg, "role", None)
            if role == "model":
                if isinstance(msg, dict):
                    msg["parts"] = [{"text": agent_response}]
                else:
                    msg.parts = [{"text": agent_response}]
                break
    
    # def _update_last_model_message(self, new_text: str):
    #     """Update the last model message in chat history with cleaned response"""
    #     # Find the last model message and update it
    #     for i in range(len(self.chat.history) - 1, -1, -1):
    #         if self.chat.history[i].role == "model":
    #             # Create new content with cleaned text
    #             from google.generativeai.types import content_types
    #             new_part = content_types.Part(text=new_text)
    #             self.chat.history[i].parts = [new_part]
    #             break

    # def _add_agent_response_to_history(self, agent_response: str):
    #     """Add agent response as model message to chat history"""
    #     from google.generativeai.types import content_types
        
    #     # Create new model message
    #     model_content = content_types.Content(
    #         role="model",
    #         parts=[content_types.Part(text=agent_response)]
    #     )
    #     self.chat.history.append(model_content)   

    @start()
    def analyze_query(self): 
        self.state.iteration = 0
        user_input = self.state.user_input

        try:
            
            text = self.analyze_query_task.description + user_input
            #print(f"Sending to Gemini: {text}")
            # Send message using Gemini's built-in history management
            response = self.chat.send_message(text)
            analysis_result = response.text
            #print(f"Gemini response: {analysis_result}")
            
            #print(f"Default Chat history : {self.chat.history}")    
            # Extract JSON from response
            match = re.search(r'\{.*\}', analysis_result, re.DOTALL) # remove this
            if match:
                clean_result = match.group(0)
            else:
                return f"Failed to extract JSON object from LLM response: {analysis_result}"
            
            analysis_dict = json.loads(clean_result)
            self.state.analysis_dict = analysis_dict
            self._update_last_user_message(user_input)

        except json.JSONDecodeError as e:
            return f"JSON parsing failed. Error: {str(e)}"
        except Exception as e:
            return f"Error analyzing query: {str(e)}"
        
        
#         self.state.iteration = 0
#         # Access state directly
#         user_input = self.state.user_input
#         prompt = self.state.prompt
#         #past_memories = self.memory.storage.search(user_input)
#         #past_conversation = self.memory.storage.messages
# #        past_conversation = "\n".join(self.memory.storage.messages)
#         #prompt_with_context = f"Past conversation: ``{past_conversation}``\n\nUser Input: {user_input}"
        
#         text = self.analyze_query_task.description + "\n\nUser Input with past conversation(you should work on only 'user_input' but being aware of past conversation to answer if there is any question related to previous conversation.): " + user_input
#         try:
#             print(f'prompt going to llm: {text}')
#             analysis_result = chat_llm.invoke(text).content 
#             print(f'llm response: {analysis_result}')
#            # Use regex to extract JSON block
#             match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
#             if match:
#                 clean_result = match.group(0)
#             else:
#                 return f"Failed to extract JSON object from LLM response: {analysis_result}"

#             print(f'clean result: {clean_result}')
#             analysis_dict = json.loads(clean_result)
#             print(f'llm response dict: {analysis_dict}')
#             self.state.analysis_dict = analysis_dict
#         except json.JSONDecodeError:
#             return f"JSON parsing failed. Cleaned content: {clean_result}. Error: {str(e)}"
#         except Exception as e:
#             return f"Error analyzing query: {str(e)}"
        
    @router(analyze_query)
    def route_query(self):
        analysis_dict = self.state.analysis_dict or {}
        query_type = analysis_dict.get('query_type', '')

        if query_type == 'general_query':
            return "general_greeting"
        elif query_type == 'property_fetch_request':
            return "property_query"
        else:
            # Default fallback event or error handling
            return "unknown_query"
    
    @listen("general_greeting")
    def handle_general_greeting(self):
        user_input = self.state.user_input
        response = self.state.analysis_dict.get('response', "Hello!")
        
        # Update the last assistant message in history with cleaned response
        self._update_last_model_message(response)
        
        # Save user input and response to memory
        # self.memory.storage.save(f"User: {user_input}")
        # self.memory.storage.save(f"Assistant: {response}")
        
        #print(f"General greeting response: {response}")
        print(f"Chat history length: {len(self.chat.history)}")
        print(f"After changes, Chat history : {self.chat.history}")
        return response

    @listen('property_query')
   # @st.cache_data
    #@st.cache_resource(show_spinner="Fetching data from database...")
    def handle_property_query(self):
        
        self.state.iteration += 1

        # Check if max_iterations is reached
        if self.state.iteration > self.state.max_iterations:
            response = "Sorry, I couldn't find a suitable property after several attempts. Please refine your query."
            # self.memory.storage.save(f"User: {self.state.user_input}")
            # self.memory.storage.save(f"Assistant: {response}")
            
            self._update_last_model_message(response)
            return response
        
        user_input = self.state.user_input
        prompt = self.state.prompt
        context = self.chat.history
        task_description = self.fetch_property_task.description.format(
            user_input=user_input,
            prompt=prompt,
            context=context
        )
        formatted_task = Task(
            description=task_description,
            expected_output=self.fetch_property_task.expected_output,
            agent=self.property_agent
        )
        try:
            property_result = self.property_agent.execute_task(formatted_task, user_input)
            
            # Save user input and assistant response to memory
            # self.memory.storage.save(f"User: {user_input}")
            # self.memory.storage.save(f"Assistant: {property_result}")
            
            self._add_agent_response_to_history(property_result)
            #print(f"Property query response: {property_result}")
            print(f"Chat history length: {len(self.chat.history)}")
            print(f"After changes, Chat history : {self.chat.history}")
            return property_result
        except Exception as e:
            error_msg = f"Error fetching property data: {str(e)}"
            # self.memory.storage.save(f"User: {user_input}")
            # self.memory.storage.save(f"Assistant: {error_msg}")
            return error_msg

    @listen("unknown_query")
    def handle_unknown_query(self):
        user_input = self.state.user_input
        response = "Sorry, I couldn't understand your query. Please try rephrasing."
        
        # self.memory.storage.save(f"User: {user_input}")
        # self.memory.storage.save(f"Assistant: {response}")
        
        self._update_last_model_message(response)
        return response

        