import psutil
import flask
import os
import numpy
import json
from datetime import datetime

app = flask.Flask(__name__, template_folder='errors')

config = {
    "name": "much wow, very dash",
    "disks": {"/": "Main Disk"}
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
        except Exception:
            # Skip disks we can't stat (invalid mount points, etc.)
            continue

        total_mb = usage.total // (1024**2)
        used_mb = usage.used // (1024**2)
        free_mb = total_mb - used_mb
        disks.append({
            "identifier": disk,
            "name": name,
            "color": color,
            "size": total_mb,
            "used": used_mb,
            "free": free_mb,
            "percent": usage.percent
        })

    return flask.jsonify(disks)

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
        "ram_used": ramused,       # Use : instead of =
        "ram_total": ramtotal,
        "ram_percent": ram.percent,
        "disk_used": diskused,
        "disk_total": disktotal,
        "disk_percent": disk.percent, # Get the specific value
        "cpu": cpu
    }

    return flask.jsonify(returnList)


try:
    if __name__ == "__main__":
        app.run('0.0.0.0', 80, debug=True)
except KeyboardInterrupt as e:
    save_config()