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
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;width:100%;margin-bottom:8px;" class="disk-heading">
                        <h2 id="${safeId}-title" class="disk-name">${disk.name}</h2>
                        <span class="disk-badge" style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;display:${!disk.connected ? 'inline-block' : 'none'};">Disconnected</span>
                    </div>
                    <div class="chart-container" style="width:120px;height:120px;margin:8px 0;">
                        <canvas id="${chartId}"></canvas>
                    </div>
                    <p class="metric-value disk-percent" style="color: ${disk.color || '#4ade80'}">${disk.percent}%</p>
                    <p class="metric-value disk-usage">${formatSize ? formatSize(disk.used) : disk.used + ' MB'} / ${formatSize ? formatSize(disk.size) : disk.size + ' MB'}</p>
                    <p class="disk-identifier" style="color: #9ca3af; font-size: 12px; margin-top: 6px;">${disk.identifier}</p>
                    <button class="delete-disk-button" data-disk="${encodeURIComponent(disk.identifier)}">Remove Disk</button>
                `;

                disksContainer.appendChild(card);

                // attach delete handler programmatically (safer than inline onclick)
                try {
                    const delBtn = card.querySelector('.delete-disk-button');
                    if (delBtn) {
                        delBtn.addEventListener('click', function () {
                            const decoded = decodeURIComponent(this.getAttribute('data-disk'));
                            if (!confirm('Are you sure you want to delete this disk?')) return;
                            fetch('/system/disks/remove', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ disk: decoded })
                            }).then(resp => {
                                if (resp.status === 204 || resp.status === 200) {
                                    // reload page to refresh and show updated state
                                    setTimeout(() => window.location.reload(), 500);
                                } else {
                                    console.error('Failed to remove disk', resp.status);
                                }
                            }).catch(err => console.error('Error removing disk', err));
                        });
                    }
                } catch (e) {}

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