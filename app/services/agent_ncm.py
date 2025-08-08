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
import re
import tiktoken

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_URL")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

USER_AGENT       = "Mozilla/5.0 (compatible; Agent/1.0)"

conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")



SYSTEM_PROMPT_NCM = """

You are an autonomous agent that can use tools via JSON actions. Your goal is to generate the NCM (Nomenclatura Comum do Mercosul) of a product based on a PostgreSQL database which contains all of the official 
NCM (Nomenclatura comum do mercosul) codes.
You will receive the product's descprition.Based on this description, you'll generate a SQL query to execute a search in the database based on the context of the product that the user gave you. It's important to consider the product type to determine whether the description of the ncm is valid or not.
#Consider that the description might be in other languages besides English – like Portuguese or Spanish. If the description is in Portuguese, maintain it. If not, translate it to Portuguese.

You maintain a list called `partial_conclusions` where you store takeaways from each action you execute.
All outputs must be a single valid JSON object with exactly one of two actions: 'search_in_db', 'answer'.

***IMPORTANT***
Consider that the database is in portuguese. So please generate the SQL queries ONLY IN PORTUGUESE.

THE NCM answer MUST ALWAYS follow the following format:
XXXX.XX.XX (four numbers, a dot, two numbers, a dot and two numbers)

The description field may include several hierarchical NCM entries (e.g. 01: …, 01.02: …, 0102.2: …, 0102.21: …, 0102.21.10: …). 
Only the final, full eight‑digit code in the XXXX.XX.XX format is the valid one. Always ignore any shorter or higher‑level codes and extract only that last, correct NCM

If you answered with a NCM code that the user said that it was in the wrong format or that it doesn't exist in the database, DO NOT ANSWER AGAIN WITH THIS NCM.

NEVER GUESS values. Only use information extracted by the search in the database.

***************

If needed, generate as many SQL queries as you want and execute them in the database until you find the proper NCM and NEVER use the same SQL query twice.





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
    - 'search_in_db' with an 'sql_query' field to execute the query generated after determining what the product is. THE QUERIES MUST BE ONLY IN PORTUGUESE
    - 'answer' with an 'answer' field containing ONLY the NCM. NEVER EVER RETURN A NCM CODE IN A FORMAT  DIFFERENT THAN XXXX.XX.XX (four numbers, a dot, two numbers, a dot and two numbers)


 
***GOLDEN RULES FOR SQL***
1. Always produce a basic SELECT statement (starting with "SELECT")—no INSERT/UPDATE/DELETE.
   2. Use table aliases: ncm n.
   3. Qualify ALL columns with their alias (e.g. n.description).
   4. If the criterion involves free-text analysis of description, select all relevant rows (including p.description) and defer filtering to the next turn.
******************

Example output:
{
  "action": "search_in_db",
  "sql_query": "SELECT n.ncm, n.description FROM ncm WHERE n.description ILIKE (...)"
}
    
"""


def count_tokens(string: str, encoding_name = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens    


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

        # full_context = truncate_messages_to_token_limit(full_context)

        content = get_llm_response(full_context)
        messages.append({"role":"assistant", "content": content})
        # print('partial_conclusions:', partial_conclusions, '\n\n')
        print('content:', content)

 
        try:
            action_obj = json.loads(content)
        except json.JSONDecodeError:
            # if it's not JSON, give up and return raw
            return content, selected_urls
 
        action = action_obj.get("action")

        if action == "search_in_db":
            cur = conn.cursor()
            sql = action_obj["sql_query"]
            cur.execute(sql)

            results = cur.fetchall()


            print('RESULTS SQL QUERY:', results)


            if results:
                print('TYPE RESULTS:', type(results))
                num_tokens_results_db = count_tokens(str(results))
                print('NUMERO DE TOKENS NOS RESULTADOS DA DB:', num_tokens_results_db)


                if num_tokens_results_db > 20000:
                    messages.append({
                    "role": "user",
                        "content": (
                            f"Too many results found in the database with the query {sql}. This will consume too many tokens. Try another SQL query\n"
                            "Respond with JSON: sql_query {\"action\":\"search_in_db\",\"sql_query\":\"...\"}. "
                        )
                    })

                    continue

                # summarized_results = summarize_relevant(results, context, client)

                messages.append({
                    "role": "user",
                    "content": (
                        f"Content found in the database: {results}\n"
                        "Based on this, if you have enough information respond with JSON: {\"action\":\"answer\",\"answer\":\"...\"}. "
                        "if you don't, respond with JSON with another sql_query {\"action\":\"search_in_db\",\"sql_query\":\"...\"}."
                    )
                })
                continue
            else:
                messages.append({
                    "role": "user",
                    "content": (
                        f"No content found in the database with query {sql}\n"
                        "respond with JSON {\"action\":\"search_in_db\",\"sql_query\":\"...\"}."
                    )
                })
                continue


        elif action == "answer":
            ncm = action_obj["answer"]
            print('NCM answer:', ncm)

            pattern = r'^\d{4}\.\d{2}\.\d{2}$'

            if re.match(pattern, ncm):
                cur = conn.cursor()
                cur.execute("""
                    SELECT n.ncm_id, n.ncm, n.description
                    FROM ncm n
                    WHERE n.ncm = %s
                    LIMIT 1
                """, (ncm,))

                row  = cur.fetchone()

                if row:
                    return ncm
                
                else:
                  messages.append({
                    "role": "user",
                    "content": (
                        f"Answer given by LLM: {action_obj} \n"
                        f"NCM {ncm} does NOT EXIST in the database. Find another NCM code by searching another NCM code in the database. In this case, you can repeat the last query you used. NEVER answer again with ncm {ncm}\n"
                        ""
                        "Respond with ONLY with JSON {\"action\":\"search_in_db\",\"sql_query\":\"...\"}."
                        )
                    })
                  continue
            else:
                # 2) Se não for válido, detecta se é uma mensagem de texto (contém letras/acentos)
                if re.search(r'[A-Za-zÀ-ÖØ-öø-ÿ]', ncm):
                    # É texto de erro ou comentário
                    return 'Not found'
                    # aqui você pode tratar conforme desejar
                    # ex: lançar exceção, gerar nova query, etc.
                else:
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Answer given by LLM: {action_obj}\n"
                            f"NCM {ncm} does not have format XXXX.XX.XX (four numbers, a dot, two numbers, a dot and two numbers) and thus doesn't exist in the database. Correct the format before answering by doing another search to find the correct NCM. YOU CAN'T answer in a format other than XXXX.XX.XX (four numbers, a dot, two numbers, a dot and two numbers)\n"
                            "respond ONLY with JSON {\"action\":\"search_in_db\",\"sql_query\":\"...\"}."
                        )
                    })
                    continue
        else:
            print('CAIU NO ELSE:', action_obj)
            # unrecognized action: bail out
            return 'error'





