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
from services.agent_description import run_agent_ncm, run_agent_datasheet

router = APIRouter()
load_dotenv()



# Inicializa o cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_URL = os.getenv("POSTGRES_URL")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# Cria um Assistente com busca em arquivos ativada
assistant = client.beta.assistants.create(
    name="Technical Datasheet Assistant",
    instructions="""You are a specialized technical datasheet assistant. Given the contents of a product datasheet PDF, you must:

    1. Identify the product **type** by matching against the keys in the JSON object below.
    2. For the determined type, extract **exactly** all properties listed in its value string—no more, no fewer—preserving order and units.
    3. If any property cannot be found in the source, set its value to "Not found".
    4. Do not guess or fabricate any data.
    5. Additionally, extract these top‐level fields from the datasheet:
   - **product**: the official product name as written prominently on the datasheet.
   - **part number**: the manufacturer’s SKU or model code.
   - **manufacturer**: the company name that makes the product.
   - **NCM**: the 8-digit Mercosul classification code, if available in the datasheet; if not, you may determine the most appropriate NCM based on the product’s description or “Not found” if uncertain. When extracting or generating an NCM code, format it as 1234.56.78 (four digits, a dot, two digits, a dot, two digits).
   - **datasheet**: the URL or file path where the full PDF datasheet can be downloaded; if the PDF itself does not include a URL, you may supply a reasonable public link (e.g. manufacturer’s website) or “Not found” if unavailable.
    5. Return your result strictly in this JSON format (no extra commentary):

    {
    "product": "<value>",
    "part number": "<value>",
    "manufacturer": "<value>",
    "NCM": "<value>",
    "datasheet": <value>,
    "type": {
        "name": "<type>",
        "<property 1>": "<value>",
        "<property 2>": "<value>",
        …
    }
    }

    ---

Types and their required properties:
    

  {
  "Keyboard": "key type (mechanical/membrane), layout (e.g. ANSI/ISO), connectivity (wired/wireless)",
  "Conference System": "microphone channels, speaker output power (W), frequency response (Hz), noise cancellation, connectivity (Ethernet/Wi-Fi/Bluetooth), control interface, power supply (PoE/adapter), dimensions (mm), mounting options",
  "Notebook": "processor model, RAM size (GB), storage type and capacity (GB), display size (inches) and resolution, battery capacity (Wh), graphics (GPU), weight (kg), port selection (USB/HDMI/etc.), operating system",
  "Monitor": "screen size (inches), resolution, panel type (IPS/VA/TN), refresh rate (Hz), brightness (cd/m²), contrast ratio, response time (ms), connectivity (HDMI/DP/VGA), aspect ratio",
  "Smartphone": "display size (inches) and resolution, processor chipset, RAM (GB), storage (GB), battery capacity (mAh), rear/front camera (MP), operating system, connectivity (5G/Wi-Fi/Bluetooth), dimensions (mm), weight (g)",
  "Speaker": "power output (W RMS), frequency response (Hz), impedance (Ω), sensitivity (dB), driver size (inches), connectivity (wired/Bluetooth/Wi-Fi), enclosure type, dimensions (mm), weight (kg)",
  "Videobar all-in-one": "video resolution (e.g. 4K), field of view (°), microphone array (count), speaker output (W), beamforming technology, connectivity (USB/PoE), built-in DSP features, mounting options, dimensions (mm)",
  "Unknown item": application
   }

    ### Output Examples

    **Example 1: All properties found**  
    The PDF provided every Monitor specification:

    ```json
        {
        "part number": "P2422H",
        "product": Dell 24 Monitor P2422H"
        "manufacturer": "Dell",
        "NCM": "8528.52.00",
        "datasheet": https://www.delltechnologies.com/asset/en-us/products/electronics-and-accessories/technical-support/dell-24-monitor-p2422h-datasheet.pdf
        "type": {
            "name": "Monitor",
            "screen size (inches)": "23.8",
            "resolution": "1920x1080",
            "panel type": "IPS",
            "refresh rate (Hz)": "60",
            "brightness (cd/m²)": "250",
            "contrast ratio": "1000:1",
            "response time (ms)": "5",
            "connectivity": "HDMI, DisplayPort, VGA",
            "aspect ratio": "16:9"
            }
        }

    **Example 2: Some properties missing**
    The datasheet did not mention “battery type” or “transfer time”; those fields are set to "Not found":

       {
        "part number": "P2422H",
        "product": Dell 24 Monitor P2422H"
        "manufacturer": "Dell",
        "NCM": "8528.52.00",
        "datasheet": Not found,
        "type": {
            "name": "Monitor",
            "screen size (inches)": "23.8",
            "resolution": "Not found",
            "panel type": "IPS",
            "refresh rate (Hz)": "60",
            "brightness (cd/m²)": "Not found",
            "contrast ratio": "1000:1",
            "response time (ms)": "Not found",
            "connectivity": "HDMI, DisplayPort, VGA",
            "aspect ratio": "16:9"
            }
        }


    """,
    model="gpt-4.1-mini",
    tools=[{"type": "file_search"}]
)

