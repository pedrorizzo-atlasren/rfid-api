from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import create_product, control_reader, logs, chat, get_products
import logging
from starlette.websockets import WebSocket, WebSocketDisconnect

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await initialize_reader()
#     yield
#     await shutdown_reader()

# app = FastAPI(lifespan=lifespan)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

logging.basicConfig(level=logging.DEBUG)

sllurp_logger = logging.getLogger("sllurp")
sllurp_logger.setLevel(logging.DEBUG)
sllurp_logger.addHandler(logging.StreamHandler())

app.include_router(create_product.router, tags=["create_product"])
app.include_router(control_reader.router, tags=["control_reader"])
app.include_router(logs.router, tags=["logs"])
app.include_router(chat.router, tags=["chat"])
app.include_router(get_products.router, tags=["get_products"])



@app.get("/")
def root():
    return {"message": "Hello FastAPI"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=4000)