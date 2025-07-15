import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import text
import requests
import psycopg2
import time
import json
from dotenv import load_dotenv
import urllib.parse
import time
from lxml import html
import urllib.parse

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_URL")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

USER_AGENT       = "Mozilla/5.0 (compatible; Agent/1.0)"

conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")



SYSTEM_PROMPT_NCM = """

You are an autonomous agent that can use tools via JSON actions. Your goal is to generate the NCM (Nomenclatura Comum do Mercosul) of a product based on its descprition.
#Consider that the description might be in other languages besides English – like Portuguese or Spanish.
You maintain a list called `partial_conclusions` where you store brief takeaways from each document you inspect.
All outputs must be a single valid JSON object with exactly one of three actions: 'search', 'select', 'answer_before_db_search' or answer_with_db.

Database schema:
The database schema is:

— **ncm**  
  • ncm_id  
  • ncm (the NCM code)  
  • description  

At each step, you MUST:
    1. Review the user's request, which will be a request to find a product's part number. The user's request will contain important information about the product and, sometimes, the part number can be found there.
    2. Look at your accumulated `partial_conclusions` to decide what information is still missing.
    3. Choose an action:
    - 'search' with a 'query' field to find new sources. Do not repeat queries. Always check the partial_conclusions to check weather the query was already used or not. THE QUERIES MUST BE IN PORTUGUESE
    - 'select' with an 'index' field to fetch and summarize a result from your last search.
    - 'answer_before_db_search' with an 'answer' field once you have enough context. The answer must be ONLY the product's NCM or 'Not found' if you wasn't able to find it. MANDATORY RULE for the NCM: the 8-digit Mercosul classification code, if available in the datasheet; if not, you may determine the most appropriate NCM based on the product’s description or “Not found” if uncertain. When extracting or generating an NCM code, format it as 1234.56.78 (four digits, a dot, two digits, a dot, two digits).
    - 'answer_with_db' generate a SQL query based on the answer you came to. the ncm values in the ncm table are unique values. If you don't find the ncm you got in the 'answer' action, the answer was wrong and you should generate a new query to repeat the steps or select another URL based returned from the first query. 
       If you find an existing result in the table for the NCM generated in the 'answer' step, this must be the final answer. so answer ONLY with the product's ncm

    When you do 'select', after fetching and summarizing, append a new concise conclusion (1–2 sentences) to `partial_conclusions`.
    Never revisit the same URL twice. When you choose 'answer', return the full final answer; don’t include any extra keys or any text outside the JSON object.
 
Example output:
{
  "action": "search",
  "query": "Painel Solar NCM
  "
}
    
"""

SYSTEM_PROMPT_DATASHEET = """

You are an autonomous agent that can use tools via JSON actions. Your goal is to determine and return the PDF datasheet URL for a given product based on its description.
#Consider that the description might be in other languages besides English – like Portuguese or Spanish.

You maintain a list called `partial_conclusions` where you store brief takeaways from each document you inspect.
All outputs must be a single valid JSON object with exactly one of three actions: 'search', 'select' or 'answer'.



At each step, you MUST:
    1. Review the user's request, which will be a request to find a product's part number. The user's request will contain important information about the product and, sometimes, the part number can be found there.
    2. Look at your accumulated `partial_conclusions` to decide what information is still missing.
    3. Choose an action:
    - 'search' with a 'query' field to find new sources. Do not repeat queries. Always check the partial_conclusions to check weather the query was already used or not.
    - 'select' with an 'index' field to fetch and summarize a result from your last search.
    - 'answer' with an 'answer' field once you have enough context.

     
When you do 'select', after fetching and summarizing, append a new concise conclusion (1–2 sentences) to `partial_conclusions`.
Never revisit the same URL twice. When you choose 'answer', return the full final answer; don’t include any extra keys or any text outside the JSON object.
 
Example output:
{
  "action": "search",
  "query": "Solar panel Canadian 555W datasheet pdf"
}
    
"""

def clean_ddg_url(href: str) -> str:
    """
    Given an <a href> value from DuckDuckGo, return the de-wrapped, decoded URL.
    """
    # Strip leading // if present (so urlparse works)
    if href.startswith("//"):
        href = href.lstrip("/")
    
    # Parse the URL into components
    parsed = urllib.parse.urlparse(href)  # :contentReference[oaicite:0]{index=0}

    # Extract query parameters into a dict
    qs = urllib.parse.parse_qs(parsed.query)  # :contentReference[oaicite:1]{index=1}

    # If the 'uddg' param exists, that's our real URL
    if "uddg" in qs and qs["uddg"]:
        real_url = urllib.parse.unquote(qs["uddg"][0])  # :contentReference[oaicite:2]{index=2}
    else:
        # Otherwise fall back to the original href
        real_url = href

    return real_url

