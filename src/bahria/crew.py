from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Optional, Dict
from crewai.flow.flow import Flow, listen, start, router
import json, os, yaml, re
from tools.mongo_tool import MongoTool
from dotenv import load_dotenv
from pydantic import BaseModel
import streamlit as st
import google.generativeai as genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
model = "gemini-1.5-flash"

genai.configure(api_key=api_key)
model = genai.GenerativeModel(model)
chat = model.start_chat(history=[])

@CrewBase
class Bahria():
    def __init__(self):
        super().__init__()
        self.agents_config = self._load_agents_config()
        self.tasks_config = self._load_tasks_config()

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
            llm= os.getenv('MODEL'), 
            tools=[MongoTool()],
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
    @start()
    def analyze_query(self): 
        self.state.iteration = 0
        user_input = self.state.user_input

        try:
            
            text = self.analyze_query_task.description + user_input
            response = self.chat.send_message(text)
            analysis_result = response.text
            match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
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
        
        #print(f"Chat history length: {len(self.chat.history)}")
        #print(f"After changes, Chat history : {self.chat.history}")
        return response

    @listen('property_query')
    def handle_property_query(self):
        
        self.state.iteration += 1

        # Check if max_iterations is reached
        if self.state.iteration > self.state.max_iterations:
            response = "Sorry, I couldn't find a suitable property after several attempts. Please refine your query."

            self._update_last_model_message(response)
            return response
        
        user_input = self.state.user_input
        prompt = self.state.prompt
       # context = self.chat.history
        task_description = self.fetch_property_task.description.format(
            user_input=user_input,
            prompt=prompt,
        #    context=context
        )
        formatted_task = Task(
            description=task_description,
            expected_output=self.fetch_property_task.expected_output,
            agent=self.property_agent
        )
        try:
            property_result = self.property_agent.execute_task(formatted_task, user_input)
            
            self._add_agent_response_to_history(property_result)
            #print(f"Property query response: {property_result}")
            #print(f"Chat history length: {len(self.chat.history)}")
            #print(f"After changes, Chat history : {self.chat.history}")
            return property_result
        except Exception as e:
            error_msg = f"Error fetching property data: {str(e)}"
            return error_msg

    @listen("unknown_query")
    def handle_unknown_query(self):
        user_input = self.state.user_input
        response = "Sorry, I couldn't understand your query. Please try rephrasing."
        
        self._update_last_model_message(response)
        return response

        