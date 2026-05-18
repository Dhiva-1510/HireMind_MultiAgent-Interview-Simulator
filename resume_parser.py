import os
import json
import chromadb
from groq import Groq
from llama_index.core import SimpleDirectoryReader

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Initialize ChromaDB client (local persistent storage)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    collection = chroma_client.get_or_create_collection(name="candidates")
except Exception as e:
    collection = chroma_client.create_collection(name="candidates")

def extract_text(file_path):
    try:
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        return "\n".join([doc.text for doc in documents])
    except Exception as e:
        return f"Error reading document: {str(e)}"

def parse_resume(file_path, session_id="default"):
    text = extract_text(file_path)
    
    # Extract profile using Groq
    prompt = f"""
    Extract the following information from the resume text into a JSON object.
    Required keys: "name", "target_role", "skills" (list), "experience_summary", "projects" (list).
    
    Resume Text:
    {text[:4000]} # Limit to 4k chars for prompt size just in case
    
    Return ONLY valid JSON.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    profile_json = json.loads(completion.choices[0].message.content)
    
    # Store text chunks in ChromaDB
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk],
            metadatas=[{"session_id": session_id, "type": "resume_chunk", "chunk_index": i}],
            ids=[f"{session_id}_chunk_{i}"]
        )
        
    # Store profile metadata in ChromaDB as well
    collection.add(
        documents=[json.dumps(profile_json)],
        metadatas=[{"session_id": session_id, "type": "profile"}],
        ids=[f"{session_id}_profile"]
    )
        
    return profile_json

def get_profile(session_id="default"):
    results = collection.get(
        ids=[f"{session_id}_profile"]
    )
    if results and results['documents']:
        return json.loads(results['documents'][0])
    return None
