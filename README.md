# ShiftSense
Automated multi-region rota generation system using rule-based logic and linear programming with persistent fairness tracking and Streamlit interface.


ShiftSense – Automated Rota Generation System

ShiftSense is a rule-based and linear programming–driven workforce scheduling system designed to generate fair and balanced weekly rotas across multi-region teams.

Built for operational environments requiring structured task allocation, it automates shift coverage while ensuring fairness, availability compliance, and role rotation.

🚀 Features

1. Automated weekly rota generation

2. Linear programming–based coverage optimisation

3. Fair task rotation with exhaustion tracking

4. Persistent assignment history (task_data.json)

5. Prevention of consecutive critical-role assignments

6. Multi-role support (Hypercare, SIM, DOR, WIMS, EOD)

7. Multi-region team support (UK, Barcelona, India)

8. Streamlit dashboard with CSV export

🏗 Architecture

-> Input Layer

  - Schedule JSON (fixed shift schedule)

  - Holiday Tracker (Excel availability file)

-> Optimisation Layer

  - Linear programming model for feasibility and shift coverage

  - Rule-based assignment constraints

  - Fairness Engine

  - JSON-based task flags

  - Rotation tracking per employee

  - Automatic reset when all employees complete a cycle

-> Interface Layer

  - Streamlit dashboard

  - Assignment history viewer

  - CSV export functionality

->  Input Format

  - Schedule JSON
      {
        "employee_login": {
          "Mon": "06:30-15:00",
          "Tue": "11:30-20:00",
          "Wed": "14:30-23:00"
        }
      }


-> Fairness Logic

  - Track assignment history per employee
  
  - Prevent repeated task allocation within a cycle
  
  - Mark task flags (true / false)
  
  - Automatically reset flags when all employees are exhausted
    



🛠 Tech Stack

  Python

  Streamlit

  Linear Programming (LP solver)

  Pandas

JSON state management

📌 Version

v1.0 – Enterprise Rota Automation System
