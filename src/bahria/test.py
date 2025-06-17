from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
load_dotenv()

uri = "mongodb+srv://adilali:<db_password>@mycluster.akfzoin.mongodb.net/?retryWrites=true&w=majority&appName=mycluster"
# Create a new client and connect to the server
client = MongoClient(os.getenv("MONGODB_URI"),server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)