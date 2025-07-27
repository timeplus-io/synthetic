let currentPipelineId = null;
let pipelines = [];
let refreshInterval = null; // Store the interval ID for cleanup

// Toast notification system
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' :
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M15 9L9 15M9 9L15 15" stroke="currentColor" stroke-width="2"/></svg>';
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => container.removeChild(toast), 300);
    }, 4000);
}

// Navigation functions
function showCreateForm() {
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('createForm').style.display = 'flex';
    document.getElementById('pipelineDetails').style.display = 'none';
    
    // Clear refresh interval when leaving pipeline details
    clearRefreshInterval();
}

function hideCreateForm() {
    document.getElementById('createForm').style.display = 'none';
    document.getElementById('welcomeScreen').style.display = 'flex';
    document.getElementById('pipelineDetails').style.display = 'none';
    document.getElementById('pipelineForm').reset();
    
    // Clear refresh interval when leaving pipeline details
    clearRefreshInterval();
}

function showPipelineDetails(pipelineId) {
    currentPipelineId = pipelineId;
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('createForm').style.display = 'none';
    document.getElementById('pipelineDetails').style.display = 'block';
    loadPipelineDetails(pipelineId);
    
    // Start auto-refresh for write count
    startAutoRefresh();
}

function hidePipelineDetails() {
    document.getElementById('pipelineDetails').style.display = 'none';
    document.getElementById('welcomeScreen').style.display = 'flex';
    document.getElementById('createForm').style.display = 'none';
    currentPipelineId = null;
    updateSidebarActive();
    
    // Clear refresh interval when leaving pipeline details
    clearRefreshInterval();
}

// Auto-refresh functionality
function startAutoRefresh() {
    // Clear any existing interval
    clearRefreshInterval();
    
    // Set up new interval to refresh every 3 seconds
    refreshInterval = setInterval(() => {
        if (currentPipelineId && document.getElementById('pipelineDetails').style.display !== 'none') {
            refreshWriteCount();
        } else {
            // Clear interval if we're no longer on pipeline details page
            clearRefreshInterval();
        }
    }, 3000);
}

function clearRefreshInterval() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

async function refreshWriteCount() {
    if (!currentPipelineId) return;
    
    try {
        const response = await fetch(`/pipelines/${currentPipelineId}`);
        
        if (!response.ok) {
            console.error('Failed to refresh write count');
            return;
        }
        
        const pipeline = await response.json();
        
        // Update only the write count display
        const writeCountElement = document.getElementById('detailsWriteCount');
        if (writeCountElement && pipeline.write_count !== undefined) {
            const newCount = pipeline.write_count || 0;
            const formattedCount = formatNumber(newCount);
            writeCountElement.textContent = formattedCount;
            
            // Add a subtle animation to indicate refresh
            writeCountElement.style.opacity = '0.7';
            setTimeout(() => {
                writeCountElement.style.opacity = '1';
            }, 150);
        }
        
    } catch (error) {
        console.error('Error refreshing write count:', error);
        // Don't show toast for refresh errors to avoid spamming user
    }
}

// Utility function to format numbers with commas
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Example prompt usage
function useExample(description) {
    document.getElementById('pipelineDescription').value = description;
    showCreateForm();
    
    // Focus on the textarea so user can see the content
    setTimeout(() => {
        const textarea = document.getElementById('pipelineDescription');
        textarea.focus();
        // Move cursor to end of text
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }, 100);
}

// Load pipelines for sidebar
async function loadPipelines() {
    try {
        const response = await fetch('/pipelines');
        const data = await response.json();
        pipelines = data.pipelines || [];
        
        // Load write counts for each pipeline
        await loadPipelineWriteCounts();
        
        updateSidebar();
    } catch (error) {
        showToast(`Error loading pipelines: ${error.message}`, 'error');
    }
}

// Load write counts for all pipelines
async function loadPipelineWriteCounts() {
    const promises = pipelines.map(async (pipeline) => {
        try {
            const response = await fetch(`/pipelines/${pipeline.id}`);
            if (response.ok) {
                const data = await response.json();
                pipeline.write_count = data.write_count || 0;
            } else {
                pipeline.write_count = 0;
            }
        } catch (error) {
            console.error(`Failed to load write count for pipeline ${pipeline.id}:`, error);
            pipeline.write_count = 0;
        }
    });
    
    await Promise.all(promises);
}

