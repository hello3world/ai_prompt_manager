/* ===== State ===== */
var prompts = [];
var groups = [];
var features = [];
var selectedPromptId = null;
var editingPromptId = null;
var collapsedGroups = JSON.parse(localStorage.getItem('collapsedGroups') || '{}');
var importStrategy = 'skip';

/* ===== Utility ===== */
function esc(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function $(id) { return document.getElementById(id); }

/* ===== Theme ===== */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    document.querySelectorAll('.theme-btn').forEach(function(b) {
        b.classList.toggle('active', b.dataset.setTheme === theme);
    });
}

/* ===== Model Selector ===== */
function onModelChange() {
    var model = $('modelSelector').value;
    localStorage.setItem('selectedModel', model);
    var zone = $('imageUploadZone');
    if (model === 'qwen-vl-max') {
        zone.classList.add('visible');
    } else {
        zone.classList.remove('visible');
        removeImage();
    }
}

function restoreModel() {
    var saved = localStorage.getItem('selectedModel') || 'qwen-max';
    $('modelSelector').value = saved;
    onModelChange();
}

/* ===== Image Handling ===== */
function onImageSelected() {
    var input = $('imageInput');
    var file = input.files[0];
    if (!file) { hideImagePreview(); return; }
    var reader = new FileReader();
    reader.onload = function(e) {
        $('imagePreviewImg').src = e.target.result;
        $('imagePreviewName').textContent = file.name;
        $('imagePreview').classList.add('visible');
    };
    reader.readAsDataURL(file);
}

function removeImage() {
    $('imageInput').value = '';
    hideImagePreview();
}

function hideImagePreview() {
    $('imagePreview').classList.remove('visible');
    $('imagePreviewImg').src = '';
    $('imagePreviewName').textContent = '';
}

/* ===== Data Loading ===== */
async function loadGroups() {
    try {
        var res = await fetch('/api/groups');
        groups = await res.json();
    } catch(e) { groups = []; }
}

async function loadFeatures() {
    try {
        var res = await fetch('/api/features');
        features = await res.json();
    } catch(e) { features = []; }
}

async function loadPrompts() {
    try {
        var res = await fetch('/api/prompts');
        prompts = await res.json();
    } catch (e) {
        prompts = [];
    }
    renderSidebar();
    if (prompts.length > 0 && !prompts.find(function(p) { return p.id === selectedPromptId; })) {
        selectPrompt(prompts[0].id);
    }
    if (prompts.length === 0) {
        selectedPromptId = null;
        $('selectedPromptName').textContent = 'none selected';
    }
}

async function loadAll() {
    await loadGroups();
    await loadFeatures();
    await loadPrompts();
}

/* ===== Sidebar Render (with groups) ===== */
function renderSidebar() {
    var list = $('sidebarList');
    var searchTerm = ($('promptSearch') ? $('promptSearch').value : '').toLowerCase();
    var filtered = searchTerm
        ? prompts.filter(function(p) { return p.name.toLowerCase().includes(searchTerm) || p.description.toLowerCase().includes(searchTerm); })
        : prompts;

    $('promptCount').textContent = prompts.length;

    if (filtered.length === 0) {
        list.innerHTML = searchTerm
            ? '<div class="no-prompt-warning">No prompts match the filter.</div>'
            : '<div class="no-prompt-warning">No prompts yet. Click "Manage Prompts" to create one.</div>';
        return;
    }

    var grouped = {};
    var ungrouped = [];
    for (var i = 0; i < filtered.length; i++) {
        var p = filtered[i];
        if (p.group_id) {
            if (!grouped[p.group_id]) grouped[p.group_id] = [];
            grouped[p.group_id].push(p);
        } else {
            ungrouped.push(p);
        }
    }

    var html = '';
    for (var gi = 0; gi < groups.length; gi++) {
        var g = groups[gi];
        var gPrompts = grouped[g.id] || [];
        if (gPrompts.length === 0 && searchTerm) continue;
        var isCollapsed = collapsedGroups[g.id];
        html += '<div class="group-header" data-group-id="' + g.id + '">' +
                    '<div class="group-header-left">' +
                        '<span class="arrow ' + (isCollapsed ? 'collapsed' : '') + '">&#9660;</span>' +
                        esc(g.name) +
                    '</div>' +
                    '<span class="group-count">' + gPrompts.length + '</span>' +
                '</div>' +
                '<div class="group-prompts ' + (isCollapsed ? 'collapsed' : '') + '">' +
                    gPrompts.map(renderPromptCard).join('') +
                '</div>';
    }

    if (ungrouped.length > 0) {
        var uc = collapsedGroups[0];
        html += '<div class="group-header" data-group-id="0">' +
                    '<div class="group-header-left">' +
                        '<span class="arrow ' + (uc ? 'collapsed' : '') + '">&#9660;</span>' +
                        'Ungrouped' +
                    '</div>' +
                    '<span class="group-count">' + ungrouped.length + '</span>' +
                '</div>' +
                '<div class="group-prompts ' + (uc ? 'collapsed' : '') + '">' +
                    ungrouped.map(renderPromptCard).join('') +
                '</div>';
    }

    list.innerHTML = html;
}

