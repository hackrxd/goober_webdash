let nameElement = document.getElementById('name')
function loadName() {
fetch('/system/name')
    .then(response => response.json())
    .then(data => {
        nameElement.innerText = data.name;
    });
}

loadName();
setInterval(loadName, 5000); // Refresh every 5 seconds