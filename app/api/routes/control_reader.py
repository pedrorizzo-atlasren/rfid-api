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
from datetime import datetime, timezone




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

ENTRY_ANTENNA_ID = 1
EXIT_ANTENNA_ID = 2


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

TAG_LAST_ANTENNA = {}
TAG_LAST_SEEN = {}
EVENT_TIME_WINDOW = 2  # seconds
TAG_MOVEMENT_STATE = {}
TAG_LAST_SEEN_EXIT = {}
TAG_LAST_SEEN_ENTRY = {}



def tag_report_cb(_reader, tag_reports):
    now = int(time.time())
    db = SessionLocal()
    global TAG_DATA, TAG_STATE, LOGS, TAG_LAST_ANTENNA, TAG_LAST_SEEN

    TAG_STATE = {}
    try:
        for tag in tag_reports:

            epc = tag["EPC"].decode("ascii")
            antenna = tag.get("AntennaID")
            channel = tag["ChannelIndex"]
            last_seen = tag["LastSeenTimestampUTC"]
            seen_count = tag["TagSeenCount"]

            if TAG_LAST_ANTENNA.get(epc) is not None:
                prev_antenna = TAG_LAST_ANTENNA[epc]
      
            if TAG_LAST_SEEN.get(epc) is not None:
                prev_seen = TAG_LAST_SEEN[epc]

            TAG_LAST_ANTENNA[epc] = antenna
            TAG_LAST_SEEN[epc] = last_seen




            TAG_DATA.append(RFIDTag(
                epc=epc,
                channel=channel,
                last_seen=last_seen,
                seen_count=seen_count,
                antenna=antenna,
            ))

            TAG_STATE[epc] = RFIDTag(
                epc=epc,
                channel=channel,
                last_seen=last_seen,
                seen_count=seen_count,
                antenna=antenna,
            )

            if not epc.startswith('e2801191'):
                continue

            item = db.query(Item).filter(Item.item_id == epc).first()

            if antenna == ENTRY_ANTENNA_ID:
                dt = datetime.fromtimestamp(last_seen/1000000, tz=timezone.utc)
                TAG_LAST_SEEN_ENTRY[epc] = dt
                dt = datetime.fromtimestamp(last_seen/1000000, tz=timezone.utc)
                if item is None:
                    item = Item(item_id=epc, status="entrance", status_desc="first entrance", ts=dt)
                    db.add(item)
                    db.commit()
                    db.refresh(item)
                    db.add(Log(item_id=item.item_id, status="entrance", timestamp=dt, registered=True, description="first entrance"))
                    db.commit()
                    TAG_MOVEMENT_STATE[epc] = "entrance"
                else:
                    
                    # if TAG_LAST_SEEN_EXIT.get(epc) is not None:
                    #     prev_exit_antenna = TAG_LAST_SEEN_EXIT[epc]

                    if prev_antenna == EXIT_ANTENNA_ID and item.status == 'exit' and ((last_seen-prev_seen)/1e6) > EVENT_TIME_WINDOW:
                        item.status = 're-entrance'
                        item.status_desc = ''
                        db.add(Log(item_id=item.item_id, status='re-entrance', timestamp=dt, registered=False, description=''))
                        db.commit()
                        TAG_MOVEMENT_STATE[epc] = "re-entrance"
                        continue

                    elif TAG_LAST_SEEN_EXIT.get(epc) is not None:
                        prev_exit: datetime = TAG_LAST_SEEN_EXIT[epc]
                        if prev_antenna == ENTRY_ANTENNA_ID and item.status == 'exit' and (dt - prev_exit) > EVENT_TIME_WINDOW:
                            item.status = 're-entrance'
                            item.status_desc = ''
                            db.add(Log(item_id=item.item_id, status='re-entrance', timestamp=dt, registered=False, description=''))
                            db.commit()
                            TAG_MOVEMENT_STATE[epc] = "re-entrance"
                            continue
                 



            elif antenna == EXIT_ANTENNA_ID:
                if item is None:
                    continue
                dt = datetime.fromtimestamp(last_seen/1000000, tz=timezone.utc)
                TAG_LAST_SEEN_EXIT[epc] = dt

                # delta = now - prev
                # diff_seconds = delta.total_seconds()
                # diff_minutes = diff_seconds / 60

                if prev_antenna == ENTRY_ANTENNA_ID and (item.status == 'entrance' or item.status =='re-entrance' ) and ((last_seen - prev_seen)/1000000) > EVENT_TIME_WINDOW:
                    print('prev_antenna')
                    item.status = 'exit'
                    item.status_desc = ''
                    db.add(Log(item_id=item.item_id, status="exit", timestamp=dt, registered=False, description=''))
                    db.commit()
                    TAG_MOVEMENT_STATE[epc] = "exit"
                    continue

                if TAG_LAST_SEEN_ENTRY.get(epc) is not None:
                    prev_entry: datetime = TAG_LAST_SEEN_ENTRY[epc]
                    print('tag_last_seen_entry')
                    print('status:', item.status)
                    print('diff:', (dt - prev_entry).total_seconds())
                    print(prev_antenna)
                    if prev_antenna == EXIT_ANTENNA_ID and (item.status == 'entrance' or item.status == 're-entrance') and ((dt-prev_entry).total_seconds()) > EVENT_TIME_WINDOW:
                        print('prev_antenna')
                        item.status = 'exit'
                        item.status_desc = ''
                        db.add(Log(item_id=item.item_id, status="exit", timestamp=dt, registered=False, description=''))
                        db.commit()
                        TAG_MOVEMENT_STATE[epc] = "exit"
                        continue




                else:
                    continue





        # serializable = [tag.model_dump() for tag in TAG_STATE.values() if tag.startswith('e2801191')]
        serializable = [
            tag.model_dump()
            for tag in TAG_STATE.values()
            if tag.epc.startswith('e2801191')
        ]
        TAG_QUEUE.put(serializable)

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