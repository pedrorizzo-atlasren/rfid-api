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


router = APIRouter()
load_dotenv()



# Inicializa o cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

@router.post("/extract-description")
async def extract_description(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # Salva o arquivo temporariamente
        suffix = os.path.splitext(file.filename)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            contents = await file.read()
            tmp.write(contents)

        # Faz upload do arquivo para OpenAI
        with open(temp_path, "rb") as f:
            uploaded_file = client.files.create(file=f, purpose="assistants")

        # Cria o thread com o arquivo como anexo
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": "Extract the main technical characteristics of this product datasheet.",
                    "attachments": [
                        {"file_id": uploaded_file.id, "tools": [{"type": "file_search"}]}
                    ]
                }
            ]
        )

        # Cria a execução do assistente
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        # Aguarda a execução completar
        import time
        while True:
            status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if status.status == "completed":
                break
            elif status.status in ["failed", "cancelled"]:
                raise Exception("Run failed or was cancelled.")
            time.sleep(1)

        # Recupera a resposta
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text.value

        return JSONResponse(content={"response": response_text}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# from fastapi import APIRouter, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import tempfile

# router = APIRouter()
# load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# @router.post("/extract-description")
# async def extract_description(file: UploadFile = File(...)):
#     if not file.filename.endswith(".pdf"):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported.")

#     try:
#         # Salva temporariamente
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#             temp_path = tmp.name
#             tmp.write(await file.read())

#         # Faz upload (com handle aberto e fechado corretamente)
#         with open(temp_path, "rb") as f:
#             uploaded_file = client.files.create(file=f, purpose="user_data")

#         # Usa o modelo que suporta PDF como input
#         response = client.chat.completions.create(
#             model="gpt-4.1",  # ✅ Necessário para suportar PDF com input_file
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {"type": "input_file", "file_id": uploaded_file.id},
#                         {"type": "text", "text": "Give a one-line summary of the main technical characteristics of this product datasheet. Format: '24V, 5A, IP67'. If not found, say 'Not found'."}
#                     ]
#                 }
#             ],
#             temperature=0
#         )

#         result = response.choices[0].message.content.strip()
#         return JSONResponse(content={"response": result}, status_code=200)

#     except Exception as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)

#     finally:
#         # Agora o arquivo já foi fechado corretamente e pode ser removido
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

@router.post("/submit-product", response_model=RegisterProduct)
async def submit_product(
    request: Request,
    payload: RegisterProduct,
    db: Session = Depends(get_db)
):

    # 1) Verifica unicidade de part_number (opcional)
    exists = db.query(Product).filter_by(part_number=payload.part_number).first()
    if exists:
        raise HTTPException(400, "part_number already exists")
    
     # 2) Garante que existe um registro em types
    type_obj = db.query(Type).filter_by(type=payload.product_type).first()
    if not type_obj:
        raise HTTPException(400, f"Type '{payload.product_type}' não encontrado")

    # 3) Garante que existe um registro em ncm
    ncm_obj = None
    if payload.ncm:
        ncm_obj = db.query(NCM).filter_by(ncm=payload.ncm).first()
        if not ncm_obj:
            raise HTTPException(400, f"NCM '{payload.ncm}' não encontrado")

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
    return payload
