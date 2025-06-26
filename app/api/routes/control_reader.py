from fastapi import APIRouter, Depends
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
from schemas.event import RegisterEvent, EventOut
from typing import List
from database import get_db
from sqlalchemy.orm import Session
from models.logs import Log
from models.item import Item
from database import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime



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


# def tag_report_cb(_reader, tag_reports):
    # global TAG_DATA, TAG_STATE, LOGS
#     now = int(time.time())
#     TAG_DATA = []

#     for tag in tag_reports:
#         epc = tag["EPC"].decode("ascii")
#         antenna = tag.get("AntennaID")
#         channel = tag["ChannelIndex"]
#         last_seen = tag["LastSeenTimestampUTC"]
#         seen_count = tag["TagSeenCount"]

#         TAG_DATA.append(RFIDTag(
#             epc=epc,
#             channel=channel,
#             last_seen=last_seen,
#             seen_count=seen_count,
#             antenna=antenna,
#         ))

#         previous = TAG_STATE.get(epc)

#         if epc not in LOGS:
#             LOGS[epc] = []


#         # PRIMERIA VEZ QUE A TAG APARECE -> BAIXA NO ESTOQUES
#         if previous is None and antenna == 1:
#             # Primeira vez que a tag aparece — baixa no estoque
#             TAG_STATE[epc] = {
#                 "last_antenna": antenna,
#                 "status": "in",
#                 "last_seen": now,
#             }
#             LOGS[epc].append({"timestamp": now, "status": "baixa", "registered": True})

#         else:
#             last_ant = previous["last_antenna"]
#             status = previous["status"]

#             if antenna == 2 and last_ant == 1:
#                 # Saída
#                 TAG_STATE[epc] = {
#                     "last_antenna": antenna,
#                     "status": "out",
#                     "last_seen": now,
#                 }
#                 LOGS[epc].append({"timestamp": now, "status": "saida", "registered": False})

#             #Se a antena atual que lê o objeto é a 1 e a última antena que o leu foi a 2,
#             #registra uma re-entrada
#             elif antenna == 1  and last_ant == 2:
#                 # Reentrada
#                 TAG_STATE[epc] = {
#                     "last_antenna": antenna,
#                     "status": "in",
#                     "last_seen": now,
#                 }
#                 LOGS[epc].append({"timestamp": now, "status": "reentrada", "registered": False})

#             else:
#                 # Atualiza apenas tempo e antena
#                 TAG_STATE[epc]["last_antenna"] = antenna
#                 TAG_STATE[epc]["last_seen"] = now


    # serializable = [tag.model_dump() for tag in TAG_DATA]
    # TAG_QUEUE.put(serializable)

def tag_report_cb(_reader, tag_reports):
    now = int(time.time())
    db = SessionLocal()
    global TAG_DATA, TAG_STATE, LOGS


    try:
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

            serializable = [tag.model_dump() for tag in TAG_DATA]
            TAG_QUEUE.put(serializable)


            # recupera estado anterior diretamente do banco
            prev_item = db.query(Item).filter_by(item_id=epc).first()
            prev_status = prev_item.status if prev_item else None

            # decide novo status
            if prev_item is None and antenna == 1:
                new_status, new_desc = "entrance", "entrance"
            elif (prev_status == "entrance" or prev_status == "re-entrance") and antenna == 2:
                new_status, new_desc = "out", ""
            elif prev_status == "out" and antenna == 1:
                new_status, new_desc = "re-entrance", ""
            else:
                # nenhum evento significativo, só atualiza timestamp
                new_status, new_desc = prev_status, prev_item.status_desc if prev_item else ""

            
            if new_status and new_status != prev_status:
                # 3) grava no histórico de logs
                log = Log(
                    item_id    = epc,
                    status     = new_status,
                    timestamp  = datetime.now(),  # sem UTC
                    registered = False
                )
                db.add(log)

                # 4) atualiza somente agora o item
                prev_item.status      = new_status
                prev_item.status_desc = ""           # ou algo genérico
                prev_item.ts          = datetime.now()
                db.add(prev_item)

                db.commit()
            

    except:
        db.rollback()
        raise
    finally:
        db.close()

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



