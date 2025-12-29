import psutil
import flask
import os
import numpy
import json
from datetime import datetime
import threading
import time

app = flask.Flask(__name__, template_folder='errors')

config = {
    "name": "New Dashboard",
    "disks": {},
    "logLines": 10000
} if not os.path.exists('config.json') else json.load(open('config.json'))

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

@app.errorhandler(403)
def forbiddon(e):
    return flask.render_template('403.html'), 403

@app.errorhandler(404)
def notfound(e):
    return flask.render_template('404.html'), 404

@app.route('/', methods=["GET"])
def index():
    return flask.send_file('index.html')

@app.route('/<file>')
def sendFile(file):
    if os.path.exists(file):
        return flask.send_file(file)
    else:
        flask.abort(404)

@app.route('/system/reboot', methods=['POST'])
def reboot():
    if os.name == 'nt':
        os.system("shutdown /r /t 1")
    else:
        os.system("sudo reboot")
    return '', 204

@app.route('/system')
def system():
    return flask.abort(403)

@app.route('/system/rename', methods=['POST'])
def rename():
    data = flask.request.get_json()
    config['name'] = data.get('name', 'Unnamed Device')
    save_config()

@app.route('/system/name', methods=['GET'])
def get_name():
    name = config.get('name', 'much wow, very dash')
    return flask.jsonify({"name": name})

@app.route('/system/disks/add', methods=['POST'])
def add_disk():
    data = flask.request.get_json()
    disk_name = data.get('name', 'Unnamed Disk')
    color = data.get('color', '#4ade80')
    disk_identifier = data.get('disk')
    if not disk_identifier:
        return flask.jsonify({"error": "missing disk identifier"}), 400
    # Store disk as object with name and color for future extensibility
    config.setdefault('disks', {})
    config['disks'][disk_identifier] = {"name": disk_name, "color": color}
    save_config()
    return '', 204

@app.route('/system/disks/remove', methods=['POST'])
def remove_disk():
    data = flask.request.get_json()
    disk_identifier = data.get('disk')
    if not disk_identifier:
        return flask.jsonify({"error": "missing disk identifier"}), 400
    if 'disks' in config and disk_identifier in config['disks']:
        del config['disks'][disk_identifier]
        save_config()
    return '', 204

@app.route('/dashboard/create/disk', methods=['GET'])
def create_disk():
    return flask.send_file('createdisk.html')

@app.route('/config/edit/', methods=['GET', 'POST'])
def edit_config():
    if flask.request.method == 'GET':
        return flask.send_file('config.html')
    data = flask.request.get_json()
    config['logLines'] = data.get('logLines', 10000)
    config['name'] = data.get('name', config['name'])
    save_config()
    return '', 200

@app.route('/system/usage/disks', methods=['GET'])
def usage_disks():
    disks = []
    for disk, v in config.get('disks', {}).items():
        # v can be a string (legacy) or an object with name/color
        if isinstance(v, dict):
            name = v.get('name', disk)
            color = v.get('color', '#4ade80')
        else:
            name = v
            color = '#4ade80'

        try:
            usage = psutil.disk_usage(disk)
            connected = True
            total_mb = usage.total // (1024**2)
            used_mb = usage.used // (1024**2)
            free_mb = total_mb - used_mb
            usage_percent = usage.percent
        except Exception:
            # Disk is not accessible but still include it with connected=False
            connected = False
            total_mb = 0
            used_mb = 0
            free_mb = 0
            usage_percent = 0

        disks.append({
            "identifier": disk,
            "name": name,
            "color": color,
            "connected": connected,
            "size": total_mb,
            "used": used_mb,
            "free": free_mb,
            "percent": usage_percent
        })

    return flask.jsonify(disks)
