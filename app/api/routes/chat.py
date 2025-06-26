import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import text


from database import get_db
from schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# memória simples para sessões
chat_sessions: dict[str, list[dict]] = {}

# SYSTEM_PROMPT = """
# Você é um assistente que, dependendo do caso, gera consultas SQL para um catálogo de produtos PostgreSQL ou responde diretamente a perguntas fora de contexto de banco de dados.

# Esquema do banco:
# O esquema do banco é:

# — **products**  
#   • product_id (PK)  
#   • product (nome do produto)  
#   • manufacturer  
#   • part_number  
#   • description (texto livre com características)  
#   • datasheet (URL)  
#   • price  
#   • type_id → referencia **types**(type_id, text, description)  
#   • ncm_id  → referencia **ncm**(ncm_id, code, description)

# — **types**  
#   • type_id  
#   • type (nome do type)  
#   • description  

# — **ncm**  
#   • ncm_id  
#   • ncm (o código NCM)  
#   • description  


# Fluxo:
# 1) Receba o prompt do usuário.
# 2) Você deve responder **APENAS** com:
#    - Uma instrução SQL (começando com SELECT) quando for algo que exija buscar dados.
#    - OU texto livre, quando for pergunta de opinião, comentário, explicação, etc.
# 3) Se gerar SQL, o host vai executá-lo e chamar você de novo com:
#      user → `"RESULTS: <JSON rows>"`
#    Então você filtra/aplica lógica e retorna **só** o texto final em linguagem natural.
# """

SYSTEM_PROMPT = """
Você é um assistente que, dependendo do caso, gera consultas SQL para um catálogo de produtos PostgreSQL ou responde diretamente a perguntas fora de contexto de banco de dados.

Esquema do banco:
O esquema do banco é:

— **products**  
  • product_id (PK)  
  • product (nome do produto)  
  • manufacturer  
  • part_number  
  • description (texto livre com características)  
  • datasheet (URL)  
  • price  
  • type_id → referencia **types**(type_id, text, description)  
  • ncm_id  → referencia **ncm**(ncm_id, code, description)

— **types**  
  • type_id  
  • type (nome do type)  
  • description  

— **ncm**  
  • ncm_id  
  • ncm (o código NCM)  
  • description  

Fluxo:
1) Receba o prompt do usuário.  
2) Você deve responder **APENAS** com:
   - Uma instrução SQL **básica** (começando com `SELECT`) quando for algo que exija buscar dados.
   - OU texto livre, quando for pergunta de opinião, comentário, explicação, etc.

   **Regras de ouro para o SQL**  
   1. Use sempre aliases: `products p`, `types t`, `ncm n`.  
   2. Qualifique TODAS as colunas com seu alias: `p.description`, `t.description`, `n.description`.  
   3. **Nunca** inclua no SQL **nenhum** filtro sobre `description` — mesmo que o usuário peça “produtos que mencionem X” ou “até Y GB de RAM”.  
      - Se o critério envolver texto livre ou análise de `description`, gere somente um SQL que traga **todas** as linhas relevantes, incluindo `p.description`.  
      - Deixe a LLM, no segundo turno (após receber `RESULTS: {...}`), aplicar toda lógica de interpretação das descrições.

3) Se você gera SQL, o host o executa e chama você de novo com:
     user → `"RESULTS: <JSON rows>"`
   Então você filtra/aplica lógica em **texto livre** e retorna somente o `answer` em linguagem natural.
"""


@router.post("/chat", response_model=ChatResponse)
async def chat_sql(
    req: ChatRequest,
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(None),
):
    print("→ INCOMING X_SESSION_ID:", x_session_id)
    # 0) (re)cria sessão
    if not x_session_id or x_session_id not in chat_sessions:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = [{"role":"system","content":SYSTEM_PROMPT}]
    else:
        session_id = x_session_id

    history = chat_sessions[session_id]
    history.append({"role":"user","content":req.prompt})

    # 1) Peça ao modelo a “primeira resposta”
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=history,
        temperature=0
    )
    assistant_msg = completion.choices[0].message.content.strip()
    history.append({"role":"assistant","content":assistant_msg})

    print("PRIMEIRA ASSISTANT MSG:", assistant_msg)

    # 2) Se NÃO for SQL (não começa com SELECT), devolva direto:
    if not assistant_msg.lstrip().upper().startswith("SELECT"):
        return ChatResponse(
            session_id=session_id,
            answer=assistant_msg
        )

    # 3) Caso seja SQL, executa e reenvia RESULTS:
    sql = assistant_msg
    try:
        print('ANTES DE EXECUTE')
        result = db.execute(text(sql))
        print('result EXECUTE:', result)
        rows = result.mappings().all()
        columns = result.keys()
    except Exception as e:
        print(e)
        raise HTTPException(400, f"Erro no SQL: {e}")

    # 4) Adiciona ao histórico e chama de novo para LLM filtrar
    results_json = {"columns": columns, "rows": rows}
    history.append({"role":"user","content":f"RESULTS: {results_json}"})

    print("RESULTS_JSON:", results_json)

    completion2 = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=history,
        temperature=0
    )
    final_answer = completion2.choices[0].message.content.strip()
    history.append({"role":"assistant","content":final_answer})

    return ChatResponse(
        session_id=session_id,
        answer=final_answer
    )