function renderPromptCard(p) {
    var feat = p.feature_id ? features.find(function(f) { return f.id === p.feature_id; }) : null;
    return '<div class="prompt-card ' + (p.id === selectedPromptId ? 'selected' : '') + '" data-prompt-id="' + p.id + '">' +
                '<div class="prompt-card-name">' + esc(p.name) + '</div>' +
                '<div class="prompt-card-desc">' + esc(p.description) + '</div>' +
                (feat ? '<div class="prompt-card-feature">Feature: ' + esc(feat.name) + '</div>' : '') +
           '</div>';
}

function toggleGroup(groupId) {
    collapsedGroups[groupId] = !collapsedGroups[groupId];
    localStorage.setItem('collapsedGroups', JSON.stringify(collapsedGroups));
    renderSidebar();
}

function selectPrompt(id) {
    selectedPromptId = id;
    var p = prompts.find(function(x) { return x.id === id; });
    $('selectedPromptName').textContent = p ? p.name : 'none selected';
    renderSidebar();
}

function editPromptDblClick(id) {
    openManager();
    setTimeout(function() { editPrompt(id); }, 100);
}

/* ===== Generate ===== */
async function generate() {
    var query = $('queryInput').value.trim();
    if (!query) { alert('Please enter a query.'); return; }
    if (!selectedPromptId) { alert('Please select a prompt template first.'); return; }

    var btn = $('generateBtn');
    var loading = $('loading');
    var outputSection = $('outputSection');
    var outputContent = $('outputContent');

    btn.disabled = true;
    loading.classList.add('visible');
    outputSection.classList.remove('visible');

    var model = $('modelSelector').value;
    var imageFile = $('imageInput').files[0];

    try {
        var res;
        if (model === 'qwen-vl-max' && imageFile) {
            var formData = new FormData();
            formData.append('prompt_id', selectedPromptId);
            formData.append('query', query);
            formData.append('file', imageFile);
            res = await fetch('/generate-vision', { method: 'POST', body: formData });
        } else {
            res = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt_id: selectedPromptId, query: query }),
            });
        }
        var data = await res.json();

        if (data.success) {
            outputContent.dataset.rawMarkdown = data.report;
            outputContent.innerHTML = marked.parse(data.report);
            outputContent.classList.remove('error');
            localStorage.setItem('lastResponse', data.report);
        } else {
            outputContent.dataset.rawMarkdown = '';
            outputContent.innerHTML = '<div class="error">Error: ' + esc(data.error) + '</div>';
            localStorage.removeItem('lastResponse');
        }
        outputSection.classList.add('visible');
    } catch (e) {
        outputContent.innerHTML = '<div class="error">Connection error: ' + esc(e.message) + '</div>';
        outputSection.classList.add('visible');
    } finally {
        btn.disabled = false;
        loading.classList.remove('visible');
    }
}

