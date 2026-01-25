"""
Simple web interface to view database contents
Run this and open http://localhost:8080 in your browser
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, text
from database import engine
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def view_database():
    """View database contents in a simple HTML table"""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CT Properties Database Viewer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .stats { display: flex; gap: 20px; margin: 20px 0; }
            .stat-box { background: #667eea; color: white; padding: 15px; border-radius: 6px; min-width: 150px; }
            .stat-box h3 { margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }
            .stat-box .number { font-size: 32px; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #667eea; color: white; padding: 12px; text-align: left; }
            td { padding: 10px; border-bottom: 1px solid #ddd; }
            tr:hover { background: #f9f9f9; }
            .refresh { background: #10b981; color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
            .refresh:hover { background: #059669; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏠 CT Properties Database Viewer</h1>
            <button class="refresh" onclick="location.reload()">🔄 Refresh</button>
    """
    
    try:
        with engine.connect() as conn:
            # Get statistics
            stats = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT municipality) as towns,
                    COUNT(DISTINCT property_type) as property_types,
                    COUNT(*) FILTER (WHERE is_vacant = 1) as vacant,
                    COUNT(*) FILTER (WHERE is_absentee = 1) as absentee
                FROM properties
            """)).fetchone()
            
            html += f"""
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Properties</h3>
                    <div class="number">{stats[0]:,}</div>
                </div>
                <div class="stat-box">
                    <h3>Towns</h3>
                    <div class="number">{stats[1]}</div>
                </div>
                <div class="stat-box">
                    <h3>Property Types</h3>
                    <div class="number">{stats[2]}</div>
                </div>
                <div class="stat-box">
                    <h3>Vacant</h3>
                    <div class="number">{stats[3]:,}</div>
                </div>
                <div class="stat-box">
                    <h3>Absentee Owners</h3>
                    <div class="number">{stats[4]:,}</div>
                </div>
            </div>
            """
            
            # Get sample properties
            properties = conn.execute(text("""
                SELECT 
                    parcel_id,
                    address,
                    municipality,
                    property_type,
                    lot_size_sqft,
                    is_vacant,
                    is_absentee
                FROM properties
                ORDER BY id
                LIMIT 100
            """)).fetchall()
            
            html += """
            <h2>Sample Properties (First 100)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Parcel ID</th>
                        <th>Address</th>
                        <th>Municipality</th>
                        <th>Property Type</th>
                        <th>Lot Size (sqft)</th>
                        <th>Vacant</th>
                        <th>Absentee</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for prop in properties:
                html += f"""
                    <tr>
                        <td><strong>{prop[0]}</strong></td>
                        <td>{prop[1] or 'N/A'}</td>
                        <td>{prop[2] or 'N/A'}</td>
                        <td>{prop[3] or 'N/A'}</td>
                        <td>{prop[4]:,.0f if prop[4] else 'N/A'}</td>
                        <td>{'✅' if prop[5] == 1 else '❌'}</td>
                        <td>{'✅' if prop[6] == 1 else '❌'}</td>
                    </tr>
                """
            
            html += """
                </tbody>
            </table>
            """
            
            # Get municipalities breakdown
            municipalities = conn.execute(text("""
                SELECT municipality, COUNT(*) as count
                FROM properties
                GROUP BY municipality
                ORDER BY count DESC
                LIMIT 20
            """)).fetchall()
            
            html += """
            <h2>Properties by Municipality (Top 20)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Municipality</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for muni in municipalities:
                html += f"""
                    <tr>
                        <td>{muni[0] or 'Unknown'}</td>
                        <td>{muni[1]:,}</td>
                    </tr>
                """
            
            html += """
                </tbody>
            </table>
            """
            
    except Exception as e:
        html += f"<p style='color: red;'>Error: {e}</p>"
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🌐 Database Viewer Starting...")
    print("="*60)
    print("\n📊 Open your browser to: http://localhost:8080")
    print("   Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8080)
