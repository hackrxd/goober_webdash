import psutil
import flask
import os
import numpy
import json
from datetime import datetime
import threading
import time
import subprocess

app = flask.Flask(__name__, template_folder='errors')

config = {
    "name": "New Dashboard",
    "disks": {},
    "logLines": 10000
} if not os.path.exists('config.json') else json.load(open('config.json'))

# check for github updates and auto-update files
# restart server afterwards if files were changed

update_status = {
    "last_check": None,
    "last_check_error": None,
    "update_available": False,
    "local_commit": None,
    "remote_commit": None,
    "is_updating": False,
    "check_count": 0,
    "failed_checks": 0
}

def log_update(message):
    """Log update messages to update.log with timestamp"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        with open('update.log', 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to update.log: {e}")

def run_command(cmd):
    """Run a command and return output, handling both Windows and Unix"""
    try:
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.returncode, result.stderr.strip()
    except Exception as e:
        return "", 1, str(e)

def check_updates():
    """Check for updates and return status"""
    global update_status
    
    try:
        update_status["check_count"] += 1
        
        # Check if git is available
        git_check, code, _ = run_command("git --version")
        if code != 0:
            update_status["last_check_error"] = "Git not installed or not in PATH"
            update_status["failed_checks"] += 1
            log_update("ERROR: Git not installed or not in PATH")
            return False
        
        # Fetch updates from remote
        fetch_output, fetch_code, fetch_err = run_command("git fetch origin main")
        if fetch_code != 0:
            # Handle Git's 'detected dubious ownership' by adding safe.directory and retrying
            fetch_err_lower = (fetch_err or "").lower()
            if "detected dubious ownership" in fetch_err_lower or "dubious ownership" in fetch_err_lower:
                suggested_cmd = f"git config --global --add safe.directory {os.getcwd()}"
                log_update(f"WARNING: Detected dubious ownership. Attempting to add safe.directory: {os.getcwd()}")
                # Try to add safe.directory automatically
                cfg_out, cfg_code, cfg_err = run_command(suggested_cmd)
                if cfg_code == 0:
                    log_update("INFO: Added safe.directory successfully, retrying git fetch")
                    fetch_output, fetch_code, fetch_err = run_command("git fetch origin main")
                    if fetch_code != 0:
                        error_msg = f"Git fetch failed after adding safe.directory: {fetch_err or 'unknown error'}"
                        update_status["last_check_error"] = error_msg
                        update_status["failed_checks"] += 1
                        log_update(f"ERROR: {error_msg}")
                        return False
                else:
                    # Failed to add safe.directory; include suggestion in error
                    error_msg = (
                        f"Git fetch failed: {fetch_err or 'unknown error'}. "
                        f"To fix, run: {suggested_cmd}"
                    )
                    update_status["last_check_error"] = error_msg
                    update_status["failed_checks"] += 1
                    log_update(f"ERROR: {error_msg}")
                    return False
            else:
                error_msg = f"Git fetch failed: {fetch_err or 'unknown error'}"
                update_status["last_check_error"] = error_msg
                update_status["failed_checks"] += 1
                log_update(f"ERROR: {error_msg}")
                return False
        
        # Get local and remote commits
        local_output, local_code, _ = run_command("git rev-parse HEAD")
        remote_output, remote_code, _ = run_command("git rev-parse origin/main")
        
        if local_code != 0 or remote_code != 0:
            update_status["last_check_error"] = "Could not get commit hashes"
            update_status["failed_checks"] += 1
            log_update("ERROR: Could not get commit hashes")
            return False
        
        local_commit = local_output[:7]
        remote_commit = remote_output[:7]
        
        update_status["local_commit"] = local_commit
        update_status["remote_commit"] = remote_commit
        update_status["last_check"] = datetime.now().isoformat()
        update_status["last_check_error"] = None
        
        if local_output != remote_output:
            update_status["update_available"] = True
            msg = f"Update available: {local_commit} -> {remote_commit}"
            log_update(msg)
            print(f"[UPDATE CHECK] {msg}")
            return True
        else:
            update_status["update_available"] = False
            msg = f"System is up to date ({local_commit})"
            log_update(msg)
            print(f"[UPDATE CHECK] {msg}")
            return False
            
    except Exception as e:
        update_status["last_check_error"] = str(e)
        update_status["failed_checks"] += 1
        log_update(f"ERROR: {str(e)}")
        print(f"[UPDATE CHECK] Error checking for updates: {e}")
        return False

def apply_update():
    """Apply available update"""
    global update_status
    
    if update_status["is_updating"]:
        msg = "Update already in progress"
        log_update(f"WARNING: {msg}")
        print(f"[UPDATE] {msg}")
        return False
    
    if not update_status["update_available"]:
        msg = "No update available"
        log_update(f"WARNING: {msg}")
        print(f"[UPDATE] {msg}")
        return False
    
    try:
        update_status["is_updating"] = True
        log_update("Starting update...")
        print("[UPDATE] Starting update...")
        
        # Pull latest changes
        pull_output, pull_code, pull_err = run_command("git pull origin main")
        if pull_code != 0:
            update_status["is_updating"] = False
            error_msg = f"Git pull failed: {pull_err}"
            update_status["last_check_error"] = error_msg
            log_update(f"ERROR: {error_msg}")
            print(f"[UPDATE] {error_msg}")
            return False
        
        log_update("Changes pulled successfully")
        log_update("Update applied. Restart recommended.")
        print("[UPDATE] Changes pulled successfully")
        print("[UPDATE] Update applied. Restart recommended.")
        update_status["update_available"] = False
        update_status["is_updating"] = False
        return True
        
    except Exception as e:
        update_status["is_updating"] = False
        error_msg = str(e)
        update_status["last_check_error"] = error_msg
        log_update(f"ERROR: {error_msg}")
        print(f"[UPDATE] Error applying update: {e}")
        return False

def updateCheckLoop():
    """Background thread to check for updates periodically"""
    check_interval = 10 
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    while True:
        try:
            check_updates()
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            print(f"[UPDATE CHECK] Unhandled error (attempt {consecutive_failures}/{max_consecutive_failures}): {e}")
            
            if consecutive_failures >= max_consecutive_failures:
                print("[UPDATE CHECK] Too many failures, pausing checks for 1 hour")
                time.sleep(3600)
                consecutive_failures = 0
                continue
        
        time.sleep(check_interval)

update_thread = threading.Thread(target=updateCheckLoop, daemon=True)
update_thread.start()

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
        "disk_percent": -100,
        "cpu": cpu,
        "has_battery": True if psutil.sensors_battery() is not None else False,
        "battery_percent": psutil.sensors_battery().percent if psutil.sensors_battery() else None,
        "battery_is_charging": psutil.sensors_battery().power_plugged if psutil.sensors_battery() else None
    }
    return flask.jsonify(returnList)

@app.route('/config/lines', methods=['GET'])
def get_log_lines():
    log_lines = config.get('logLines', 10000)
    return flask.jsonify({"logLines": log_lines})

@app.route('/system/updates/check', methods=['GET'])
def api_check_updates():
    """Check for updates"""
    check_updates()
    return flask.jsonify(update_status)

@app.route('/system/updates/status', methods=['GET'])
def api_update_status():
    """Get current update status"""
    return flask.jsonify(update_status)

@app.route('/system/updates/apply', methods=['POST'])
def api_apply_update():
    """Apply available update"""
    if not update_status["update_available"]:
        return flask.jsonify({"error": "No update available"}), 400
    
    success = apply_update()
    return flask.jsonify({
        "success": success,
        "message": update_status.get("last_check_error") or "Update applied successfully"
    })

try:
    if __name__ == "__main__":
        app.run('0.0.0.0', 80)
except KeyboardInterrupt as e:
    save_config()