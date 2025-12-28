let cpuChart, ramChart, diskChart;

function setAllZero() {
    cpuChart.data.datasets[0].data = [0, 100];
    cpuChart.update();
    ramChart.data.datasets[0].data = [0, 100];
    ramChart.update();
    diskChart.data.datasets[0].data = [0, 100];
    diskChart.update();
    document.getElementById('cpu').innerHTML = `0%`;
    document.getElementById('ram').innerHTML = `0%`;
    document.getElementById('ramUsage').innerHTML = `0 MB / 0 MB`;
    document.getElementById('disk').innerHTML = `0%`;
    document.getElementById('diskUsage').innerHTML = `0 MB / 0 MB`;
}

function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: '#ffffff',
                    font: {
                        family: "'Montserrat', sans-serif",
                        size: 12
                    }
                }
            }
        }
    };
    
    // CPU Chart
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'doughnut',
        data: {
            labels: ['Used', 'Available'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#ef4444', '#374151'],
                borderColor: 'rgb(28, 28, 28)',
                borderWidth: 2
            }]
        },
        options: chartOptions
    });

    // RAM Chart
    const ramCtx = document.getElementById('ramChart').getContext('2d');
    ramChart = new Chart(ramCtx, {
        type: 'doughnut',
        data: {
            labels: ['Used', 'Available'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#3b82f6', '#374151'],
                borderColor: 'rgb(28, 28, 28)',
                borderWidth: 2
            }]
        },
        options: chartOptions
    });

    // Disk Chart
    const diskCtx = document.getElementById('diskChart').getContext('2d');
    diskChart = new Chart(diskCtx, {
        type: 'doughnut',
        data: {
            labels: ['Used', 'Available'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#f59e0b', '#374151'],
                borderColor: 'rgb(28, 28, 28)',
                borderWidth: 2
            }]
        },
        options: chartOptions
    });
}

function fetchUsage() {
    if (paused) {
        return;
    }
    fetch('/system/usage')
        .then(response => response.json())
        .then(data => {
            // Update CPU
            const cpuPercent = data.cpu.toFixed(1);
            document.getElementById('cpu').innerHTML = `${cpuPercent}%`;
            cpuChart.data.datasets[0].data = [cpuPercent, 100 - cpuPercent];
            cpuChart.update();

            // Update RAM
            const ramPercent = data.ram_percent.toFixed(1);
            const ramUsed = data.ram_used;
            const ramTotal = data.ram_total;
            document.getElementById('ramUsage').innerHTML = `${ramUsed} MB / ${ramTotal} MB`;
            document.getElementById('ram').innerHTML = `${ramPercent}%`;
            ramChart.data.datasets[0].data = [ramPercent, 100 - ramPercent];
            ramChart.update();

            // Update Disk
            const diskPercent = data.disk_percent;
            const diskUsed = data.disk_used;
            const diskTotal = data.disk_total;
            if (diskUsed < 1024) {
                document.getElementById('diskUsage').innerHTML = `${diskUsed} MB / ${diskTotal} MB`;
            }
            else {
                const diskUsedGB = (diskUsed / 1024).toFixed(2);
                const diskTotalGB = (diskTotal / 1024).toFixed(2);
                document.getElementById('diskUsage').innerHTML = `${diskUsedGB} GB / ${diskTotalGB} GB`;
            }
            document.getElementById('disk').innerHTML = `${diskPercent}%`;
            diskChart.data.datasets[0].data = [diskPercent, 100 - diskPercent];
            diskChart.update();
        })
        .catch(error => setAllZero());
}
let paused = false;

function pauseUpdates() {
    paused = !paused;
    const pauseButton = document.getElementsByClassName('pauseButton')[0];
    if (paused) {
        pauseButton.textContent = "Resume";
        pauseButton.style.backgroundColor = "#10b981";
    } else {
        pauseButton.textContent = "Pause";
        pauseButton.style.backgroundColor = "#f1a10cff";
    }
}

// Initialize charts when page loads
window.addEventListener('DOMContentLoaded', function() {
    initCharts();
    fetchUsage();
    setInterval(fetchUsage, 2000);
});