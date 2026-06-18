// State Variables
let allData = [];
let filteredData = [];
let sortColumn = 'date_time';
let sortDirection = 'desc'; // 'asc' or 'desc'
let currentPage = 1;
const pageSize = 15;
let activeFilters = {
    date_time: '',
    part_number: '',
    serial: '',
    status: '',
    cumulative_tests: ''
};
let globalSearchQuery = '';
let diagnosticSearchQuery = '';
let dateFromValue = '';
let dateToValue = '';
let selectedRun = null;

// DOM Elements
const selectDirBtn = document.getElementById('select-dir-btn');
const parentDirInput = document.getElementById('parent-dir-input');
const parserSelect = document.getElementById('parser-select');
const scanBtn = document.getElementById('scan-btn');
const exportBtn = document.getElementById('export-btn');
const failureViewBtn = document.getElementById('failure-view-btn');
const logsTbody = document.getElementById('logs-tbody');

// KPIs
const kpiTotalVal = document.querySelector('#kpi-total .value');
const kpiPassVal = document.querySelector('#kpi-pass .value');
const kpiPassSub = document.querySelector('#kpi-pass .subtext');
const kpiFailVal = document.querySelector('#kpi-fail .value');
const kpiFailSub = document.querySelector('#kpi-fail .subtext');
const kpiUniqueVal = document.querySelector('#kpi-unique .value');

// Search & Pagination Elements
const globalSearchInput = document.getElementById('global-search');
const diagnosticSearchInput = document.getElementById('diagnostic-search');
const filterDiagnosticCheck = document.getElementById('filter-diagnostic-check');
const filterNeverPassedCheck = document.getElementById('filter-never-passed-check');
const dateFromInput = document.getElementById('date-from');
const dateToInput = document.getElementById('date-to');
const clearFiltersBtn = document.getElementById('clear-filters-btn');
const prevPageBtn = document.getElementById('prev-page-btn');
const nextPageBtn = document.getElementById('next-page-btn');
const pageNumSpan = document.getElementById('page-num');
const pageStartSpan = document.getElementById('page-start');
const pageEndSpan = document.getElementById('page-end');
const totalRowsSpan = document.getElementById('total-rows');

