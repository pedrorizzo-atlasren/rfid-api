from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
from database import get_db
from fastapi import Depends
from models.item import Item
from models.product import Product
from sqlalchemy.orm import Session
from typing import List
from schemas.product import ProductOut
from sqlalchemy import func






router = APIRouter()

@router.get('/products', response_model=List[ProductOut])
def get_products(db: Session = Depends(get_db)):
    produtos = db.query(Product).order_by(Product.product_id).all()
    if produtos is None:
        raise HTTPException(404, "Nenhum produto encontrado")
    return produtos


@router.get("/items/last")
def last_item(db: Session = Depends(get_db)):
    last_id = db.query(func.max(Item.item_id)).scalar() or 0
    return {"last_item_id": last_id}