def get_llm_response(messages):
    """
    Send `prompt` to the GPT-4.1 chat model and return its reply.
    """
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0,
        max_tokens=5000
    )
    # pull out the assistant’s reply
    return resp.choices[0].message.content.strip()

def fetch_url_content(url: str, max_chars: int = 2000) -> str:
    """Fetches a page and returns the first up to max_chars of text."""
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    text = resp.text
    # Simple heuristic: strip tags and truncate
    clean = ''.join(text.splitlines(True))[:max_chars]
    return clean

def duckduckgo_search(query, num_results=10, lang="us-en", pause=1.0):
    """
    Perform a DuckDuckGo search and return a list of result URLs.

    Args:
        query (str): Search query.
        num_results (int): Max number of URLs to return.
        lang (str): Region/language code (e.g. 'us-en').
        pause (float): Seconds to wait before returning (rate-limit).

    Returns:
        List[str]: List of result URLs.
    """
    session = requests.Session()
    # 1. Use the static HTML interface
    base_url = "https://html.duckduckgo.com/html/"
    # 2. Spoof headers to mimic a real browser
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/"
    })

    # 3. Fetch the HTML results page
    resp = session.get(base_url, params={"q": query, "kl": lang})
    resp.raise_for_status()
    doc = html.fromstring(resp.text)

    # 4. Select all <a> tags with class containing "result__a"
    links = doc.cssselect('a.result__a')  # CSS selector for static HTML links

    results = []

    for a in doc.cssselect('a.result__a'):
        href = a.get("href")
        url  = clean_ddg_url(href)
        if url not in results:
            results.append(url)
        if len(results) >= num_results:
            break


    # 6. Polite pause before returning
    time.sleep(pause)
    return results


def run_agent_ncm(messages):
    urls = []
    selected_urls = []
    partial_conclusions = []
    queries = []

 
    # seed with system prompt that mentions partial_conclusions
    messages = [{"role": "system", "content": SYSTEM_PROMPT_NCM + "\npartial_conclusions = []"}] + messages
    last_search_query = None
    while True:
        # include partial_conclusions in the planning context
        planning_message = {
            "role": "system",
            "content": "Current partial conclusions:\n- " + "\n- ".join(partial_conclusions)
        }
        full_context = messages + [planning_message]
        content = get_llm_response(full_context)
        # print('partial_conclusions:', partial_conclusions, '\n\n')
        print('content:', content)

 
        try:
            action_obj = json.loads(content)
        except json.JSONDecodeError:
            # if it's not JSON, give up and return raw
            return content, selected_urls
 
        action = action_obj.get("action")
        if action == "search":
            print('esta em search')
            query = action_obj["query"]
      

            last_search_query = query
            urls = duckduckgo_search(query)
            print('URLS:', urls)
            formatted = "\n".join(f"[{i}] {u}" for i, u in enumerate(urls))
            messages.append({
                "role": "user",
                "content": (
                    f"Search results for '{query}':\n{formatted}\n"
                    "Respond with JSON: {\"action\":\"select\",\"index\":<number>}"
                )
            })

            action_obj['last_search_query'] = last_search_query
            partial_conclusions.append(json.dumps(action_obj))


            time.sleep(3)
 
        elif action == "select":
            print('esta em select')
            idx = action_obj.get("index")
            if idx is None or idx < 0 or idx >= len(urls):
                messages.append({
                    "role": "user",
                    "content": f"Index {idx} out of range. Choose between 0 and {len(urls)-1}."
                })
                continue
 
            url = urls[idx]
            print('url:', url)
            if url in selected_urls:
                messages.append({
                    "role": "user",
                    "content": f"URL '{url}' already visited. Pick a different index."
                })
                continue
 
            selected_urls.append(url)
            try:
                snippet = fetch_url_content(url)
                summary = get_llm_response([
                    {"role": "system", "content": "Summarize this content in 1 sentence with that is relevant to the user's final answer:"},
                    {"role": "user", "content": snippet}
                ])
            except Exception as e:
                summary = f"Failed to fetch content from {url}: {e}"
 
            # ask LLM to extract a partial conclusion
            conclusion = summary
           
            action_obj['last_search_query'] = last_search_query
            action_obj['selected_url'] = url
            action_obj['conclusion'] = conclusion.strip()
            partial_conclusions.append(json.dumps(action_obj))

            print('CONCLUSION:', conclusion)
 
            # feed both summary and conclusion back into messages for continued planning
            messages.append({
                "role": "user",
                "content": (
                    f"Content from '{url}':\n{summary}\n"
                    f"Partial conclusion: {conclusion}\n"
                    "Based on this, respond with JSON: {\"action\":\"search\",\"query\":\"...\"}, "
                    "or {\"action\":\"select\",\"index\":<number>}, or {\"action\":\"answer_before_db_search\",\"answer_before_db_search\":\"...\"}."
                )
            })
 
        elif action == "answer_before_db_search":
            print('ESTA EM ANSWER BEFORE DB SEARCH:', action_obj["answer_before_db_search"])
            messages.append({
                "role": "user",
                "content": (
                    f"You have just suggest the NCM before db search: {action_obj["answer_before_db_search"]}\n"
                    "Based on this, respond with JSON: {\"action\":\"answer_with_db\",\"answer_with_db\":<final_answer>\"...\"}."
                )
            })

            continue

           
        elif action == "answer_with_db":
            print('ESTA EM ANSWER WITH DB')
            print('OBJECT:', action_obj["answer_with_db"])
            print('Esta em answer with db: ')
            cur = conn.cursor()
            cur.execute("""
                SELECT n.ncm_id, n.ncm, n.description
                FROM ncm n
                WHERE n.ncm = %s
                LIMIT 1
            """, (action_obj["answer_with_db"],))

            row  = cur.fetchone()
            print('ROW:', row)

            if row:
                return row[1]
            else:
                messages.append({
                "role": "user",
                "content": (
                    f"NCM {action_obj["answer_with_db"]} does not exist in Database\n"
                    "Based on this, respond with JSON: {\"action\":\"search\",\"query\":\"...\"}, "
                    "or {\"action\":\"select\",\"index\":<number>}."
                )
            })


 
        else:
            # unrecognized action: bail out
            return content, selected_urls


