# SMS and Call Log Automation (sms-cl-daily-follow-up-digest)
*Comprehensive Setup, Requirements, and Deployment Guide*

## 1. Overview & Requirements
The **sms-cl-daily-follow-up-digest** automation processes daily Android XML backup exports (sms-*.xml and calls-*.xml) stored in Google Drive. It runs as a serverless Python Cloud Run function, parsing communication logs to generate a structured, clean HTML daily follow-up digest.

### Core Requirements & Specifications
- **Active Google Cloud Project:** sms-cl-automations (Region: australia-southeast1).
- **Storage Location:** Google Drive Folder named SMSB&RP (must be shared with the project service account 635312912411-compute@developer.gserviceaccount.com).
- **Master Table Layout (1250px total width, table-layout: fixed; with top sizing row):**
  - **Contact:** 250px (Name + normalized phone number)
  - **Type:** 150px (Missed Call, Unanswered SMS, Follow-up Required)
  - **Date:** 150px (Format: -[YYYY-MM-DD] on top, time HHMM underneath)
  - **Action:** 150px (Direct click-to-call / click-to-SMS actionable links)
  - **Details / Snippet:** 600px (Cleaned multi-line text with whitespace normalization, word-break: break-word)
  - **VIP:** 50px (Interaction frequency score indicator)

---

## 2. Complete Variable Reference
| Variable / Parameter | Scope / Location | Significance & Description |
| :--- | :--- | :--- |
| **FOLDER_NAME** | Python Code (main.py) | Specifies the Google Drive folder name (SMSB&RP) scanned for daily backup files. |
| **Project ID** | GCP Configuration | sms-cl-automations — the active Google Cloud project hosting the serverless function. |
| **Region** | GCP Deployment | australia-southeast1 — geographic deployment zone for Cloud Run and supporting services. |
| **Entry Point** | Cloud Function Config | process_backups — the primary Python function handler executed upon HTTP trigger. |
| **Table Widths** | HTML / CSS Template | Fixed sizing values (250px, 150px, 600px, 50px) guaranteeing uniform layout across email clients. |

---

## 3. Step-by-Step Access Guide: Google Cloud & Terminal
### Accessing Google Cloud Console
1. Open your web browser and navigate to the Google Cloud Console (https://console.cloud.google.com/).
2. Click the project dropdown selector located at the top navigation bar.
3. Select the **sms-cl-automations** project.

### Accessing Google Cloud Shell (Terminal)
1. In the top right corner of the Google Cloud Console, click the **Activate Cloud Shell** icon (>_).
2. Cloud Shell provides an authenticated, pre-configured Linux terminal environment loaded with the Google Cloud SDK (gcloud), Git, and Python.

---

## 4. Disaster Recovery & Re-creation Guide (Setup from Scratch)
1. **Initialize Local Directory:** `cd ~ && mkdir -p sms-cl-daily-follow-up-digest && cd sms-cl-daily-follow-up-digest`
2. **Enable GCP APIs:** `gcloud config set project sms-cl-automations && gcloud services enable run.googleapis.com cloudbuild.googleapis.com drive.googleapis.com`
3. **Configure Drive Folder Permissions:** Share the `SMSB&RP` folder in Google Drive with `635312912411-compute@developer.gserviceaccount.com`.
4. **Deploy Function:**
   `gcloud functions deploy sms-cl-daily-follow-up-digest --gen2 --runtime=python311 --region=australia-southeast1 --source=. --entry-point=process_backups --trigger-http --memory=8Gi --timeout=900s --allow-unauthenticated`

---

## 5. GitHub Backup Integration & Automation Setup
1. **Configure Git Identity:** `git config --global user.name "GT-TW-O" && git config --global user.email "tomward@outlook.com"`
2. **Push Backups:** `git add . && git commit -m "Backup" && git push origin main`