/* ===== Rich Copy ===== */
async function copyToClipboard() {
    var outputContent = $('outputContent');
    var btn = $('copyBtn');
    var btnText = btn.querySelector('span');
    var rawMarkdown = outputContent.dataset.rawMarkdown || outputContent.textContent;
    var renderedHtml = outputContent.innerHTML;

    try {
        var htmlBlob = new Blob([renderedHtml], { type: 'text/html' });
        var textBlob = new Blob([rawMarkdown], { type: 'text/plain' });
        await navigator.clipboard.write([
            new ClipboardItem({ 'text/html': htmlBlob, 'text/plain': textBlob })
        ]);
    } catch (e) {
        await navigator.clipboard.writeText(rawMarkdown);
    }

    btn.classList.add('copied');
    btn.querySelector('svg').innerHTML = '<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>';
    btnText.textContent = 'Copied!';
    setTimeout(function() {
        btn.classList.remove('copied');
        btn.querySelector('svg').innerHTML = '<path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>';
        btnText.textContent = 'Copy';
    }, 2000);
}

/* ===== Prompt Manager Modal ===== */
function openManager() {
    $('modalOverlay').classList.add('visible');
    hideForm();
    renderModalList();
}

function closeManager() {
    $('modalOverlay').classList.remove('visible');
}

async function renderModalList() {
    try {
        var res = await fetch('/api/prompts');
        prompts = await res.json();
    } catch(e) {}
    await loadGroups();
    await loadFeatures();
    renderSidebar();

    var list = $('modalPromptList');
    if (prompts.length === 0) {
        list.innerHTML = '<div class="no-prompt-warning">No prompts yet.</div>';
        return;
    }

    var groupOpts = groups.map(function(g) { return '<option value="' + g.id + '">' + esc(g.name) + '</option>'; }).join('');

    list.innerHTML = prompts.map(function(p) {
        var gName = (groups.find(function(g) { return g.id === p.group_id; }) || {}).name || 'Ungrouped';
        return '<div class="modal-prompt-item">' +
                    '<div class="modal-prompt-item-info">' +
                        '<div class="modal-prompt-item-name">' + esc(p.name) + '</div>' +
                        '<div class="modal-prompt-item-group">Group: ' + esc(gName) +
                            '&nbsp; | Move to: ' +
                            '<select class="move-select" data-prompt-id="' + p.id + '">' +
                                '<option value="">--</option>' + groupOpts +
                            '</select>' +
                        '</div>' +
                    '</div>' +
                    '<div class="modal-prompt-item-actions">' +
                        '<button class="modal-action-btn" data-action="edit-prompt" data-id="' + p.id + '">Edit</button>' +
                        '<button class="modal-action-btn delete" data-action="delete-prompt" data-id="' + p.id + '">Delete</button>' +
                    '</div>' +
                '</div>';
    }).join('');
}

async function movePrompt(promptId, groupId) {
    if (!groupId) return;
    try {
        await fetch('/api/prompts/' + promptId + '/move', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ group_id: parseInt(groupId) }),
        });
    } catch(e) {}
    await renderModalList();
}

function showForm(id) {
    editingPromptId = id || null;
    $('modalListView').style.display = 'none';
    $('modalFormView').classList.add('visible');
    $('modalTitle').textContent = editingPromptId ? 'Edit Prompt' : 'New Prompt';

    var groupSel = $('formGroup');
    groupSel.innerHTML = groups.map(function(g) {
        return '<option value="' + g.id + '">' + esc(g.name) + '</option>';
    }).join('');

    var featSel = $('formFeature');
    featSel.innerHTML = '<option value="">-- None --</option>' +
        features.map(function(f) { return '<option value="' + f.id + '">' + esc(f.name) + '</option>'; }).join('');

    $('formName').value = '';
    $('formDesc').value = '';
    $('formTemplate').value = '';
}

function hideForm() {
    editingPromptId = null;
    $('modalFormView').classList.remove('visible');
    $('modalListView').style.display = '';
    $('modalTitle').textContent = 'Manage Prompts';
}

async function editPrompt(id) {
    showForm(id);
    try {
        var res = await fetch('/api/prompts/' + id);
        var p = await res.json();
        $('formName').value = p.name;
        $('formDesc').value = p.description;
        $('formTemplate').value = p.template_text;
        if (p.group_id) $('formGroup').value = p.group_id;
        if (p.feature_id) $('formFeature').value = p.feature_id;
    } catch(e) {
        alert('Failed to load prompt.');
        hideForm();
    }
}

