from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
import shutil
import speech_recognition as sr
from agents.llm_agent import workflow
from agents.browser_agent import fill_timesheet
import json
import os
from fastapi import Form

app = FastAPI()

# ✅ Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict later, e.g., ["http://127.0.0.1:8000"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Setup templates + static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
  temp_file = "temp_audio.wav"
  with open(temp_file, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)

  recognizer = sr.Recognizer()
  with sr.AudioFile(temp_file) as source:
      audio = recognizer.record(source)
  transcription = recognizer.recognize_google(audio)

  # ✅ Run through LLM workflow
  result = workflow.invoke({"user_text": transcription})

  return JSONResponse({
      "transcription": transcription,
      "timeSheetData": result.get("normalized_timesheet")
  })

@app.post("/submit_timesheet")
async def submit_timesheet(timesheet_data: dict):
    screenshot, _ = await fill_timesheet(timesheet_data, preview_only=False)
    return JSONResponse({"status": "submitted", "screenshot": screenshot})


@app.post("/copyFromLastWeek")
async def copy_from_last_week():
    lastWeekData = {
  "application_code": "19572",
  "monday": [
    {
      "date": "09/01",
      "day": "Mon",
      "project": "BC#452 Data Synchronisation",
      "hours": 8,
      "activity": "4",
      "activityLabel": "Build"
    }
  ],
  "tuesday": [
    {
      "date": "09/02",
      "day": "Tue",
      "project": "BC#736 Edge Automation",
      "hours": 8,
      "activity": "5",
      "activityLabel": "Functionality Testing & Install - Excludes UAT"
    }
  ],
  "wednesday": [
    {
      "date": "09/03",
      "day": "Wed",
      "project": "AZ#0912 Site Builder",
      "hours": 8,
      "activity": "1",
      "activityLabel":"Planning, Tracking & Mgmt"
    }
  ],
  "thursday": [
    {
      "date": "09/04",
      "day": "Thu",
      "project": "CR#76311 Circuit Screen",
      "hours": 8,
      "activity": "9",
      "activityLabel":"End User Maintenance Support"
    }
  ],
  "friday": [
    {
      "date": "09/05",
      "day": "Fri",
      "project": "BC#8922 Equipment Built",
      "hours": 4,
      "activity": "11",
      "activityLabel":"Application Production Support"
    }
  ],
  "NAW - VDSI Absence": [{ "date": "09/05", "day": "Fri", "hours": 4 }]
}
    
    # result = fill_timesheet(lastWeekData, preview_only=False)
    return JSONResponse({"status": "Submitted", "normalized": lastWeekData})

@app.post("/modifyTimeSheet")
async def modify_time_sheet(file: UploadFile = File(...), timesheet: str = Form(...)):
    print("✅ modify_time_sheet called")

    # Step 1️⃣ Save uploaded audio
    temp_file = "temp_mod_audio.wav"
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Step 2️⃣ Transcribe audio → text
    recognizer = sr.Recognizer()
    with sr.AudioFile(temp_file) as source:
        audio = recognizer.record(source)
    modification_text = recognizer.recognize_google(audio)

    print("🎧 Transcription:", modification_text)

    # Step 3️⃣ Parse existing JSON from the frontend
    original_timesheet = json.loads(timesheet)
    print("📄 Original JSON received")

    # Step 4️⃣ Run LLM to apply modifications
    from agents.llm_agent import modify_timesheet_with_llm, normalize_timesheet
    updated_timesheet = modify_timesheet_with_llm(original_timesheet, modification_text)

    # ✅ Step 5️⃣ Normalize updated JSON for UI/browser filling
    try:
        state = {"timesheet_data": updated_timesheet}
        normalized_state = normalize_timesheet(state)
        normalized_data = normalized_state["normalized_timesheet"]
    except Exception as e:
        print("⚠️ Normalization failed:", e)
        normalized_data = None

    # Step 6️⃣ Return modified + normalized data
    return JSONResponse({
        "status": "modified",
        "modification_text": modification_text,
        "updated_timesheet": updated_timesheet,   # raw LLM-updated JSON
        "normalized_data": normalized_data         # structured for filling UI
    })

@app.post("/submitTimesheet")
async def submit_timesheet(data: dict):
    # log the data received from frontend more verbosely
    print("Received request to submit timesheet.")
    print("Data received:", json.dumps(data, indent=2))
    return JSONResponse({"status": "Submitted"})
