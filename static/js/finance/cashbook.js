const API_BASE_URL = '/api';
const API_ENDPOINTS = {
    income: `${API_BASE_URL}/income`,
    expense: `${API_BASE_URL}/expense`,
    transfer: `${API_BASE_URL}/transfer`,
    loan: `${API_BASE_URL}/loan`,
    categories: `${API_BASE_URL}/categories`,
    contacts: `${API_BASE_URL}/contacts`,
    branches: `${API_BASE_URL}/branches`,
    loanSettings: `${API_BASE_URL}/loan-settings`
};

async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        if (data) {
            if (data instanceof FormData) {
                delete config.headers['Content-Type']; 
                config.body = data;
            } else {
                config.body = JSON.stringify(data);
            }
        }

        const response = await fetch(endpoint, config);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

const attachmentArea = document.getElementById('attachmentArea');
const fileInput = document.getElementById('fileInput');
const attachmentAreaExpense = document.getElementById('attachment-Area');
const fileInputExpense = document.getElementById('fileInputExpense');
const recurringIncomeLink = document.querySelector('.incomeRec');
const incomeReminderLink = document.querySelector('.incomeRem');
const incomeRecordButton = document.querySelector('.btn-record');
const loanLink = document.querySelector('.loan');
const recurringExpenseLink = document.querySelector('.recExp');
const expenseReminderLink = document.querySelector('.expRem');
const expenseRecordButton = document.querySelector('.btn-record-expense');
const transferRecordButton = document.querySelector('.btn.btn-teal');
const transferFormContainer = document.getElementById('transferForm');
const recurringIncomeSection = document.createElement('div');
const incomeReminderSection = document.createElement('div');
const recurringExpenseSection = document.createElement('div');
const expenseReminderSection = document.createElement('div');
const loanSection = document.createElement('div'); 

let filteredTransactions = [];
let currentFilter = 'all';
let currentType = 'all';

