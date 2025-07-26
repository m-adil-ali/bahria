from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

# Connect to MongoDB
print("mongo uri:", os.getenv("MONGODB_URI"))
client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print("Connection failed:", e)
    exit()


# # Select the database
# db = client[os.getenv("DB_NAME")]  # Or specify: client["your_db_name"]

# # Utility to flatten fields (including nested)
# def extract_fields(document, parent_key='', result=None):
#     if result is None:
#         result = set()
#     for key, value in document.items():
#         full_key = f"{parent_key}.{key}" if parent_key else key
#         if isinstance(value, dict):
#             extract_fields(value, full_key, result)
#         else:
#             result.add(full_key)
#     return result

# # Generate schema summary
# schema_summary = defaultdict(set)

# print("\nExtracting schema from collections...\n")

# for collection_name in db.list_collection_names():
#     collection = db[collection_name]
#     sample_doc = collection.find_one()
#     if sample_doc:
#         fields = extract_fields(sample_doc)
#         schema_summary[collection_name] = fields
#     else:
#         print(f"⚠️ Skipping empty collection: {collection_name}")

# # Print the summary in required format
# print("Schemas:")
# for name, fields in schema_summary.items():
#     formatted_fields = sorted(list(fields))
#     formatted = '", "'.join(formatted_fields)
#     print(f'- **{name}**: ["{formatted}"]')




# # from pymongo.mongo_client import MongoClient
# # from pymongo.server_api import ServerApi
# # import os
# # from dotenv import load_dotenv
# # import tiktoken

# # load_dotenv()
# # print("mongo uri:", os.getenv("MONGODB_URI"))
# # # Create a new client and connect to the server
# # client = MongoClient(os.getenv("MONGODB_URI"),server_api=ServerApi('1'))
# # # Send a ping to confirm a successful connection
# # try:
# #     client.admin.command('ping')
# #     print("Pinged your deployment. You successfully connected to MongoDB!")
# # except Exception as e:
# #     print(e)

# # # MONGODB_URI1="mongodb+srv://adilali:mongopass@mycluster.akfzoin.mongodb.net/?retryWrites=true&w=majority&appName=mycluster"
# # # DB_NAME1 = "RealEstate"