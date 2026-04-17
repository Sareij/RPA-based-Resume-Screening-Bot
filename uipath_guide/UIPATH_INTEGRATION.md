# UiPath RPA Integration Guide for CHIS
## Cognitive Hiring Intelligence System

---

## Overview

The UiPath RPA bot automates the following tasks:
1. Watch a folder for new resume files (PDF/DOCX/images)
2. Move files to organized subfolders by date/job role
3. Call the CHIS Flask API to trigger AI processing
4. Send email notifications with results summary
5. Generate an Excel shortlist report

---

## Prerequisites

- UiPath Studio (Community Edition is free)
  Download: https://www.uipath.com/start-trial
- CHIS Flask app running at http://127.0.0.1:5000
- Microsoft Excel installed (for report generation)
- Outlook or Gmail for email notifications

---

## Bot 1: Resume Collector Bot

### Purpose
Watches the "Incoming_Resumes" folder and automatically organizes files.

### Steps in UiPath Studio:

```
1. Create New Process → Name: "CHIS_Resume_Collector"

2. Add activities in Main.xaml:

   [While Loop: True]
   │
   ├─ [Assign] folderPath = "C:\CHIS_Resumes\Incoming"
   │
   ├─ [Get Files] → files = Directory.GetFiles(folderPath, "*.pdf")
   │                         + Directory.GetFiles(folderPath, "*.docx")
   │
   ├─ [For Each: file in files]
   │   │
   │   ├─ [Assign] destFolder = "C:\CHIS_Resumes\Processing\" + DateTime.Now.ToString("yyyy-MM-dd")
   │   │
   │   ├─ [Create Directory] destFolder (if not exists)
   │   │
   │   ├─ [Move File] file → destFolder + "\" + Path.GetFileName(file)
   │   │
   │   └─ [Log Message] "Moved: " + Path.GetFileName(file)
   │
   └─ [Delay] 30 seconds (poll every 30s)
```

### UiPath Activity Settings:
- Get Files: Filter = "*.pdf,*.docx,*.jpg,*.png"
- Move File: Overwrite = False (rename if duplicate)

---

## Bot 2: CHIS API Trigger Bot

### Purpose
Sends resume files to the CHIS web app for AI processing.

### Steps:

```
1. Add HTTP Request activity (UiPath.Web.Activities package)

2. Sequence: "Process_Resumes_API"

   [Assign] apiUrl = "http://127.0.0.1:5000/upload"
   
   [For Each file in processedFiles]
   │
   ├─ [HTTP Request]
   │   Method: POST
   │   URL: apiUrl
   │   Body Type: Multipart
   │   File: file path
   │
   └─ [Log Message] response status

```

### Install Web Activities:
```
UiPath Studio → Manage Packages → 
Search: UiPath.Web.Activities → Install
```

---

## Bot 3: Results Reporter Bot

### Purpose
After processing, generates Excel report and sends email.

### Steps:

```
1. New Process: "CHIS_Results_Reporter"

   [HTTP Request]
   URL: http://127.0.0.1:5000/api/export
   Method: GET
   Output: jsonResponse
   
   [Deserialize JSON] → resultsData
   
   [Build Data Table]
   Columns: Rank, Name, Score, Skills, Cluster, Fraud Risk
   
   [For Each item in resultsData.candidates]
   ├─ [Add Data Row] with candidate info
   
   [Write Range Workbook]
   File: "C:\CHIS_Reports\Results_" + DateTime.Now.ToString("yyyyMMdd") + ".xlsx"
   SheetName: "Screening Results"
   
   [Send Outlook Mail]
   To: "hr@company.com"
   Subject: "CHIS Resume Screening Complete — " + DateTime.Now.ToString("dd MMM yyyy")
   Body: "Screening complete. " + totalCount + " resumes processed. 
          Top candidate: " + topCandidateName + " (Score: " + topScore + "%)
          Please check the attached Excel report."
   Attachments: reportFilePath
```

---

## Bot 4: Scheduled Overnight Screening Bot

### Purpose
Runs full screening automatically at a set time.

### Setup with Windows Task Scheduler:

```
1. In UiPath Studio → Publish your process
   → Publish Location: Local

2. Windows Task Scheduler:
   → Create Basic Task
   → Name: "CHIS Nightly Screening"
   → Trigger: Daily at 11:00 PM
   → Action: Start a Program
   → Program: "C:\Program Files\UiPath\Studio\UiPath.exe"
   → Arguments: -file "path\to\CHIS_Collector.xaml" -input "{'folder': 'C:\\CHIS_Resumes'}"

3. Or use UiPath Orchestrator (free Community edition):
   → Create a Schedule → Set time → Assign robot
```

---

## Folder Structure Setup (Windows)

Create this folder structure on your PC:

```
C:\CHIS_Resumes\
├── Incoming\          ← HR drops resumes here
├── Processing\
│   └── 2025-06-01\   ← Organized by date
├── Processed\         ← Completed resumes
└── Reports\           ← Excel output files

C:\CHIS_Project\       ← Your Flask app folder
├── run.py
├── app\
└── ...
```

---

## UiPath Packages to Install

In UiPath Studio → Manage Packages → search and install:

| Package | Purpose |
|---------|---------|
| UiPath.Excel.Activities | Read/Write Excel files |
| UiPath.Mail.Activities | Send Outlook/SMTP email |
| UiPath.Web.Activities | HTTP requests to CHIS API |
| UiPath.System.Activities | File/folder operations |
| UiPath.UIAutomation.Activities | UI interaction (if needed) |

---

## Demo Script for Viva

"Our UiPath bot monitors the HR folder every 30 seconds.
When new resumes arrive, it automatically organizes them,
sends them to our AI engine via REST API, waits for the
AI to complete analysis, then generates an Excel shortlist
and emails it to the HR team — all without human intervention.
This is the RPA layer of our three-layer CHIS architecture."

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Bot can't find UiPath | Install UiPath Studio Community |
| HTTP 500 error | Make sure Flask app is running (python run.py) |
| Excel not writing | Install UiPath.Excel.Activities package |
| Email not sending | Check Outlook is open / SMTP settings |
