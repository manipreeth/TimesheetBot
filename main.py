from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import shutil
import speech_recognition as sr
from agents.llm_agent import workflow
from agents.browser_agent import fill_timesheet
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_file = "temp_audio.wav"
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(temp_file) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return JSONResponse(content={"text": text})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
@app.post("/process_timesheet")
async def process_timesheet(file: UploadFile = File(...)):
    # # 1. Save + transcribe audio (your existing code reused)
    # temp_file = "temp_audio.wav"
    # with open(temp_file, "wb") as buffer:
    #     shutil.copyfileobj(file.file, buffer)

    # recognizer = sr.Recognizer()
    # with sr.AudioFile(temp_file) as source:
    #     audio = recognizer.record(source)
    # transcription = recognizer.recognize_google(audio)

    # print ("Transcription--->", transcription)
    # transcription = "application code 90685 Monday TR hashtag 76891 circuit Path 8 hours application maintenance Tuesday BC hashtag 5716 site builder 8 hours planning Wednesday AP hashtag 9751 equipment Creation 8 hours testing Thursday AC hashtag 8450 data synchronisation 8 hours admin Friday IG hashtag 8574 edge automation 8 hours data conversion"

    # # 2. Run through LLM workflow
    # result = workflow.invoke({"user_text": transcription})
    # timesheet_data = result["timesheet_data"]
    # preview = result["preview"]

    raw_json = """
    {
    "application_code": "90685",
    "monday": [
        {
            "date": "09/01",
            "day": "Mon",
            "project": "TR#76891 circuit Path",
            "hours": 8,
            "activity": "15"
        }
    ],
    "tuesday": [
        {
            "date": "09/02",
            "day": "Tue",
            "project": "BC#5716 site builder",
            "hours": 8,
            "activity": "7"
        }
    ],
    "wednesday": [
        {
            "date": "09/03",
            "day": "Wed",
            "project": "TR#76891 circuit Path",
            "hours": 8,
            "activity": "15"
        }
    ],
    "thursday": [
        {
            "date": "09/04",
            "day": "Thu",
            "project": "AC#8450 data synchronisation",
            "hours": 8,
            "activity": "6"
        }
    ],
    "friday": [
        {
            "date": "09/05",
            "day": "Fri",
            "project": "IG#8574 edge automation",
            "hours": 8,
            "activity": "5"
        }
    ],
    "NAW - VDSI Absence": []
}
"""

    timesheet_data = json.loads(raw_json)
    # 3. Generate Selenium preview screenshot
    screenshot, _ = await fill_timesheet(timesheet_data, preview_only=False)

    return JSONResponse({
        # "transcription": transcription,
        "timesheet_data": timesheet_data,
        # "preview_text": preview,
        "screenshot": f"/{screenshot}"
    })


@app.post("/submit_timesheet")
async def submit_timesheet(timesheet_data: dict):
    result = fill_timesheet(timesheet_data, preview_only=False)
    return JSONResponse({"status": result})