question_mapping = {
    "product": "what is the name of the product?",
    "part_number": "what is the part number of the product?",
    "manufacturer": "who is the manufacturer of the product?",
    "NCM": "what is the Nomenclatura Comum do Mercosul (NCM) of the product? You can answer this even if this information isn't provided in the document. If that's the case, answer it based on your knowledge.  When extracting or generating an NCM code, format it as 1234.56.78 (four digits, a dot, two digits, a dot, two digits).",
    "datasheet": "what is the URL of the product's datasheet? You can answer this even if this information isn't provided in the document. If that's the case, answer it based on your knowledge",
    "type": "what is the type of the product? It can be Keyboard, Conference System, Notebook, Monitor, Smartphone, Speaker, Videobar all-in-one or Unknown item.",
    "if this document is related to a Conference System, return": '''{
      "microphone channels": "value",
      "speaker output power (W)": "value",
      "frequency response (Hz)": "value",
      "noise cancellation": "value",
      "connectivity (Ethernet/Wi-Fi/Bluetooth)": "value",
      "control interface": "value",
      "power supply (PoE/adapter)": "value",
      "dimensions (mm)": "value",
      "mounting options": "value"
    }'''.strip(),
    "if this document is related to a Notebook, return": '''{
      "processor model": "value",
      "RAM size (GB)": "value",
      "storage type and capacity (GB)": "value",
      "display size (inches) and resolution": "value",
      "battery capacity (Wh)": "value",
      "graphics (GPU)": "value",
      "weight (kg)": "value",
      "port selection (USB/HDMI/etc.)": "value",
      "operating system": "value"
    }'''.strip(),
    "if this document is related to a Monitor, return": '''{
      "screen size (inches)": "value",
      "resolution": "value",
      "panel type (IPS/VA/TN)": "value",
      "refresh rate (Hz)": "value",
      "brightness (cd/m²)": "value",
      "contrast ratio": "value",
      "response time (ms)": "value",
      "connectivity (HDMI/DP/VGA)": "value",
      "aspect ratio": "value"
    }'''.strip(),
    "if this document is related to a Smartphone, return": '''{
      "display size (inches) and resolution": "value",
      "processor chipset": "value",
      "RAM (GB)": "value",
      "storage (GB)": "value",
      "battery capacity (mAh)": "value",
      "rear/front camera (MP)": "value",
      "operating system": "value",
      "connectivity (5G/Wi-Fi/Bluetooth)": "value",
      "dimensions (mm)": "value",
      "weight (g)": "value"
    }'''.strip(),
    "if this document is related to a Speaker, return": '''{
      "power output (W RMS)": "value",
      "frequency response (Hz)": "value",
      "impedance (Ω)": "value",
      "sensitivity (dB)": "value",
      "driver size (inches)": "value",
      "connectivity (wired/Bluetooth/Wi-Fi)": "value",
      "enclosure type": "value",
      "dimensions (mm)": "value",
      "weight (kg)": "value"
    }'''.strip(),
    "if this document is related to a Videobar all-in-one, return": '''{
      "video resolution (e.g. 4K)": "value",
      "field of view (°)": "value",
      "microphone array (count)": "value",
      "speaker output (W)": "value",
      "beamforming technology": "value",
      "connectivity (USB/PoE)": "value",
      "built-in DSP features": "value",
      "mounting options": "value",
      "dimensions (mm)": "value"
    }'''.strip(),
    "if this document is related to an Unknown item, return": '''{
      "application": "value"
    }'''.strip()
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

        # question_ncm =  [{"role": "user", "content": f"I will describe you a product and I want you to return me the NCM (Nomenclatura Comum do Mercosul) of this product. Name of the product: {data["product"]}; Part Number: {data["part_number"]}; Manufacturer: {data["manufacturer"]}"}]
        # question_datasheet =  [{"role": "user", "content": f"I will describe you a product and I want you to return me the URL of the PDF datasheet of this product. Name of the product: {data["product"]}; Part Number: {data["part_number"]}; Manufacturer: {data["manufacturer"]}"}]


        # ncm = None
        # datasheet_url = None
        # try:
        #     ncm = run_agent_ncm(question_ncm)
        #     datasheet_url = run_agent_datasheet(question_datasheet)
        # except Exception as e:
        #     print('Erro detectado:', e)        

        # print('NCM:' , ncm)
        # print('datasheer URL:',datasheet_url)


        # resp.raise_for_status()

        return JSONResponse(status_code=resp.status_code, content=resp.json())


        


    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    # finally:
    #     if os.path.exists(temp_path):
    #         os.remove(temp_path)


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