// Update sidebar with pipelines
function updateSidebar() {
    const container = document.getElementById('sidebarPipelines');
    
    if (pipelines.length === 0) {
        container.innerHTML = '<div style="padding: 12px; color: var(--text-tertiary); font-size: 12px; text-align: center;">No pipelines yet</div>';
        return;
    }
    
    container.innerHTML = pipelines.map(pipeline => {
        const writeCount = pipeline.write_count || 0;
        const formattedCount = formatNumber(writeCount);
        const showBadge = writeCount > 0;
        
        return `
            <div class="pipeline-item-sidebar ${pipeline.id === currentPipelineId ? 'active' : ''}" 
                 data-pipeline-id="${pipeline.id}">
                <div class="pipeline-header">
                    <div class="pipeline-name">${escapeHtml(pipeline.name)}</div>
                    ${showBadge ? `<div class="pipeline-count-badge">${formattedCount}</div>` : ''}
                </div>
                <div class="pipeline-preview">${escapeHtml(pipeline.question || '')}</div>
            </div>
        `;
    }).join('');
    
    // Add click listeners to sidebar items
    container.querySelectorAll('.pipeline-item-sidebar').forEach(item => {
        item.addEventListener('click', () => {
            const pipelineId = item.getAttribute('data-pipeline-id');
            showPipelineDetails(pipelineId);
        });
    });
}

// Update sidebar active state
function updateSidebarActive() {
    const items = document.querySelectorAll('.pipeline-item-sidebar');
    items.forEach(item => {
        item.classList.remove('active');
        const pipelineId = item.getAttribute('data-pipeline-id');
        if (pipelineId === currentPipelineId) {
            item.classList.add('active');
        }
    });
}

// Load pipeline details
async function loadPipelineDetails(pipelineId) {
    try {
        const response = await fetch(`/pipelines/${pipelineId}`);
        
        if (!response.ok) {
            const error = await response.json();
            showToast(`Error: ${error.detail}`, 'error');
            return;
        }
        
        const pipeline = await response.json();
        console.log('Pipeline data received:', pipeline); // Debug log
        
        // Validate pipeline structure
        if (!pipeline || !pipeline.pipeline) {
            showToast('Invalid pipeline data received', 'error');
            return;
        }
        
        displayPipelineDetails(pipeline);
        updateSidebarActive();
        
    } catch (error) {
        console.error('Error in loadPipelineDetails:', error); // Debug log
        showToast(`Error loading pipeline: ${error.message}`, 'error');
    }
}

// Display pipeline details
function displayPipelineDetails(pipeline) {
    try {
        console.log('Displaying pipeline:', pipeline); // Debug log
        
        // Safely set pipeline name and ID
        const nameElement = document.getElementById('detailsPipelineName');
        const idElement = document.getElementById('detailsPipelineId');
        const descElement = document.getElementById('detailsDescription');
        const writeCountElement = document.getElementById('detailsWriteCount');
        
        if (nameElement) nameElement.textContent = pipeline.name || 'Unknown Pipeline';
        if (idElement) idElement.textContent = pipeline.id || 'Unknown ID';
        if (descElement) descElement.textContent = (pipeline.pipeline && pipeline.pipeline.question) || 'No description available';
        if (writeCountElement) {
            const writeCount = pipeline.write_count || 0;
            writeCountElement.textContent = formatNumber(writeCount);
        }
        
        // Components section - with null checks
        const componentsContainer = document.getElementById('detailsComponents');
        if (componentsContainer && pipeline.pipeline) {
            const components = [];
            
            if (pipeline.pipeline.random_stream && pipeline.pipeline.random_stream.name) {
                components.push({ name: pipeline.pipeline.random_stream.name, type: 'Random Stream' });
            }
            if (pipeline.pipeline.kafka_external_stream && pipeline.pipeline.kafka_external_stream.name) {
                components.push({ name: pipeline.pipeline.kafka_external_stream.name, type: 'Kafka Stream' });
            }
            if (pipeline.pipeline.write_to_kafka_mv && pipeline.pipeline.write_to_kafka_mv.name) {
                components.push({ name: pipeline.pipeline.write_to_kafka_mv.name, type: 'Materialized View' });
            }
            
            componentsContainer.innerHTML = components.map(comp => `
                <div class="component-item">
                    <span class="component-name">${escapeHtml(comp.name)}</span>
                    <span class="component-type">${comp.type}</span>
                </div>
            `).join('');
        }
        
        // DDL section - with null checks
        const ddlContainer = document.getElementById('detailsDDL');
        if (ddlContainer && pipeline.pipeline) {
            const ddlItems = [];
            
            if (pipeline.pipeline.random_stream && pipeline.pipeline.random_stream.ddl) {
                ddlItems.push({ title: 'Random Stream DDL', content: pipeline.pipeline.random_stream.ddl });
            }
            if (pipeline.pipeline.kafka_external_stream && pipeline.pipeline.kafka_external_stream.ddl) {
                ddlItems.push({ title: 'Kafka External Stream DDL', content: pipeline.pipeline.kafka_external_stream.ddl });
            }
            if (pipeline.pipeline.write_to_kafka_mv && pipeline.pipeline.write_to_kafka_mv.ddl) {
                ddlItems.push({ title: 'Materialized View DDL', content: pipeline.pipeline.write_to_kafka_mv.ddl });
            }
            
            ddlContainer.innerHTML = ddlItems.map((item, index) => `
                <div class="ddl-item" id="ddl-${index}">
                    <div class="ddl-header" data-ddl-index="${index}">
                        <span class="ddl-title">${item.title}</span>
                        <svg class="ddl-toggle" width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div class="ddl-content">
                        <div class="ddl-code">${escapeHtml(item.content)}</div>
                    </div>
                </div>
            `).join('');
            
            // Add click listeners to DDL headers
            ddlContainer.querySelectorAll('.ddl-header').forEach(header => {
                header.addEventListener('click', () => {
                    const index = header.getAttribute('data-ddl-index');
                    toggleDDL(index);
                });
            });
        }
        
    } catch (error) {
        console.error('Error in displayPipelineDetails:', error);
        showToast(`Error displaying pipeline details: ${error.message}`, 'error');
    }
}

