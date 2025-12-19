from flask import Flask, request, jsonify, session, redirect, url_for, render_template, Response, stream_with_context
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
import time
import math
import random
import json

# Get the project root directory (parent of Eco-route folder)
# app.py is at: c:\Users\Vinay V\Eco-Route\Eco-route\app.py
# templates are at: c:\Users\Vinay V\Eco-Route\templates
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'static')
TEMPLATE_FOLDER = os.path.join(PROJECT_ROOT, 'templates')

app = Flask(__name__, static_folder=STATIC_FOLDER, template_folder=TEMPLATE_FOLDER)
app.secret_key = os.environ.get('ECO_ROUTE_SECRET', 'eco_route_dev_secret')

DB_PATH = os.path.join(os.path.dirname(__file__), 'eco_route.db')

MYSORE_ZONES = [
    {"name": "Devaraja Mohalla", "lat": 12.311, "lon": 76.652, "radius_m": 1200, "aqi": 78, "co2_factor": 0.13},
    {"name": "VV Mohalla", "lat": 12.328, "lon": 76.627, "radius_m": 900, "aqi": 65, "co2_factor": 0.12},
    {"name": "Kuvempunagar", "lat": 12.287, "lon": 76.640, "radius_m": 1400, "aqi": 72, "co2_factor": 0.12},
    {"name": "Jayalakshmipuram", "lat": 12.330, "lon": 76.617, "radius_m": 900, "aqi": 68, "co2_factor": 0.11},
    {"name": "Saraswathipuram", "lat": 12.305, "lon": 76.632, "radius_m": 1100, "aqi": 70, "co2_factor": 0.12},
    {"name": "Chamundi Hills", "lat": 12.289, "lon": 76.689, "radius_m": 2000, "aqi": 55, "co2_factor": 0.10},
    {"name": "Hebbal", "lat": 12.356, "lon": 76.623, "radius_m": 1000, "aqi": 74, "co2_factor": 0.13},
    {"name": "Yadavagiri", "lat": 12.314, "lon": 76.660, "radius_m": 800, "aqi": 80, "co2_factor": 0.14},
    {"name": "Gokulam", "lat": 12.307, "lon": 76.635, "radius_m": 900, "aqi": 69, "co2_factor": 0.12},
    {"name": "Vijayanagar", "lat": 12.290, "lon": 76.610, "radius_m": 1300, "aqi": 75, "co2_factor": 0.13},
    {"name": "Hinkal", "lat": 12.345, "lon": 76.680, "radius_m": 1100, "aqi": 77, "co2_factor": 0.13},
    {"name": "Chamundipuram", "lat": 12.295, "lon": 76.625, "radius_m": 900, "aqi": 73, "co2_factor": 0.12},
    {"name": "Ashokapuram", "lat": 12.280, "lon": 76.635, "radius_m": 1000, "aqi": 71, "co2_factor": 0.12},
    {"name": "Vontikoppal", "lat": 12.300, "lon": 76.620, "radius_m": 800, "aqi": 67, "co2_factor": 0.11},
    {"name": "Nazarbad", "lat": 12.325, "lon": 76.645, "radius_m": 900, "aqi": 76, "co2_factor": 0.13},
    {"name": "Srirampura", "lat": 12.335, "lon": 76.660, "radius_m": 1000, "aqi": 79, "co2_factor": 0.14},
    {"name": "Yelwala", "lat": 12.360, "lon": 76.670, "radius_m": 1300, "aqi": 66, "co2_factor": 0.12},
    {"name": "Metagalli", "lat": 12.340, "lon": 76.600, "radius_m": 1100, "aqi": 70, "co2_factor": 0.12},
    {"name": "Ramakrishnanagar", "lat": 12.295, "lon": 76.645, "radius_m": 800, "aqi": 75, "co2_factor": 0.13},
    {"name": "Chamundi Vihar", "lat": 12.300, "lon": 76.670, "radius_m": 1200, "aqi": 79, "co2_factor": 0.14},
    {"name": "Gandhinagar", "lat": 12.330, "lon": 76.640, "radius_m": 900, "aqi": 72, "co2_factor": 0.12},
    {"name": "Kuvempunagar 2nd Stage", "lat": 12.285, "lon": 76.642, "radius_m": 1200, "aqi": 76, "co2_factor": 0.13},
    {"name": "Chamundi Hills Base", "lat": 12.292, "lon": 76.685, "radius_m": 1500, "aqi": 58, "co2_factor": 0.10},
    {"name": "rajiv nagar", "lat": 12.315, "lon": 76.615, "radius_m": 900, "aqi": 70, "co2_factor": 0.12},
    {"name": "siddarthanagar", "lat": 12.322, "lon": 76.628, "radius_m": 800, "aqi": 75, "co2_factor": 0.13},
    {"name": "manipal hospital area", "lat": 12.310, "lon": 76.635, "radius_m": 700, "aqi": 80, "co2_factor": 0.14},
]
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
    conn.commit()
    conn.close()

