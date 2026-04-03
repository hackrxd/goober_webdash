function getName() {
    return fetch('/system/name')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load name (${response.status})`);
            }
            return response.json();
        })
        .then(data => data.name);
}

async function updateName() {
    try {
        const name = await getName();
        document.getElementById('name').value = name;
    } catch (error) {
        console.error(error);
    }
}

function getLogLines() {
    return fetch('/config/lines', { method: 'GET' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load config lines (${response.status})`);
            }
            return response.json();
        });
}
updateName();
getLogLines().then(lines => {
    // `lines` may now be an object with `logLines` and `updateInterval`
    if (lines && typeof lines === 'object') {
        document.getElementById('logLines').value = lines.logLines;
        if (document.getElementById('updateInterval')) {
            document.getElementById('updateInterval').value = lines.updateInterval;
        }
    } else {
        document.getElementById('logLines').value = lines;
    }
}).catch(error => {
    console.error(error);
});
