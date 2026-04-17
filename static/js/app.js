document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const statusDot = document.getElementById('processor-status-dot');
    const statusText = document.getElementById('processor-status-text');
    const statPending = document.getElementById('stat-pending');
    const statDownloaded = document.getElementById('stat-downloaded');
    const statTimer = document.getElementById('stat-timer');
    
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    
    const selectModel = document.getElementById('select-model');
    const inputConf = document.getElementById('input-conf');
    const inputCooldown = document.getElementById('input-cooldown');
    const inputBlur = document.getElementById('input-blur');
    
    const valConf = document.getElementById('val-conf');
    const valCooldown = document.getElementById('val-cooldown');
    const valBlur = document.getElementById('val-blur');

    // Controls
    btnStart.addEventListener('click', async () => {
        await fetch('/api/start', { method: 'POST' });
        updateStatus();
    });

    btnStop.addEventListener('click', async () => {
        await fetch('/api/stop', { method: 'POST' });
        updateStatus();
    });

    // Settings
    const updateSettings = async (payload) => {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    };

    selectModel.addEventListener('change', (e) => {
        updateSettings({ model_name: e.target.value });
    });

    inputConf.addEventListener('input', (e) => {
        valConf.textContent = e.target.value;
    });
    inputConf.addEventListener('change', (e) => {
        updateSettings({ confidence_threshold: parseFloat(e.target.value) });
    });

    inputCooldown.addEventListener('input', (e) => {
        valCooldown.textContent = e.target.value;
    });
    inputCooldown.addEventListener('change', (e) => {
        updateSettings({ cooldown_seconds: parseInt(e.target.value) });
    });

    inputBlur.addEventListener('input', (e) => {
        valBlur.textContent = e.target.value;
    });
    inputBlur.addEventListener('change', (e) => {
        updateSettings({ blur_threshold: parseFloat(e.target.value) });
    });

    // Status Polling
    const updateStatus = async () => {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            if (data.processor_running) {
                statusDot.className = 'dot green';
                statusText.textContent = 'Running';
            } else {
                statusDot.className = 'dot red';
                statusText.textContent = 'Stopped';
            }

            statPending.textContent = data.sentry_stats.pending_count;
            statDownloaded.textContent = data.sentry_stats.downloaded_count;
            
            if (data.sentry_stats.pending_count > 0) {
                statTimer.textContent = `${data.sentry_stats.inactivity_timer}s remaining...`;
            } else {
                statTimer.textContent = 'Idle';
            }

            // Sync model selection if changed externally
            if (selectModel.value !== data.current_model) {
                // Ensure model exists in options, append if not
                let exists = false;
                for (let i = 0; i < selectModel.options.length; i++) {
                    if (selectModel.options[i].value === data.current_model) exists = true;
                }
                if (!exists) {
                    const opt = document.createElement('option');
                    opt.value = data.current_model;
                    opt.textContent = data.current_model;
                    selectModel.appendChild(opt);
                }
                selectModel.value = data.current_model;
            }

        } catch (e) {
            console.error('Failed to fetch status:', e);
            statusDot.className = 'dot red';
            statusText.textContent = 'Disconnected';
        }
    };

    // Load initial settings
    const loadSettings = async () => {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            
            inputConf.value = data.confidence_threshold || 0.6;
            valConf.textContent = inputConf.value;
            
            inputCooldown.value = data.cooldown_seconds || 10;
            valCooldown.textContent = inputCooldown.value;

            inputBlur.value = data.blur_threshold || 10;
            valBlur.textContent = inputBlur.value;

        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    };

    loadSettings();
    updateStatus();
    setInterval(updateStatus, 2000); // Poll every 2 seconds
});
