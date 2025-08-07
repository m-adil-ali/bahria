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
from openai import OpenAI


load_dotenv()

# #api_key = os.getenv('GEMINI_API_KEY')
# model = "gemini-2.5-flash-lite-preview-06-17" 
# #-lite-preview-06-17 
# print(f"Using model and api: {model, api_key}")
# genai.configure(api_key=api_key)

# llm_model = genai.GenerativeModel(model_name=model, system_instruction="""You are a helpful context aware real estate agent that can assist users in finding properties in Bahria Town, Pakistan. You can answer questions about property details, availability, and pricing. If you don't have enough information, ask the user for more details.""")
# chating = llm_model.start_chat(history=[])

# Ensure telemetry is disabled
if os.getenv("CREWAI_DISABLE_TELEMETRY") != "true":
    print("Warning: CREWAI_DISABLE_TELEMETRY is not set to 'true'. Set this environment variable to disable telemetry and avoid connection errors.")


property_details: str = ""
agent_output: str = ""
sr_number: int = 1
agent_history: List[Dict] = []


class Chat:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL")
        self.messages: List[Dict[str, str]] = []
        self._load_system_prompt()
        
    def _load_system_prompt(self):
        # Load tasks.yaml
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tasks_path = os.path.join(base_dir, "config", "tasks.yaml")
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks_config = yaml.safe_load(f)
        # Get description and clean it
        raw_description = tasks_config['analyze_query_task']['description']
        # Replace literal "\n" with actual newlines
        cleaned_description = raw_description.replace('\\n', '\n')
        # Format with agent_history and sr_number
        system_prompt = cleaned_description.format(agent_history=json.dumps(agent_history, indent=2), sr_number=sr_number)
        # Update or set system prompt as the first message
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = system_prompt
        else:
            self.messages.insert(0, {"role": "system", "content": system_prompt})
        
        
    def send_message(self, user_message: str):
        self._load_system_prompt()
        self.messages.append({"role": "user", "content": user_message})
        response = self.client.chat.completions.create(
            model= self.model,
            messages=self.messages,
            temperature=0,
            max_tokens=1500  
        )
        assistant_reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_reply})
        # Write chat history to file
        with open('chat_history.txt', 'a', encoding='utf-8') as f:
            f.write(json.dumps(self.messages, indent=2) + "\n")
        return assistant_reply
    
@CrewBase
class Bahria():
    def __init__(self):
        super().__init__()
        self.agents_config = self._load_agents_config()
        self.tasks_config = self._load_tasks_config()

    def _load_agents_config(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "agents.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_tasks_config(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tasks_path = os.path.join(base_dir, "config", "tasks.yaml")
        with open(tasks_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
        
    @agent
    def property_agent(self) -> Agent:
        agent_cfg = self.agents_config.get('property_agent', {})
        return Agent(
            config=agent_cfg,
            llm = os.getenv("OPENAI_MODEL"),
            tools=[MongoTool()],
            verbose= True
        )

    @task
    def analyze_query_task(self) -> Task:
        task_cfg = self.tasks_config.get('analyze_query_task', {})
        return Task(
            description=task_cfg.get('description', ''),
            expected_output=task_cfg.get('expected_output', ''),
            agent=self.property_agent()
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
        self.chater = Chat()
        

    @start()
    def analyze_query(self): 
        self.state.iteration = 0
        user_input = self.state.user_input

        try: 
            print("agent_history:", agent_history)
            
            response = self.chater.send_message(user_input)
            print("openai response:", response)
            

            try:
                analysis_dict = json.loads(response)

                print(f"Cleaned result: {analysis_dict}")
                self.state.analysis_dict = analysis_dict
                
                return self.handle_property_query()
            

            except json.JSONDecodeError:
                #print("Response was not a valid JSON object:", response)
                return response
            
        except Exception as e:
            return f"Error analyzing query: {str(e)}"
        
    @listen('property_query')
    def handle_property_query(self):
        
        self.state.iteration += 1

        # Check if max_iterations is reached
        if self.state.iteration > self.state.max_iterations:
            response = "Sorry, I couldn't find a suitable property after several attempts. Please refine your query."

           
            return response
        
        #user_input = self.state.user_input
        global property_details, agent_output, sr_number, agent_history
        property_details = self.state.analysis_dict.get("property_details", "")
        prompt = self.state.prompt
       # context = self.chat.history
        task_description = self.fetch_property_task.description.format(
            user_input=property_details,
            prompt=prompt,
        #    context=context
        )
        formatted_task = Task(
            description=task_description,
            expected_output=self.fetch_property_task.expected_output,
            agent=self.property_agent,
        )
        try:
            property_result = self.property_agent.execute_task(formatted_task, property_details)
            agent_output = property_result
            agent_history.append({
            "sr_number": sr_number,
            "property_details": property_details,
            "agent_output": agent_output
        })
            sr_number += 1
            
            print(f"value replaced in agent_output: {agent_output}")
            # print(f"Chat history length: {len(self.chater.history)}")
            # print(f"Chat history : {self.chater.history}")
            return property_result
        except Exception as e:
            error_msg = f"Error fetching property data: {str(e)}"
            
            return error_msg

    @listen("unknown_query")
    def handle_unknown_query(self):
        user_input = self.state.user_input
        response = "Sorry, I couldn't understand your query. Please try rephrasing."
        
        return response
    

        