if (attachmentArea && fileInput) {
    attachmentArea.addEventListener('dragover', function(event) {
        event.preventDefault();
        attachmentArea.classList.add('bg-light');
    });

    attachmentArea.addEventListener('dragleave', function() {
        attachmentArea.classList.remove('bg-light');
    });

    attachmentArea.addEventListener('drop', function(event) {
        event.preventDefault();
        const files = event.dataTransfer.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        const files = fileInput.files;
        handleFiles(files);
    });

    function handleFiles(files) {
        attachmentArea.innerHTML = '';
        if (files.length > 0) {
            Array.from(files).forEach(function(file) {
                const fileElement = document.createElement('div');
                fileElement.className = 'file-item d-flex align-items-center justify-content-between p-2 mb-2 bg-light rounded';
                fileElement.innerHTML = `
                    <span><i class="bx bx-file me-2"></i>${file.name}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(this)">
                        <i class="bx bx-x"></i>
                    </button>
                `;
                attachmentArea.appendChild(fileElement);
            });
        } else {
            resetAttachmentArea(attachmentArea, 'attachmentArea');
        }
    }

    attachmentArea.addEventListener('click', function() {
        if (!attachmentArea.querySelector('.file-item')) {
            fileInput.click();
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const loanSettingsForm = document.getElementById('loanSettingsForm');
    const loanSettingsOffcanvas = document.getElementById('loanSettingsOffcanvas');
    const cancelLoanSettingsBtn = document.getElementById('cancelLoanSettings');

    if (loanSettingsForm) {
        loanSettingsForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
            
            try {
                const loanSettingsData = {
                    principal: document.getElementById('principalAmount')?.value,
                    interestType: document.getElementById('interestType')?.value,
                    defaultRate: parseFloat(document.getElementById('defaultRate')?.value) || 0,
                    interestFrequency: document.getElementById('interestFrequency')?.value,
                    minDuration: parseInt(document.getElementById('minDuration')?.value) || 0,
                    maxDuration: parseInt(document.getElementById('maxDuration')?.value) || 0,
                    defaultDuration: parseInt(document.getElementById('defaultDuration')?.value) || 0,
                    termUnit: document.getElementById('termUnit')?.value,
                    repaymentFrequency: document.getElementById('repaymentFrequency')?.value,
                    gracePeriod: parseInt(document.getElementById('gracePeriod')?.value) || 0,
                    latePenaltyType: document.getElementById('latePenaltyType')?.value,
                    penaltyValue: parseFloat(document.getElementById('penaltyValue')?.value) || 0,
                    autoDeduction: document.getElementById('autoDeduction')?.checked,
                    minIncome: parseFloat(document.getElementById('minIncome')?.value) || 0,
                    minMembership: parseInt(document.getElementById('minMembership')?.value) || 0,
                    minCreditScore: parseInt(document.getElementById('minCreditScore')?.value) || 0,
                    collateralRequired: document.getElementById('collateralRequired')?.checked,
                    limitType: document.getElementById('limitType')?.value,
                    maxLoanAmount: parseFloat(document.getElementById('maxLoanAmount')?.value) || 0,
                    multipleLoans: document.getElementById('multipleLoans')?.checked,
                    userRole: document.getElementById('userRole')?.value,
                    approversRequired: parseInt(document.getElementById('approversRequired')?.value) || 1,
                    approvalRoles: Array.from(document.getElementById('approvalRoles')?.selectedOptions || []).map(opt => opt.value),
                    autoApproval: document.getElementById('autoApproval')?.checked,
                    updatedAt: new Date().toISOString()
                };
                
                const response = await apiCall(API_ENDPOINTS.loanSettings, 'POST', loanSettingsData);
                
                console.log('Loan settings saved:', response);
                
                Swal.fire({
                    icon: 'success',
                    title: 'Loan settings saved successfully!',
                    confirmButtonColor: '#009788'
                });
                
                if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas && loanSettingsOffcanvas) {
                    const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(loanSettingsOffcanvas);
                    bsOffcanvas.hide();
                }
                
            } catch (error) {
                console.error('Error saving loan settings:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error saving loan settings',
                    text: error.message || 'An unexpected error occurred',
                    confirmButtonColor: '#e57373'
                });
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    if (cancelLoanSettingsBtn) {
        cancelLoanSettingsBtn.addEventListener('click', function() {
            if (loanSettingsForm) loanSettingsForm.reset();
            if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas && loanSettingsOffcanvas) {
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(loanSettingsOffcanvas);
                bsOffcanvas.hide();
            }
        });
    }

    const loanBtn = document.querySelector('.option-links .loan');
    if (loanBtn) {
        loanBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const loanCanvas = document.getElementById('loanSettingsOffcanvas');
            if (loanCanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(loanCanvas);
                bsOffcanvas.show();
            }
        });
    }

    const transferBtn = document.querySelector('[data-bs-target="#offcanvasTransfer"]');
    const transferCanvas = document.getElementById('offcanvasTransfer');
    if (transferBtn && transferCanvas) {
        transferBtn.addEventListener('click', function(e) {
            e.preventDefault();
            try {
                if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(transferCanvas);
                    offcanvas.show();
                    console.log('Transfer offcanvas opened');
                }
            } catch (err) {
                console.error('Error showing transfer offcanvas:', err);
            }
        });
    }

    // Category button handlers
    const expenseCategoryBtn = document.querySelector('#expenseForm .dropdown-toggle[data-bs-target="#offcanvasCategory"]');
    if (expenseCategoryBtn) {
        expenseCategoryBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const catCanvas = document.getElementById('offcanvasCategory');
            if (catCanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(catCanvas);
                bsOffcanvas.show();
            }
        });
    }

    const incomeCategoryBtn = document.querySelector('#incomeForm .dropdown-toggle[data-bs-target="#offcanvasCategory"]');
    if (incomeCategoryBtn) {
        incomeCategoryBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const catCanvas = document.getElementById('offcanvasCategory');
            if (catCanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(catCanvas);
                bsOffcanvas.show();
            }
        });
    }

    // Contact selection handlers
    const contactItems = document.querySelectorAll('.contact-item');
    contactItems.forEach(item => {
        item.addEventListener('click', function() {
            const contactName = this.querySelector('.fw-semibold')?.textContent || '';
            const contactEmail = this.querySelector('.text-muted')?.textContent || '';
            
            // Update contact input fields
            const contactInputs = document.querySelectorAll('input[placeholder*="Contact"], input[placeholder*="contact"]');
            contactInputs.forEach(input => {
                input.value = contactName;
            });
            
            // Close offcanvas if open
            const contactOffcanvas = document.getElementById('offcanvasContact');
            if (contactOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(contactOffcanvas);
                if (bsOffcanvas) {
                    bsOffcanvas.hide();
                }
            }
        });
    });

    // Category selection handlers
    const categoryItems = document.querySelectorAll('.category-item');
    categoryItems.forEach(item => {
        item.addEventListener('click', function() {
            const categoryName = this.textContent.trim();
            
            // Update category dropdown buttons
            const categoryDropdowns = document.querySelectorAll('#categoryDropdown, .category-dropdown');
            categoryDropdowns.forEach(dropdown => {
                dropdown.textContent = categoryName;
            });
            
            // Close offcanvas if open
            const categoryOffcanvas = document.getElementById('offcanvasCategory');
            if (categoryOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(categoryOffcanvas);
                if (bsOffcanvas) {
                    bsOffcanvas.hide();
                }
            }
        });
    });

    // Add new category functionality
    const addCategoryBtn = document.querySelector('.add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', async function() {
            const categoryName = prompt('Enter new category name:');
            if (categoryName && categoryName.trim()) {
                try {
                    const newCategory = {
                        name: categoryName.trim(),
                        createdAt: new Date().toISOString()
                    };
                    
                    const response = await apiCall(API_ENDPOINTS.categories, 'POST', newCategory);
                    
                    // Add to UI
                    const categoryContainer = document.querySelector('.category-container');
                    if (categoryContainer) {
                        const newCategoryElement = document.createElement('div');
                        newCategoryElement.className = 'category-item p-2 rounded hover-bg-light cursor-pointer';
                        newCategoryElement.textContent = categoryName.trim();
                        newCategoryElement.addEventListener('click', function() {
                            const categoryDropdowns = document.querySelectorAll('#categoryDropdown, .category-dropdown');
                            categoryDropdowns.forEach(dropdown => {
                                dropdown.textContent = categoryName.trim();
                            });
                            
                            const categoryOffcanvas = document.getElementById('offcanvasCategory');
                            if (categoryOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                                const bsOffcanvas = bootstrap.Offcanvas.getInstance(categoryOffcanvas);
                                if (bsOffcanvas) {
                                    bsOffcanvas.hide();
                                }
                            }
                        });
                        categoryContainer.appendChild(newCategoryElement);
                    }
                    
                    Swal.fire({
                        icon: 'success',
                        title: 'Category added successfully!',
                        confirmButtonColor: '#009788'
                    });
                    
                } catch (error) {
                    console.error('Error adding category:', error);
                    Swal.fire({
                        icon: 'error',
                        title: 'Error adding category',
                        text: error.message || 'An unexpected error occurred',
                        confirmButtonColor: '#e57373'
                    });
                }
            }
        });
    }
});