// Modal Elements
const detailsModal = document.getElementById('details-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const modalSerialVal = document.getElementById('modal-serial-val');
const metaCustomer = document.getElementById('meta-customer');
const metaPartL1 = document.getElementById('meta-part-l1');
const metaDatetime = document.getElementById('meta-datetime');
const metaStatus = document.getElementById('meta-status');
const stepsTbody = document.getElementById('steps-tbody');
const modalStepSearch = document.getElementById('modal-step-search');
const modalSearchBox = document.querySelector('.modal-search-box');
const modalFailOnlyCheck = document.getElementById('modal-fail-only-check');

// Barcode Elements
const barcodeToggleBtn = document.getElementById('barcode-toggle-btn');
const stepsView = document.getElementById('steps-view');
const barcodeView = document.getElementById('barcode-view');
const barcodeLoading = document.getElementById('barcode-loading');
const barcodeContent = document.getElementById('barcode-content');
const barcodeTextBlock = document.getElementById('barcode-text-block');
const barcodeQrImg = document.getElementById('barcode-qr-img');
const barcodeError = document.getElementById('barcode-error');
let barcodeMode = false;

// Wait for pywebview api to be loaded
window.addEventListener('pywebviewready', async () => {
    console.log('PyWebview API is ready');
    try {
        const lastParser = await window.pywebview.api.get_last_parser();
        if (lastParser) {
            parserSelect.value = lastParser;
        }
    } catch (err) {
        console.error('Error loading last parser:', err);
    }
    try {
        const lastDir = await window.pywebview.api.get_last_directory();
        if (lastDir) {
            parentDirInput.value = lastDir;
            scanBtn.removeAttribute('disabled');
        }
    } catch (err) {
        console.error('Error loading last directory:', err);
    }
});

// Event Listeners
selectDirBtn.addEventListener('click', async () => {
    try {
        const path = await window.pywebview.api.select_directory();
        if (path) {
            parentDirInput.value = path;
            scanBtn.removeAttribute('disabled');
        }
    } catch (err) {
        console.error('Error selecting directory:', err);
    }
});

parserSelect.addEventListener('change', async () => {
    try {
        await window.pywebview.api.set_active_parser(parserSelect.value);
        resetData();
    } catch (err) {
        console.error('Error setting active parser:', err);
    }
});

function resetData() {
    allData = [];
    filteredData = [];
    currentPage = 1;
    
    // Clear filters UI
    globalSearchInput.value = '';
    globalSearchQuery = '';
    diagnosticSearchInput.value = '';
    diagnosticSearchQuery = '';
    filterDiagnosticCheck.checked = false;
    filterNeverPassedCheck.checked = false;
    dateFromInput.value = '';
    dateToInput.value = '';
    dateFromValue = '';
    dateToValue = '';
    
    document.querySelectorAll('.column-filter').forEach(input => {
        input.value = '';
    });
    
    for (let col in activeFilters) {
        activeFilters[col] = '';
    }
    
    updatePartNumberDropdown([]);
    updateKPIs();
    applyFiltersAndRender();
    
    exportBtn.setAttribute('disabled', 'true');
    failureViewBtn.setAttribute('disabled', 'true');
}

scanBtn.addEventListener('click', async () => {
    const path = parentDirInput.value;
    if (!path) return;

    scanBtn.setAttribute('disabled', 'true');
    scanBtn.textContent = 'Scanning...';
    logsTbody.innerHTML = `<tr><td colspan="6" class="empty-state">Scanning directory tree... please wait.</td></tr>`;

    try {
        const results = await window.pywebview.api.scan_directory(path);
        allData = results || [];
        updatePartNumberDropdown(allData);
        filteredData = [...allData];
        currentPage = 1;
        
        updateKPIs();
        applyFiltersAndRender();
        
        if (allData.length > 0) {
            exportBtn.removeAttribute('disabled');
            failureViewBtn.removeAttribute('disabled');
        } else {
            exportBtn.setAttribute('disabled', 'true');
            failureViewBtn.setAttribute('disabled', 'true');
        }
    } catch (err) {
        console.error('Error scanning directory:', err);
        logsTbody.innerHTML = `<tr><td colspan="6" class="empty-state" style="color:var(--color-fail)">Scan failed: ${err.message || err}</td></tr>`;
    } finally {
        scanBtn.removeAttribute('disabled');
        scanBtn.textContent = 'Scan Directory';
    }
});

exportBtn.addEventListener('click', async () => {
    if (filteredData.length === 0) return;
    try {
        // Strip steps data to keep export fast, Python just needs key fields of current view
        const exportList = filteredData.map(d => ({
            date_time: d.date_time,
            part_number: d.part_number,
            serial: d.serial,
            status: d.status,
            cumulative_tests: d.cumulative_tests,
            customer: d.customer,
            part_num_3rd: d.part_num_3rd
        }));
        const filePath = await window.pywebview.api.export_csv(exportList);
        if (filePath) {
            alert(`Successfully exported data to:\n${filePath}`);
        }
    } catch (err) {
        console.error('Error exporting CSV:', err);
        alert(`Export failed: ${err.message || err}`);
    }
});

// Global Search
globalSearchInput.addEventListener('input', (e) => {
    globalSearchQuery = e.target.value.toLowerCase().trim();
    currentPage = 1;
    applyFiltersAndRender();
});

// Diagnostic Search
diagnosticSearchInput.addEventListener('input', (e) => {
    diagnosticSearchQuery = e.target.value.toLowerCase().trim();
    applyFiltersAndRender(); // Only highlights, doesn't filter out rows
});

// Column Filters
document.querySelectorAll('.column-filter').forEach(input => {
    const eventType = input.tagName === 'SELECT' ? 'change' : 'input';
    input.addEventListener(eventType, (e) => {
        const th = e.target.closest('th');
        const column = th.dataset.column;
        activeFilters[column] = e.target.value.toLowerCase().trim();
        currentPage = 1;
        applyFiltersAndRender();
    });
});

// Clear Filters Button
clearFiltersBtn.addEventListener('click', () => {
    globalSearchInput.value = '';
    globalSearchQuery = '';
    diagnosticSearchInput.value = '';
    diagnosticSearchQuery = '';
    filterDiagnosticCheck.checked = false;
    filterNeverPassedCheck.checked = false;
    dateFromInput.value = '';
    dateToInput.value = '';
    dateFromValue = '';
    dateToValue = '';
    
    document.querySelectorAll('.column-filter').forEach(input => {
        input.value = '';
    });
    
    activeFilters = {
        date_time: '',
        part_number: '',
        serial: '',
        status: '',
        cumulative_tests: ''
    };
    
    currentPage = 1;
    applyFiltersAndRender();
});

// Date Range listeners
dateFromInput.addEventListener('change', (e) => {
    dateFromValue = e.target.value; // "YYYY-MM-DDTHH:MM"
    currentPage = 1;
    applyFiltersAndRender();
});

dateToInput.addEventListener('change', (e) => {
    dateToValue = e.target.value;
    currentPage = 1;
    applyFiltersAndRender();
});

// Diagnostic Filter toggle listener
filterDiagnosticCheck.addEventListener('change', () => {
    currentPage = 1;
    applyFiltersAndRender();
});

// Never Passed Only toggle listener
filterNeverPassedCheck.addEventListener('change', () => {
    currentPage = 1;
    applyFiltersAndRender();
});

// Column Sorting (restricted to logs-table headers with data-column)
document.querySelectorAll('#logs-table th[data-column]').forEach(th => {
    th.addEventListener('click', () => {
        const column = th.dataset.column;
        if (sortColumn === column) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortColumn = column;
            sortDirection = 'asc';
        }
        updateSortIcons();
        applyFiltersAndRender();
    });
});

