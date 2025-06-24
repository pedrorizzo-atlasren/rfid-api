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
from database import get_db


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
   - **NCM**: the 8-digit Mercosul classification code, if available in the datasheet; if not, you may determine the most appropriate NCM based on the product’s description or “Not found” if uncertain.
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
  "HMI": "display type, screen size (inches), resolution, interface",
  "UPS": "input voltage (V), output voltage (V), battery type, backup time (min), supply type (AC or DC), rated capacity (kVA), efficiency (%), topology (online/offline), transfer time (ms), weight (kg)",
  "accessory": "accessory type",
  "actuator": "actuator type", 
  "adapter": "input voltage (V), output voltage (V), connector type, power rating (W)",
  "air dryer": "airflow (CFM), operating pressure (bar), power consumption (W)",
  "analyzer": "measured parameters, input range, accuracy, display type",
  "antenna": "frequency range (MHz), gain (dBi), polarization, beamwidth (°), connector type",
  "antenna accessory": "accessory type, compatible antenna types",
  "auxiliary contact": "contact configuration, rated current (A), rated voltage (V)",
  "battery": "nominal voltage (V), capacity (Ah), chemistry, cycle life (cycles), weight (kg), energy density (Wh/kg), internal resistance (mΩ), maximum discharge rate (C), operating temperature range (°C), self-discharge rate (%/month)",  "battery module": "nominal voltage (V), capacity (Ah), chemistry, weight (kg)",
  "busbar": "cross-sectional area (mm²), material, rated current (A)",
  "bushing": "voltage rating (kV)",
  "cabinet": "material, degree of protection (IP/NEMA), mounting style",
  "cable": "cross-sectional area (mm²), operating voltage (V), conductor material, insulation material, temperature rating (°C), outer diameter (mm)",
  "cable accessory": "accessory type, compatible cable types",
  "cable connector": "compatible conductor cross-sectional area (mm²), connection type, number of contacts, rated current (A), rated voltage (V)",
  "cable insulation": "insulation material, thickness (mm), maximum temperature (°C), dielectric strength (kV/mm)",
  "capacitor": "capacitance (µF), rated voltage (V), tolerance (%), dielectric type, ESR (Ω), ripple current (A), temperature coefficient (ppm/°C), leakage current (µA), operating temperature range (°C), dimensions (mm)",
  "capacitor bank": "total capacitance (µF), rated voltage (V), number of modules",
  "capacitor board": "board type, number of capacitor slots, mounting style",
  "chemical dispenser": "application",
  "chemical product": "type of product",
  "circuit breaker": "rated current (A), rated voltage (V), trip curve, number of poles, breaking capacity (kA)",
  "circuit breaker accessory": "accessory type, compatible circuit breakers",
  "communication module": "supported protocols, input voltage (V), power consumption (W), data rate (Mbps), interface type, inputs, outputs",
  "connector": "compatible conductor cross-sectional area (mm²), connection type, number of contacts, rated current (A), rated voltage (V), contact material, termination style",
  "contact accessory": "compatible contactors",
  "contact block": "number of circuits, contact configuration, rated current (A)",
  "contact relay": "coil voltage (V), contact configuration, rated current (A), rated voltage (V)",
  "contactor": "coil voltage (V), contact configuration, rated current (A), rated voltage (V), number of poles, utilization category (e.g. AC3), mechanical life (operations), electrical life (operations), auxiliary contacts count, operating temperature range (°C)",
  "contactor accessory": "compatible contactors, accessory type",
  "contactor auxiliary contact": "contact configuration, rated current (A), rated voltage (V)",
  "contactor coil": "coil voltage (V), power consumption (W)",
  "contactors": "coil voltage (V), contact configuration, rated current (A)",
  "controller": "type of controller",
  "cooling oil": "viscosity (cSt), dielectric strength (kV), flash point (°C), pour point (°C), density (kg/m³), viscosity index (VI), total acid number (TAN), oxidation stability (hours)",
  "disconnector": "rated voltage (V), rated current (A), number of poles",
  "display": "screen size (inches), resolution, display type, interface",
  "drive": "rated power (kW), supply voltage (V), control type, efficiency (%), current rating (A), frequency range (Hz), overload capacity (e.g. % for x s), cooling method, communication interface",
  "enclosure": "enclousure application",
  "fan": "power consumption (W), voltage (V), type of fan",
  "fan accessory": "accessory type, compatible fan models",
  "fastener": "type of fastener",
  "filter": "type of filter",
  "fuse": "rated current (A), rated voltage (V), fuse type, breaking capacity (kA), time characteristic, I²t (A²s), voltage drop (V), ambient temperature rating (°C), dimensions (mm), material",
  "fuse base": "supported fuse type, mounting style",
  "fuse holder": "supported fuse size, rated current (A), rated voltage (V), number of poles",
  "heater":"heating power (W), supply voltage (V), element type, enclosure rating, temperature range (°C), control type (e.g. thermostat, PID), heating element material, mounting style",
  "indicator light": "voltage (V), application",
  "inductor": "inductance (µH), rated current (A), rated voltage (V), DC resistance (Ω), self-resonant frequency (MHz)",
  "insulating oil": "viscosity (cSt), dielectric strength (kV), flash point (°C), pour point (°C), total acid number (TAN), density (kg/m³)",
  "insulation": "insulation material, thickness (mm), dielectric strength (kV/mm)",
  "insulator": "material, rated voltage (kV), mechanical load (kN)",
  "insulator chain": "link material, link strength (kN), link length (mm)",
  "inverter": "rated power (kW), input voltage (V), output voltage (V), efficiency (%), switching frequency (kHz), total harmonic distortion (THD), protection class (IP), cooling method",
  "inverter accessory": "type of accessory, compatible inverters",
  "limit switch": "actuation type, rated current (A), rated voltage (V)",
  "lock": "lock type, material, mounting style",
  "lubricant": "viscosity (cSt), temperature range (°C), base oil type, viscosity index (VI), pour point (°C), flash point (°C), additive package, density (kg/m³)",
  "measurement device": "measured parameter, range, accuracy, resolution",
  "mechanical component (tracker)": "mechanical motion range (°), load capacity (kg)",
  "module": "module type, input voltage (V), power consumption (W)",
  "monitoring device": "application",
  "motor": "power (kW), voltage (V), frequency (Hz), speed (rpm), number of poles, supply type (AC or DC), efficiency (%), enclosure type (IP rating)",
  "mounting bracket": "application",
  "mounting rail": "rail type",
  "network converter": "number of ports, rated voltage (V)",
  "network switch": "number of ports, supported speeds, power consumption (W), switching capacity (Gbps), port types (RJ45/SFP), PoE support, management interface, VLAN support, manageable (yes/no), supported protocols (e.g. SNMP, STP, LACP), dimensions (mm), operating temperature range (°C)",
  "packing set": "number of items, item type",
  "panel": "material, number of cells, finish, weight (kg)",
  "power module": "rated power (kW), input voltage (V), output voltage (V)",
  "power supply": "output voltage (V), output current (A), input voltage range (V)",
  "reactor": "rated inductance (mH), rated current (A), rated voltage (V)",
  "rectifier": "rated current (A), rated voltage (V), number of phases",
  "regulatory relay": "function type, coil voltage (V), contact configuration",
  "relay": "type, coil voltage (V), contact configuration, contact material, rated current (A), switching voltage (V)",
  "relay socket": "compatible relays, mounting style",
  "relay timer": "timing range, supply voltage (V), timing accuracy, output type",
  "resistor": "resistance (Ω), tolerance (%), power rating (W), material",
  "resistor card": "number of resistors, card type, mounting style",
  "seal kit": "kit contents, material compatibility",
  "sensor": "sensor type, measurement range, output signal, supply voltage (V)",
  "sensor amplifier": "gain, input range, bandwidth",
  "sensor module": "sensor type, interface, supply voltage (V)",
  "signage": "material, type of signage",
  "solar panel": "maximum power (Wp), voltage at max power (Vmp), current at max power (Imp), open-circuit voltage (Voc), short-circuit current (Isc), efficiency (%), temperature coefficient (%/°C), dimensions (mm), weight (kg), frame material",
  "surge arrester": "nominal discharge current (kA), maximum continuous operating voltage (V), number of poles, material",
  "surge protector": "nominal discharge current (kA), maximum continuous operating voltage (V)",
  "switch": "switch type, rated current (A), rated voltage (V), actuator type",
  "test block": "type, number of circuits, material, insulation rating",
  "timer": "timing range, supply voltage (V), timing accuracy",
  "timer switch": "actuation type, timing range, rated voltage (V)",
  "tool set": "number of tools, tool types",
  "tracker": "tracking type, input voltage (V), input current (A), power consumption (W), mechanical motion range (°)",
  "transformer": "rated power (kVA), primary voltage (V), secondary voltage (V), frequency (Hz)",
  "transformer accessory": "compatible transformers, accessory type",
  "transformer monitor": "monitored parameters, interface, supply voltage (V)",
  "unknown item": "application",
  "valve": "valve type, material, pressure rating (bar)",
  "washer": "washer type, material, dimensions (mm)"
    }

    ### Output Examples

    **Example 1: All properties found**  
    The PDF provided every UPS specification:

    ```json
        {
        "part number": "UPS-5000X",
        "manufacturer": "PowerTech",
        "type": {
            "name": "UPS",
            "input voltage (V)": "230 V",
            "output voltage (V)": "230 V",
            "battery type": "Lead-acid",
            "backup time (min)": "15",
            "supply type (AC or DC)": "AC",
            "rated capacity (kVA)": "5",
            "efficiency (%)": "95%",
            "topology (online/offline)": "online",
            "transfer time (ms)": "0",
            "weight (kg)": "25"
            }
        }

    **Example 2: Some properties missing**
    The datasheet did not mention “battery type” or “transfer time”; those fields are set to "Not found":

    {
    "part number": "UPS-3000Z",
    "manufacturer": "SecurePower",
    "type": {
        "name": "UPS",
        "input voltage (V)": "120 V",
        "output voltage (V)": "120 V",
        "battery type": "Not found",
        "backup time (min)": "10",
        "supply type (AC or DC)": "AC",
        "rated capacity (kVA)": "3",
        "efficiency (%)": "92%",
        "topology (online/offline)": "offline",
        "transfer time (ms)": "Not found",
        "weight (kg)": "18"
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

    # 2) Cria instância do ORM
    new = Product(
        product      = payload.product,
        manufacturer = payload.manufacturer,
        part_number  = payload.part_number,
        description  = payload.description,    # aqui vai a string concatenada
        ncm          = payload.ncm,   # ou payload.NCM, conforme seu modelo
        datasheet    = payload.datasheetURL,
        qtde         = 0,
        type         = payload.product_type,
        price        = payload.price
    )

    # 3) Persiste no banco
    db.add(new)
    db.commit()
    db.refresh(new)

    # 4) Retorna de volta o objeto salvo (ou apenas um OK)
    return payload
