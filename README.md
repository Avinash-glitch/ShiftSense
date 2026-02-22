# ShiftSense
Automated multi-region rota generation system using rule-based logic and linear programming with persistent fairness tracking and Streamlit interface.


ShiftSense – Automated Rota Generation System

ShiftSense is a rule-based and optimisation-driven workforce scheduling system designed to generate fair and balanced weekly rotas across multi-region teams.

Built for operational environments requiring structured task allocation, ShiftSense combines linear programming, fairness tracking, and availability constraints to automate rota generation.

🚀 Overview

ShiftSense automates weekly rota creation by:

Generating fair task assignments

Tracking employee assignment history

Preventing consecutive assignments for critical roles

Managing multiple task categories

Handling holidays, leave, and availability constraints

Ensuring rotation fairness across scheduling cycles

The system supports multi-region teams (e.g., UK, Barcelona, India) with structured shift patterns.

🏗 System Architecture

ShiftSense consists of four main layers:

1️⃣ Input Layer

Schedule JSON (fixed shift schedule)

Holiday Tracker (Excel file)

Team configuration settings

2️⃣ Optimisation Layer

Linear programming model for feasibility and coverage

Rule-based assignment constraints

Shift coverage validation

3️⃣ Fairness Engine

task_data.json persistent state

Task flags per employee

Rotation exhaustion detection

Automatic reset logic when all employees complete a cycle

4️⃣ Interface Layer

Built with Streamlit

Interactive dashboard

CSV export functionality

Assignment history search

📂 Required Input Files
1️⃣ Schedule JSON

Defines fixed employee shift schedules.

Example:

{
  "employee_login": {
    "Mon": "06:30-15:00",
    "Tue": "11:30-20:00",
    "Wed": "14:30-23:00"
  }
}

Supported shifts:

06:30–15:00 (Morning)

09:30–18:00 (Mid-Morning)

11:30–20:00 (Mid)

14:30–23:00 (Night)

23:30–08:30 (Midnight)

2️⃣ Holiday Tracker (Excel)

Defines daily availability.

Codes:

S1, S2, S3, S4 → Working

H → Holiday

P → Personal Leave

S → Sick Leave

Empty → Day Off

🧠 Core Features
✅ Fair Task Rotation

Prevents repeated assignments within the same cycle

Uses task flags stored in task_data.json

Automatically resets when all employees have completed rotation

✅ Multi-Role Allocation

Supports assignment of:

Hypercare

SIM (Shift coverage)

DOR (Daily Operations Review)

WIMS (Workload Management)

EOD (End of Day Report)

✅ Consecutive-Day Protection

Prevents assignment of sensitive roles (e.g., Hypercare) on consecutive days.

✅ Multi-Region Support

Handles:

Time zone differences

Local holidays

Regional team segmentation

✅ Persistent State Management

task_data.json stores:

Employee assignment history

Task counts

Date-based role allocation

Fairness flags

📊 Outputs

ShiftSense generates:

Weekly Rota View

Daily Statistics Dashboard

Shift Summary View

CSV exports for:

Full weekly rota

Assignment history

Statistics

⚙️ How It Works

Load schedule JSON

Load holiday tracker

Configure team roles

Run optimisation

Apply fairness rules

Persist assignment history

Export final rota

🗄 task_data.json Structure

The file stores:

Employees

Total assignments per role

Assignment history

Fairness tracking flags

Date Assignments

Role allocations per date

Shift coverage mapping

Task Flags

true → already assigned this cycle

false → eligible for assignment

When all flags are true, the system resets automatically for the next cycle.

🛠 Tech Stack

Python

Streamlit

Linear Programming (LP solver)

JSON state management

Pandas

Excel integration

🎯 Design Principles

Fairness-first allocation

Deterministic and explainable scheduling

Separation of optimisation and rule layers

Persistent state without database dependency

Lightweight and deployable as standalone executable

⚠️ Notes

Do not manually edit task_data.json

Use in-app reset functionality to clear assignment history

Ensure input file formats are validated before generation

📌 Version

v1.0
Built for enterprise rota management environments.