async function savePrompt() {
    var name = $('formName').value.trim();
    var description = $('formDesc').value.trim();
    var template_text = $('formTemplate').value;
    var group_id = parseInt($('formGroup').value) || null;
    var feature_id = parseInt($('formFeature').value) || null;

    if (!name || !description || !template_text) {
        alert('All fields are required.');
        return;
    }

    if (template_text.indexOf('{QUERY}') === -1) {
        if (!confirm('Warning: template does not contain {QUERY} placeholder. The user query will not be inserted. Continue?')) {
            return;
        }
    }

    var body = JSON.stringify({ name: name, description: description, template_text: template_text, group_id: group_id, feature_id: feature_id });
    var headers = { 'Content-Type': 'application/json' };

    try {
        var res;
        if (editingPromptId) {
            res = await fetch('/api/prompts/' + editingPromptId, { method: 'PUT', headers: headers, body: body });
        } else {
            res = await fetch('/api/prompts', { method: 'POST', headers: headers, body: body });
        }
        if (!res.ok) {
            var err = await res.json();
            alert('Error: ' + (err.detail || JSON.stringify(err)));
            return;
        }
    } catch(e) {
        alert('Failed to save: ' + e.message);
        return;
    }

    hideForm();
    await renderModalList();
}

async function deletePrompt(id) {
    if (!confirm('Are you sure you want to delete this prompt?')) return;
    try {
        await fetch('/api/prompts/' + id, { method: 'DELETE' });
    } catch(e) {}
    if (selectedPromptId === id) {
        selectedPromptId = null;
        $('selectedPromptName').textContent = 'none selected';
    }
    await renderModalList();
}

/* ===== Reset ===== */
function resetState() {
    $('queryInput').value = '';
    $('outputSection').classList.remove('visible');
    $('outputContent').innerHTML = '';
    $('outputContent').dataset.rawMarkdown = '';
    localStorage.removeItem('lastResponse');
    removeImage();
}

function restoreLastResponse() {
    var saved = localStorage.getItem('lastResponse');
    if (saved) {
        $('outputContent').dataset.rawMarkdown = saved;
        $('outputContent').innerHTML = marked.parse(saved);
        $('outputContent').classList.remove('error');
        $('outputSection').classList.add('visible');
    }
}

/* ===== Export / Import ===== */
function exportPrompts() {
    window.location.href = '/api/prompts/export';
}

function openImportDialog() {
    $('importOverlay').classList.add('visible');
    $('importFileInput').value = '';
    $('importFileArea').classList.remove('has-file');
    $('importFileLabel').textContent = 'Click to select a .json file';
    $('importFileName').textContent = '';
    $('importResults').classList.remove('visible');
    $('importRunBtn').disabled = false;
    $('importRunBtn').textContent = 'Import';
    importStrategy = 'skip';
    document.querySelectorAll('.strategy-option').forEach(function(el) {
        el.classList.toggle('active', el.dataset.strategy === 'skip');
    });
}

function closeImportDialog() {
    $('importOverlay').classList.remove('visible');
}

function onImportFileSelected() {
    var file = $('importFileInput').files[0];
    if (file) {
        $('importFileArea').classList.add('has-file');
        $('importFileLabel').textContent = 'Selected:';
        $('importFileName').textContent = file.name;
    }
}

function selectStrategy(el) {
    importStrategy = el.dataset.strategy;
    document.querySelectorAll('.strategy-option').forEach(function(o) { o.classList.remove('active'); });
    el.classList.add('active');
}

