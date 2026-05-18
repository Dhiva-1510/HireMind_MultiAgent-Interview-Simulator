import os
import requests

def fetch_resources_for_weakness(weak_areas):
    """
    Uses SerpApi or Tavily to find top learning resources (articles, youtube videos)
    for the identified weak areas.
    """
    if not weak_areas or weak_areas == "None":
        return []

    resources = []
    topics = weak_areas.split(", ")[:3] # Limit to top 3 weak areas
    
    serp_key = os.getenv("SERPAPI_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    for topic in topics:
        query = f"best tutorial or course for {topic} programming interview"
        
        # Try Tavily first if available
        if tavily_key:
            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json={"api_key": tavily_key, "query": query, "search_depth": "basic", "max_results": 2}
                )
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    for r in results:
                        resources.append({"topic": topic, "title": r.get("title"), "url": r.get("url")})
                    continue
            except:
                pass
                
        # Fallback to SerpAPI if Tavily fails or is absent
        if serp_key:
            try:
                response = requests.get(f"https://serpapi.com/search.json?q={query}&api_key={serp_key}")
                if response.status_code == 200:
                    results = response.json().get("organic_results", [])[:2]
                    for r in results:
                        resources.append({"topic": topic, "title": r.get("title"), "url": r.get("link")})
            except:
                pass

    return resources