// Load data from backend on page load
async function loadInitialData() {
    try {
        // Load categories
        const categories = await apiCall(API_ENDPOINTS.categories);
        populateCategories(categories);
        
        // Load contacts
        const contacts = await apiCall(API_ENDPOINTS.contacts);
        populateContacts(contacts);
        
        // Load branches
        const branches = await apiCall(API_ENDPOINTS.branches);
        populateBranches(branches);
        
        console.log('Initial data loaded successfully');
    } catch (error) {
        console.error('Error loading initial data:', error);
    }
}

// Populate categories in UI
function populateCategories(categories) {
    const categoryContainer = document.querySelector('.category-container');
    if (categoryContainer && categories.length > 0) {
        categoryContainer.innerHTML = '';
        categories.forEach(category => {
            const categoryElement = document.createElement('div');
            categoryElement.className = 'category-item p-2 rounded hover-bg-light cursor-pointer';
            categoryElement.textContent = category.name;
            categoryElement.addEventListener('click', function() {
                const categoryDropdowns = document.querySelectorAll('#categoryDropdown, .category-dropdown');
                categoryDropdowns.forEach(dropdown => {
                    dropdown.textContent = category.name;
                });
                
                const categoryOffcanvas = document.getElementById('offcanvasCategory');
                if (categoryOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(categoryOffcanvas);
                    if (bsOffcanvas) {
                        bsOffcanvas.hide();
                    }
                }
            });
            categoryContainer.appendChild(categoryElement);
        });
    }
}

// Populate contacts in UI
function populateContacts(contacts) {
    const contactContainer = document.querySelector('.contact-container');
    if (contactContainer && contacts.length > 0) {
        contactContainer.innerHTML = '';
        contacts.forEach(contact => {
            const contactElement = document.createElement('div');
            contactElement.className = 'contact-item d-flex align-items-center p-2 rounded hover-bg-light cursor-pointer';
            contactElement.innerHTML = `
                <div class="me-3">
                    <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                        ${contact.name.charAt(0).toUpperCase()}
                    </div>
                </div>
                <div>
                    <div class="fw-semibold">${contact.name}</div>
                    <div class="text-muted small">${contact.email || contact.phone || ''}</div>
                </div>
            `;
            contactElement.addEventListener('click', function() {
                const contactInputs = document.querySelectorAll('input[placeholder*="Contact"], input[placeholder*="contact"]');
                contactInputs.forEach(input => {
                    input.value = contact.name;
                });
                
                const contactOffcanvas = document.getElementById('offcanvasContact');
                if (contactOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(contactOffcanvas);
                    if (bsOffcanvas) {
                        bsOffcanvas.hide();
                    }
                }
            });
            contactContainer.appendChild(contactElement);
        });
    }
}

// Populate branches in UI
function populateBranches(branches) {
    const branchDropdowns = document.querySelectorAll('.branch-dropdown .dropdown-menu');
    branchDropdowns.forEach(dropdown => {
        if (branches.length > 0) {
            dropdown.innerHTML = '';
            branches.forEach(branch => {
                const branchItem = document.createElement('li');
                branchItem.innerHTML = `<a class="dropdown-item" href="#">${branch.name}</a>`;
                branchItem.addEventListener('click', function(e) {
                    e.preventDefault();
                    const dropdownButton = dropdown.closest('.dropdown').querySelector('.dropdown-toggle');
                    if (dropdownButton) {
                        dropdownButton.textContent = branch.name;
                    }
                });
                dropdown.appendChild(branchItem);
            });
        }
    });
}

// Initialize default dates
function setDefaultDates() {
    const today = new Date();
    const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, today.getDate());
    
    const fromDateInputs = document.querySelectorAll('#incomeFromDate, #expenseFromDate');
    fromDateInputs.forEach(input => {
        if (input) input.value = today.toISOString().slice(0, 10);
    });
    
    const toDateInputs = document.querySelectorAll('#incomeToDate, #expenseToDate');
    toDateInputs.forEach(input => {
        if (input) input.value = nextMonth.toISOString().slice(0, 10);
    });
}

// Initialize dropdowns
function initializeDropdowns() {
    const dropdownItems = document.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(item => {
        if (!item.onclick && !item.hasAttribute('data-listener-added')) {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const dropdown = this.closest('.dropdown');
                const button = dropdown.querySelector('.dropdown-toggle');
                if (button && !this.querySelector('i.bx-plus')) {
                    button.textContent = this.textContent;
                    
                    if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                        const dropdownInstance = bootstrap.Dropdown.getInstance(button);
                        if (dropdownInstance) {
                            dropdownInstance.hide();
                        }
                    }
                }
            });
            item.setAttribute('data-listener-added', 'true');
        }
    });
}

// Reset dropdown text
function resetDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        const defaultText = dropdown.getAttribute('data-default-text');
        if (defaultText) {
            dropdown.textContent = defaultText;
        } else {
            // Set default values based on context
            const text = dropdown.textContent;
            if (text.includes('CASH')) dropdown.textContent = 'CASH';
            else if (text.includes('USD')) dropdown.textContent = 'USD';
            else if (text.includes('Branch')) dropdown.textContent = 'Select Branch';
            else if (text.includes('category')) dropdown.textContent = 'Select Category';
            else if (text.includes('Account')) dropdown.textContent = 'Select Account';
            else if (text.includes('User')) dropdown.textContent = 'Select User';
        }
    });
}

