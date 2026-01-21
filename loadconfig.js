function getName() {
    return fetch('/system/name')
        .then(response => response.json())
        .then(data => data.name);
}

async function updateName() {
    const name = await getName();
    document.getElementById('name').value = name;
}

function getLogLines() {
    return fetch('/config/lines', { method: 'GET' })
        .then(response => response.json())
        .then(data => data.logLines);
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
});