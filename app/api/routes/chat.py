import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import text
import json


from database import get_db
from schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# memória simples para sessões
chat_sessions: dict[str, list[dict]] = {}


new_system_prompt = """
You are an assistant who, depending on the situation, either generates SQL queries for a PostgreSQL product catalog or directly answers questions that fall outside the database context.
All outputs must be a single valid JSON object with exactly one of three actions: "search"or "answer".

Database schema:
- products p
    • p.product_id        (PK)
    • p.product           (product name)
    • p.manufacturer
    • p.part_number
    • p.description       (free text with characteristics)
    • p.datasheet         (URL)
    • p.price
    • p.type_id → types t (t.type_id, t.type, t.description)
- types t
    • t.type_id
    • t.type
    • t.description
- ncm n
    • n.ncm_id
    • n.ncm       (NCM code)
    • n.description

At each step you MUST:
1) Review the user's current prompt together with your full history to decide:
     – If it requires fetching structured data from the product catalog, proceed to choose the "search" action.
     – If it does NOT require any database lookup (e.g. commentary, opinion, explanation, conceptual question), immediately choose the "answer" action and provide your natural-language response.
2) Consult your history to determine what information is still missing and avoid re-issuing queries that already succeeded or failed.
3) Choose exactly one action:
   • "search" with a "query" field to fetch data:
     {
       "action": "search",
       "query": "<basic SELECT statement>"
     }
   
   • "answer" with an "answer" field once you have enough context (or when the prompt does not require a DB query):
     {
       "action": "answer",
       "answer": "<final response text in markdown>"
     }

4) Golden rules for SQL:
   1. Always produce a basic SELECT statement (starting with "SELECT")—no INSERT/UPDATE/DELETE.
   2. Use table aliases: products p, types t, ncm n.
   3. Qualify ALL columns with their alias (e.g. p.product_id, t.description, n.description).
   4. Never include any filter on p.description—even if the user asks “products that mention X” or “up to Y GB of RAM”.
   5. If the criterion involves free-text analysis of description, select all relevant rows (including p.description) and defer filtering to the next turn.

5) After each cycle:
   • Evaluate whether the user's most recent prompt has been fully and correctly addressed.
     – If it has, emit only the "answer" action with your final natural-language answer.
     – If it has not, repeat steps 1–4 to refine your SQL or interpretation, but do NOT re-execute any "search" actions that already succeeded.
"""



@router.post("/chat", response_model=ChatResponse)
async def chat_sql(
    req: ChatRequest,
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(None),
):
    new_user_prompt = True
    print("→ INCOMING X_SESSION_ID:", x_session_id)
    # 0) (re)cria sessão
    if not x_session_id or x_session_id not in chat_sessions:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = [{"role":"system","content":new_system_prompt}]
    else:
        session_id = x_session_id

    while True:
        print('INÍCIO DO LOOP')
        history = chat_sessions[session_id]
        print('HISTORY:', history)

        print(len(history))

        if new_user_prompt:
            history.append(
                {"role": "user", "content": req.prompt}
            )
            new_user_prompt = False


       

        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=history,
            temperature=0
        )


        

        raw = completion.choices[0].message.content.strip()
        print('RAW:', raw)

        try:
            assistant_msg = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail=f"Could not parse JSON from model:\n{raw}"
            )

        if assistant_msg.get('action') == 'search':
            sql = assistant_msg["query"]
            try:
                result = db.execute(text(sql))
                rows = result.mappings().all()
                columns = result.keys()
            except Exception as e:
                print(e)
                raise HTTPException(400, f"Erro no SQL: {e}")
            
            results_json = {"columns": columns, "rows": rows}
            print('RESULTS JSON:', results_json)

            history.append({"role":"user","content":req.prompt})
            history.append({"role": "assistant", "content": raw})


            history.append({"role": "user", "content": (
                    f"Results extracted from database: {results_json}\n"
                    "Based on this, respond with JSON {\"action\":\"answer\",\"answer\":\"...\"}, "
                    "or {\"action\":\"search\",\"query\":\"...\"}"
                )
            })

            
            continue

        elif assistant_msg.get("action") == "answer":
            history.append({"role":"assistant","content":raw})

            return ChatResponse(
                session_id=session_id,
                answer=assistant_msg.get("answer")
            )
        
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Problem with the LLM:\n{raw}"
            )