// Pagination Navigation
prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        renderTable();
    }
});

nextPageBtn.addEventListener('click', () => {
    const totalPages = Math.ceil(filteredData.length / pageSize);
    if (currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
});

// Modal Actions
closeModalBtn.addEventListener('click', () => {
    detailsModal.classList.remove('active');
    selectedRun = null;
});

detailsModal.addEventListener('click', (e) => {
    if (e.target === detailsModal) {
        detailsModal.classList.remove('active');
        selectedRun = null;
    }
});

modalStepSearch.addEventListener('input', (e) => {
    if (selectedRun) {
        renderModalSteps(e.target.value.toLowerCase().trim());
    }
});

modalFailOnlyCheck.addEventListener('change', () => {
    if (selectedRun) {
        renderModalSteps(modalStepSearch.value.toLowerCase().trim());
    }
});

// Barcode Toggle
barcodeToggleBtn.addEventListener('click', async () => {
    barcodeMode = !barcodeMode;
    if (barcodeMode) {
        // Switch to barcode view
        barcodeToggleBtn.textContent = '\u2190 Back to Steps';
        barcodeToggleBtn.classList.add('active');
        stepsView.style.display = 'none';
        modalSearchBox.style.display = 'none';
        barcodeView.style.display = 'flex';
        barcodeLoading.style.display = 'block';
        barcodeContent.style.display = 'none';
        barcodeError.style.display = 'none';

        try {
            const result = await window.pywebview.api.generate_barcode(
                selectedRun.path,
                selectedRun.is_zip,
                selectedRun.serial,
                selectedRun.date_time
            );
            if (result.error) {
                barcodeLoading.style.display = 'none';
                barcodeError.textContent = result.error;
                barcodeError.style.display = 'block';
            } else {
                barcodeTextBlock.textContent = result.text;
                barcodeQrImg.src = 'data:image/png;base64,' + result.qr_base64;
                barcodeLoading.style.display = 'none';
                barcodeContent.style.display = 'flex';
            }
        } catch (err) {
            barcodeLoading.style.display = 'none';
            barcodeError.textContent = 'Error generating barcode: ' + (err.message || err);
            barcodeError.style.display = 'block';
        }
    } else {
        // Switch back to steps view
        barcodeToggleBtn.textContent = '\u25A6 Barcode';
        barcodeToggleBtn.classList.remove('active');
        stepsView.style.display = '';
        modalSearchBox.style.display = '';
        barcodeView.style.display = 'none';
    }
});

// Business Logic Functions
function updatePartNumberDropdown(data) {
    const partSelect = document.getElementById('part-number-filter');
    if (!partSelect) return;

    // Get current selection value so we can try to preserve it
    const currentSelection = partSelect.value;

    // Clear existing options except the first one ("All Parts")
    partSelect.innerHTML = '<option value="">All Parts</option>';

    // Get unique part numbers
    const parts = new Set();
    data.forEach(item => {
        if (item.part_number) {
            parts.add(item.part_number.trim());
        }
    });

    // Sort alphabetically
    const sortedParts = Array.from(parts).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base', numeric: true }));

    // Populate dropdown
    sortedParts.forEach(part => {
        const option = document.createElement('option');
        option.value = part;
        option.textContent = part;
        partSelect.appendChild(option);
    });

    // Restore selection if it still exists
    if (currentSelection && sortedParts.includes(currentSelection)) {
        partSelect.value = currentSelection;
    } else {
        partSelect.value = '';
        activeFilters['part_number'] = '';
    }
}

function updateKPIs() {
    const total = filteredData.length;
    kpiTotalVal.textContent = total;

    const passes = filteredData.filter(d => d.status === 'PASS').length;
    const fails = filteredData.filter(d => d.status === 'FAIL').length;
    const uniqueSerials = new Set(filteredData.map(d => d.serial)).size;

    kpiPassVal.textContent = passes;
    const passRate = total > 0 ? Math.round((passes / total) * 100) : 0;
    kpiPassSub.textContent = `${passRate}% Success Rate`;

    kpiFailVal.textContent = fails;
    const failRate = total > 0 ? Math.round((fails / total) * 100) : 0;
    kpiFailSub.textContent = `${failRate}% Failure Rate`;

    kpiUniqueVal.textContent = uniqueSerials;
}

function applyFiltersAndRender() {
    filteredData = allData.filter(item => {
        // 1. Global Search
        const fieldsToSearch = [
            item.date_time,
            item.part_number,
            item.serial,
            item.status,
            item.customer,
            item.part_num_3rd,
            String(item.cumulative_tests)
        ].map(f => (f || '').toLowerCase());
        
        const matchesGlobal = globalSearchQuery === '' || fieldsToSearch.some(f => f.includes(globalSearchQuery));
        if (!matchesGlobal) return false;

        // 2. Column Filters
        for (const col in activeFilters) {
            const filterVal = activeFilters[col];
            if (filterVal !== '') {
                const itemVal = String(item[col] || '').toLowerCase();
                if (!itemVal.includes(filterVal)) {
                    return false;
                }
            }
        }

        // 3. Date Range Filter
        if (dateFromValue || dateToValue) {
            // item.date_time is "YYYY-MM-DD HH:MM" - convert to datetime-local compatible string
            const itemDt = item.date_time ? item.date_time.replace(' ', 'T') : '';
            if (dateFromValue && itemDt < dateFromValue) return false;
            if (dateToValue && itemDt > dateToValue) return false;
        }

        // 4. Optional Diagnostic Filter (only if checkbox is checked)
        if (diagnosticSearchQuery !== '' && filterDiagnosticCheck.checked) {
            const hasFailedStepMatching = item.steps && item.steps.some(step => {
                return step.type === 'step' && 
                       step.result === 'FAIL' && 
                       step.name.toLowerCase().includes(diagnosticSearchQuery);
            });
            if (!hasFailedStepMatching) return false;
        }

        return true;
    });

    // 5. Never Passed Only — two-pass: find serials with ≥1 PASS among candidates, then exclude
    if (filterNeverPassedCheck.checked) {
        const passedSerials = new Set(
            filteredData.filter(r => r.status === 'PASS').map(r => r.serial)
        );
        filteredData = filteredData.filter(r => !passedSerials.has(r.serial));
    }

    // Update KPIs based on dynamic filtered data
    updateKPIs();

    // Sort
    sortData();
    renderTable();
}

function sortData() {
    filteredData.sort((a, b) => {
        let valA = a[sortColumn];
        let valB = b[sortColumn];

        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

function updateSortIcons() {
    document.querySelectorAll('#logs-table th[data-column]').forEach(th => {
        const column = th.dataset.column;
        const icon = th.querySelector('.sort-icon');
        if (icon) {
            if (column === sortColumn) {
                icon.textContent = sortDirection === 'asc' ? '▲' : '▼';
            } else {
                icon.textContent = '';
            }
        }
    });
}

function renderTable() {
    logsTbody.innerHTML = '';
    
    const total = filteredData.length;
    totalRowsSpan.textContent = total;

    if (total === 0) {
        logsTbody.innerHTML = `<tr><td colspan="6" class="empty-state">No matching test runs found.</td></tr>`;
        pageStartSpan.textContent = '0';
        pageEndSpan.textContent = '0';
        prevPageBtn.setAttribute('disabled', 'true');
        nextPageBtn.setAttribute('disabled', 'true');
        pageNumSpan.textContent = '1';
        return;
    }

    const totalPages = Math.ceil(total / pageSize);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    pageNumSpan.textContent = currentPage;

    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, total);

    pageStartSpan.textContent = startIdx + 1;
    pageEndSpan.textContent = endIdx;

    // Toggle pagination button states
    if (currentPage === 1) {
        prevPageBtn.setAttribute('disabled', 'true');
    } else {
        prevPageBtn.removeAttribute('disabled');
    }

    if (currentPage === totalPages) {
        nextPageBtn.setAttribute('disabled', 'true');
    } else {
        nextPageBtn.removeAttribute('disabled');
    }

    const pageSlice = filteredData.slice(startIdx, endIdx);

    pageSlice.forEach(item => {
        const tr = document.createElement('tr');
        
        // Add Pass/Fail row styling
        if (item.status === 'PASS') {
            tr.classList.add('row-pass');
        } else {
            tr.classList.add('row-fail');
        }

        // Check diagnostic highlighting
        if (diagnosticSearchQuery !== '') {
            const hasFailedStepMatching = item.steps && item.steps.some(step => {
                return step.type === 'step' && 
                       step.result === 'FAIL' && 
                       step.name.toLowerCase().includes(diagnosticSearchQuery);
            });
            if (hasFailedStepMatching) {
                tr.classList.add('diagnostic-match');
            }
        }

        tr.innerHTML = `
            <td>${item.date_time}</td>
            <td>${item.part_number}</td>
            <td>${item.serial}</td>
            <td><span class="badge ${item.status.toLowerCase()}">${item.status}</span></td>
            <td style="text-align: center; font-weight: 500;">${item.cumulative_tests}</td>
            <td style="text-align: center;">
                <div class="actions-wrapper">
                    <button class="btn-icon-only btn-explorer" title="Open in File Explorer">&#x1F4C1;</button>
                    <button class="btn-icon-only btn-qr" title="Generate QR Barcode">&#x1F4F7;</button>
                </div>
            </td>
        `;

        // Programmatically bind open explorer click handler
        const explorerBtn = tr.querySelector('.btn-explorer');
        if (explorerBtn) {
            explorerBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                openExplorer(item.path);
            });
            explorerBtn.addEventListener('dblclick', (e) => {
                e.stopPropagation();
            });
        }

        // Bind QR barcode button
        const qrBtn = tr.querySelector('.btn-qr');
        if (qrBtn) {
            qrBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                showDetailsInBarcodeMode(item);
            });
            qrBtn.addEventListener('dblclick', (e) => {
                e.stopPropagation();
            });
        }

        // Double click to open details modal
        tr.addEventListener('dblclick', () => showDetails(item));
        logsTbody.appendChild(tr);
    });
}