def get_nearest_zone(lat, lon):
    nearest = None
    best_d = None
    for z in MYSORE_ZONES:
        d = haversine(lat, lon, z["lat"], z["lon"]) * 1000
        if best_d is None or d < best_d:
            best_d = d
            nearest = z
    return nearest

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

def route_metrics(coords):
    aqi_values = []
    co2_factors = []
    for idx in range(0, len(coords), max(1, len(coords)//15)):
        lon, lat = coords[idx]
        z = get_nearest_zone(lat, lon)
        aqi_values.append(z["aqi"]) 
        co2_factors.append(z["co2_factor"]) 
    avg_aqi = sum(aqi_values)/len(aqi_values) if aqi_values else 0
    avg_co2_factor = sum(co2_factors)/len(co2_factors) if co2_factors else 0.12
    eco_score = max(0, 100 - (avg_aqi * 0.6 + avg_co2_factor*100*0.4))
    return avg_aqi, avg_co2_factor, eco_score

def aqi_subindex_pm25(c):
    bp = [(0,30,0,50),(31,60,51,100),(61,90,101,200),(91,120,201,300),(121,250,301,400),(251,300,401,500)]
    for lo,hi,ilo,ihi in bp:
        if c<=hi:
            return (ihi-ilo)/(hi-lo)*(c-lo)+ilo
    return 500

def aqi_subindex_pm10(c):
    bp = [(0,50,0,50),(51,100,51,100),(101,250,101,200),(251,350,201,300),(351,430,301,400),(431,500,401,500)]
    for lo,hi,ilo,ihi in bp:
        if c<=hi:
            return (ihi-ilo)/(hi-lo)*(c-lo)+ilo
    return 500

def indian_aqi(pm25, pm10):
    s25 = aqi_subindex_pm25(pm25) if pm25 is not None else 0
    s10 = aqi_subindex_pm10(pm10) if pm10 is not None else 0
    return max(s25, s10)

def fetch_air_quality(lat, lon):
    url = 'https://air-quality-api.open-meteo.com/v1/air-quality'
    params = {'latitude': lat, 'longitude': lon, 'hourly': ['pm10','pm2_5'], 'timezone': 'auto'}
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        return None
    j = r.json()
    if 'hourly' not in j:
        return None
    h = j['hourly']
    pm25 = None
    pm10 = None
    if 'pm2_5' in h and h['pm2_5']:
        pm25 = h['pm2_5'][-1]
    if 'pm10' in h and h['pm10']:
        pm10 = h['pm10'][-1]
    return {'pm25': pm25, 'pm10': pm10}

def compute_area_metrics(speed_kmh=30.0):
    out = []
    for z in MYSORE_ZONES:
        aq = fetch_air_quality(z['lat'], z['lon'])
        pm25 = aq['pm25'] if aq else None
        pm10 = aq['pm10'] if aq else None
        aqi = indian_aqi(pm25 or 0, pm10 or 0)
        co2_per_km = 0.192
        co2_rate_kgh = co2_per_km * speed_kmh
        aqi_norm = min(100.0, aqi/5.0)
        co2_norm = min(100.0, (co2_per_km/0.25)*100.0)
        eco_score = max(0.0, 100.0 - (0.6*aqi_norm + 0.4*co2_norm))
        out.append({
            'name': z['name'],
            'lat': z['lat'],
            'lon': z['lon'],
            'pm25': pm25,
            'pm10': pm10,
            'aqi': round(aqi,1),
            'eco_score': round(eco_score,1),
            'co2_per_km': round(co2_per_km,3),
            'co2_rate_kgh': round(co2_rate_kgh,3)
        })
    return out

def fetch_weather(lat, lon):
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': ['temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'weather_code'],
        'hourly': ['precipitation_probability'],
        'timezone': 'auto'
    }
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        return None
    j = r.json()
    cur = j.get('current', {})
    temp = cur.get('temperature_2m')
    rh = cur.get('relative_humidity_2m')
    wind = cur.get('wind_speed_10m')
    code = cur.get('weather_code')
    rain_prob = None
    if 'hourly' in j and 'precipitation_probability' in j['hourly'] and j['hourly']['precipitation_probability']:
        rain_prob = j['hourly']['precipitation_probability'][-1]
    return {'temperature_c': temp, 'humidity': rh, 'wind_kmh': wind, 'code': code, 'rain_probability': rain_prob}

@app.route('/')
def root():
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json(force=True)
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not name or not email or not password:
        return jsonify({'error': 'missing_fields'}), 400
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)', (name, email, generate_password_hash(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'email_exists'}), 409
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True)
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'missing_fields'}), 400
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, password_hash, name FROM users WHERE email = ?', (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'invalid_credentials'}), 401
    uid, phash, name = row
    if not check_password_hash(phash, password):
        return jsonify({'error': 'invalid_credentials'}), 401
    session['user_id'] = uid
    session['user_name'] = name
    return jsonify({'status': 'ok', 'name': name})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'status': 'ok'})

