# 🚀 Deployment Automation Scripts

This repository contains Python scripts to automate the **safe deployment of backend and frontend applications**.

These scripts are designed for environments where:

* Code is pushed to GitHub first
* Deployment is triggered manually on a server machine
* Backend and frontend are deployed separately

---

# 📁 Scripts Overview

## 1. Backend Deployment Script

```bash
deploy_backend_server.py
```

### Purpose

* Pull latest backend code from the main branch
* Detect database-related changes
* Pause deployment if DB changes are found
* Allow manual migration execution
* Resume deployment safely
* Restart backend service

---

## 2. Frontend Deployment Script

```bash
deploy_frontend_server.py
```

### Purpose

* Pull latest frontend code from the main branch
* Install dependencies if required
* Build the frontend application
* Backup existing deployed build
* Replace with the new build

---

# 🔄 Deployment Flow

## Backend Deployment

### Step 1: Run deployment

```bash
python deploy_backend_server.py
```

### Step 2: If NO DB changes

* Dependencies are installed if needed
* Backend is restarted
* Deployment completes

---

### Step 3: If DB changes are detected

The script will:

* Pause deployment
* Display DB-related changed files
* Ask for manual migration execution

Run the required migrations using your standard process.

---

### Step 4: Resume deployment

```bash
python deploy_backend_server.py --resume
```

This will:

* Continue deployment
* Restart backend service

---

## Frontend Deployment

```bash
python deploy_frontend_server.py
```

This will:

* Pull latest code
* Install dependencies if needed
* Build the project
* Backup current build
* Replace deployed build

---

# 📌 Important Notes

## 1. Keep Server Code Clean

* Do NOT modify code directly on the server
* Always deploy from version-controlled code

---

## 2. Database Changes Handling

* Deployment will pause if DB-related changes are detected
* Migrations must be completed manually before resuming

---

## 3. Deployment Order

Always follow:

```text
1. Deploy backend
2. Run migrations (if required)
3. Resume backend deployment
4. Deploy frontend
```

---

## 4. Backup Safety

* Frontend deployment automatically creates backups before replacing builds

---

# ⚠️ Limitations

* Database migrations are not fully automated (by design for safety)
* Configuration or environment changes require manual review
* Scripts assume backend and frontend are deployed on the same environment

---

# 🧠 Best Practices

* Use feature branches and review changes before merging
* Keep the main branch always stable and deployable
* Validate migrations before resuming deployment
* Avoid making direct changes on the deployment environment

---

# ✅ Summary

These scripts provide:

* ✔ Safe backend deployment with pause/resume mechanism
* ✔ Controlled handling of database changes
* ✔ Automated frontend build and deployment
* ✔ Backup and recovery support
* ✔ Simple and reliable deployment workflow

---

**Use these scripts to standardize and streamline your deployment process.**
