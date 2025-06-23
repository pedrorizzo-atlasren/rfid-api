from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect
from queue import Queue
from typing import Optional
from models.rfid import RFIDTag
import asyncio
from sllurp.llrp import (
    LLRP_DEFAULT_PORT,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)
import logging
from threading import Timer
import time
from schemas.event import RegisterEvent



router = APIRouter()

# Store the reader and tag data
READER: Optional[LLRPReaderClient] = None
TAG_DATA: list[RFIDTag] = []
TAG_QUEUE = Queue()
ACTIVE_CONNECTIONS = []

TAG_STATE = {}  # ex: { "EPC1": {"last_antenna": 1, "status": "in", "last_seen": timestamp} }
LOGS = {}       # eventos de entrada/saída

READER_IP = "10.50.0.18"
PORT = LLRP_DEFAULT_PORT
READER = None


def get_reader():
    return READER


async def initialize_reader():
    global READER
    config = LLRPReaderConfig({
        "tag_content_selector": {
            "EnableAntennaID": True,
            "EnableChannelIndex": True,
            "EnablePeakRSSI": True,
            "EnableLastSeenTimestamp": True,
            "EnableTagSeenCount": True,
            # outros flags conforme seu código
        }
    })
    config.reset_on_connect = True
    config.start_inventory = True
    config.antennas = [1, 2]
    config.tx_power = {1: 0, 2: 0}
    config.report_every_n_tags = 65535
    config.report_timeout_ms = 1200
    config.event_selector = {"GPIEvent": True}

    READER = LLRPReaderClient(READER_IP, PORT, config)
    READER.add_tag_report_callback(tag_report_cb)
    READER.add_event_callback(handle_event)

    READER.connect()
    logging.info("RFID Reader initialized")

    task = asyncio.create_task(process_queue())

async def shutdown_reader():
    global READER
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        READER.disconnect()
        logging.info("RFID Reader disconnected")

def start_reading():
    if READER and READER.is_alive():
        # clear_tag_data()
        READER.llrp.startInventory()
        return
    
def stop_reading():
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        return

def get_status():
    return {"status": READER.is_alive()}

CONFIRM_DELAY = 1.0  

CONFIRM_TIMERS: dict[str, Timer] = {}

# def schedule_confirmation(epc: str, to_status: str):
#     # cancela timer anterior, se existir
#     prev_timer = CONFIRM_TIMERS.get(epc)
#     if prev_timer:
#         prev_timer.cancel()

#     def confirm():
#         now = time.time()
#         prev = TAG_STATE.get(epc)
#         if prev and prev["status"] != to_status:
#             TAG_STATE[epc]["status"]    = to_status
#             TAG_STATE[epc]["last_seen"] = now
#             LOGS[epc].append({"timestamp": now, "status": to_status})
#         CONFIRM_TIMERS.pop(epc, None)

#     # agenda o timer
#     timer = Timer(CONFIRM_DELAY, confirm)
#     timer.daemon = True
#     timer.start()
#     CONFIRM_TIMERS[epc] = timer


