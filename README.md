# SMS and Call Log Automation (`sms-cl-daily-follow-up-digest`)

*Enterprise-Grade Architecture, Comprehensive Re-creation, Multi-Platform Variables, and Operational Guide*

## 1. System Architecture & Core Requirements

The **sms-cl-daily-follow-up-digest** automation ingests, parses, and cleans daily Android XML communication exports (`sms-*.xml` and `calls-*.xml`) stored in Google Drive. It executes as a secure, serverless Python Cloud Run function, rendering a prioritized, professional HTML follow-up digest.

### Infrastructure Specifications

* **Active Google Cloud Project:** `sms-cl-automations` (Project Number: `635312912411`, Region: `australia-southeast1`).
* **Storage Layer:** Google Drive Folder named **`SMSB&RP`** (must be shared with the project compute service account: `635312912411-compute@developer.gserviceaccount.com`).
* **Compute Engine:** Google Cloud Run Function (Gen 2), Runtime `python311`, allocated with `8Gi` memory and a `900s` execution timeout.
* **Version Control & Backup:** GitHub repository **`GT-TW-O/SMS-CL_automations`** (`main` branch), synchronized via local Cloud Shell (`~/sms-cl-daily-follow-up-digest`) using Git credential helper `store` (`~/.git-credentials`).

### Master Table Layout (`1250px` Total Width, `table-layout: fixed;`)

* **Contact:** `250px` (Name + normalized phone number)
* **Type:** `150px` (Missed Call, Unanswered SMS, Follow-up Required)
* **Date:** `150px` (Format: `-[YYYY-MM-DD]` on top, time `HHMM` underneath)
* **Action:** `150px` (Direct click-to-call / click-to-SMS actionable links)
* **Details / Snippet:** `600px` (Cleaned multi-line text with whitespace normalization, `word-break: break-word`)
* **VIP:** `50px` (Interaction frequency score indicator)

---

## 2. Complete Cross-Platform Variable Reference

| Variable / Parameter | Platform / Scope | Exact Value & Operational Purpose |
| :--- | :--- | :--- |
| **`FOLDER_NAME`** | Python Code (`main.py`) | `'SMSB&RP'` — Specifies the target Google Drive folder scanned for daily XML backups. |
| **Project ID** | GCP Configuration | `sms-cl-automations` — The active Google Cloud project hosting the serverless function. |
| **Project Number** | GCP IAM / Drive | `635312912411` — Used in service account identifiers. |
| **Region** | GCP Deployment | `australia-southeast1` — Geographic deployment zone for Cloud Run, Cloud Build, and Cloud Functions. |
| **Entry Point** | Cloud Function Config | `process_backups` — The primary Python handler function executed upon HTTP trigger. |
| **Runtime & Specs** | Cloud Run Environment | `python311`, Memory: `8Gi`, Timeout: `900s`, Gen 2 architecture. |
| **Service Account** | Google Cloud IAM | `635312912411-compute@developer.gserviceaccount.com` — Requires Viewer/Editor permissions on the `SMSB&RP` Google Drive folder. |
| **Table Widths** | HTML / CSS Template | Fixed sizing values (`250px`, `150px`, `600px`, `50px`) guaranteeing uniform layout across email clients. |
| **GitHub Repository** | Version Control (Git) | `https://github.com/GT-TW-O/SMS-CL_automations.git` (User: `GT-TW-O`, Email: `tomward@outlook.com`, Branch: `main`). |
| **Git Credential Store** | Cloud Shell Terminal | `credential.helper store` (saves credentials persistently to `~/.git-credentials`). |

---

## 3. Step-by-Step Access Guide: Google Cloud & Terminal

### Accessing Google Cloud Console

1. Open your browser and navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown selector located in the top navigation bar.
3. Select the **`sms-cl-automations`** project.

### Accessing Google Cloud Shell (Terminal)

1. Click the **Activate Cloud Shell** icon (`>_`) in the top right corner of the Google Cloud Console.
2. Cloud Shell provides an authenticated, pre-configured Linux terminal environment loaded with `gcloud`, Git, and Python.

---

## 4. Disaster Recovery & Re-creation Guide (Setup from Scratch)

If you need to rebuild the environment from an empty state, execute these exact commands in Cloud Shell:

1. **Initialize Local Directory:**
   ```bash
   cd ~ && mkdir -p sms-cl-daily-follow-up-digest && cd sms-cl-daily-follow-up-digest
   ```

2. **Configure GCP Project & Enable Required APIs:**
   ```bash
   gcloud config set project sms-cl-automations && \
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com drive.googleapis.com
   ```

3. **Configure Google Drive Folder Permissions:**
   Share your **`SMSB&RP`** folder in Google Drive with the service account:
   `635312912411-compute@developer.gserviceaccount.com`

4. **Deploy the Cloud Function:**
   ```bash
   gcloud functions deploy sms-cl-daily-follow-up-digest \
     --gen2 \
     --runtime=python311 \
     --region=australia-southeast1 \
     --source=. \
     --entry-point=process_backups \
     --trigger-http \
     --memory=8Gi \
     --timeout=900s \
     --allow-unauthenticated
   ```

---

## 5. Adding, Modifying, and Recreating Code & Documentation

### Updating Code Locally (`main.py` or `requirements.txt`)

1. Edit your files inside `~/sms-cl-daily-follow-up-digest` using the Cloud Shell Editor or terminal text editors (`nano main.py`).
2. Test local execution or redeploy to GCP using the deployment command shown in Section 4.

### Synchronizing with GitHub

1. Configure Git identity and credential caching once:
   ```bash
   git config --global user.name "GT-TW-O" && \
   git config --global user.email "tomward@outlook.com" && \
   git config --global credential.helper store
   ```

2. Set the clean remote URL and push updates:
   ```bash
   cd ~/sms-cl-daily-follow-up-digest && \
   git remote set-url origin https://github.com/GT-TW-O/SMS-CL_automations.git && \
   git add . && \
   git commit -m "Update automation codebase and configuration" && \
   git push origin main
   ```
   *(When prompted for credentials on your first push, enter your GitHub username `GT-TW-O` and your Personal Access Token as the password).*
