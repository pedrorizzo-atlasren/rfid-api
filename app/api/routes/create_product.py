from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
from schemas.product import RegisterProduct
from fastapi import Depends
from sqlalchemy.orm import Session
from models.product import Product
from models.types import Type
from models.ncm import NCM
from database import get_db
import re
from sqlalchemy import select, func
from langchain_postgres.vectorstores import PGVector
from langchain_community.embeddings import OpenAIEmbeddings
import psycopg2
import requests
import json
from services.agent_ncm import run_agent_ncm
from services.decription_type_prompt import description_type_prompt

router = APIRouter()
load_dotenv()



# Inicializa o cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_URL = os.getenv("POSTGRES_URL")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")



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


question_mapping = {
    "product": "what is the name of the product?",
    "part_number": "what is the part number of the product?",
    "manufacturer": "who is the manufacturer of the product?",
    "Technical information": "Provide a comprehensive technical description of the product, covering specifications, materials, performance metrics, and design details.",
    "Summary": "Give a concise overview of the product’s purpose, highlight its key features, and describe its primary functionality."
}




@router.post("/extract-description")
async def extract_description(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # Salva o arquivo temporariamente
        suffix = os.path.splitext(file.filename)[-1]
        # with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        #     temp_path = tmp.name
        #     contents = await file.read()
        #     tmp.write(contents)


        data = {
            "questions_mapping": json.dumps(question_mapping)
        }
        # files = {
        #     # o ‘file’ deve ter o mesmo nome de campo usado pelo serviço externo
        #     "file": open(temp_path, "rb")
        # }
        files = {
            "file": (file.filename, file.file, file.content_type or "application/pdf")
        }

        url = "https://core-staging.atlasren.com/pdf/process-invoice"
        headers = {
            "X-API-Key": "odoostaging_key4gg@wQqLJ8EWsuWA",
            "Accept": "application/json",
            # Note que não é necessário definir Content-Type:
            # o requests faz isso automaticamente para multipart/form-data
        }

        
        # Abrimos o arquivo DENTRO do with para garantir que será fechado logo após o POST
        # with open(temp_path, "rb") as f:
        #     files = {"file": f}
        #     resp = requests.post(url, headers=headers, data=data, files=files)
        #     resp.raise_for_status()
        #     return JSONResponse(status_code=resp.status_code, content=resp.json())

        resp = requests.post(url, headers=headers, data=data, files=files)

        if resp.status_code >= 400:
            print('esta em >= 400')
            # tenta parsear como JSON; se falhar, usa texto puro
            try:
                error_content = resp.json()
                print('error_content:', error_content)
            except ValueError:
                print('ValueError')
                error_content = resp.text

            # opcional: você pode logar também no servidor:
            # print(f"Erro na API externa ({resp.status_code}): {error_content}")

            # retorna o status e corpo de erro
            return JSONResponse(status_code=resp.status_code, content={
                "external_api_error": error_content
            })
        
        print('antes de resp wo')
        resp_withou_ncm_and_datasheet = resp.json()
        print('RESP_WO_NCM_DATASHEET', resp_withou_ncm_and_datasheet)

      

        data = resp_withou_ncm_and_datasheet["results"]
        product = data["product"]
        manufacturer = data["manufacturer"]
        technical_description = data["Technical information"]
        summary = data["Summary"]
        part_number = data["part_number"]
        print(manufacturer, part_number)

        prompt_type_description = description_type_prompt(product, manufacturer, technical_description, summary)
  

        type_and_description = get_llm_response([{"role": "user", "content": prompt_type_description}])

        answer_object = json.loads(type_and_description)

        product_type = answer_object["type"]



        prompt_ncm =  [{"role": "user", "content": f"""I will describe you an item and I want you to answer me the NCM (Nomenclatura Comum do Mercosul) of the item for tax reasons. 
                  The description may be in any language (English, Portuguese, Spanish, etc.). Description: {product};type of the product: {product_type}  ;manufacturer of the product: {manufacturer}; summary about the product: {summary}.
                """}]

        ncm = run_agent_ncm(prompt_ncm)

        answer_object['product'] = product
        answer_object['manufacturer'] = manufacturer
        answer_object['part_number'] = part_number
        answer_object['NCM'] = ncm

        print("TYPE AND DESCRIPTION:", answer_object)

        print(type(answer_object))

        return JSONResponse(status_code=resp.status_code, content=answer_object)


        


    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)




# distância máxima de cosine para considerar “muito parecido”
SIMILARITY_THRESHOLD = 0.8
# quantos candidatos queremos de volta
TOP_K = 5

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


@router.post("/submit-product", response_model=RegisterProduct)
async def submit_product(
    request: Request,
    payload: RegisterProduct,
    db: Session = Depends(get_db),
):

    # # 1) Verifica unicidade de part_number (opcional)
    # exists = db.query(Product).filter_by(part_number=payload.part_number).first()
    # if exists:
    #     raise HTTPException(400, "part_number already exists")
    
    #  2) Garante que existe um registro em types
    type_obj = db.query(Type).filter_by(type=payload.product_type).first()
    if not type_obj:
        raise HTTPException(400, f"Type '{payload.product_type}' não encontrado")

    # 3) Garante que existe um registro em ncm
    ncm_obj = None
    if payload.ncm:
        ncm_obj = db.query(NCM).filter_by(ncm=payload.ncm).first()
        if not ncm_obj:
            raise HTTPException(400, f"NCM '{payload.ncm}' não encontrado")
        
    similar  = []
        
    if not payload.confirm:
        product_text = (
        f"Product: {payload.product}; "
        f"Part Number: {payload.part_number}; "
        f"Manufacturer: {payload.manufacturer}; "
        f"Description: {payload.description or ''}"
        ) 

        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cur = conn.cursor()

        new_embedding = embeddings.embed_query(product_text)

        cur.execute("""
                    SELECT
                        product_id,
                        product,
                        part_number,
                        manufacturer,
                        description,
                        embedding <-> %s::vector AS distance
                        FROM products
                        WHERE embedding <-> %s::vector < %s
                        ORDER BY distance
                        LIMIT %s
                    """, (new_embedding, new_embedding, SIMILARITY_THRESHOLD, TOP_K))
        
        rows = cur.fetchall()

        print('ROWS:', rows)

        similar = [
            {
            "product_id": pid,
            "product":     name,
            "part_number": pn,
            "manufacturer": manu,
            "description":  desc,
            "distance":     dist
            }
            for pid, name, pn, manu, desc, dist in rows
        ]

        print('SIMILAR:', similar)

    # se houver similares e não veio confirm=True, devolve a lista pra front
    if len(similar) > 0:
        return JSONResponse(
            status_code=200,
            content={
                "action": "check_similarity",
                "candidates": similar
            }
        )
    

    new = Product(
        product      = payload.product,
        manufacturer = payload.manufacturer,
        part_number  = payload.part_number,
        description  = payload.description,    # aqui vai a string concatenada
        datasheet    = payload.datasheetURL,
        price        = payload.price,
        type_id      = type_obj.type_id,
        ncm_id       = ncm_obj.ncm_id
    )

    # 3) Persiste no banco
    db.add(new)
    db.commit()
    db.refresh(new)

    # 4) Retorna de volta o objeto salvo (ou apenas um OK)
    return JSONResponse(
        status_code=200,
        content={
            "action": "product_uploaded",
            "content": payload
        }
    )