def background_logger():
    """Continuously log system usage in the background"""
    while True:
        try:
            max_lines = config.get('logLines', 10000)
            ram = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery() if psutil.sensors_battery() else None
            
            # Convert bytes to Megabytes
            ramused = ram.used // (1024**2)
            ramtotal = ram.total // (1024**2)
            disktotal = disk.total // (1024**2)
            diskused = disk.used // (1024**2)

            now = datetime.now()
            timestamp = now.isoformat()
            
            # Write to text log
            with open('usage.log', 'a') as f:
                if battery is not None:
                    f.write(f"[{now}] CPU: {cpu}%, RAM: {ramused} MB / {ramtotal} MB ({ram.percent}%), Disk (root): {diskused} MB / {disktotal} MB ({disk.percent}%), Battery: {battery.percent}%\n")
                else:
                    f.write(f"[{now}] CPU: {cpu}%, RAM: {ramused} MB / {ramtotal} MB ({ram.percent}%), Disk (root): {diskused} MB / {disktotal} MB ({disk.percent}%)\n")
            
            if not max_lines == 0:
                with open('usage.log', 'r') as f:
                    lines = f.readlines()
                    if len(lines) > max_lines:
                        # remove oldest lines
                        lines = lines[-max_lines:]
                
                with open('usage.log', 'w') as f:
                    f.writelines(lines)
            
            # Write to JSON log for graphing
            json_data = {
                "timestamp": timestamp,
                "cpu": round(cpu, 2),
                "ram_used": ramused,
                "ram_total": ramtotal,
                "ram_percent": round(ram.percent, 2),
                "disk_used": diskused,
                "disk_total": disktotal,
                "disk_percent": round(disk.percent, 2),
                "battery_percent": round(battery.percent, 2) if battery is not None else None
            }
            
            # Read existing data
            graph_data = []
            if os.path.exists('usage.json'):
                try:
                    with open('usage.json', 'r') as f:
                        graph_data = json.load(f)
                except:
                    graph_data = []
            
            # Add new entry
            graph_data.append(json_data)
            
            # Keep only the most recent entries
            if len(graph_data) > max_lines:
                graph_data = graph_data[-max_lines:]
            
            # Write back to file
            with open('usage.json', 'w') as f:
                json.dump(graph_data, f, indent=2)
            
            time.sleep(5)  # Log every 5 seconds
        except Exception as e:
            print(f"Error in background logger: {e}")
            time.sleep(5)

# Start background logger thread
logger_thread = threading.Thread(target=background_logger, daemon=True)
logger_thread.start()

fetches = 0

@app.route('/log/download', methods=["GET"])
def download_log():
    return flask.send_file('usage.log', as_attachment=True)

@app.route('/api/graph/data', methods=["GET"])
def get_graph_data():
    """Return JSON graph data"""
    try:
        with open('usage.json', 'r') as f:
            data = json.load(f)
        return flask.jsonify(data)
    except:
        return flask.jsonify([])

@app.route('/graphview', methods=["GET"])
def graphview():
    return flask.send_file('graphview.html')

@app.route('/system/usage', methods=["GET"])
def log_usage():
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    disk = psutil.disk_usage('/')
    
    # Convert bytes to Megabytes
    ramused = ram.used // (1024**2)
    ramtotal = ram.total // (1024**2)
    disktotal = disk.total // (1024**2)
    diskused = disk.used // (1024**2)

    returnList = {
        "ram_used": ramused,
        "ram_total": ramtotal,
        "ram_percent": ram.percent,
        "disk_used": diskused,
        "disk_total": disktotal,
        "disk_percent": disk.percent,
        "cpu": 100,
        "has_battery": True if psutil.sensors_battery() is not None else False,
        "battery_percent": psutil.sensors_battery().percent if psutil.sensors_battery() else None,
        "battery_is_charging": psutil.sensors_battery().power_plugged if psutil.sensors_battery() else None
    }
    return flask.jsonify(returnList)

@app.route('/config/lines', methods=['GET'])
def get_log_lines():
    log_lines = config.get('logLines', 10000)
    return flask.jsonify({"logLines": log_lines})

try:
    if __name__ == "__main__":
        app.run('0.0.0.0', 80)
except KeyboardInterrupt as e:
    save_config()