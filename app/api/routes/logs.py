from fastapi import APIRouter, Depends, HTTPException
from schemas.event import RegisterEvent, EventOut
from typing import List
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.logs import Log
from models.item import Item


router = APIRouter()


@router.get("/logs", response_model=List[EventOut])
def get_all_logs(db: Session = Depends(get_db)):
    stm = select(Log).order_by(Log.timestamp)
    logs = db.execute(stm).scalars().all()
    print('LOGS:', logs)
    return logs

@router.post("/register-event")
async def register_event(
    data: RegisterEvent,
    db: Session = Depends(get_db)
):
    # 1) Busca o log pelo log_id
    log = db.query(Log).filter(Log.log_id == data.log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    # 2) Marca este log como registrado
    log.registered = True
    if data.description:
      log.description = data.description
    db.add(log)

    # 3) Se veio description, atualiza o Item apenas se este log for o mais recente
    if data.description:
        # busca o log mais recente para este item
        latest = (
            db.query(Log)
              .filter(Log.item_id == log.item_id)
              .order_by(Log.timestamp.desc())
              .first()
        )
        if latest and latest.log_id == log.log_id:
            # é o mais recente → atualiza o status_desc do item
            item = db.query(Item).filter(Item.item_id == log.item_id).first()
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")
            item.status_desc = data.description
            db.add(item)

    # 4) persiste tudo numa só transação
    db.commit()

    return {
        "ok": True,
        "log_id": log.log_id,
        "registered": log.registered,
        "item_description_updated": bool(data.description and latest and latest.log_id == log.log_id)
    }