import os
import xml.etree.ElementTree as ET
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

# Compute the absolute path to the .env file (one directory up)
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')

def load_env():
    """Read the .env file and return a dict of key-value pairs."""
    config = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
    return config

def write_env(new_config):
    """Write the key-value pairs in new_config to the .env file."""
    with open(ENV_PATH, 'w') as f:
        for key, value in new_config.items():
            f.write(f"{key}={value}\n")

def get_active_app(roku_ip):
    """
    Query the Roku device for its active app.
    Returns the app name or an error message.
    """
    url = f"http://{roku_ip}:8060/query/active-app"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            app_elem = root.find('app')
            if app_elem is not None:
                return app_elem.text
            else:
                return "No active app"
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {e}"

def get_apps(roku_ip):
    """
    Query the Roku device for the list of installed apps.
    Returns a list of dictionaries with 'id' and 'name' keys,
    sorted alphabetically by app name.
    """
    url = f"http://{roku_ip}:8060/query/apps"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            apps = []
            for app in root.findall('app'):
                app_id = app.attrib.get('id', 'N/A')
                app_name = app.text or 'N/A'
                apps.append({"id": app_id, "name": app_name})
            # Sort apps alphabetically by app name (case-insensitive)
            apps = sorted(apps, key=lambda x: x["name"].lower())
            return apps
        else:
            return [{"error": f"HTTP {response.status_code}"}]
    except Exception as e:
        return [{"error": str(e)}]

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key

@app.route('/login', methods=['GET', 'POST'])
def login():
    config = load_env()
    admin_password = config.get("ADMIN_PASSWORD", "admin")
    if request.method == 'POST':
        password = request.form.get('password')
        if password == admin_password:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash("Invalid password", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    config = load_env()
    tv1_ip = config.get("TV01_IP", "10.24.10.23")
    tv2_ip = config.get("TV02_IP", "10.24.10.99")
    
    active_app_tv1 = get_active_app(tv1_ip)
    active_app_tv2 = get_active_app(tv2_ip)
    
    # Retrieve the list of apps from TV01 using the /query/apps endpoint
    apps = get_apps(tv1_ip)
    
    if request.method == 'POST':
        config['TV01_IP'] = request.form.get('TV01_IP')
        config['TV02_IP'] = request.form.get('TV02_IP')
        config['APP1_ID'] = request.form.get('APP1_ID')
        config['APP2_ID'] = request.form.get('APP2_ID')
        config['APP3_ID'] = request.form.get('APP3_ID')
        config['APP4_ID'] = request.form.get('APP4_ID')
        config['ADMIN_PASSWORD'] = request.form.get('ADMIN_PASSWORD')
        config['ICON_DIR'] = request.form.get('ICON_DIR')
        
        write_env(config)
        flash("Configuration updated!", "success")
        return redirect(url_for('admin'))
    
    return render_template('admin.html',
                           config=config,
                           tv1_ip=tv1_ip,
                           tv2_ip=tv2_ip,
                           active_app_tv1=active_app_tv1,
                           active_app_tv2=active_app_tv2,
                           apps=apps)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
