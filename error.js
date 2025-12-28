let connectionChecker; // Variable to hold our main interval
let timeRemaining = 0;

function reconnect() {
    // 1. Stop the main checker so we don't trigger multiple reconnections
    clearInterval(connectionChecker);
    
    timeRemaining = 3;
    const errorEl = document.getElementById('error');
    
    // Update UI immediately
    errorEl.textContent = `Connection lost. Reconnecting in ${timeRemaining} seconds...`;
    errorEl.style.display = 'block';

    const countdown = setInterval(() => {
        timeRemaining -= 1;
        
        if (timeRemaining > 0) {
            errorEl.textContent = `Connection lost. Reconnecting in ${timeRemaining} seconds...`;
        } else {
            clearInterval(countdown);
            errorEl.textContent = 'Reconnecting...';
            checkConnection(); 
        }
    }, 1000);
}

function checkConnection() {
    fetch('/system/usage', { cache: 'no-store' })
        .then(response => {
            if (!response.ok) {
                reconnect();
            } else {
                document.getElementById('error').style.display = 'none';
                document.getElementById('error').textContent = '';
                // 2. Restart the main interval only after a successful check
                startChecking();
            }
        })
        .catch(() => {
            reconnect();
        });
}

function startChecking() {
    // Clear any existing interval to prevent duplicates
    clearInterval(connectionChecker);
    connectionChecker = setInterval(checkConnection, 3000);
}

// Start the process
startChecking();