// Reset toggle links
function resetToggleLinks() {
    if (recurringIncomeLink) {
        recurringIncomeLink.classList.remove('text-primary', 'fw-bold');
        recurringIncomeLink.innerHTML = 'Recurring Income?';
    }
    if (incomeReminderLink) {
        incomeReminderLink.classList.remove('text-primary', 'fw-bold');
        incomeReminderLink.innerHTML = 'Set a Reminder?';
    }
    if (loanLink) {
        loanLink.classList.remove('text-primary', 'fw-bold');
        loanLink.innerHTML = 'Loan?';
    }
    if (recurringExpenseLink) {
        recurringExpenseLink.classList.remove('text-primary', 'fw-bold');
        recurringExpenseLink.innerHTML = 'Recurring Expense?';
    }
    if (expenseReminderLink) {
        expenseReminderLink.classList.remove('text-primary', 'fw-bold');
        expenseReminderLink.innerHTML = 'Set a Reminder?';
    }
}

// Currency formatting
function formatCurrency(amount, currency = 'USD') {
    const numAmount = parseFloat(amount) || 0;
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    }).format(numAmount);
}

// Form validation
function validateForm(formData) {
    const errors = [];
    
    let amt = formData.amount;
    if (typeof amt === 'string') amt = amt.trim();
    if (!amt || isNaN(amt) || parseFloat(amt) <= 0) {
        errors.push('Amount must be greater than 0');
    }

    let title = formData.title;
    if (!title && formData.expenseTitle) title = formData.expenseTitle;
    if (!title && formData.incomeTitle) title = formData.incomeTitle;
    if (typeof title === 'string') title = title.trim();
    if (!title) {
        errors.push('Title is required');
    }
    
    return errors;
}

// Amount input handling
function handleAmountInput() {
    const amountInputs = document.querySelectorAll('#amountInput, #amountInputExpense, #incomeAmount, #expenseAmount, input[placeholder="Amount"], input[placeholder="Enter Amount"]');
    amountInputs.forEach(input => {
        if (!input.hasAttribute('data-listener-added')) {
            input.addEventListener('input', function() {
                const value = parseFloat(this.value);
                if (value < 0) {
                    this.value = '';
                } else if (value > 999999999) {
                    this.value = '999999999';
                }
            });
            
            input.addEventListener('blur', function() {
                if (this.value && !isNaN(this.value)) {
                    const formatted = parseFloat(this.value).toFixed(2);
                    this.value = formatted;
                }
            });
            
            input.setAttribute('data-listener-added', 'true');
        }
    });
}

// Search functionality
function initializeSearchFunctionality() {
    const categorySearch = document.getElementById('categorySearch');
    if (categorySearch && !categorySearch.hasAttribute('data-listener-added')) {
        categorySearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const categoryItems = document.querySelectorAll('.category-item');
            categoryItems.forEach(item => {
                const categoryName = item.textContent.toLowerCase();
                item.style.display = categoryName.includes(searchTerm) ? 'block' : 'none';
            });
        });
        categorySearch.setAttribute('data-listener-added', 'true');
    }

    const contactSearch = document.getElementById('contactSearch');
    if (contactSearch && !contactSearch.hasAttribute('data-listener-added')) {
        contactSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const contactItems = document.querySelectorAll('.contact-item');
            contactItems.forEach(item => {
                const nameElement = item.querySelector('.fw-semibold');
                const emailElement = item.querySelector('.text-muted');
                const contactName = nameElement ? nameElement.textContent.toLowerCase() : '';
                const contactEmail = emailElement ? emailElement.textContent.toLowerCase() : '';
                const matches = contactName.includes(searchTerm) || contactEmail.includes(searchTerm);
                item.style.display = matches ? 'flex' : 'none';
            });
        });
        contactSearch.setAttribute('data-listener-added', 'true');
    }
}

// Loan calculation
function initializeLoanCalculation() {
    const principalInput = document.getElementById('principalAmount');
    if (principalInput) {
        principalInput.addEventListener('input', function() {
            const principal = parseFloat(this.value) || 0;
            const rate = parseFloat(document.getElementById('defaultRate')?.value) || 0;
            const duration = parseFloat(document.getElementById('defaultDuration')?.value) || 0;
            
            // Simple interest calculation
            const interest = (principal * rate * duration) / 100;
            const repayment = principal + interest;
            
            const repaymentDisplay = document.getElementById('repaymentDisplay');
            if (repaymentDisplay) {
                repaymentDisplay.textContent = repayment.toFixed(2);
            }
        });
    }
}

// Initialize original dropdown texts
function initializeOriginalTexts() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        if (!dropdown.getAttribute('data-original-text')) {
            dropdown.setAttribute('data-original-text', dropdown.textContent.trim());
        }
    });
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing financial management system...');
    
    try {
        setDefaultDates();
        initializeOriginalTexts();
        initializeDropdowns();
        handleAmountInput();
        initializeSearchFunctionality();
        initializeLoanCalculation();
        loadInitialData();
        
        console.log('Financial management system initialized successfully');
    } catch (error) {
        console.error('Error initializing system:', error);
    }
    
    // Delayed initialization for dynamic content
    setTimeout(() => {
        try {
            initializeDropdowns();
            handleAmountInput();
            initializeSearchFunctionality();
        } catch (error) {
            console.error('Error in delayed initialization:', error);
        }
    }, 500);
});

// Global error handler
window.addEventListener('error', function(event) {
    console.error('JavaScript error:', event.error);
});