def run_agent_datasheet(messages):
    urls = []
    selected_urls = []
    partial_conclusions = []
 
    # seed with system prompt that mentions partial_conclusions
    messages = [{"role": "system", "content": SYSTEM_PROMPT_DATASHEET + "\npartial_conclusions = []"}] + messages
    last_search_query = None
    while True:
        # include partial_conclusions in the planning context
        planning_message = {
            "role": "system",
            "content": "Current partial conclusions:\n- " + "\n- ".join(partial_conclusions)
        }
        full_context = messages + [planning_message]
        content = get_llm_response(full_context)
        print('partial_conclusions:', partial_conclusions, '\n\n')
        print('content:', content)
 
        try:
            action_obj = json.loads(content)
        except json.JSONDecodeError:
            # if it's not JSON, give up and return raw
            return content, selected_urls
 
        action = action_obj.get("action")
        if action == "search":
            query = action_obj["query"]
            last_search_query = query
            urls = duckduckgo_search(query)
            formatted = "\n".join(f"[{i}] {u}" for i, u in enumerate(urls))
            messages.append({
                "role": "user",
                "content": (
                    f"Search results for '{query}':\n{formatted}\n"
                    "Respond with JSON: {\"action\":\"select\",\"index\":<number>}"
                )
            })
            time.sleep(3)
 
        elif action == "select":
            idx = action_obj.get("index")
            if idx is None or idx < 0 or idx >= len(urls):
                messages.append({
                    "role": "user",
                    "content": f"Index {idx} out of range. Choose between 0 and {len(urls)-1}."
                })
                continue
 
            url = urls[idx]
            print('url:', url)
            if url in selected_urls:
                messages.append({
                    "role": "user",
                    "content": f"URL '{url}' already visited. Pick a different index."
                })
                continue
 
            selected_urls.append(url)
            try:
                snippet = fetch_url_content(url)
                summary = get_llm_response([
                    {"role": "system", "content": "Summarize this content in 1 sentence with that is relevant to the user's final answer:"},
                    {"role": "user", "content": snippet}
                ])
            except Exception as e:
                summary = f"Failed to fetch content from {url}: {e}"
 
            # ask LLM to extract a partial conclusion
            conclusion = summary
           
            action_obj['last_search_query'] = last_search_query
            action_obj['selected_url'] = url
            action_obj['conclusion'] = conclusion.strip()
            partial_conclusions.append(json.dumps(action_obj))
 
            # feed both summary and conclusion back into messages for continued planning
            messages.append({
                "role": "user",
                "content": (
                    f"Content from '{url}':\n{summary}\n"
                    f"Partial conclusion: {conclusion}\n"
                    "Based on this, respond with JSON: {\"action\":\"search\",\"query\":\"...\"}, "
                    "or {\"action\":\"select\",\"index\":<number>}, or {\"action\":\"answer\",\"answer\":\"...\"}."
                )
            })
 
        elif action == "answer":
            return action_obj["answer"]
 
        else:
            # unrecognized action: bail out
            return content, selected_urls