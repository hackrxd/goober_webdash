import psutil
import flask
import os
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
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('update.log', 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error writing to update.log: {e}")

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.returncode, result.stderr.strip()
    except Exception as e:
        return "", 1, str(e)

def get_gpu_info():
    """Detect GPUs (NVIDIA, AMD, Intel) and return usage info"""
    gpus = []

    # NVIDIA
    try:
        output, code, err = run_command(
            "nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits"
        )
        if code == 0 and output:
            for line in output.splitlines():
                name, mem_total, mem_used, util = [x.strip() for x in line.split(',')]
                gpus.append({
                    "vendor": "NVIDIA",
                    "name": name,
                    "memory_total_mb": int(mem_total),
                    "memory_used_mb": int(mem_used),
                    "utilization_percent": int(util)
                })
    except Exception:
        pass

    # AMD (rocm-smi)
    try:
        output, code, err = run_command(
            "rocm-smi --showuse --csv"
        )
        if code == 0 and output:
            for line in output.splitlines()[1:]:
                parts = line.split(',')
                if len(parts) >= 3:
                    gpus.append({
                        "vendor": "AMD",
                        "name": parts[0].strip(),
                        "memory_total_mb": int(parts[1].strip()),
                        "memory_used_mb": int(parts[2].strip()),
                        "utilization_percent": int(parts[2].strip())  # rough approximation
                    })
    except Exception:
        pass

    # Intel (intel_gpu_top)
    try:
        output, code, err = run_command("intel_gpu_top -J -s 1")  # JSON output with 1-second sample
        if code == 0 and output:
            data = json.loads(output)
            for idx, gpu in enumerate(data.get("devices", [])):
                gpus.append({
                    "vendor": "Intel",
                    "name": gpu.get("name", f"Intel GPU {idx}"),
                    "memory_total_mb": gpu.get("mem_total", 0),
                    "memory_used_mb": gpu.get("mem_used", 0),
                    "utilization_percent": gpu.get("engines", {}).get("Render/3D", 0)
                })
    except Exception:
        pass

    return gpus

# ----------------------- Update functions (unchanged) -----------------------
def check_updates():
    global update_status
    try:
        update_status["check_count"] += 1
        git_check, code, _ = run_command("git --version")
        if code != 0:
            update_status["last_check_error"] = "Git not installed or not in PATH"
            update_status["failed_checks"] += 1
            log_update("ERROR: Git not installed or not in PATH")
            return False

        fetch_output, fetch_code, fetch_err = run_command("git fetch origin main")
        if fetch_code != 0:
            fetch_err_lower = (fetch_err or "").lower()
            if "dubious ownership" in fetch_err_lower:
                suggested_cmd = f"git config --global --add safe.directory {os.getcwd()}"
                cfg_out, cfg_code, cfg_err = run_command(suggested_cmd)
                if cfg_code == 0:
                    fetch_output, fetch_code, fetch_err = run_command("git fetch origin main")
                    if fetch_code != 0:
                        update_status["last_check_error"] = f"Git fetch failed after adding safe.directory: {fetch_err or 'unknown error'}"
                        update_status["failed_checks"] += 1
                        return False
                else:
                    update_status["last_check_error"] = f"Git fetch failed: {fetch_err or 'unknown error'}. To fix, run: {suggested_cmd}"
                    update_status["failed_checks"] += 1
                    return False
            else:
                update_status["last_check_error"] = f"Git fetch failed: {fetch_err or 'unknown error'}"
                update_status["failed_checks"] += 1
                return False

        local_output, local_code, _ = run_command("git rev-parse HEAD")
        remote_output, remote_code, _ = run_command("git rev-parse origin/main")
        if local_code != 0 or remote_code != 0:
            update_status["last_check_error"] = "Could not get commit hashes"
            update_status["failed_checks"] += 1
            return False

        local_commit = local_output[:7]
        remote_commit = remote_output[:7]
        update_status.update({
            "local_commit": local_commit,
            "remote_commit": remote_commit,
            "last_check": datetime.now().isoformat(),
            "last_check_error": None
        })
        if local_output != remote_output:
            update_status["update_available"] = True
            log_update(f"Update available: {local_commit} -> {remote_commit}")
            return True
        else:
            update_status["update_available"] = False
            return False

    except Exception as e:
        update_status["last_check_error"] = str(e)
        update_status["failed_checks"] += 1
        log_update(f"ERROR: {str(e)}")
        return False

def apply_update():
    global update_status
    if update_status["is_updating"]:
        return False
    if not update_status["update_available"]:
        return False
    try:
        update_status["is_updating"] = True
        pull_output, pull_code, pull_err = run_command("git pull origin main")
        if pull_code != 0:
            update_status["last_check_error"] = f"Git pull failed: {pull_err}"
            update_status["is_updating"] = False
            return False
        update_status["update_available"] = False
        update_status["is_updating"] = False
        return True
    except Exception as e:
        update_status["last_check_error"] = str(e)
        update_status["is_updating"] = False
        return False

# ----------------------- Threads -----------------------
def updateCheckLoop():
    while True:
        try:
            check_updates()
        except Exception as e:
            print(f"[UPDATE CHECK] Error: {e}")
        time.sleep(10)

update_thread = threading.Thread(target=updateCheckLoop, daemon=True)
update_thread.start()

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def background_logger():
    while True:
        try:
            max_lines = config.get('logLines', 10000)
            ram = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery() if psutil.sensors_battery() else None
            gpus = get_gpu_info()  # GPU info

            ramused = ram.used // (1024**2)
            ramtotal = ram.total // (1024**2)
            disktotal = disk.total // (1024**2)
            diskused = disk.used // (1024**2)

            now = datetime.now()
            timestamp = now.isoformat()

            # Append to text log
            with open('usage.log', 'a') as f:
                battery_str = f", Battery: {battery.percent}%" if battery else ""
                gpu_str = f", GPUs: {len(gpus)} detected" if gpus else ""
                f.write(f"[{now}] CPU: {cpu}%, RAM: {ramused}/{ramtotal} MB ({ram.percent}%), Disk: {diskused}/{disktotal} MB ({disk.percent}%){battery_str}{gpu_str}\n")

            # Trim log lines
            if max_lines != 0:
                with open('usage.log', 'r') as f:
                    lines = f.readlines()
                if len(lines) > max_lines:
                    lines = lines[-max_lines:]
                with open('usage.log', 'w') as f:
                    f.writelines(lines)

            # JSON log
            json_data = {
                "timestamp": timestamp,
                "cpu": round(cpu, 2),
                "ram_used": ramused,
                "ram_total": ramtotal,
                "ram_percent": round(ram.percent, 2),
                "disk_used": diskused,
                "disk_total": disktotal,
                "disk_percent": round(disk.percent, 2),
                "battery_percent": round(battery.percent, 2) if battery else None,
                "gpus": gpus
            }
            graph_data = []
            if os.path.exists('usage.json'):
                try:
                    with open('usage.json', 'r') as f:
                        graph_data = json.load(f)
                except:
                    graph_data = []
            graph_data.append(json_data)
            if len(graph_data) > max_lines:
                graph_data = graph_data[-max_lines:]
            with open('usage.json', 'w') as f:
                json.dump(graph_data, f, indent=2)

            time.sleep(5)
        except Exception as e:
            print(f"Error in background logger: {e}")
            time.sleep(5)

logger_thread = threading.Thread(target=background_logger, daemon=True)
logger_thread.start()

# ----------------------- Flask routes -----------------------
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

@app.route('/system/usage', methods=["GET"])
def log_usage_api():
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    disk = psutil.disk_usage('/')
    battery = psutil.sensors_battery() if psutil.sensors_battery() else None
    gpus = get_gpu_info()

    ramused = ram.used // (1024**2)
    ramtotal = ram.total // (1024**2)
    disktotal = disk.total // (1024**2)
    diskused = disk.used // (1024**2)

    return flask.jsonify({
        "ram_used": ramused,
        "ram_total": ramtotal,
        "ram_percent": ram.percent,
        "disk_used": diskused,
        "disk_total": disktotal,
        "disk_percent": disk.percent,
        "cpu": cpu,
        "has_battery": battery is not None,
        "battery_percent": battery.percent if battery else None,
        "battery_is_charging": battery.power_plugged if battery else None,
        "gpus": gpus
    })

@app.route('/graph/data', methods=["GET"])
def get_graph_data():
    try:
        with open('usage.json', 'r') as f:
            data = json.load(f)
        return flask.jsonify(data)
    except:
        return flask.jsonify([])

@app.route('/graphview', methods=["GET"])
def graphview():
    return flask.send_file('graphview.html')

@app.route('/log/download', methods=["GET"])
def download_log():
    return flask.send_file('usage.log', as_attachment=True)

# ----------------------- Remaining routes unchanged -----------------------
@app.route('/system/disks/add', methods=['POST'])
def add_disk():
    data = flask.request.get_json()
    disk_name = data.get('name', 'Unnamed Disk')
    color = data.get('color', '#4ade80')
    disk_identifier = data.get('disk')
    if not disk_identifier:
        return flask.jsonify({"error": "missing disk identifier"}), 400
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

# System updates routes
@app.route('/system/updates/check', methods=['GET'])
def api_check_updates():
    check_updates()
    return flask.jsonify(update_status)

@app.route('/system/updates/status', methods=['GET'])
def api_update_status():
    return flask.jsonify(update_status)

@app.route('/system/updates/apply', methods=['POST'])
def api_apply_update():
    if not update_status["update_available"]:
        return flask.jsonify({"error": "No update available"}), 400
    success = apply_update()
    return flask.jsonify({
        "success": success,
        "message": update_status.get("last_check_error") or "Update applied successfully"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