def tag_report_cb(_reader, tag_reports):
    global TAG_DATA, TAG_STATE, LOGS
    now = int(time.time())
    TAG_DATA = []

    for tag in tag_reports:
        epc = tag["EPC"].decode("ascii")
        antenna = tag.get("AntennaID")
        channel = tag["ChannelIndex"]
        last_seen = tag["LastSeenTimestampUTC"]
        seen_count = tag["TagSeenCount"]

        TAG_DATA.append(RFIDTag(
            epc=epc,
            channel=channel,
            last_seen=last_seen,
            seen_count=seen_count,
            antenna=antenna,
        ))

        previous = TAG_STATE.get(epc)

        if epc not in LOGS:
            LOGS[epc] = []


        # PRIMERIA VEZ QUE A TAG APARECE -> BAIXA NO ESTOQUES
        if previous is None and antenna == 1:
            # Primeira vez que a tag aparece — baixa no estoque
            TAG_STATE[epc] = {
                "last_antenna": antenna,
                "status": "in",
                "last_seen": now,
            }
            LOGS[epc].append({"timestamp": now, "status": "baixa", "registered": True})

        else:
            last_ant = previous["last_antenna"]
            status = previous["status"]

            if antenna == 2 and last_ant == 1:
                # Saída
                TAG_STATE[epc] = {
                    "last_antenna": antenna,
                    "status": "out",
                    "last_seen": now,
                }
                LOGS[epc].append({"timestamp": now, "status": "saida", "registered": False})

            #Se a antena atual que lê o objeto é a 1 e a última antena que o leu foi a 2,
            #registra uma re-entrada
            elif antenna == 1  and last_ant == 2:
                # Reentrada
                TAG_STATE[epc] = {
                    "last_antenna": antenna,
                    "status": "in",
                    "last_seen": now,
                }
                LOGS[epc].append({"timestamp": now, "status": "reentrada", "registered": False})

            else:
                # Atualiza apenas tempo e antena
                TAG_STATE[epc]["last_antenna"] = antenna
                TAG_STATE[epc]["last_seen"] = now


    serializable = [tag.model_dump() for tag in TAG_DATA]
    TAG_QUEUE.put(serializable)

# Define callback for events
def handle_event(_reader, event):
    if "GPIEvent" in event:
        gpi_event = event.get("GPIEvent")
        logging.info(f"GPI Event: {gpi_event}")

        if gpi_event and gpi_event.get("GPIPortNumber") == 1:
            if gpi_event.get("GPIEvent"):
                if READER and READER.is_alive():
                    logging.info("Starting inventory via GPI")
                    start_reading()
            else:
                logging.info("Stopping inventory")
                stop_reading()

    if "ConnectionAttemptEvent" in event:
        connection_event = event["ConnectionAttemptEvent"]
        logging.info(f"Connection Event: {connection_event}")
    else:
        logging.info(f"Other Event: {event}")

async def process_queue():
    while True:
        # Check queue in a loop
        if not TAG_QUEUE.empty():
            tags = TAG_QUEUE.get()
            logging.info(f"Processing tags from queue: {tags}")
            # Send to all websocket connections
            for connection in ACTIVE_CONNECTIONS[:]:
                try:
                    await connection.send_json({"tags": tags})
                    logging.info("Sent tags to websocket connection")
                except Exception as e:
                    logging.error(f"Error sending to websocket: {e}")
                    ACTIVE_CONNECTIONS.remove(connection)
        await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging

@router.get("/start-reader")
async def start_reader():
    try:
        await initialize_reader()
        return {"message: Succeeded to start reader"}
    except Exception as e:
        return {"message": "Failed to start reader"}

@router.get("/stop-reader")
async def stop_reader():
    stop_reading()

@router.get("/status")
async def status():
    get_status()



@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logging.info("New WebSocket connection attempt")
    await websocket.accept()
    ACTIVE_CONNECTIONS.append(websocket)
    try:
        while True:
            await websocket.receive_text() #Keeps connection alive
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
        ACTIVE_CONNECTIONS.remove(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        if websocket in ACTIVE_CONNECTIONS:
            ACTIVE_CONNECTIONS.remove(websocket)


@router.get("/logs")
async def get_logs():
    return LOGS

@router.post("/register-event")
async def register_event(data: RegisterEvent):
    """
    Marca o evento como registrado. 
    Aqui você pode salvar em BD, arquivo, ou simplesmente sinalizar
    no LOGS[epc] definindo data.registered = True.
    """
    epc = data.epc
    ts  = data.timestamp
    # encontra no LOGS[epc] o evento com mesmo timestamp e status
    for evt in LOGS.get(epc, []):
        if evt["timestamp"] == ts and evt["status"] == data.status:
            evt["registered"] = True
            break
    return {"ok": True}