async function showDetails(item) {
    selectedRun = item;
    modalSerialVal.textContent = item.serial;
    metaCustomer.textContent = item.customer || 'Unknown';
    metaPartL1.textContent = item.part_number || 'Unknown';
    metaDatetime.textContent = item.date_time;
    
    metaStatus.textContent = item.status;
    metaStatus.className = `meta-value badge ${item.status.toLowerCase()}`;

    // Always reset to steps view when opening a new run
    barcodeMode = false;
    barcodeToggleBtn.textContent = '\u25A6 Barcode';
    barcodeToggleBtn.classList.remove('active');
    stepsView.style.display = '';
    modalSearchBox.style.display = '';
    barcodeView.style.display = 'none';
    // Reset barcode content state
    barcodeLoading.style.display = 'block';
    barcodeContent.style.display = 'none';
    barcodeError.style.display = 'none';
    barcodeQrImg.src = '';
    barcodeTextBlock.textContent = '';

    modalStepSearch.value = '';
    modalFailOnlyCheck.checked = false;

    // If steps are empty or missing, fetch them dynamically
    if (!item.steps || item.steps.length === 0) {
        stepsTbody.innerHTML = `<tr><td colspan="6" class="empty-state">Loading steps data...</td></tr>`;
        try {
            const steps = await window.pywebview.api.get_run_steps(item.path);
            item.steps = steps || [];
        } catch (err) {
            console.error('Error loading run steps:', err);
            item.steps = [];
        }
    }

    renderModalSteps('');

    detailsModal.classList.add('active');
}