async function performImport() {
    var file = $('importFileInput').files[0];
    if (!file) { alert('Please select a JSON file.'); return; }

    var btn = $('importRunBtn');
    btn.disabled = true;
    btn.textContent = 'Importing...';

    var formData = new FormData();
    formData.append('file', file);

    try {
        var res = await fetch('/api/prompts/import?strategy=' + importStrategy, {
            method: 'POST',
            body: formData,
        });
        if (!res.ok) {
            var err = await res.json();
            alert('Import error: ' + (err.detail || JSON.stringify(err)));
            btn.disabled = false;
            btn.textContent = 'Import';
            return;
        }
        var result = await res.json();
        var resultsDiv = $('importResults');
        resultsDiv.classList.add('visible');
        resultsDiv.innerHTML =
            '<div class="result-row"><span class="result-label">Imported:</span> <span class="result-value">' + result.imported + '</span></div>' +
            '<div class="result-row"><span class="result-label">Skipped:</span> <span class="result-value">' + result.skipped + '</span></div>' +
            '<div class="result-row"><span class="result-label">Updated:</span> <span class="result-value">' + result.updated + '</span></div>' +
            (result.errors.length > 0 ? '<div class="result-row" style="color:var(--error);margin-top:6px">' + esc(result.errors.join(', ')) + '</div>' : '');
        btn.textContent = 'Done';
        await loadAll();
    } catch(e) {
        alert('Import failed: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Import';
    }
}

/* ===== Settings Modal ===== */
function openSettings() {
    $('settingsOverlay').classList.add('visible');
    switchSettingsTab('tokens');
    loadSettingsData();
}

function closeSettings() {
    $('settingsOverlay').classList.remove('visible');
}

function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab').forEach(function(t) { t.classList.toggle('active', t.dataset.tab === tab); });
    $('panelTokens').classList.toggle('visible', tab === 'tokens');
    $('panelGroups').classList.toggle('visible', tab === 'groups');
    $('panelFeatures').classList.toggle('visible', tab === 'features');
}

async function loadSettingsData() {
    await Promise.all([renderTokenList(), renderGroupList(), renderFeatureList()]);
}

/* ===== Token CRUD ===== */
async function renderTokenList() {
    try {
        var res = await fetch('/api/tokens');
        var tokens = await res.json();
        var list = $('tokenList');
        if (tokens.length === 0) {
            list.innerHTML = '<div style="padding:8px;color:var(--text-muted);font-size:0.85rem">No API tokens configured.</div>';
            return;
        }
        list.innerHTML = tokens.map(function(t) {
            return '<div class="settings-item">' +
                '<div class="settings-item-info">' +
                    '<div class="settings-item-name">' + esc(t.name) +
                        '<span class="active-badge ' + (t.is_active ? 'yes' : 'no') + '">' + (t.is_active ? 'Active' : 'Inactive') + '</span>' +
                    '</div>' +
                    '<div class="settings-item-detail">' + esc(t.token_masked) + '</div>' +
                '</div>' +
                '<div class="settings-item-actions">' +
                    (t.is_active
                        ? '<button class="modal-action-btn" data-action="toggle-token" data-id="' + t.id + '" data-activate="false">Deactivate</button>'
                        : '<button class="modal-action-btn" data-action="toggle-token" data-id="' + t.id + '" data-activate="true">Activate</button>'
                    ) +
                    '<button class="modal-action-btn" data-action="edit-token" data-id="' + t.id + '">Edit</button>' +
                    '<button class="modal-action-btn delete" data-action="delete-token" data-id="' + t.id + '">Delete</button>' +
                '</div>' +
            '</div>';
        }).join('');
    } catch(e) {}
}

function showTokenForm(editId) {
    $('tokenFormArea').innerHTML =
        '<div class="inline-form">' +
            '<label>Name</label>' +
            '<input type="text" id="tokenFormName" placeholder="e.g. My Qwen Token" value="Default">' +
            '<label>Token</label>' +
            '<input type="text" id="tokenFormValue" placeholder="sk-...">' +
            '<div class="inline-form-actions">' +
                '<button class="btn" data-action="save-token" data-edit-id="' + (editId || '') + '">' + (editId ? 'Update' : 'Save') + '</button>' +
                '<button class="btn-secondary" data-action="cancel-token">Cancel</button>' +
            '</div>' +
        '</div>';
}

function hideTokenForm() { $('tokenFormArea').innerHTML = ''; }

async function editTokenInline(id) {
    showTokenForm(id);
    try {
        var res = await fetch('/api/tokens/' + id);
        var t = await res.json();
        $('tokenFormName').value = t.name;
        $('tokenFormValue').value = t.token_value;
    } catch(e) {}
}

