import logging
from pymongo import MongoClient, errors

# ------------------------------
# Setup Logging
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# ------------------------------
# MongoDB Connection Test
# ------------------------------
def connect_to_mongodb(uri="mongodb://localhost:27017/", db_name="test_database"):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)  # 3-second timeout
        client.server_info()  # Force connection to test
        logging.info("✅ MongoDB connection successful")

        db = client[db_name]
        return db

    except errors.ServerSelectionTimeoutError as err:
        logging.error("❌ Could not connect to MongoDB. Please check if MongoDB service is running.")
        logging.error(f"Error: {err}")
        return None

# ------------------------------
# Insert and Fetch Test Data
# ------------------------------
def insert_and_verify(db):
    if db is None:
        logging.warning("⚠️ Skipping data insertion since DB connection failed.")
        return

    collection = db["sample_data"]
    test_doc = {"name": "Hari", "role": "Investor", "focus": "Renewable Energy"}

    try:
        result = collection.insert_one(test_doc)
        logging.info(f"✅ Data inserted with ID: {result.inserted_id}")

        for item in collection.find():
            logging.info(f"📦 Document: {item}")

    except Exception as e:
        logging.error(f"❌ Error inserting/fetching data: {e}")

# ------------------------------
# Main Execution
# ------------------------------
if __name__ == "__main__":
    db = connect_to_mongodb()
    insert_and_verify(db)
