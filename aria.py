import anthropic
import requests
import time
from datetime import datetime

client = anthropic.Anthropic()

SYSTEM_PROMPT = """
You are the user's personal AI assistant. Your name is ARIA (Advanced Research & Intelligence Assistant).
after the first prompt from the user ask the user for their name and use it in your responses.
if the user does not provide a name, use the default name "User".
Your personality:
- Direct and efficient — no fluff, get to the point
- Knowledgeable about gaming, tech, and AI
- Speaks like a smart friend, not a formal assistant
- Uses gaming references when relevant

You have access to tools. Use them when needed:
- search_web: use when the user asks about current events, recent updates, or anything needing live data
- save_file: use when the user asks to save or write something to a file
- read_file: use when the user asks to read or open a file
- fetch_page: use after search_web to open a URL and get real prices or content from the actual page
- get_time: use when the user asks about the current date or time

The current year is 2026. When searching, always use 2026 in your queries for recent information.

When a user asks for a PC build within a budget:
1. Use search_web to find current prices for each component separately
2. Search each component on these sites: akakce, itopya, and vatanbilgisayar — maximum 3 searches per component, never search the same component on the same site twice
3. Search for: CPU, GPU, motherboard, RAM, SSD, PSU, case, CPU cooler
4. Use fetch_page on the most relevant URLs to get real prices from the actual pages
5. After all searches, build the best possible PC where ALL parts combined stay under the budget
6. Present the final build as a clean table with component, model, and price in TL
7. Show the total at the bottom and confirm it stays within budget
8. Share the links of the components you found
9. Only use prices from search results, never from your own knowledge

Always be honest about what you can and cannot do.
"""

TOOLS = [
    {
        "name": "search_web",
        "description": "Search the internet for current information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_file",
        "description": "Save text content to a file on the user's computer",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The filename to save to"},
                "content": {"type": "string", "description": "The content to write"}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from the user's computer",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The filename to read"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "fetch_page",
        "description": "Open a URL and read the actual content of the page. Use this after search_web to get real prices from product pages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "get_time",
        "description": "Get the current date and time",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def search_web(query: str) -> str:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": "b069bcdac164b6f37bc7bef22d1fc6f3c608ea06",
        "Content-Type": "application/json"
    }
    payload = {"q": query, "num": 10}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        data = response.json()
        
        output = ""
        for result in data.get("organic", []):
            output += f"Title: {result['title']}\n"
            output += f"URL: {result.get('link', 'N/A')}\n"
            output += f"Snippet: {result['snippet']}\n\n"
        
        return output if output else "No results found."
    except Exception as e:
        return f"Search failed: {e}"

def save_file(filename: str, content: str) -> str:
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{filename}' saved successfully."
    except Exception as e:
        return f"Failed to save file: {e}"

def read_file(filename: str) -> str:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"File '{filename}' not found."
    except Exception as e:
        return f"Failed to read file: {e}"

def fetch_page(url: str) -> str:
    try:
        import re
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        text = response.text
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:2000]
    except Exception as e:
        return f"Failed to fetch page: {e}"

def get_time() -> str:
    now = datetime.now()
    return f"Current date and time: {now.strftime('%A, %B %d, %Y at %H:%M:%S')}"

TOOL_FUNCTIONS = {
    "search_web": search_web,
    "save_file": save_file,
    "read_file": read_file,
    "fetch_page": fetch_page,
    "get_time": get_time
}

def ask_aria(user_input, history):
    history.append({"role": "user", "content": user_input})
    
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=history
    )
    
    while response.stop_reason == "tool_use":
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        
        history.append({"role": "assistant", "content": response.content})
        
        tool_results = []
        for tool_use_block in tool_use_blocks:
            tool_name = tool_use_block.name
            tool_input = tool_use_block.input
            
            print(f"  [ARIA is using: '{tool_name}' → {tool_input}]")
            
            tool_result = TOOL_FUNCTIONS[tool_name](**tool_input)
            time.sleep(1)
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_result
            })
        
        history.append({
            "role": "user",
            "content": tool_results
        })
        
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history
        )
    
    aria_response = response.content[0].text
    history.append({"role": "assistant", "content": aria_response})
    return aria_response, history


# --- Main loop ---
history = []

print("=" * 50)
print("  ARIA — Personal AI Assistant")
print('  Type "quit" to exit | "clear" to reset')
print("=" * 50)
print()

while True:
    user_input = input("You: ").strip()
    
    if not user_input:
        continue
    if user_input.lower() == "quit":
        print("ARIA: Later! 👋")
        break
    if user_input.lower() == "clear":
        history = []
        print("ARIA: Memory cleared.")
        continue
    
    response, history = ask_aria(user_input, history)
    print(f"\nARIA: {response}\n")