// Opens the modal and immediately switches to barcode view
async function showDetailsInBarcodeMode(item) {
    await showDetails(item); // sets up modal, resets to steps view, loads steps
    // Trigger barcode toggle programmatically after a short tick
    // so the modal is rendered before we fire the async QR generation
    setTimeout(() => barcodeToggleBtn.click(), 50);
}

function renderModalSteps(query = '') {
    stepsTbody.innerHTML = '';
    if (!selectedRun || !selectedRun.steps || selectedRun.steps.length === 0) {
        stepsTbody.innerHTML = `<tr><td colspan="6" class="empty-state">No steps data available.</td></tr>`;
        return;
    }

    const showFailedOnly = modalFailOnlyCheck.checked;

    // Filter matching items, keeping track of sections and their steps
    const filteredItems = [];
    let currentSection = null;

    selectedRun.steps.forEach(item => {
        if (item.type === 'section') {
            currentSection = item;
        } else {
            const matchesQuery = query === '' || item.name.toLowerCase().includes(query);
            const matchesFailOnly = !showFailedOnly || item.result === 'FAIL';

            if (matchesQuery && matchesFailOnly) {
                if (currentSection) {
                    filteredItems.push({ ...currentSection, type: 'section' });
                    currentSection = null; // Mark as pushed so we don't repeat it
                }
                filteredItems.push(item);
            }
        }
    });

    filteredItems.forEach(step => {
        if (step.type === 'section') {
            const tr = document.createElement('tr');
            tr.classList.add('step-row-section');
            tr.innerHTML = `<td colspan="6">${step.name}</td>`;
            stepsTbody.appendChild(tr);
        } else {
            const tr = document.createElement('tr');
            const rowClass = step.result === 'PASS' ? 'step-row-pass' : 'step-row-fail';
            tr.classList.add(rowClass);
            
            tr.innerHTML = `
                <td>${step.name}</td>
                <td>${step.low_limit}</td>
                <td>${step.high_limit}</td>
                <td>${step.expected}</td>
                <td>${step.measured}</td>
                <td><span class="badge ${step.result.toLowerCase()}">${step.result}</span></td>
            `;
            stepsTbody.appendChild(tr);
        }
    });

    if (stepsTbody.children.length === 0) {
        stepsTbody.innerHTML = `<tr><td colspan="6" class="empty-state">No matching steps found.</td></tr>`;
    }
}