// Debug function
window.debugFinancialSystem = function() {
    const elements = {
        incomeForm: document.getElementById('incomeForm'),
        expenseForm: document.getElementById('expenseForm'),
        transferForm: document.getElementById('transferForm'),
        attachmentArea: document.getElementById('attachmentArea'),
        attachmentAreaExpense: document.getElementById('attachment-Area'),
        recurringIncomeLink: document.querySelector('.incomeRec'),
        incomeReminderLink: document.querySelector('.incomeRem'),
        loanLink: document.querySelector('.loan'),
        recurringExpenseLink: document.querySelector('.recExp'),
        expenseReminderLink: document.querySelector('.expRem')
    };
    
    console.log('System elements status:', elements);
    return elements;
};

// File handling for expense attachments
if (attachmentAreaExpense && fileInputExpense) {
    attachmentAreaExpense.addEventListener('dragover', function(event) {
        event.preventDefault();
        attachmentAreaExpense.classList.add('bg-light');
    });

    attachmentAreaExpense.addEventListener('dragleave', function() {
        attachmentAreaExpense.classList.remove('bg-light');
    });

    attachmentAreaExpense.addEventListener('drop', function(event) {
        event.preventDefault();
        const files = event.dataTransfer.files;
        handleFilesExpense(files);
    });

    fileInputExpense.addEventListener('change', function() {
        const files = fileInputExpense.files;
        handleFilesExpense(files);
    });

    function handleFilesExpense(files) {
        attachmentAreaExpense.innerHTML = '';
        if (files.length > 0) {
            Array.from(files).forEach(function(file) {
                const fileElement = document.createElement('div');
                fileElement.className = 'file-item d-flex align-items-center justify-content-between p-2 mb-2 bg-light rounded';
                fileElement.innerHTML = `
                    <span><i class="bx bx-file me-2"></i>${file.name}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(this)">
                        <i class="bx bx-x"></i>
                    </button>
                `;
                attachmentAreaExpense.appendChild(fileElement);
            });
        } else {
            resetAttachmentArea(attachmentAreaExpense, 'attachment-Area');
        }
    }

    attachmentAreaExpense.addEventListener('click', function() {
        if (!attachmentAreaExpense.querySelector('.file-item')) {
            fileInputExpense.click();
        }
    });
}

// Remove file function
window.removeFile = function(button) {
    button.parentElement.remove();
    const container = button.closest('#attachmentArea, #attachment-Area');
    if (container && !container.querySelector('.file-item')) {
        resetAttachmentArea(container, container.id);
    }
}

function resetAttachmentArea(container, id) {
    container.innerHTML = `
        <i class="bx bx-paperclip text-muted" style="font-size: 1.5rem;"></i>
        <p class="text-muted mb-0 mt-2">Drag & drop files or click to browse</p>
        <input type="file" class="d-none" id="${id === 'attachmentArea' ? 'fileInput' : 'fileInputExpense'}" multiple>
    `;
    
    if (id === 'attachmentArea') {
        const newFileInput = container.querySelector('#fileInput');
        if (newFileInput) {
            newFileInput.addEventListener('change', function() {
                const files = newFileInput.files;
                handleFiles(files);
            });
        }
        container.addEventListener('click', function() {
            if (!container.querySelector('.file-item')) {
                newFileInput.click();
            }
        });
    } else {
        const newFileInput = container.querySelector('#fileInputExpense');
        if (newFileInput) {
            newFileInput.addEventListener('change', function() {
                const files = newFileInput.files;
                handleFilesExpense(files);
            });
        }
        container.addEventListener('click', function() {
            if (!container.querySelector('.file-item')) {
                newFileInput.click();
            }
        });
    }
}

// Recurring Income Section HTML
recurringIncomeSection.innerHTML = `
    <div class="mb-3" style="padding: 15px; background: transparent; border-radius: 10px; border: 1px solid #e9ecef;">
        <div class="row mb-3">
            <div class="col-4">
                <label class="form-label small">Repeat every</label>
                <input type="number" class="form-control" value="1" min="1">
            </div>
            <div class="col-8">
                <label class="form-label small">Period</label>
                <div class="dropdown w-100">
                    <button class="btn btn-outline-secondary dropdown-toggle w-100 text-start" type="button" data-bs-toggle="dropdown">
                        Day(s)
                    </button>
                    <ul class="dropdown-menu w-100">
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Day(s)</a></li>
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Week(s)</a></li>
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Month(s)</a></li>
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Year(s)</a></li>
                    </ul>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-6">
                <label class="form-label small"><i class="bx bx-calendar me-1"></i>From Date</label>
                <input type="date" class="form-control" id="incomeFromDate">
            </div>
            <div class="col-6">
                <label class="form-label small"><i class="bx bx-calendar me-1"></i>To Date</label>
                <input type="date" class="form-control" id="incomeToDate">
            </div>
        </div>
    </div>
`;

// Income Reminder Section HTML
incomeReminderSection.innerHTML = `
    <div class="mb-3" style="padding: 15px; background: transparent; border-radius: 10px; border: 1px solid #e9ecef;">
        <div class="row">
            <div class="col-12">
                <label class="form-label small"><i class="bx bx-calendar me-1"></i>Reminder Date & Time</label>
                <input type="datetime-local" class="form-control" id="incomeReminderDate">
            </div>
        </div>
    </div>
`;

