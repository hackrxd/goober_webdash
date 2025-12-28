// make new cards for returned disks
function initDisks() {
    // ensure shared chart map exists
    window.diskCharts = window.diskCharts || {};

    fetch('/system/usage/disks', { cache: 'no-store' })
        .then(response => response.json())
        .then(data => {
            const disksContainer = document.getElementById('disks-container');
            if (!disksContainer) return; // No place to show disks
            disksContainer.innerHTML = ''; // Clear existing disks

            (data || []).forEach(disk => {
                const safeId = 'disk-' + encodeURIComponent(disk.identifier).replace(/%/g, '');
                const chartId = safeId + '-chart';

                // Create a full <section class="card"> per disk so they match other cards
                const card = document.createElement('section');
                card.className = 'card disk-card';
                card.id = safeId;
                card.setAttribute('aria-labelledby', `${safeId}-title`);
                card.innerHTML = `
                    <h2 id="${safeId}-title" class="disk-name">${disk.name}</h2>
                    <div class="chart-container" style="width:120px;height:120px;margin:8px 0;">
                        <canvas id="${chartId}"></canvas>
                    </div>
                    <p class="metric-value disk-percent" style="color: ${disk.color || '#4ade80'}">${disk.percent}%</p>
                    <p class="metric-value disk-usage">${formatSize ? formatSize(disk.used) : disk.used + ' MB'} / ${formatSize ? formatSize(disk.size) : disk.size + ' MB'}</p>
                    <p class="disk-identifier" style="color: #9ca3af; font-size: 12px; margin-top: 6px;">${disk.identifier}</p>
                `;

                disksContainer.appendChild(card);

                // initialize chart for this disk (if Chart.js is available)
                try {
                    if (typeof Chart !== 'undefined') {
                        const ctx = document.getElementById(chartId).getContext('2d');
                        window.diskCharts[safeId] = new Chart(ctx, {
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
                    }
                } catch (e) {
                    // ignore
                }
            });
        })
        .catch(error => {
            console.error('Error fetching disks:', error);
        });
}

// run once on load to create cards; usage.js will update them
initDisks();