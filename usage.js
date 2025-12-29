let cpuChart, ramChart, diskChart, batteryChart;
// shared map of disk safeId -> Chart instance (may be created by initDisks.js)
let diskCharts = window.diskCharts = window.diskCharts || {};

// format sizes: show MB, or GB when >= 1024 MB
function formatSize(mb) {
    if (typeof mb !== 'number') mb = Number(mb) || 0;
    if (mb >= 1024) {
        return (mb / 1024).toFixed(2) + ' GB';
    }
    return mb + ' MB';
}

function setAllZero() {
    cpuChart.data.datasets[0].data = [0, 100];
    cpuChart.update();
    ramChart.data.datasets[0].data = [0, 100];
    ramChart.update();
    diskChart.data.datasets[0].data = [0, 100];
    diskChart.update();
    if (batteryChart) {
        batteryChart.data.datasets[0].data = [0, 100];
        batteryChart.update();
    }
    document.getElementById('cpu').innerHTML = `0%`;
    document.getElementById('ram').innerHTML = `0%`;
    document.getElementById('ramUsage').innerHTML = `0 MB / 0 MB`;
    document.getElementById('disk').innerHTML = `0%`;
    document.getElementById('diskUsage').innerHTML = `0 MB / 0 MB`;
    const batteryEl = document.getElementById('battery');
    if (batteryEl) batteryEl.innerHTML = `0%`;
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
                    backgroundColor: ['#4ade80', '#374151'],
                borderColor: 'rgb(28, 28, 28)',
                borderWidth: 2
            }]
        },
        options: chartOptions
    });
    // Battery Chart
    const batteryCtx = document.getElementById('batteryChart').getContext('2d');
    batteryChart = new Chart(batteryCtx, {
        type: 'doughnut',
        data: {
            labels: ['Charged', 'Uncharged'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#00ff55ff', '#374151'],
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

            // Update Disk (global)
            const diskPercent = data.disk_percent;
            const diskUsed = data.disk_used;
            const diskTotal = data.disk_total;
            document.getElementById('diskUsage').innerHTML = `${formatSize(diskUsed)} / ${formatSize(diskTotal)}`;
            document.getElementById('disk').innerHTML = `${diskPercent}%`;
            diskChart.data.datasets[0].data = [diskPercent, 100 - diskPercent];
            diskChart.update();

            // Update Battery
            const batteryPercent = data.battery_percent;
            const batteryIsCharging = data.battery_is_charging;
            const batteryCard = document.getElementById('batteryChart')?.parentElement;
            if (batteryPercent !== null && batteryPercent !== undefined) {
                if (batteryCard) batteryCard.style.display = 'block';
                const chargingBadge = batteryIsCharging ? '<span style="display: inline-block; background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px; font-weight: 500;">Charging</span>' : '';
                document.getElementById('battery').innerHTML = `${batteryPercent.toFixed(1)}%${chargingBadge}`;
                batteryChart.data.datasets[0].data = [batteryPercent, 100 - batteryPercent];
                batteryChart.update();
            } else {
                if (batteryCard) batteryCard.style.display = 'none';
            }
        })
        .catch(error => setAllZero());
}

// Fetch per-disk usage and update/create disk cards in the disks container
function fetchDisks() {
    const container = document.getElementById('disks-container');
    if (!container) return;

    fetch('/system/usage/disks', { cache: 'no-store' })
        .then(response => response.json())
        .then(data => {
            const disks = data || [];

            // Update only: expect cards (and canvases) to be created by initDisks.js.
            disks.forEach(disk => {
                const safeId = 'disk-' + encodeURIComponent(disk.identifier).replace(/%/g, '');
                const chartId = safeId + '-chart';
                const card = document.getElementById(safeId);
                if (!card) return; // card not created yet

                // update DOM values
                const nameEl = card.querySelector('.disk-name');
                if (nameEl) nameEl.textContent = disk.name;

                // update disconnected badge
                const badgeEl = card.querySelector('.disk-badge');
                if (badgeEl) {
                    if (disk.connected === false) {
                        badgeEl.style.display = 'inline-block';
                    } else {
                        badgeEl.style.display = 'none';
                    }
                }

                const percentEl = card.querySelector('.disk-percent');
                if (percentEl) {
                    percentEl.textContent = disk.percent + '%';
                    percentEl.style.color = disk.color || '#4ade80';
                }
                const usageEl = card.querySelector('.disk-usage');
                if (usageEl) usageEl.textContent = `${formatSize(disk.used)} / ${formatSize(disk.size)}`;
                const idEl = card.querySelector('.disk-identifier');
                if (idEl) idEl.textContent = disk.identifier;

                // update or initialize chart
                let chart = diskCharts[safeId];
                if (!chart) {
                    const canvas = document.getElementById(chartId);
                    if (canvas) {
                        try {
                            const ctx = canvas.getContext('2d');
                            chart = new Chart(ctx, {
                                type: 'doughnut',
                                data: {
                                    labels: ['Used', 'Available'],
                                    datasets: [{
                                        data: [disk.percent, Math.max(0, 100 - disk.percent)],
                                        backgroundColor: [disk.color || '#4ade80', '#374151'],
                                        borderColor: 'rgb(28, 28, 28)',
                                        borderWidth: 2
                                    }]
                                },
                                options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } } }
                            });
                            diskCharts[safeId] = chart;
                        } catch (e) {}
                    }
                } else {
                    chart.data.datasets[0].data = [disk.percent, Math.max(0, 100 - disk.percent)];
                    chart.update();
                }
            });

            // Remove cards for disks that no longer exist
            const existing = Array.from(container.querySelectorAll('.disk-card'));
            existing.forEach(c => {
                const stillExists = disks.some(d => ('disk-' + encodeURIComponent(d.identifier).replace(/%/g, '')) === c.id);
                if (!stillExists) {
                    // destroy chart if present
                    try {
                        const ch = diskCharts[c.id];
                        if (ch && typeof ch.destroy === 'function') ch.destroy();
                    } catch (e) {}
                    delete diskCharts[c.id];
                    c.remove();
                }
            });
        })
        .catch(() => {});
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
    fetchDisks();
    setInterval(fetchUsage, 2000);
    setInterval(fetchDisks, 2000);
});