async function saveToken(editId) {
    var name = $('tokenFormName').value.trim();
    var token_value = $('tokenFormValue').value.trim();
    if (!token_value) { alert('Token value is required.'); return; }

    var body = JSON.stringify({ name: name, token_value: token_value });
    var headers = { 'Content-Type': 'application/json' };

    try {
        if (editId) {
            await fetch('/api/tokens/' + editId, { method: 'PUT', headers: headers, body: body });
        } else {
            await fetch('/api/tokens', { method: 'POST', headers: headers, body: body });
        }
    } catch(e) { alert('Failed: ' + e.message); return; }

    hideTokenForm();
    await renderTokenList();
}

async function toggleToken(id, activate) {
    try {
        await fetch('/api/tokens/' + id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: activate }),
        });
    } catch(e) {}
    await renderTokenList();
}

async function deleteToken(id) {
    if (!confirm('Delete this token?')) return;
    try { await fetch('/api/tokens/' + id, { method: 'DELETE' }); } catch(e) {}
    await renderTokenList();
}

/* ===== Group CRUD ===== */
async function renderGroupList() {
    await loadGroups();
    var list = $('groupList');
    if (groups.length === 0) {
        list.innerHTML = '<div style="padding:8px;color:var(--text-muted);font-size:0.85rem">No groups.</div>';
        return;
    }
    list.innerHTML = groups.map(function(g) {
        return '<div class="settings-item">' +
            '<div class="settings-item-info"><div class="settings-item-name">' + esc(g.name) + '</div></div>' +
            '<div class="settings-item-actions">' +
                '<button class="modal-action-btn" data-action="edit-group" data-id="' + g.id + '">Edit</button>' +
                '<button class="modal-action-btn delete" data-action="delete-group" data-id="' + g.id + '">Delete</button>' +
            '</div>' +
        '</div>';
    }).join('');
}

function showGroupForm(editId) {
    $('groupFormArea').innerHTML =
        '<div class="inline-form">' +
            '<label>Group Name</label>' +
            '<input type="text" id="groupFormName" placeholder="e.g. Regression Tests">' +
            '<div class="inline-form-actions">' +
                '<button class="btn" data-action="save-group" data-edit-id="' + (editId || '') + '">' + (editId ? 'Update' : 'Save') + '</button>' +
                '<button class="btn-secondary" data-action="cancel-group">Cancel</button>' +
            '</div>' +
        '</div>';
}

function hideGroupForm() { $('groupFormArea').innerHTML = ''; }

async function editGroupInline(id) {
    showGroupForm(id);
    try {
        var res = await fetch('/api/groups/' + id);
        var g = await res.json();
        $('groupFormName').value = g.name;
    } catch(e) {}
}

async function saveGroup(editId) {
    var name = $('groupFormName').value.trim();
    if (!name) { alert('Group name is required.'); return; }

    var body = JSON.stringify({ name: name });
    var headers = { 'Content-Type': 'application/json' };

    try {
        if (editId) {
            await fetch('/api/groups/' + editId, { method: 'PUT', headers: headers, body: body });
        } else {
            await fetch('/api/groups', { method: 'POST', headers: headers, body: body });
        }
    } catch(e) { alert('Failed: ' + e.message); return; }

    hideGroupForm();
    await renderGroupList();
    await loadAll();
}

async function deleteGroup(id) {
    if (!confirm('Delete this group? Prompts in this group will become ungrouped.')) return;
    try { await fetch('/api/groups/' + id, { method: 'DELETE' }); } catch(e) {}
    await renderGroupList();
    await loadAll();
}

/* ===== Feature CRUD ===== */
async function renderFeatureList() {
    await loadFeatures();
    var list = $('featureList');
    if (features.length === 0) {
        list.innerHTML = '<div style="padding:8px;color:var(--text-muted);font-size:0.85rem">No feature descriptions.</div>';
        return;
    }
    list.innerHTML = features.map(function(f) {
        return '<div class="settings-item">' +
            '<div class="settings-item-info"><div class="settings-item-name">' + esc(f.name) + '</div></div>' +
            '<div class="settings-item-actions">' +
                '<button class="modal-action-btn" data-action="edit-feature" data-id="' + f.id + '">Edit</button>' +
                '<button class="modal-action-btn delete" data-action="delete-feature" data-id="' + f.id + '">Delete</button>' +
            '</div>' +
        '</div>';
    }).join('');
}