// Recurring Expense Section HTML
recurringExpenseSection.innerHTML = `
    <div class="mb-3" style="padding: 15px; background: transparent; border-radius: 10px; border: 1px solid #e9ecef;">
        <div class="row mb-3">
            <div class="col-4">
                <label class="form-label small">Repeat every</label>
                <input type="number" class="form-control" value="1" min="1">
            </div>
            <div class="col-8">
                <label class="form-label small">Period</label>
                <div class="dropdown w-100">
                    <button class="btn btn-outline-secondary dropdown-toggle w-100 text-start" type="button" data-bs-toggle="dropdown">
                        Month(s)
                    </button>
                    <ul class="dropdown-menu w-100">
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Day(s)</a></li>
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Week(s)</a></li>
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Month(s)</a></li>
                        <li><a class="dropdown-item" href="#" onclick="updateDropdownText(this)">Year(s)</a></li>
                    </ul>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-6">
                <label class="form-label small"><i class="bx bx-calendar me-1"></i>From Date</label>
                <input type="date" class="form-control" id="expenseFromDate">
            </div>
            <div class="col-6">
                <label class="form-label small"><i class="bx bx-calendar me-1"></i>To Date</label>
                <input type="date" class="form-control" id="expenseToDate">
            </div>
        </div>
    </div>
`;

// Expense Reminder Section HTML
expenseReminderSection.innerHTML = `
    <div class="mb-3" style="padding: 15px; background: transparent; border-radius: 10px; border: 1px solid #e9ecef;">
        <div class="row">
            <div class="col-12">
                <label class="form-label small"><i class="bx bx-calendar me-1"></i>Reminder Date & Time</label>
                <input type="datetime-local" class="form-control" id="expenseReminderDate">
            </div>
        </div>
    </div>
`;

// Initialize sections as hidden
recurringIncomeSection.style.display = 'none';
incomeReminderSection.style.display = 'none';
loanSection.style.display = 'none';
recurringExpenseSection.style.display = 'none';
expenseReminderSection.style.display = 'none';

// Insert sections into DOM
if (incomeRecordButton) {
    incomeRecordButton.parentNode.insertBefore(incomeReminderSection, incomeRecordButton);
    incomeRecordButton.parentNode.insertBefore(recurringIncomeSection, incomeRecordButton);
}

if (expenseRecordButton) {
    expenseRecordButton.parentNode.insertBefore(expenseReminderSection, expenseRecordButton);
    expenseRecordButton.parentNode.insertBefore(recurringExpenseSection, expenseRecordButton);
    expenseRecordButton.parentNode.insertBefore(loanSection, expenseRecordButton);
}

// Event Listeners for Income Links
if (recurringIncomeLink) {
    recurringIncomeLink.addEventListener('click', function(event) {
        event.preventDefault();
        toggleSection(recurringIncomeSection, this);
    });
}

if (incomeReminderLink) {
    incomeReminderLink.addEventListener('click', function(event) {
        event.preventDefault();
        toggleSection(incomeReminderSection, this);
        
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(9, 0, 0, 0);
        const reminderInput = document.getElementById('incomeReminderDate');
        if (reminderInput) {
            reminderInput.value = tomorrow.toISOString().slice(0, 16);
        }
    });
}

// Event Listeners for Expense Links
if (loanLink) {
    loanLink.addEventListener('click', function(event) {
        event.preventDefault();
        const loanOffcanvas = document.getElementById('offcanvasLoan');
        if (loanOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
            const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(loanOffcanvas);
            bsOffcanvas.show();
        }
        const nextMonth = new Date();
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        const loanDateInput = document.getElementById('loanDueDate');
        if (loanDateInput) {
            loanDateInput.value = nextMonth.toISOString().slice(0, 10);
        }
    });
}

if (recurringExpenseLink) {
    recurringExpenseLink.addEventListener('click', function(event) {
        event.preventDefault();
        toggleSection(recurringExpenseSection, this);
    });
}

if (expenseReminderLink) {
    expenseReminderLink.addEventListener('click', function(event) {
        event.preventDefault();
        toggleSection(expenseReminderSection, this);
        
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(9, 0, 0, 0);
        const expenseReminderInput = document.getElementById('expenseReminderDate');
        if (expenseReminderInput) {
            expenseReminderInput.value = tomorrow.toISOString().slice(0, 16);
        }
    });
}

// Toggle section visibility function
function toggleSection(section, link) {
    if (section.style.display === 'none' || section.style.display === '') {
        section.style.display = 'block';
        link.classList.add('text-primary', 'fw-bold');
        const originalText = link.textContent.replace(/✓ /, '').replace(/^.*bx-check-circle.*?> /, '');
        link.innerHTML = `<i class="bx bx-check-circle me-1"></i>${originalText}`;
    } else {
        section.style.display = 'none';
        link.classList.remove('text-primary', 'fw-bold');
        const originalText = link.textContent.replace(/✓ /, '');
        link.innerHTML = originalText;
    }
}

// Dropdown text update function
window.updateDropdownText = function(element) {
    const dropdownButton = element.closest('.dropdown').querySelector('.dropdown-toggle');
    if (dropdownButton) {
        dropdownButton.textContent = element.textContent;
    }
    
    if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
        const dropdown = bootstrap.Dropdown.getInstance(dropdownButton);
        if (dropdown) {
            dropdown.hide();
        }
    }
}

