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
    document.getElementById('logLines').value = lines;
});