// Toggle DDL section
function toggleDDL(index) {
    const item = document.getElementById(`ddl-${index}`);
    item.classList.toggle('expanded');
}

// Delete current pipeline
async function deleteCurrentPipeline() {
    if (!currentPipelineId) return;
    
    const pipeline = pipelines.find(p => p.id === currentPipelineId);
    const pipelineName = pipeline ? pipeline.name : 'this pipeline';
    
    if (!confirm(`Are you sure you want to delete "${pipelineName}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/pipelines/${currentPipelineId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast(`Pipeline "${pipelineName}" deleted successfully!`);
            hidePipelineDetails();
            await loadPipelines();
        } else {
            const error = await response.json();
            showToast(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        showToast(`Error deleting pipeline: ${error.message}`, 'error');
    }
}

// Utility function to escape HTML - with null check
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape key to go back
    if (e.key === 'Escape') {
        if (document.getElementById('createForm').style.display !== 'none') {
            hideCreateForm();
        } else if (document.getElementById('pipelineDetails').style.display !== 'none') {
            hidePipelineDetails();
        }
    }
    
    // Ctrl/Cmd + N for new pipeline
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        showCreateForm();
    }
});

// Mobile sidebar toggle (for future mobile support)
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('open');
}

// Initialize app
window.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners first
    setupEventListeners();
    
    // Then load pipelines
    loadPipelines();
    
    // Add click outside to close mobile sidebar
    document.addEventListener('click', (e) => {
        const sidebar = document.querySelector('.sidebar');
        if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    clearRefreshInterval();
});

// Setup all event listeners
function setupEventListeners() {
    // New pipeline button
    const newPipelineBtn = document.getElementById('newPipelineBtn');
    if (newPipelineBtn) {
        newPipelineBtn.addEventListener('click', showCreateForm);
    }
    
    // Close form buttons
    const closeFormBtn = document.getElementById('closeFormBtn');
    if (closeFormBtn) {
        closeFormBtn.addEventListener('click', hideCreateForm);
    }
    
    const cancelFormBtn = document.getElementById('cancelFormBtn');
    if (cancelFormBtn) {
        cancelFormBtn.addEventListener('click', hideCreateForm);
    }
    
    // Back button
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', hidePipelineDetails);
    }
    
    // Delete pipeline button
    const deletePipelineBtn = document.getElementById('deletePipelineBtn');
    if (deletePipelineBtn) {
        deletePipelineBtn.addEventListener('click', deleteCurrentPipeline);
    }
    
    // Example prompts
    const examplePrompts = document.querySelectorAll('.example-prompt');
    examplePrompts.forEach(prompt => {
        prompt.addEventListener('click', () => {
            // Get the content from the example-desc div
            const descDiv = prompt.querySelector('.example-desc');
            const description = descDiv.innerText.trim(); // innerText preserves line breaks
            useExample(description);
        });
    });
    
    // Form submission
    const form = document.getElementById('pipelineForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
}

// Handle form submission
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        question: formData.get('question').trim()
    };
    
    if (!data.question) {
        showToast('Please fill in all required fields', 'error');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnSpinner = submitBtn.querySelector('.btn-spinner');
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'flex';
    
    try {
        const response = await fetch('/pipelines', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Pipeline created:', result); // Debug log
            showToast(`Pipeline "${result.name}" created successfully!`);
            e.target.reset();
            hideCreateForm();
            await loadPipelines();
            
            // Show pipeline details if ID is available
            if (result.id) {
                showPipelineDetails(result.id);
            }
        } else {
            const error = await response.json();
            console.error('API Error:', error); // Debug log
            showToast(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Network Error:', error); // Debug log
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        // Reset loading state
        submitBtn.disabled = false;
        btnText.style.display = 'block';
        btnSpinner.style.display = 'none';
    }
}