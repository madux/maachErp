/**
 * Attachments Module
 * Handles file attachments for memo forms with Odoo integration
 */
const AttachmentsModule = (function() {
    'use strict';

    // Private variables
    let attachedFiles = [];
    let memoId = null;

    /**
     * Initialize the module
     */
    function init() {
        setupEventListeners();
        setupDragAndDrop();
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Attach button click
        $('#attachBtn').on('click', function() {
            console.log("Molessssssss")
            $('#fileInput').click();
        });

        // File input change
        $('#fileInput').on('change', function(e) {
            const files = e.target.files;
            for (let i = 0; i < files.length; i++) {
                addFile(files[i]);
            }
            $(this).val(''); // Clear input
        });

        // Modal close
        $('.close').on('click', function() {
            $('#fileModal').hide();
        });

        $(window).on('click', function(e) {
            if ($(e.target).is('#fileModal')) {
                $('#fileModal').hide();
            }
        });
    }

    /**
     * Setup drag and drop functionality
     */
    function setupDragAndDrop() {
        const container = $('.attach_container');
        
        container.on('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).css('background-color', '#f0f9ff');
        });

        container.on('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).css('background-color', 'white');
        });

        container.on('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).css('background-color', 'white');

            const files = e.originalEvent.dataTransfer.files;
            const allowedExtensions = ['pdf', 'txt', 'xls', 'xlsx', 'csv'];

            for (let i = 0; i < files.length; i++) {
                const ext = getFileExtension(files[i].name);
                if (allowedExtensions.includes(ext)) {
                    addFile(files[i]);
                } else {
                    showToast(`File type .${ext} is not allowed`, 'error');
                }
            }
        });
    }

    /**
     * Add file to attachments array
     */
    function addFile(file) {
        const fileData = {
            id: Date.now() + Math.random(),
            file: file,
            name: file.name,
            type: file.type,
            size: file.size,
            url: URL.createObjectURL(file),
            isExisting: false
        };

        attachedFiles.push(fileData);
        renderFiles();
        showToast(`${file.name} added`);
    }

    /**
     * Render files in grid
     */
    function renderFiles() {
        const grid = $('#filesGrid');
        
        if (attachedFiles.length === 0) {
            grid.html(`
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                        <polyline points="13 2 13 9 20 9"/>
                    </svg>
                    <p>No files attached yet</p>
                </div>
            `);
            return;
        }

        grid.empty();
        attachedFiles.forEach(fileData => {
            const fileExt = getFileExtension(fileData.name);
            const icon = getFileIcon(fileExt);
            
            const fileItem = $(`
                <div class="file-item" data-id="${fileData.id}">
                    <div class="file-icon-wrapper">
                        ${icon}
                    </div>
                    <div class="file-info">
                        <div class="file-name">${fileData.name}</div>
                        <div class="file-type">${fileExt.toUpperCase()}</div>
                    </div>
                    <div class="file-actions">
                        <button class="action-btn download-btn" title="Download">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                        </button>
                        <button class="action-btn delete-btn" title="Delete">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `);

            // View file
            fileItem.on('click', function(e) {
                if (!$(e.target).closest('.file-actions').length) {
                    viewFile(fileData);
                }
            });

            // Download file
            fileItem.find('.download-btn').on('click', function(e) {
                e.stopPropagation();
                downloadFile(fileData);
            });

            // Delete file
            fileItem.find('.delete-btn').on('click', function(e) {
                e.stopPropagation();
                deleteFile(fileData);
            });

            grid.append(fileItem);
        });
    }

    /**
     * Get file extension
     */
    function getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    /**
     * Get file icon SVG
     */
    function getFileIcon(ext) {
        const icons = {
            'pdf': `<svg class="file-icon" viewBox="0 0 24 24" fill="#ef4444">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8" stroke="white" stroke-width="2" fill="none"/>
                <text x="12" y="17" text-anchor="middle" fill="white" font-size="6" font-weight="bold">PDF</text>
            </svg>`,
            'txt': `<svg class="file-icon" viewBox="0 0 24 24" fill="#6b7280">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8" stroke="white" stroke-width="2" fill="none"/>
                <line x1="16" y1="13" x2="8" y2="13" stroke="white" stroke-width="2"/>
                <line x1="16" y1="17" x2="8" y2="17" stroke="white" stroke-width="2"/>
            </svg>`,
            'xls': `<svg class="file-icon" viewBox="0 0 24 24" fill="#10b981">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8" stroke="white" stroke-width="2" fill="none"/>
                <text x="12" y="17" text-anchor="middle" fill="white" font-size="5" font-weight="bold">XLS</text>
            </svg>`,
            'xlsx': `<svg class="file-icon" viewBox="0 0 24 24" fill="#10b981">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8" stroke="white" stroke-width="2" fill="none"/>
                <text x="12" y="17" text-anchor="middle" fill="white" font-size="5" font-weight="bold">XLS</text>
            </svg>`,
            'csv': `<svg class="file-icon" viewBox="0 0 24 24" fill="#10b981">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8" stroke="white" stroke-width="2" fill="none"/>
                <text x="12" y="17" text-anchor="middle" fill="white" font-size="5" font-weight="bold">CSV</text>
            </svg>`
        };
        return icons[ext] || icons['txt'];
    }

    /**
     * View file in modal
     */
    function viewFile(fileData) {
        const modal = $('#fileModal');
        const modalBody = $('#modalBody');
        const modalTitle = $('#modalTitle');
        const ext = getFileExtension(fileData.name);

        modalTitle.text(fileData.name);
        modalBody.html('<div class="loading"><div class="spinner"></div><p>Loading file...</p></div>');
        modal.show();

        setTimeout(() => {
            if (ext === 'pdf') {
                modalBody.html(`<iframe id="fileViewer" src="${fileData.url}"></iframe>`);
            } else if (ext === 'txt') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const content = $('<div>').text(e.target.result).html(); // Escape HTML
                    modalBody.html(`<div class="text-viewer">${content}</div>`);
                };
                reader.readAsText(fileData.file);
            } else if (['xls', 'xlsx', 'csv'].includes(ext)) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    try {
                        const data = new Uint8Array(e.target.result);
                        const workbook = XLSX.read(data, { type: 'array' });
                        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
                        const html = XLSX.utils.sheet_to_html(firstSheet);
                        modalBody.html(`<div class="excel-viewer">${html}</div>`);
                    } catch (error) {
                        modalBody.html(`<div class="text-viewer">Error loading Excel file: ${error.message}</div>`);
                    }
                };
                reader.readAsArrayBuffer(fileData.file);
            }
        }, 300);
    }

    /**
     * Download file
     */
    function downloadFile(fileData) {
        if (fileData.isExisting && fileData.odooId) {
            // Download from Odoo
            window.open(`/web/content/${fileData.odooId}?download=true`, '_blank');
        } else {
            // Download local file
            const a = document.createElement('a');
            a.href = fileData.url;
            a.download = fileData.name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
        showToast('Downloading file...');
    }

    /**
     * Delete file
     */
    function deleteFile(fileData) {
        if (fileData.isExisting && fileData.odooId) {
            // Confirm deletion
            if (!confirm(`Are you sure you want to delete "${fileData.name}"?`)) {
                return;
            }

            // Delete from Odoo using custom controller
            $.ajax({
                url: `/memo/attachment/delete/${fileData.odooId}`,
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({
                    params: {}
                }),
                success: function(response) {
                    if (response.status === 'success') {
                        attachedFiles = attachedFiles.filter(f => f.id !== fileData.id);
                        renderFiles();
                        showToast('File deleted');
                    } else {
                        showToast(response.message || 'Error deleting file', 'error');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Delete error:', error);
                    showToast('Error deleting file', 'error');
                }
            });
        } else {
            // Just remove from local array (not yet uploaded)
            attachedFiles = attachedFiles.filter(f => f.id !== fileData.id);
            renderFiles();
            showToast('File removed');
        }
    }

    /**
     * Upload single file to Odoo
     */
    function uploadSingleFile(fileData) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const base64Data = e.target.result.split(',')[1];
                
                $.ajax({
                    url: '/memo/attachment/upload',
                    type: 'POST',
                    data: JSON.stringify({
                        params: {
                            name: fileData.name,
                            data: base64Data,
                            res_model: 'memo.model',
                            res_id: memoId || 0
                        }
                    }),
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        console.log('what is my upload ressssssssssssssssssssssssss', response.result.id, response)
                        if (response.result.id){//(response.status === 'success'){// && response.result && response.result.id) {
                            console.log("FILE DATA HAS BEEN UPLOADED", response.result.id);
                            resolve(response.result.id);
                        } else {
                            reject(new Error(response.message || 'Upload failed: No ID returned'));
                        }
                        console.log('what is my upload rexxxxxxxxxxxxxxxxxxxxxxxxxx', response.result.id, response)

                    },
                    error: function(xhr, status, error) {
                        let errorMsg = 'Upload failed: ' + error;
                        if (xhr.responseJSON && xhr.responseJSON.message) {
                            errorMsg = xhr.responseJSON.message;
                        }
                        reject(new Error(errorMsg));
                    }
                });
            };

            reader.onerror = function() {
                reject(new Error('File read error'));
            };

            reader.readAsDataURL(fileData.file);
        });
    }
    /**
     * Upload multiple files to Odoo
     */
    function uploadFilesToOdoo(newFiles, existingIds) {
        return new Promise((resolve, reject) => {
            const uploadPromises = newFiles.map(fileData => uploadSingleFile(fileData));

            Promise.all(uploadPromises)
                .then(newAttachmentIds => {
                    // Mark uploaded files as existing
                    newFiles.forEach((fileData, index) => {
                        const attachedFile = attachedFiles.find(f => f.id === fileData.id);
                        if (attachedFile) {
                            attachedFile.isExisting = true;
                            attachedFile.odooId = newAttachmentIds[index];
                        }
                    });

                    const allIds = [...existingIds, ...newAttachmentIds];
                    resolve(allIds);
                })
                .catch(error => {
                    reject(error);
                });
        });
    }

    /**
     * Get attachments for saving (uploads new files if needed)
     * Returns Promise that resolves with array of attachment IDs
     */
    function getAttachmentsForSave() {
        return new Promise((resolve, reject) => {
            if (attachedFiles.length === 0) {
                resolve([]);
                return;
            }

            // Separate new files from existing ones
            const newFiles = attachedFiles.filter(f => !f.isExisting);
            const existingIds = attachedFiles.filter(f => f.isExisting).map(f => f.odooId);

            if (newFiles.length === 0) {
                // Only existing files, no need to upload
                resolve(existingIds);
                return;
            }

            // Upload new files
            uploadFilesToOdoo(newFiles, existingIds)
                .then(allIds => resolve(allIds))
                .catch(error => reject(error));
        });
    }

    // /**
    //  * Load single attachment from Odoo
    //  */
    // function loadSingleAttachment(attachmentId) {
    //     return new Promise((resolve, reject) => {
    //         $.ajax({
    //             url: `/web/content/${attachmentId}?download=true`,
    //             type: 'GET',
    //             xhrFields: {
    //                 responseType: 'blob'
    //             },
    //             success: function(blob, status, xhr) {
    //                 // Get filename from Content-Disposition header
    //                 const disposition = xhr.getResponseHeader('Content-Disposition');
    //                 let filename = `attachment_${attachmentId}`;
                    
    //                 if (disposition) {
    //                     const filenameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    //                     if (filenameMatch && filenameMatch[1]) {
    //                         filename = filenameMatch[1].replace(/['"]/g, '');
    //                     }
    //                 }

    //                 // Create file object from blob
    //                 const file = new File([blob], filename, { type: blob.type });
                    
    //                 const fileData = {
    //                     id: attachmentId,
    //                     file: file,
    //                     name: filename,
    //                     type: blob.type,
    //                     size: blob.size,
    //                     url: URL.createObjectURL(blob),
    //                     isExisting: true,
    //                     odooId: attachmentId
    //                 };

    //                 resolve(fileData);
    //             },
    //             error: function(xhr, status, error) {
    //                 reject(new Error(`Error loading attachment ${attachmentId}: ${error}`));
    //             }
    //         });
    //     });
    // }

    /**
     * Load single attachment from Odoo
     */
    function loadSingleAttachment(attachmentId) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: `/memo/attachment/get/${attachmentId}`,
                type: 'GET',
                xhrFields: {
                    responseType: 'blob'
                },
                success: function(blob, status, xhr) {
                    // Get filename from Content-Disposition header
                    const disposition = xhr.getResponseHeader('Content-Disposition');
                    let filename = `attachment_${attachmentId}`;
                    
                    if (disposition) {
                        const filenameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                        if (filenameMatch && filenameMatch[1]) {
                            filename = filenameMatch[1].replace(/['"]/g, '');
                        }
                    }

                    // Create file object from blob
                    const file = new File([blob], filename, { type: blob.type });
                    
                    const fileData = {
                        id: attachmentId,
                        file: file,
                        name: filename,
                        type: blob.type,
                        size: blob.size,
                        url: URL.createObjectURL(blob),
                        isExisting: true,
                        odooId: attachmentId
                    };

                    resolve(fileData);
                },
                error: function(xhr, status, error) {
                    reject(new Error(`Error loading attachment ${attachmentId}: ${error}`));
                }
            });
        });
    }

    /**
     * Load attachments from Odoo
     * @param {Array} attachmentIds - Array of attachment IDs
     * @param {Number} memoIdParam - Memo ID
     */
    function loadAttachments(attachmentIds, memoIdParam) {
        return new Promise((resolve, reject) => {
            // Set memo ID
            memoId = memoIdParam;

            if (!attachmentIds || attachmentIds.length === 0) {
                attachedFiles = [];
                renderFiles();
                resolve([]);
                return;
            }

            // Clear existing files
            attachedFiles = [];
            renderFiles(); // Show empty state first

            // Load all attachments
            const loadPromises = attachmentIds.map(id => loadSingleAttachment(id));

            Promise.all(loadPromises)
                .then(filesData => {
                    attachedFiles = filesData;
                    renderFiles();
                    resolve(filesData);
                })
                .catch(error => {
                    console.error('Error loading attachments:', error);
                    showToast('Error loading some attachments', 'error');
                    // Still render whatever we managed to load
                    renderFiles();
                    reject(error);
                });
        });
    }

    



    /**
     * Clear all attachments
     */
    function clearAttachments() {
        attachedFiles = [];
        memoId = null;
        renderFiles();
    }

    /**
     * Set memo ID
     */
    function setMemoId(id) {
        memoId = id;
        console.log("WHAT IS MEMMO ID FILEVIEWER", memoId)

    }

    /**
     * Get current memo ID
     */
    function getMemoId() {
        return memoId;
    }

    /**
     * Get count of attached files
     */
    function getAttachmentCount() {
        return attachedFiles.length;
    }

    /**
     * Show toast notification
     */
    function showToast(message, type = 'success') {
        const toast = $('#toast');
        toast.text(message)
            .removeClass('error')
            .addClass(type === 'error' ? 'error' : '')
            .fadeIn(300)
            .delay(3000)
            .fadeOut(300);
    }

    // Public API
    return {
        init: init,
        getAttachmentsForSave: getAttachmentsForSave,
        loadAttachments: loadAttachments,
        clearAttachments: clearAttachments,
        setMemoId: setMemoId,
        getMemoId: getMemoId,
        getAttachmentCount: getAttachmentCount
    };
})();

// Initialize when DOM is ready
$(document).ready(function() {
    // Check if required elements exist before initializing
    if ($('#attachBtn').length && $('#fileInput').length && $('#filesGrid').length) {
        AttachmentsModule.init();
        console.log('AttachmentsModule initialized');
    } else {
        console.warn('AttachmentsModule: Required elements not found');
    }
});