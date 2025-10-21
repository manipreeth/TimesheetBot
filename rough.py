        timeSheetData = {
  "application_code": "19572",
  "monday": [
    {
      "date": "09/01",
      "day": "Mon",
      "project": "BC#452 Data Synchronisation",
      "hours": 8,
      "activity": "4"
    }
  ],
  "tuesday": [
    {
      "date": "09/02",
      "day": "Tue",
      "project": "BC#736 Edge Automation",
      "hours": 8,
      "activity": "5"
    }
  ],
  "wednesday": [
    {
      "date": "09/03",
      "day": "Wed",
      "project": "AZ#0912 Site Builder",
      "hours": 8,
      "activity": "1"
    }
  ],
  "thursday": [
    {
      "date": "09/04",
      "day": "Thu",
      "project": "CR#76311 Circuit Screen",
      "hours": 8,
      "activity": "9"
    }
  ],
  "friday": [
    {
      "date": "09/05",
      "day": "Fri",
      "project": "BC#8922 Equipment Built",
      "hours": 4,
      "activity": "11"
    }
  ],
  "NAW - VDSI Absence": [{ "date": "09/05", "day": "Fri", "hours": 4 }]
}

        return JSONResponse({
            "transcription": "Mock transcription",
            "timeSheetData": timeSheetData
        })