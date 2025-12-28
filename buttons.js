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
    const diskName = prompt("Enter the name of the new disk:");
    const disk = prompt("Enter the disk identifier (e.g., /dev/sda):");
    if (diskName) {
        fetch('/system/disks/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: diskName, disk: disk })
        })
    }
}