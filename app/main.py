import os
import logging
import sqlite3
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routes import appointment, voice, phone


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


app = FastAPI(title="American Dental Clinic AI Receptionist", docs_url="/docs", redoc_url="/redoc")


# Add CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(appointment.router, prefix="/api")
app.include_router(voice.router)
app.include_router(phone.router, prefix="/api")


# Initialize DB
from app.db import init_db
init_db()

# Seed doctors data
try:
    from seed_doctors import seed_doctors
    seed_doctors()
except Exception as e:
    logger.warning(f"Failed to seed doctors: {e}")


# Serve frontend for testing
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def home():
    return {"status":"ok", "message":"American Dental Clinic AI Receptionist: visit /static/index.html"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2023-12-01T00:00:00Z"}


@app.get("/config.js", response_class=HTMLResponse)
async def frontend_config():
    """Serve dynamic configuration to the frontend"""
    websocket_url = os.environ.get("WEBSOCKET_URL", "")
    if not websocket_url:
        # Default to relative URL if not set
        websocket_url = "/ws/ai"
    
    config_js = f"""
    // Dynamic configuration from backend
    window.WEBSOCKET_URL = "{websocket_url}";
    console.log("WebSocket URL configured from backend:", window.WEBSOCKET_URL);
    """
    return config_js


@app.get("/database", response_class=HTMLResponse)
async def database_view():
    """View database tables in browser"""
    try:
        # Connect to database
        conn = sqlite3.connect("appointments.db")
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Generate HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Database Viewer</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .table-container { margin: 20px 0; }
                h2 { color: #333; }
                .no-data { color: #666; font-style: italic; }
            </style>
        </head>
        <body>
            <h1>Database Viewer</h1>
        """
        
        if not tables:
            html += "<p>No tables found in database.</p>"
        else:
            for table in tables:
                table_name = table[0]
                html += f"<h2>Table: {table_name}</h2>"
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                html += "<h3>Schema:</h3><table><tr>"
                for col in columns:
                    html += f"<th>{col[1]} ({col[2]})</th>"
                html += "</tr></table>"
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                html += f"<p><strong>Rows:</strong> {count}</p>"
                
                # Show sample data (first 10 rows)
                if count > 0:
                    html += "<h3>Sample Data:</h3>"
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
                    rows = cursor.fetchall()
                    
                    html += "<table><tr>"
                    for col in columns:
                        html += f"<th>{col[1]}</th>"
                    html += "</tr>"
                    
                    for row in rows:
                        html += "<tr>"
                        for cell in row:
                            html += f"<td>{cell}</td>"
                        html += "</tr>"
                    html += "</table>"
                else:
                    html += "<p class='no-data'>No data in this table.</p>"
        
        html += """
        </body>
        </html>
        """
        
        conn.close()
        return html
        
    except Exception as e:
        return f"<h1>Error</h1><p>Failed to connect to database: {str(e)}</p>"


@app.get("/dashboard", response_class=HTMLResponse)
async def clinic_dashboard():
    """Clinic management dashboard to view appointments and patient information"""
    try:
        # Connect to database
        conn = sqlite3.connect("appointments.db")
        cursor = conn.cursor()
        
        # Get all appointments (handle case where doctor_name column might not exist)
        try:
            cursor.execute("""
                SELECT 
                    a.id,
                    a.patient_name,
                    a.phone,
                    a.date,
                    a.time,
                    a.purpose,
                    a.urgency_level,
                    a.doctor_name,
                    a.created_at
                FROM appointment a
                ORDER BY a.date DESC, a.time DESC
            """)
            appointments = cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "no such column: a.doctor_name" in str(e):
                # Fallback query without doctor_name column
                cursor.execute("""
                    SELECT 
                        a.id,
                        a.patient_name,
                        a.phone,
                        a.date,
                        a.time,
                        a.purpose,
                        a.urgency_level,
                        NULL as doctor_name,
                        a.created_at
                    FROM appointment a
                    ORDER BY a.date DESC, a.time DESC
                """)
                appointments = cursor.fetchall()
            else:
                raise e
        
        # Get doctor information
        cursor.execute("SELECT name, specialty FROM doctor")
        doctors = cursor.fetchall()
        
        # Get appointment statistics
        cursor.execute("SELECT COUNT(*) FROM appointment")
        total_appointments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT patient_name) FROM appointment")
        total_patients = cursor.fetchone()[0]
        
        # Generate HTML for dashboard
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Clinic Management Dashboard</title>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f5f7fa;
                    color: #333;
                }
                .container { 
                    max-width: 1200px; 
                    margin: 0 auto; 
                }
                header { 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    padding: 20px; 
                    border-radius: 10px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                h1 { 
                    margin: 0; 
                    font-size: 2em;
                }
                .stats-container { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                    gap: 20px; 
                    margin-bottom: 30px;
                }
                .stat-card { 
                    background: white; 
                    padding: 20px; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                }
                .stat-number { 
                    font-size: 2em; 
                    font-weight: bold; 
                    color: #667eea;
                }
                .stat-label { 
                    color: #666; 
                    margin-top: 5px;
                }
                .section { 
                    background: white; 
                    margin-bottom: 30px; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    overflow: hidden;
                }
                .section-header { 
                    background: #f8f9fa; 
                    padding: 15px 20px; 
                    border-bottom: 1px solid #eee;
                    font-weight: bold;
                    color: #495057;
                }
                .doctors-grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 15px; 
                    padding: 20px;
                }
                .doctor-card { 
                    background: #e9ecef; 
                    padding: 15px; 
                    border-radius: 6px;
                    text-align: center;
                }
                .doctor-name { 
                    font-weight: bold; 
                    color: #495057;
                }
                .doctor-specialty { 
                    color: #6c757d; 
                    font-size: 0.9em;
                }
                table { 
                    width: 100%; 
                    border-collapse: collapse;
                }
                th, td { 
                    padding: 12px 15px; 
                    text-align: left; 
                    border-bottom: 1px solid #eee;
                }
                th { 
                    background-color: #f8f9fa; 
                    font-weight: 600;
                    color: #495057;
                }
                tr:hover { 
                    background-color: #f8f9fa;
                }
                .urgency-high { 
                    color: #dc3545; 
                    font-weight: bold;
                }
                .urgency-medium { 
                    color: #ffc107; 
                    font-weight: bold;
                }
                .urgency-low { 
                    color: #28a745;
                }
                .no-data { 
                    text-align: center; 
                    padding: 40px; 
                    color: #6c757d;
                }
                .refresh-btn { 
                    background: #667eea; 
                    color: white; 
                    border: none; 
                    padding: 10px 20px; 
                    border-radius: 5px; 
                    cursor: pointer;
                    float: right;
                    margin-top: 10px;
                }
                .refresh-btn:hover { 
                    background: #5a6fd8;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>🦷 Clinic Management Dashboard</h1>
                    <p>View appointments, patient information, and clinic statistics</p>
                </header>
                
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-number">""" + str(total_appointments) + """</div>
                        <div class="stat-label">Total Appointments</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">""" + str(total_patients) + """</div>
                        <div class="stat-label">Total Patients</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">""" + str(len(doctors)) + """</div>
                        <div class="stat-label">Available Doctors</div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">
                        Available Doctors
                    </div>
                    <div class="doctors-grid">
        """
        
        # Add doctor cards
        if doctors:
            for doctor in doctors:
                html += f"""
                <div class="doctor-card">
                    <div class="doctor-name">{doctor[0]}</div>
                    <div class="doctor-specialty">{doctor[1]}</div>
                </div>
                """
        else:
            html += "<p>No doctors available</p>"
        
        html += """
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">
                        Recent Appointments
                        <button class="refresh-btn" onclick="location.reload()">Refresh</button>
                    </div>
        """
        
        # Add appointments table
        if appointments:
            html += """
                    <table>
                        <thead>
                            <tr>
                                <th>Patient Name</th>
                                <th>Phone</th>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Doctor</th>
                                <th>Purpose</th>
                                <th>Urgency</th>
                                <th>Booked At</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for appointment in appointments:
                # Format urgency level with color
                urgency_class = ""
                if appointment[6] == "high":
                    urgency_class = "urgency-high"
                elif appointment[6] == "medium":
                    urgency_class = "urgency-medium"
                else:
                    urgency_class = "urgency-low"
                
                doctor_name = appointment[7] if appointment[7] else 'Not assigned'
                
                html += f"""
                            <tr>
                                <td>{appointment[1]}</td>
                                <td>{appointment[2]}</td>
                                <td>{appointment[3]}</td>
                                <td>{appointment[4]}</td>
                                <td>{doctor_name}</td>
                                <td>{appointment[5] if appointment[5] else 'Not specified'}</td>
                                <td class="{urgency_class}">{appointment[6].title()}</td>
                                <td>{appointment[8][:16]}</td>
                            </tr>
                """
            
            html += """
                        </tbody>
                    </table>
            """
        else:
            html += """
                    <div class="no-data">
                        <h3>No appointments found</h3>
                        <p>Patients will appear here after booking appointments</p>
                    </div>
            """
        
        html += """
                </div>
            </div>
            
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(function(){
                    location.reload();
                }, 30000);
            </script>
        </body>
        </html>
        """
        
        conn.close()
        return html
        
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .error {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <h1>Dashboard Error</h1>
            <p class="error">Failed to load dashboard: {str(e)}</p>
            <p>Please make sure the database is initialized and contains data.</p>
        </body>
        </html>
        """


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)