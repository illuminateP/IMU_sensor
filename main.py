import csv
import os
import socket
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(" 🚀 HTTPS Server is Running!")
    print(" 👉 접속 주소: https://localhost:8000")
    print("=" * 50 + "\n")
    yield

app = FastAPI(title="IMU Sensor Server", lifespan=lifespan)

# --- 설정 및 초기화 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
templates = Jinja2Templates(directory="templates")

os.makedirs(DATA_DIR, exist_ok=True)
CSV_FILE_PATH = os.path.join(DATA_DIR, "sensor_log.csv")
CSV_HEADERS = ["timestamp", "client_id", "ax", "ay", "az", "gx", "gy", "gz"]

# CSV 헤더 초기화
if not os.path.exists(CSV_FILE_PATH):
    with open(CSV_FILE_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# 웹소켓 클래스
class ConnectionManager:
    def __init__(self):
        self.monitors: List[WebSocket] = []
        self.client_counter = 0  # 접속자 카운터 추가

    async def connect_monitor(self, websocket: WebSocket):
        await websocket.accept()
        self.monitors.append(websocket)

    def disconnect_monitor(self, websocket: WebSocket):
        if websocket in self.monitors:
            self.monitors.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.monitors:
            try:
                await connection.send_json(message)
            except Exception:
                pass

    def generate_client_id(self, prefix="Mobile"):
        """접속 순서대로 고유 ID 생성 (예: Mobile-1, Mobile-2)"""
        self.client_counter += 1
        return f"{prefix}-{self.client_counter}"

manager = ConnectionManager()

# 데이터 저장 함수
def save_data(data: dict):
    try:
        with open(CSV_FILE_PATH, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                data["timestamp"], data["client_id"],
                data["ax"], data["ay"], data["az"],
                data["gx"], data["gy"], data["gz"]
            ])
    except Exception as e:
        print(f"CSV Error: {e}")

# 라우팅
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "server_ip": get_local_ip(),
        "server_port": 8000
    })

@app.get("/mode/sensor", response_class=HTMLResponse)
async def sensor_view(request: Request):
    return templates.TemplateResponse("sensor.html", {"request": request})

@app.get("/mode/monitor", response_class=HTMLResponse)
async def monitor_view(request: Request):
    return templates.TemplateResponse("monitor.html", {"request": request})


@app.websocket("/ws/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str):
    
    # 모니터링 PC 접속
    if client_type == "monitor":
        await manager.connect_monitor(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect_monitor(websocket)
            
    # 스마트폰 센서 접속
    elif client_type == "sensor":
        await websocket.accept()
        
        # 서버에서 접속 순서대로 고유 ID 부여 (Mobile-1, Mobile-2...)
        session_id = manager.generate_client_id("Mobile")
        print(f"New Connection: {session_id}")

        try:
            while True:
                data = await websocket.receive_json()
                
                # 부여받은 ID를 데이터에 포함
                processed_data = {
                    "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    "client_id": session_id,  
                    **data
                }
                
                save_data(processed_data)
                await manager.broadcast(processed_data)
                
        except WebSocketDisconnect:
            print(f"Disconnected: {session_id}")