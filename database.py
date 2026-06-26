import os
import json
import hashlib
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = "hiremind_db"

client = None
db = None
use_fallback = False
FALLBACK_FILE = "db_fallback.json"

try:
    # Try to connect with a 2-second timeout
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
    # Check if server is online
    client.server_info()
    db = client[DB_NAME]
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"MongoDB connection failed: {e}. Falling back to file-based database.")
    use_fallback = True
    if not os.path.exists(FALLBACK_FILE):
        with open(FALLBACK_FILE, "w") as f:
            json.dump({"users": {}, "sessions": {}}, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(name, email, password):
    if not name or not email or not password:
        return False, "All fields are required."
    
    hashed = hash_password(password)
    user_data = {
        "name": name,
        "email": email,
        "password": hashed
    }
    
    if use_fallback:
        try:
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
            if email in data["users"]:
                return False, "Email already registered."
            data["users"][email] = user_data
            with open(FALLBACK_FILE, "w") as f:
                json.dump(data, f, indent=4)
            return True, "User created successfully."
        except Exception as e:
            return False, f"Fallback database error: {str(e)}"
    else:
        try:
            if db.users.find_one({"email": email}):
                return False, "Email already registered."
            db.users.insert_one(user_data)
            return True, "User created successfully."
        except Exception as e:
            return False, f"MongoDB error: {str(e)}"

def authenticate_user(email, password):
    if not email or not password:
        return None
        
    hashed = hash_password(password)
    if use_fallback:
        try:
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
            user = data["users"].get(email)
            if user and user["password"] == hashed:
                return user
            return None
        except:
            return None
    else:
        try:
            user = db.users.find_one({"email": email})
            if user and user["password"] == hashed:
                user["_id"] = str(user["_id"])
                return user
            return None
        except:
            return None

def save_interview_session(email, session_id, profile, evaluations, feedback):
    session_data = {
        "email": email,
        "session_id": session_id,
        "profile": profile,
        "evaluations": evaluations,
        "feedback": feedback
    }
    if use_fallback:
        try:
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
            data["sessions"][session_id] = session_data
            with open(FALLBACK_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Fallback DB error saving session: {e}")
    else:
        try:
            db.sessions.update_one(
                {"session_id": session_id},
                {"$set": session_data},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB error saving session: {e}")

def get_user_sessions(email):
    if use_fallback:
        try:
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
            user_sessions = [s for s in data["sessions"].values() if s.get("email") == email]
            return user_sessions
        except Exception as e:
            print(f"Fallback DB error retrieving sessions: {e}")
            return []
    else:
        try:
            cursor = db.sessions.find({"email": email})
            sessions = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                sessions.append(doc)
            return sessions
        except Exception as e:
            print(f"MongoDB error retrieving sessions: {e}")
            return []