@app.route('/api/profile')
def api_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthenticated'}), 401
    return jsonify({'id': session['user_id'], 'name': session['user_name']})

@app.route('/api/geocode')
def api_geocode():
    q = request.args.get('q')
    if not q:
        return jsonify({'error': 'missing_q'}), 400
    params = {
        'q': q + ', Mysuru, Karnataka, India',
        'format': 'json',
        'limit': 1
    }
    headers = {'User-Agent': 'EcoRoute/1.0'}
    r = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=15)
    if r.status_code != 200 or not r.json():
        return jsonify({'error': 'not_found'}), 404
    j = r.json()[0]
    return jsonify({'lat': float(j['lat']), 'lon': float(j['lon']), 'display_name': j['display_name']})

@app.route('/api/route')
def api_route():
    try:
        flon = float(request.args.get('from_lon'))
        flat = float(request.args.get('from_lat'))
        tlon = float(request.args.get('to_lon'))
        tlat = float(request.args.get('to_lat'))
    except Exception:
        return jsonify({'error': 'bad_coords'}), 400
    osrm_url = f'https://router.project-osrm.org/route/v1/driving/{flon},{flat};{tlon},{tlat}'
    params = {'overview': 'full', 'alternatives': 'true', 'geometries': 'geojson', 'steps': 'true'}
    r = requests.get(osrm_url, params=params, timeout=20)
    if r.status_code != 200:
        return jsonify({'error': 'routing_failed'}), 502
    data = r.json()
    if 'routes' not in data or not data['routes']:
        return jsonify({'error': 'no_routes'}), 404
    def instr_for_step(step):
        m = step.get('maneuver', {})
        t = m.get('type', '')
        mod = m.get('modifier', '')
        name = step.get('name') or 'road'
        if t == 'turn':
            return f"Turn {mod or ''} onto {name}".replace('  ',' ')
        if t == 'depart':
            return f"Head {mod or ''} on {name}".replace('  ',' ')
        if t == 'arrive':
            return "Arrive at destination"
        if t == 'roundabout':
            ex = m.get('exit')
            return f"At roundabout, take exit {ex} onto {name}" if ex else f"At roundabout, continue onto {name}"
        if t in ('new name','merge','continue'):
            return f"Continue onto {name}"
        if t == 'fork':
            return f"Keep {mod or ''} onto {name}".replace('  ',' ')
        return f"Continue on {name}"

    routes = []
    for rt in data['routes']:
        coords = rt['geometry']['coordinates']
        dist_km = rt['distance']/1000.0
        dur_min = rt['duration']/60.0
        avg_aqi, avg_co2_factor, eco_score = route_metrics(coords)
        co2_kg = dist_km * (avg_co2_factor * 0.2)
        steps = []
        for leg in rt.get('legs', []):
            for st in leg.get('steps', []):
                s = {
                    'distance_m': st.get('distance', 0),
                    'duration_s': st.get('duration', 0),
                    'location': st.get('maneuver', {}).get('location', []),
                    'text': instr_for_step(st)
                }
                steps.append(s)
        routes.append({
            'distance_km': round(dist_km, 2),
            'duration_min': round(dur_min, 1),
            'avg_aqi': round(avg_aqi, 1),
            'co2_kg': round(co2_kg, 3),
            'eco_score': round(eco_score, 1),
            'pollution_index': avg_aqi*0.7 + co2_kg*0.3,
            'geometry': coords,
            'steps': steps
        })
    eco = sorted(routes, key=lambda x: (x['pollution_index']))[0]
    polluted = sorted(routes, key=lambda x: (x['pollution_index']), reverse=True)[0]
    return jsonify({'polluted': polluted, 'eco': eco, 'zones': MYSORE_ZONES})

@app.route('/api/aqi-stream')
def api_aqi_stream():
    def gen():
        while True:
            speed = float(request.args.get('speed_kmh', 30.0))
            payload = compute_area_metrics(speed)
            msg = 'data: ' + json.dumps(payload) + '\n\n'
            yield msg
            time.sleep(15)
    return Response(stream_with_context(gen()), mimetype='text/event-stream')

@app.route('/api/areas-metrics')
def api_areas_metrics():
    try:
        speed = float(request.args.get('speed_kmh', 30.0))
    except Exception:
        speed = 30.0
    data = compute_area_metrics(speed)
    return jsonify({'areas': data})

@app.route('/api/weather')
def api_weather():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    except Exception:
        return jsonify({'error': 'bad_coords'}), 400
    w = fetch_weather(lat, lon)
    if not w:
        return jsonify({'error': 'weather_failed'}), 502
    return jsonify(w)

@app.route('/api/weather-stream')
def api_weather_stream():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    except Exception:
        return jsonify({'error': 'bad_coords'}), 400
    def gen():
        while True:
            w = fetch_weather(lat, lon)
            msg = 'data: ' + json.dumps(w or {}) + '\n\n'
            yield msg
            time.sleep(60)
    return Response(stream_with_context(gen()), mimetype='text/event-stream')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)