// Explorer API Wrapper
async function openExplorer(path) {
    try {
        if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.open_explorer(path);
        }
    } catch (err) {
        console.error('Error calling open_explorer API:', err);
    }
}

// Custom Right-Click Context Menu Logic
const contextMenu = document.getElementById('custom-context-menu');
const ctxCopy = document.getElementById('ctx-copy');
const ctxFilter = document.getElementById('ctx-filter');
let activeRightClickCell = null;

// Intercept right click on table cells
document.querySelector('#logs-table tbody').addEventListener('contextmenu', (e) => {
    const td = e.target.closest('td');
    if (!td) return;
    
    // Skip the actions column cell (last cell of the row)
    const rowCells = td.parentNode.children;
    if (td.cellIndex === rowCells.length - 1) return;

    e.preventDefault();
    activeRightClickCell = td;
    
    contextMenu.style.display = 'block';
    contextMenu.style.left = `${e.pageX}px`;
    contextMenu.style.top = `${e.pageY}px`;
});

// Hide context menu on any left click
document.addEventListener('click', () => {
    contextMenu.style.display = 'none';
});

// Copy Value Option
ctxCopy.addEventListener('click', () => {
    if (activeRightClickCell) {
        const text = activeRightClickCell.textContent.trim();
        navigator.clipboard.writeText(text).then(() => {
            console.log('Value copied to clipboard:', text);
        }).catch(err => {
            console.error('Clipboard copy failed:', err);
        });
    }
});

