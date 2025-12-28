import psutil
import flask
import os
from datetime import datetime

app = flask.Flask(__name__, template_folder='errors')

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



if __name__ == "__main__":
    app.run('0.0.0.0', 80, debug=True)