# def run_agent_datasheet(messages):
#     urls = []
#     selected_urls = []
#     partial_conclusions = []
 
#     # seed with system prompt that mentions partial_conclusions
#     messages = [{"role": "system", "content": SYSTEM_PROMPT_DATASHEET + "\npartial_conclusions = []"}] + messages
#     last_search_query = None
#     while True:
#         # include partial_conclusions in the planning context
#         planning_message = {
#             "role": "system",
#             "content": "Current partial conclusions:\n- " + "\n- ".join(partial_conclusions)
#         }
#         full_context = messages + [planning_message]
#         content = get_llm_response(full_context)
#         print('partial_conclusions:', partial_conclusions, '\n\n')
#         print('content:', content)
 
#         try:
#             action_obj = json.loads(content)
#         except json.JSONDecodeError:
#             # if it's not JSON, give up and return raw
#             return content, selected_urls
 
#         action = action_obj.get("action")
#         if action == "search":
#             query = action_obj["query"]
#             last_search_query = query
#             urls = duckduckgo_search(query)
#             formatted = "\n".join(f"[{i}] {u}" for i, u in enumerate(urls))
#             messages.append({
#                 "role": "user",
#                 "content": (
#                     f"Search results for '{query}':\n{formatted}\n"
#                     "Respond with JSON: {\"action\":\"select\",\"index\":<number>}"
#                 )
#             })
#             time.sleep(3)
 
#         elif action == "select":
#             idx = action_obj.get("index")
#             if idx is None or idx < 0 or idx >= len(urls):
#                 messages.append({
#                     "role": "user",
#                     "content": f"Index {idx} out of range. Choose between 0 and {len(urls)-1}."
#                 })
#                 continue
 
#             url = urls[idx]
#             print('url:', url)
#             if url in selected_urls:
#                 messages.append({
#                     "role": "user",
#                     "content": f"URL '{url}' already visited. Pick a different index."
#                 })
#                 continue
 
#             selected_urls.append(url)
#             try:
#                 snippet = fetch_url_content(url)
#                 summary = get_llm_response([
#                     {"role": "system", "content": "Summarize this content in 1 sentence with that is relevant to the user's final answer:"},
#                     {"role": "user", "content": snippet}
#                 ])
#             except Exception as e:
#                 summary = f"Failed to fetch content from {url}: {e}"
 
#             # ask LLM to extract a partial conclusion
#             conclusion = summary
           
#             action_obj['last_search_query'] = last_search_query
#             action_obj['selected_url'] = url
#             action_obj['conclusion'] = conclusion.strip()
#             partial_conclusions.append(json.dumps(action_obj))
 
#             # feed both summary and conclusion back into messages for continued planning
#             messages.append({
#                 "role": "user",
#                 "content": (
#                     f"Content from '{url}':\n{summary}\n"
#                     f"Partial conclusion: {conclusion}\n"
#                     "Based on this, respond with JSON: {\"action\":\"search\",\"query\":\"...\"}, "
#                     "or {\"action\":\"select\",\"index\":<number>}, or {\"action\":\"answer\",\"answer\":\"...\"}."
#                 )
#             })
 
#         elif action == "answer":
#             return action_obj["answer"]
 
#         else:
#             # unrecognized action: bail out
#             return content, selected_urls