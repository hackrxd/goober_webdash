function reboot() {
    fetch('/system/reboot', { method: 'POST' })
}