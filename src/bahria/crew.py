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
model = "gemini-2.5-flash-lite-preview-06-17" 
print(f"Using model and api: {model, api_key}")
genai.configure(api_key=api_key)

llm_model = genai.GenerativeModel(model_name=model, system_instruction="""You are a helpful context aware real estate agent that can assist users in finding properties in Bahria Town, Pakistan. You can answer questions about property details, availability, and pricing. If you don't have enough information, ask the user for more details.""")
chating = llm_model.start_chat(history=[])

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
            llm = os.getenv("MODEL"),
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
        self.chater = chating
       
    def _update_last_model_message(self, new_text: str):
    # Traverse history in reverse to find the last model message
        for i in range(len(self.chater.history) - 1, -1, -1):
            msg = self.chater.history[i]
            # For dict-based or attribute-based access
            role = msg["role"] if isinstance(msg, dict) else getattr(msg, "role", None)
            if role == "model":
                # Update the parts with the cleaned text
                if isinstance(msg, dict):
                    msg["parts"] = [{"text": new_text}]
                else:
                    msg.parts = [{"text": new_text}]
                break

        # with open('chat_history.txt', 'a') as f:
        #             f.write(str(self.chater.history) + "\n")
    @start()
    def analyze_query(self): 
        self.state.iteration = 0
        user_input = self.state.user_input

        try:  
            length = len(self.chater.history)
            if length == 0:
                text = self.analyze_query_task.description + "\nExpected Output:" + self.analyze_query_task.expected_output + "\nUser Input:" + user_input
                #print("prompt to llm:", text)
                response = self.chater.send_message(text).text
            else:
                response = self.chater.send_message(user_input).text
            try:
                analysis_dict = json.loads(response)

                #print(f"Cleaned result: {analysis_dict}")
                self.state.analysis_dict = analysis_dict
                
                return self.handle_property_query()

            except json.JSONDecodeError:
                #print("Response was not a valid JSON object:", response)
                return response
           
        except json.JSONDecodeError as e:
            return f"JSON parsing failed. Error: {str(e)}"
        except Exception as e:
            return f"Error analyzing query: {str(e)}"
        
    @listen('property_query')
    def handle_property_query(self):
        
        self.state.iteration += 1

        # Check if max_iterations is reached
        if self.state.iteration > self.state.max_iterations:
            response = "Sorry, I couldn't find a suitable property after several attempts. Please refine your query."

            #self._update_last_model_message(response)
            return response
        
        #user_input = self.state.user_input
        user_input = self.state.analysis_dict.get("property_details", "")
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
            
            #self._update_last_model_message(property_result)
            #print(f"Property query response: {property_result}")
            # print(f"Chat history length: {len(self.chater.history)}")
            # print(f"Chat history : {self.chater.history}")
            return property_result
        except Exception as e:
            error_msg = f"Error fetching property data: {str(e)}"
            self._update_last_model_message(error_msg)
            return error_msg

    @listen("unknown_query")
    def handle_unknown_query(self):
        user_input = self.state.user_input
        response = "Sorry, I couldn't understand your query. Please try rephrasing."
        
        self._update_last_model_message(response)
        return response
    

        