// Global dropdown handler
document.addEventListener('click', function(event) {
    if (event.target.matches('.dropdown-item') && !event.target.closest('.file-item')) {
        const dropdownButton = event.target.closest('.dropdown').querySelector('.dropdown-toggle');
        if (dropdownButton && !event.target.getAttribute('href')) {
            event.preventDefault();
            dropdownButton.textContent = event.target.textContent;
            
            if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                const dropdown = bootstrap.Dropdown.getInstance(dropdownButton);
                if (dropdown) {
                    dropdown.hide();
                }
            }
        }
    }
});

// Income Form Submission with Backend Integration
if (document.getElementById('incomeForm')) {
    document.getElementById('incomeForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Show loading state
        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Recording...';
        
        try {
            let amountInput = document.getElementById('amountInput');
            if (!amountInput) amountInput = document.getElementById('incomeAmount');
            if (!amountInput) amountInput = document.querySelector('input[placeholder="Amount"]');
            
            const titleInput = this.querySelector('input[placeholder="Title"]');
            const categoryButton = document.getElementById('categoryDropdown');
            const descriptionTextarea = this.querySelector('textarea[placeholder="Description"]');
            const contactInput = this.querySelector('input[type="text"]:not([placeholder="Title"])');
            const branchButton = document.getElementById('branchDropdown');
            const paymentMethodButtons = this.querySelectorAll('.dropdown .btn.text-success');
            
            const incomeData = {
                amount: amountInput ? parseFloat(amountInput.value) : 0,
                title: titleInput ? titleInput.value : '',
                category: categoryButton ? categoryButton.textContent.trim() : '',
                description: descriptionTextarea ? descriptionTextarea.value : '',
                contact: contactInput ? contactInput.value : '',
                branch: branchButton ? branchButton.textContent.trim() : '',
                paymentMethod: paymentMethodButtons.length > 0 ? paymentMethodButtons[0].textContent.trim() : '',
                currency: paymentMethodButtons.length > 1 ? paymentMethodButtons[1].textContent.trim() : 'USD',
                isRecurring: recurringIncomeSection.style.display === 'block',
                hasReminder: incomeReminderSection.style.display === 'block',
                createdAt: new Date().toISOString()
            };
            
            const errors = validateForm(incomeData);
            if (errors.length > 0) {
                throw new Error(errors.join('<br>'));
            }
            
            // Add recurring settings if applicable
            if (incomeData.isRecurring) {
                const repeatInput = recurringIncomeSection.querySelector('input[type="number"]');
                const periodButton = recurringIncomeSection.querySelector('.dropdown-toggle');
                const fromDateInput = document.getElementById('incomeFromDate');
                const toDateInput = document.getElementById('incomeToDate');
                
                incomeData.recurringSettings = {
                    repeatEvery: repeatInput ? parseInt(repeatInput.value) : 1,
                    period: periodButton ? periodButton.textContent.trim() : 'Day(s)',
                    fromDate: fromDateInput ? fromDateInput.value : '',
                    toDate: toDateInput ? toDateInput.value : ''
                };
            }
            
            // Add reminder settings if applicable
            if (incomeData.hasReminder) {
                const reminderDateInput = document.getElementById('incomeReminderDate');
                incomeData.reminderDate = reminderDateInput ? reminderDateInput.value : '';
            }
            
            // Handle file attachments
            const formData = new FormData();
            
            // Add all income data
            Object.keys(incomeData).forEach(key => {
                if (key !== 'files') {
                    if (typeof incomeData[key] === 'object') {
                        formData.append(key, JSON.stringify(incomeData[key]));
                    } else {
                        formData.append(key, incomeData[key]);
                    }
                }
            });
            
            // Add files if any
            if (fileInput && fileInput.files.length > 0) {
                Array.from(fileInput.files).forEach((file, index) => {
                    formData.append(`attachments`, file);
                });
            }
            
            // Send to backend
            const response = await apiCall(API_ENDPOINTS.income, 'POST', formData);
            
            console.log('Income recorded:', response);
            
            Swal.fire({
                icon: 'success',
                title: 'Income recorded successfully!',
                text: `Transaction ID: ${response.id || 'N/A'}`,
                confirmButtonColor: '#009788'
            });
            
            // Reset form
            this.reset();
            if (attachmentArea) resetAttachmentArea(attachmentArea, 'attachmentArea');
            recurringIncomeSection.style.display = 'none';
            incomeReminderSection.style.display = 'none';
            resetToggleLinks();
            
        } catch (error) {
            console.error('Error recording income:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error recording income',
                html: error.message || 'An unexpected error occurred',
                confirmButtonColor: '#009788'
            });
        } finally {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    });
}