function showFeatureForm(editId) {
    $('featureFormArea').innerHTML =
        '<div class="inline-form">' +
            '<label>Feature Name</label>' +
            '<input type="text" id="featureFormName" placeholder="e.g. Dashboard Module">' +
            '<label>Description</label>' +
            '<textarea id="featureFormText" placeholder="Describe the feature/functionality..."></textarea>' +
            '<div class="inline-form-actions">' +
                '<button class="btn" data-action="save-feature" data-edit-id="' + (editId || '') + '">' + (editId ? 'Update' : 'Save') + '</button>' +
                '<button class="btn-secondary" data-action="cancel-feature">Cancel</button>' +
            '</div>' +
        '</div>';
}

function hideFeatureForm() { $('featureFormArea').innerHTML = ''; }

async function editFeatureInline(id) {
    showFeatureForm(id);
    try {
        var res = await fetch('/api/features/' + id);
        var f = await res.json();
        $('featureFormName').value = f.name;
        $('featureFormText').value = f.description_text;
    } catch(e) {}
}

async function saveFeature(editId) {
    var name = $('featureFormName').value.trim();
    var description_text = $('featureFormText').value.trim();
    if (!name || !description_text) { alert('All fields are required.'); return; }

    var body = JSON.stringify({ name: name, description_text: description_text });
    var headers = { 'Content-Type': 'application/json' };

    try {
        if (editId) {
            await fetch('/api/features/' + editId, { method: 'PUT', headers: headers, body: body });
        } else {
            await fetch('/api/features', { method: 'POST', headers: headers, body: body });
        }
    } catch(e) { alert('Failed: ' + e.message); return; }

    hideFeatureForm();
    await renderFeatureList();
}

async function deleteFeature(id) {
    if (!confirm('Delete this feature description? Linked prompts will be unlinked.')) return;
    try { await fetch('/api/features/' + id, { method: 'DELETE' }); } catch(e) {}
    await renderFeatureList();
    await loadAll();
}


/* ===========================================================
   Event Listeners (replaces all inline onclick/onchange/etc)
   =========================================================== */
