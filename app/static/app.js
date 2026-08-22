document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const uploadBtn = document.getElementById('upload-btn');
    const exportBtn = document.getElementById('export-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const activityFeed = document.getElementById('activity-feed');
    const toast = document.getElementById('toast');

    let selectedFiles = [];

    // --- drag and drop handlers ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        const newFiles = Array.from(files);
        selectedFiles = [...selectedFiles, ...newFiles];
        updateFileList();
    }

    function updateFileList() {
        fileList.innerHTML = '';
        if (selectedFiles.length > 0) {
            uploadBtn.disabled = false;
            uploadBtn.classList.remove('disabled');
        } else {
            uploadBtn.disabled = true;
            uploadBtn.classList.add('disabled');
        }

        selectedFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <div class="file-info">
                    <span class="file-icon">${file.type === 'application/pdf' ? '📕' : '🖼️'}</span>
                    <span class="file-name" title="${file.name}">${file.name}</span>
                </div>
                <button class="remove-btn" onclick="removeFile(${index})">✕</button>
            `;
            fileList.appendChild(item);
        });
    }

    window.removeFile = (index) => {
        selectedFiles.splice(index, 1);
        updateFileList();
    };

    // --- toggle option container click logic ---
    const toggleContainer = document.getElementById('toggle-option-container');
    const toggleCheckbox = document.getElementById('allow-duplicates-toggle');

    if (toggleContainer && toggleCheckbox) {
        toggleContainer.addEventListener('click', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.closest('.switch')) return;
            toggleCheckbox.checked = !toggleCheckbox.checked;
            toggleCheckbox.dispatchEvent(new Event('change'));
        });

        toggleCheckbox.addEventListener('change', () => {
            if (toggleCheckbox.checked) {
                toggleContainer.classList.add('active');
            } else {
                toggleContainer.classList.remove('active');
            }
        });
    }

    // --- upload logic ---
    uploadBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        uploadBtn.disabled = true;
        uploadBtn.innerText = 'Uploading...';

        const allowDuplicates = toggleCheckbox ? Boolean(toggleCheckbox.checked) : false;
        console.log('Uploading with allowDuplicates =', allowDuplicates);

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('allow_duplicates', allowDuplicates ? 'true' : 'false');

        try {
            const response = await fetch('/api/v1/upload/', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                showToast(`🚀 ${result.queued} invoices queued for processing!`);
                selectedFiles = [];
                updateFileList();
                // Refresh activity after a delay to show queued status (if DB updated)
                setTimeout(fetchActivity, 1000);
            } else {
                showToast(`❌ Error: ${result.detail || 'Upload failed'}`, 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showToast('❌ Network error during upload', 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.innerText = 'Process Invoices';
        }
    });

    // --- activity feed ---
    async function fetchActivity() {
        try {
            const response = await fetch('/api/v1/recent/');
            const data = await response.json();

            activityFeed.innerHTML = '';
            if (data.length === 0) {
                activityFeed.innerHTML = '<div class="loading-state">No recent activity found.</div>';
                return;
            }

            data.forEach(item => {
                const card = document.createElement('div');
                card.className = 'activity-card';

                const statusClass = getStatusClass(item.verification_status);
                let displayNo = item.invoice_no;
                if (!displayNo || displayNo === 'Processing...') {
                    if (item.verification_status && item.verification_status.toUpperCase().includes('DUPLICATE')) {
                        displayNo = 'DUPLICATE';
                    } else {
                        displayNo = 'Processing...';
                    }
                }
                const displayVendor = item.vendor || item.file_name;
                const displayDate = item.processed_at ? new Date(item.processed_at).toLocaleString() : 'Just now';

                card.innerHTML = `
                    <div class="card-top">
                        <span class="invoice-no">${displayNo}</span>
                        <span class="status-tag ${statusClass}">${item.verification_status}</span>
                    </div>
                    <div class="card-details">
                        <span class="vendor-name">${displayVendor}</span>
                        <span class="time">${displayDate}</span>
                    </div>
                `;
                activityFeed.appendChild(card);
            });
        } catch (error) {
            console.error('Fetch activity error:', error);
            activityFeed.innerHTML = '<div class="loading-state">Error loading activity.</div>';
        }
    }

    function getStatusClass(status) {
        if (!status) return '';
        const s = status.toLowerCase();
        if (s.includes('verified')) return 'status-verified';
        if (s.includes('error') || s.includes('failed')) return 'status-error';
        if (s.includes('duplicate')) return 'status-duplicate';
        return '';
    }

    function showToast(message, type = 'success') {
        toast.innerText = message;
        toast.classList.remove('hidden');
        if (type === 'error') {
            toast.style.borderColor = '#ef4444';
        } else {
            toast.style.borderColor = '#6366f1';
        }

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4000);
    }

    refreshBtn.addEventListener('click', fetchActivity);

    exportBtn.addEventListener('click', async () => {
        try {
            showToast('📊 Generating Excel report...');
            const response = await fetch('/api/v1/export/');

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `invoices_export_${new Date().toISOString().split('T')[0]}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                showToast('✅ Export complete!');
            } else {
                const error = await response.json();
                showToast(`❌ Export failed: ${error.detail || 'Data not found'}`, 'error');
            }
        } catch (error) {
            console.error('Export error:', error);
            showToast('❌ Network error during export', 'error');
        }
    });

    // Init
    fetchActivity();
    // Auto refresh every 10 seconds
    setInterval(fetchActivity, 10000);
});
