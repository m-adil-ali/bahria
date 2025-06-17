import os, re, json
from typing import Optional, List, Dict, Type
from pydantic import BaseModel, Field
from pydantic import model_validator
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.json_util import dumps
from dotenv import load_dotenv
from crewai.tools import BaseTool

# Load environment variables
load_dotenv()

# MongoDB client setup
client = MongoClient(os.getenv("MONGODB_URI"),server_api=ServerApi('1'))
db = client[os.getenv("DB_NAME")]


# ------------------------------
# Pydantic Input Schema
# ------------------------------
class MongoToolInput(BaseModel):
    filter: Optional[Dict] = Field(None, description="MongoDB filter query. Can include '_collection' or use 'collection_hint'.")
    pipeline: Optional[List[Dict]] = Field(None, description="MongoDB aggregation pipeline. Can include '_collection' or use 'collection_hint'.")
    collection_hint: Optional[str] = Field(None, description="Optional hint of the MongoDB collection name if not embedded.")

    @model_validator(mode="after")
    def validate_input(cls, values):
        if not values.filter and not values.pipeline:
            raise ValueError("Either 'filter' or 'pipeline' must be provided.")
        return values


# ------------------------------
# Mongo Query Tool Class
# ------------------------------
class MongoTool(BaseTool):
    name: str = "Smart MongoDB Query Tool"
    description: str = (
        "Executes a MongoDB query using either `find()` with a filter or `aggregate()` with a pipeline. "
        "Collection name can be embedded using '_collection' or passed via `collection_hint`."
    )
    args_schema: Type[BaseModel] = MongoToolInput

    def _extract_json_from_string(self, raw_str: str):
        """
        Extract JSON substring from a string that may contain backticks or markdown.
        Returns parsed JSON object or raises ValueError.
        """
        # Regex to extract JSON inside backticks or triple backticks
        pattern = r"``````|``````|(\{.*\})|(\[.*\])"
        match = re.search(pattern, raw_str, re.DOTALL)
        if not match:
            # If no JSON found, try to parse the whole string
            try:
                return json.loads(raw_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON: {str(e)}")
        # Extract matched group ignoring None
        json_str = next(g for g in match.groups() if g)
        return json.loads(json_str)

    def _run(
        self,
        filter: Optional[Dict] = None,
        pipeline: Optional[List[Dict]] = None,
        collection_hint: Optional[str] = None
    ) -> str:
        try:
            # Clean and parse filter if it is a string (from LLM)
            if filter and isinstance(filter, str):
                try:
                    filter = self._extract_json_from_string(filter)
                except ValueError as e:
                    return f"Error parsing filter JSON: {str(e)}"

            # Clean and parse pipeline if it is a string (from LLM)
            if pipeline and isinstance(pipeline, str):
                try:
                    pipeline = self._extract_json_from_string(pipeline)
                except ValueError as e:
                    return f"Error parsing pipeline JSON: {str(e)}"

            # Proceed with existing logic
            if filter:
                collection_name = filter.pop("_collection", None) or collection_hint
                if not collection_name:
                    return "Error: Collection name not found. Provide '_collection' in filter or set 'collection_hint'."
                col = db[collection_name]
                docs = list(col.find(filter, {"_id": 0}))
                return dumps(docs) if docs else "No matching documents found."

            elif pipeline:
                if not isinstance(pipeline, list) or not pipeline:
                    return "Error: Pipeline must be a non-empty list of stages."
                collection_name = pipeline[0].pop("_collection", None) or collection_hint
                if not collection_name:
                    return "Error: Collection name not found. Provide '_collection' in pipeline[0] or set 'collection_hint'."
                col = db[collection_name]
                docs = list(col.aggregate(pipeline))
                return dumps(docs) if docs else "No matching documents found."

            return "Error: Neither 'filter' nor 'pipeline' provided."

        except Exception as e:
            return f"Error while querying MongoDB: {str(e)}"