document.addEventListener('DOMContentLoaded', function() {

    /* --- Theme buttons (event delegation) --- */
    document.querySelector('.header-controls').addEventListener('click', function(e) {
        var themeBtn = e.target.closest('.theme-btn');
        if (themeBtn) setTheme(themeBtn.dataset.setTheme);
    });

    /* --- Header --- */
    $('modelSelector').addEventListener('change', onModelChange);
    $('settingsBtn').addEventListener('click', openSettings);

    /* --- Sidebar search --- */
    $('promptSearch').addEventListener('input', renderSidebar);

    /* --- Sidebar buttons --- */
    $('sidebarExportBtn').addEventListener('click', exportPrompts);
    $('sidebarImportBtn').addEventListener('click', openImportDialog);
    $('managePromptsBtn').addEventListener('click', openManager);

    /* --- Sidebar list: event delegation for clicks and dblclicks --- */
    $('sidebarList').addEventListener('click', function(e) {
        var groupHeader = e.target.closest('[data-group-id]');
        if (groupHeader && !e.target.closest('[data-prompt-id]')) {
            toggleGroup(parseInt(groupHeader.dataset.groupId));
            return;
        }
        var card = e.target.closest('[data-prompt-id]');
        if (card) {
            selectPrompt(parseInt(card.dataset.promptId));
        }
    });
    $('sidebarList').addEventListener('dblclick', function(e) {
        var card = e.target.closest('[data-prompt-id]');
        if (card) {
            editPromptDblClick(parseInt(card.dataset.promptId));
        }
    });

    /* --- Image handling --- */
    $('imageInput').addEventListener('change', onImageSelected);
    $('imageRemoveBtn').addEventListener('click', removeImage);

    /* --- Main buttons --- */
    $('generateBtn').addEventListener('click', generate);
    $('resetBtn').addEventListener('click', resetState);
    $('copyBtn').addEventListener('click', copyToClipboard);

    /* --- Keyboard shortcut --- */
    $('queryInput').addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') generate();
    });

    /* --- Prompt Manager Modal --- */
    $('promptModalClose').addEventListener('click', closeManager);
    $('addPromptBtn').addEventListener('click', function() { showForm(); });
    $('savePromptBtn').addEventListener('click', savePrompt);
    $('cancelFormBtn').addEventListener('click', hideForm);

    $('modalOverlay').addEventListener('click', function(e) {
        if (e.target === this) closeManager();
    });

    /* --- Modal prompt list: event delegation --- */
    $('modalPromptList').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var action = btn.dataset.action;
        var id = parseInt(btn.dataset.id);
        if (action === 'edit-prompt') editPrompt(id);
        if (action === 'delete-prompt') deletePrompt(id);
    });
    $('modalPromptList').addEventListener('change', function(e) {
        var sel = e.target.closest('.move-select');
        if (sel && sel.value) {
            movePrompt(parseInt(sel.dataset.promptId), sel.value);
        }
    });

    /* --- Import Modal --- */
    $('importFileArea').addEventListener('click', function() {
        $('importFileInput').click();
    });
    $('importFileInput').addEventListener('change', onImportFileSelected);
    $('importModalClose').addEventListener('click', closeImportDialog);
    $('importRunBtn').addEventListener('click', performImport);
    $('importCancelBtn').addEventListener('click', closeImportDialog);

    $('importOverlay').addEventListener('click', function(e) {
        if (e.target === this) closeImportDialog();
    });

    /* --- Strategy options: event delegation --- */
    document.querySelector('.import-strategy-options').addEventListener('click', function(e) {
        var opt = e.target.closest('.strategy-option');
        if (opt) selectStrategy(opt);
    });

    /* --- Settings Modal --- */
    $('settingsCloseBtn').addEventListener('click', closeSettings);
    $('settingsOverlay').addEventListener('click', function(e) {
        if (e.target === this) closeSettings();
    });

    /* --- Settings tabs: event delegation --- */
    document.querySelector('.settings-tabs').addEventListener('click', function(e) {
        var tab = e.target.closest('.settings-tab');
        if (tab) switchSettingsTab(tab.dataset.tab);
    });

    /* --- Settings add buttons --- */
    $('addTokenBtn').addEventListener('click', function() { showTokenForm(); });
    $('addGroupBtn').addEventListener('click', function() { showGroupForm(); });
    $('addFeatureBtn').addEventListener('click', function() { showFeatureForm(); });

    /* --- Token panel: event delegation --- */
    $('panelTokens').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var action = btn.dataset.action;
        var id = parseInt(btn.dataset.id);
        var editId = btn.dataset.editId;
        if (action === 'toggle-token') toggleToken(id, btn.dataset.activate === 'true');
        if (action === 'edit-token') editTokenInline(id);
        if (action === 'delete-token') deleteToken(id);
        if (action === 'save-token') saveToken(editId ? parseInt(editId) : null);
        if (action === 'cancel-token') hideTokenForm();
    });

    /* --- Group panel: event delegation --- */
    $('panelGroups').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var action = btn.dataset.action;
        var id = parseInt(btn.dataset.id);
        var editId = btn.dataset.editId;
        if (action === 'edit-group') editGroupInline(id);
        if (action === 'delete-group') deleteGroup(id);
        if (action === 'save-group') saveGroup(editId ? parseInt(editId) : null);
        if (action === 'cancel-group') hideGroupForm();
    });

    /* --- Feature panel: event delegation --- */
    $('panelFeatures').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var action = btn.dataset.action;
        var id = parseInt(btn.dataset.id);
        var editId = btn.dataset.editId;
        if (action === 'edit-feature') editFeatureInline(id);
        if (action === 'delete-feature') deleteFeature(id);
        if (action === 'save-feature') saveFeature(editId ? parseInt(editId) : null);
        if (action === 'cancel-feature') hideFeatureForm();
    });

    /* --- Init --- */
    setTheme(localStorage.getItem('theme') || 'dark');
    restoreModel();
    restoreLastResponse();
    loadAll();
});