// Filter by Selection Option
ctxFilter.addEventListener('click', () => {
    if (activeRightClickCell) {
        const text = activeRightClickCell.textContent.trim();
        // Find corresponding th element by cell index
        const thElements = Array.from(document.querySelectorAll('#logs-table th'));
        const th = thElements[activeRightClickCell.cellIndex];
        if (th && th.dataset.column) {
            const column = th.dataset.column;
            // Set input value
            const filterInput = th.querySelector('.column-filter');
            if (filterInput) {
                if (filterInput.tagName === 'SELECT') {
                    // Find option case-insensitively
                    const option = Array.from(filterInput.options).find(opt => opt.value.toLowerCase() === text.toLowerCase());
                    if (option) {
                        filterInput.value = option.value;
                    } else {
                        filterInput.value = '';
                    }
                } else {
                    filterInput.value = text;
                }
            }
            // Update active filters and render
            activeFilters[column] = text.toLowerCase();
            currentPage = 1;
            applyFiltersAndRender();
        }
    }
});

// ─────────────────────────────────────────────
// Failure Data View
// ─────────────────────────────────────────────

const mainContent = document.querySelector('.main-content');
const failureView = document.getElementById('failure-view');
const backToMainBtn = document.getElementById('back-to-main-btn');
const failureDateFrom = document.getElementById('failure-date-from');
const failureDateTo = document.getElementById('failure-date-to');
const failureClearDates = document.getElementById('failure-clear-dates-btn');
const failurePartsContainer = document.getElementById('failure-parts-container');

let failureDateFromValue = '';
let failureDateToValue = '';

function showView(view) {
    if (view === 'failure') {
        mainContent.style.display = 'none';
        failureView.style.display = 'flex';
        failureViewBtn.classList.add('active-view');
        renderFailureView();
    } else {
        mainContent.style.display = '';
        failureView.style.display = 'none';
        failureViewBtn.classList.remove('active-view');
    }
}

failureViewBtn.addEventListener('click', () => showView('failure'));
backToMainBtn.addEventListener('click', () => showView('main'));

failureDateFrom.addEventListener('change', (e) => {
    failureDateFromValue = e.target.value;
    renderFailureView();
});
failureDateTo.addEventListener('change', (e) => {
    failureDateToValue = e.target.value;
    renderFailureView();
});
failureClearDates.addEventListener('click', () => {
    failureDateFrom.value = '';
    failureDateTo.value = '';
    failureDateFromValue = '';
    failureDateToValue = '';
    renderFailureView();
});

