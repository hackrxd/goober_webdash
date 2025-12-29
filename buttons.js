function reboot() {
    areyousure = confirm("Are you sure you want to reboot the system?");
    if (areyousure) {
        fetch('/system/reboot', { method: 'POST' })
    }
}

function rename() {
    const newName = prompt("Enter new hostname:");
    if (newName) {
        fetch('/system/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: newName })
        })
    }
}

function pauseButton() {
    pauseUpdates()
}

function addDisk() {
    location.href = '/dashboard/create/disk'
}

function changeLog() {
    const newSize = prompt("Enter maximum number of log lines to keep (e.g., 10000):");
    const sizeInt = parseInt(newSize);
    if (!isNaN(sizeInt) && sizeInt > 0) {
        fetch('/config/edit/log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ logLines: sizeInt })
        }).then(() => {
            alert(`Log size updated to ${sizeInt} lines.`);
        });
    } else {
        alert("Invalid number entered.");
    }
}

function config() {
    location.href = '/config/edit'
}

function downloadLog() {
  location.href = '/log/download';
}

function downloadUpdateLog() {
  location.href = '/update.log';
}

function switchToGraph() {
    window.open('/graphview', '_blank');
}

function update() {
    fetch('/system/updates/check', { method: 'GET' });
    fetch('/system/updates/apply', { method: 'POST' });
}