// Expense Form Submission with Backend Integration
if (document.getElementById('expenseForm')) {
    document.getElementById('expenseForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Show loading state
        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Recording...';
        
        try {
            let amountInput = document.getElementById('amountInputExpense');
            if (!amountInput) amountInput = document.getElementById('expenseAmount');
            if (!amountInput) amountInput = document.querySelector('#expenseForm input[placeholder="Amount"]');
            
            const titleInput = this.querySelector('input[placeholder="Title"]');
            const categoryButtons = this.querySelectorAll('.btn.btn-outline-secondary.dropdown-toggle');
            const descriptionTextarea = this.querySelector('textarea[placeholder="Description"]');
            const contactInput = this.querySelector('input[type="text"]:not([placeholder="Title"])');
            const branchButton = categoryButtons.length > 1 ? categoryButtons[1] : null;
            const paymentMethodButtons = this.querySelectorAll('.dropdown .btn.text-danger');
            
            const expenseData = {
                amount: amountInput ? parseFloat(amountInput.value) : 0,
                title: titleInput ? titleInput.value : '',
                category: categoryButtons.length > 0 ? categoryButtons[0].textContent.trim() : '',
                description: descriptionTextarea ? descriptionTextarea.value : '',
                contact: contactInput ? contactInput.value : '',
                branch: branchButton ? branchButton.textContent.trim() : '',
                paymentMethod: paymentMethodButtons.length > 0 ? paymentMethodButtons[0].textContent.trim() : '',
                currency: paymentMethodButtons.length > 1 ? paymentMethodButtons[1].textContent.trim() : 'USD',
                isLoan: loanSection.style.display === 'block',
                isRecurring: recurringExpenseSection.style.display === 'block',
                hasReminder: expenseReminderSection.style.display === 'block',
                createdAt: new Date().toISOString()
            };
            
            const errors = validateForm(expenseData);
            if (errors.length > 0) {
                throw new Error(errors.join('<br>'));
            }
            
            // Add loan details if applicable
            if (expenseData.isLoan) {
                const interestRateInput = loanSection.querySelector('input[type="number"]');
                const loanTermButton = loanSection.querySelector('.dropdown-toggle');
                const dueDateInput = document.getElementById('loanDueDate');
                
                expenseData.loanDetails = {
                    interestRate: interestRateInput ? parseFloat(interestRateInput.value) : 0,
                    loanTerm: loanTermButton ? loanTermButton.textContent.trim() : 'Month(s)',
                    dueDate: dueDateInput ? dueDateInput.value : ''
                };
            }
            
            // Add recurring settings if applicable
            if (expenseData.isRecurring) {
                const repeatInput = recurringExpenseSection.querySelector('input[type="number"]');
                const periodButton = recurringExpenseSection.querySelector('.dropdown-toggle');
                const fromDateInput = document.getElementById('expenseFromDate');
                const toDateInput = document.getElementById('expenseToDate');
                
                expenseData.recurringSettings = {
                    repeatEvery: repeatInput ? parseInt(repeatInput.value) : 1,
                    period: periodButton ? periodButton.textContent.trim() : 'Month(s)',
                    fromDate: fromDateInput ? fromDateInput.value : '',
                    toDate: toDateInput ? toDateInput.value : ''
                };
            }
            
            // Add reminder settings if applicable
            if (expenseData.hasReminder) {
                const reminderDateInput = document.getElementById('expenseReminderDate');
                expenseData.reminderDate = reminderDateInput ? reminderDateInput.value : '';
            }
            
            // Handle file attachments
            const formData = new FormData();
            
            // Add all expense data
            Object.keys(expenseData).forEach(key => {
                if (key !== 'files') {
                    if (typeof expenseData[key] === 'object') {
                        formData.append(key, JSON.stringify(expenseData[key]));
                    } else {
                        formData.append(key, expenseData[key]);
                    }
                }
            });
            
            // Add files if any
            if (fileInputExpense && fileInputExpense.files.length > 0) {
                Array.from(fileInputExpense.files).forEach((file, index) => {
                    formData.append(`attachments`, file);
                });
            }
            
            // Send to backend
            const response = await apiCall(API_ENDPOINTS.expense, 'POST', formData);
            
            console.log('Expense recorded:', response);
            
            Swal.fire({
                icon: 'success',
                title: 'Expense recorded successfully!',
                text: `Transaction ID: ${response.id || 'N/A'}`,
                confirmButtonColor: '#e57373'
            });
            
            // Reset form
            this.reset();
            if (attachmentAreaExpense) resetAttachmentArea(attachmentAreaExpense, 'attachment-Area');
            loanSection.style.display = 'none';
            recurringExpenseSection.style.display = 'none';
            expenseReminderSection.style.display = 'none';
            resetToggleLinks();
            
        } catch (error) {
            console.error('Error recording expense:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error recording expense',
                html: error.message || 'An unexpected error occurred',
                confirmButtonColor: '#e57373'
            });
        } finally {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    });
}

// Transfer Form Submission with Backend Integration
if (document.getElementById('transferForm')) {
    document.getElementById('transferForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Show loading state
        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        
        try {
            const amountInput = this.querySelector('input[placeholder="Enter Amount"]');
            const dropdownButtons = this.querySelectorAll('.dropdown-toggle');
            
            const transferData = {
                amount: amountInput ? parseFloat(amountInput.value) : 0,
                fromBranch: dropdownButtons.length > 0 ? dropdownButtons[0].textContent.trim() : '',
                fromAccount: dropdownButtons.length > 1 ? dropdownButtons[1].textContent.trim() : '',
                toAccount: dropdownButtons.length > 2 ? dropdownButtons[2].textContent.trim() : '',
                toUser: dropdownButtons.length > 3 ? dropdownButtons[3].textContent.trim() : '',
                createdAt: new Date().toISOString()
            };
        }
        catch {}
    });
}
document.addEventListener('DOMContentLoaded', function() {
    // Handle dropdown item clicks
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            const siblings = this.parentElement.parentElement.querySelectorAll('.dropdown-item');
            siblings.forEach(sibling => sibling.classList.remove('active'));
            this.classList.add('active');
            
            const dropdown = this.closest('.dropdown');
            const button = dropdown.querySelector('.dropdown-toggle');
            const filterType = this.getAttribute('data-filter');
            const filterValue = this.getAttribute('data-value');
            
            console.log(`Filter applied: ${filterType} = ${filterValue}`);
            
        });
    });

    document.getElementById('search').addEventListener('click', function() {
        console.log('Search clicked');
    });
});

function filterTable(filterType, filterValue) {
    const tbody = document.getElementById('transaction-tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
    });
}