function renderFailureView() {
    failurePartsContainer.innerHTML = '';

    if (!allData || allData.length === 0) {
        failurePartsContainer.innerHTML = '<div class="empty-state" style="padding:60px;">Scan a directory first, then switch to Failure Data view.</div>';
        return;
    }

    // Apply date range filter
    const visibleRuns = allData.filter(item => {
        if (failureDateFromValue || failureDateToValue) {
            const itemDt = item.date_time ? item.date_time.replace(' ', 'T') : '';
            if (failureDateFromValue && itemDt < failureDateFromValue) return false;
            if (failureDateToValue && itemDt > failureDateToValue) return false;
        }
        return true;
    });

    if (visibleRuns.length === 0) {
        failurePartsContainer.innerHTML = '<div class="empty-state" style="padding:60px;">No runs match the selected date range.</div>';
        return;
    }

    // Group by Part Number (L1)
    const partMap = {};
    visibleRuns.forEach(run => {
        const pn = run.part_number || 'Unknown';
        if (!partMap[pn]) {
            partMap[pn] = { runs: [], failRuns: 0, stepFailCounts: {} };
        }
        partMap[pn].runs.push(run);
        if (run.status === 'FAIL') {
            partMap[pn].failRuns++;
            // Tally failing steps
            if (run.steps) {
                run.steps.forEach(step => {
                    if (step.type === 'step' && step.result === 'FAIL') {
                        const name = step.name.trim();
                        partMap[pn].stepFailCounts[name] = (partMap[pn].stepFailCounts[name] || 0) + 1;
                    }
                });
            }
        }
    });

    // Sort part numbers alphabetically
    const sortedParts = Object.keys(partMap).sort();

    sortedParts.forEach(partName => {
        const data = partMap[partName];
        const totalRuns = data.runs.length;
        const failRuns = data.failRuns;
        const failRate = totalRuns > 0 ? ((failRuns / totalRuns) * 100).toFixed(1) : '0.0';

        // Sort steps by count desc
        const sortedSteps = Object.entries(data.stepFailCounts)
            .sort((a, b) => b[1] - a[1]);

        const card = document.createElement('div');
        card.className = 'failure-part-card';

        // Build steps table rows
        let rowsHtml = '';
        if (sortedSteps.length === 0) {
            rowsHtml = `<tr><td colspan="4" class="no-failures-msg">No individual step failures recorded for this part number.</td></tr>`;
        } else {
            sortedSteps.forEach(([stepName, count], idx) => {
                const pct = failRuns > 0 ? ((count / failRuns) * 100).toFixed(1) : '0.0';
                const pctNum = parseFloat(pct);
                rowsHtml += `
                    <tr>
                        <td class="failure-rank">${idx + 1}</td>
                        <td>${stepName}</td>
                        <td class="failure-count-cell">${count}</td>
                        <td class="failure-pct-cell">
                            <div class="failure-pct-bar-wrap">
                                <div class="failure-pct-bar-bg">
                                    <div class="failure-pct-bar-fill" style="width:${pctNum}%"></div>
                                </div>
                                <span class="failure-pct-label">${pct}%</span>
                            </div>
                        </td>
                    </tr>`;
            });
        }

        card.innerHTML = `
            <div class="failure-part-card-header">
                <span class="failure-part-name">${partName}</span>
                <div class="failure-part-stats">
                    <div class="failure-stat">
                        <span class="failure-stat-label">Total Runs</span>
                        <span class="failure-stat-value">${totalRuns}</span>
                    </div>
                    <div class="failure-stat">
                        <span class="failure-stat-label">Failed Runs</span>
                        <span class="failure-stat-value">${failRuns}</span>
                    </div>
                    <div class="failure-stat">
                        <span class="failure-stat-label">Failure Rate</span>
                        <span class="failure-stat-value rate-value">${failRate}%</span>
                    </div>
                </div>
            </div>
            <div class="failure-steps-table-wrap">
                <table class="failure-steps-table">
                    <thead>
                        <tr>
                            <th style="width:48px;">#</th>
                            <th>Failing Step Name</th>
                            <th style="width:80px;">Count</th>
                            <th style="width:220px;">% of Failed Runs</th>
                        </tr>
                    </thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            </div>`;

        failurePartsContainer.appendChild(card);
    });
}
