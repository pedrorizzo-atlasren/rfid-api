# from fastapi import APIRouter, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import tempfile
# from app.schemas.event import RegisterEvent

# router = APIRouter()



# @router.post("/register-event")
# async def register_event(data: RegisterEvent):
#     """
#     Marca o evento como registrado. 
#     Aqui você pode salvar em BD, arquivo, ou simplesmente sinalizar
#     no LOGS[epc] definindo data.registered = True.
#     """
#     epc = data.epc
#     ts  = data.timestamp
#     # encontra no LOGS[epc] o evento com mesmo timestamp e status
#     for evt in LOGS.get(epc, []):
#         if evt["timestamp"] == ts and evt["status"] == data.status:
#             evt["registered"] = True
#             break
#     return {"ok": True}
