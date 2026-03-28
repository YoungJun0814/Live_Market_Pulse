import json
import sys

def search_skills():
    file_path = r"C:\Users\Jun\Desktop\Files\Hackathon\tmp_awesome_skills\skills_index.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    keywords = {
        "Backend & DB": ["fastapi", "python", "websocket", "socket.io", "async"],
        "Frontend": ["react", "vite", "dashboard", "chart", "recharts", "globe", "3d", "webrtc", "canvas"],
        "APIs & Data": ["yfinance", "gemini", "youtube", "telegram", "twitter", "sns", "market", "finance"],
        "Architecture": ["architecture", "planning", "diagram", "system"]
    }

    found = {k: [] for k in keywords}

    for skill in data:
        name = skill.get("name", "").lower()
        desc = skill.get("description", "").lower()
        content = skill.get("content", "").lower()
        
        search_text = name + " " + desc + " " + content
        
        for category, kws in keywords.items():
            for kw in kws:
                if kw in search_text:
                    found[category].append({
                        "name": skill.get("name"),
                        "description": skill.get("description"),
                        "match": kw
                    })
                    break # just need one match per category to include it

    # Print top 15 from each category
    for category, items in found.items():
        print(f"\n--- {category} ---")
        # deduplicate by name
        unique_items = {item['name']: item for item in items}.values()
        for i, item in enumerate(list(unique_items)[:15]):
            print(f"- {item['name']} (matched: {item['match']}): {item['description']}")

if __name__ == "__main__":
    search_skills()
