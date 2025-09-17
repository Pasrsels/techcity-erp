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

recurringIncomeSection.style.display = 'none';
incomeReminderSection.style.display = 'none';
loanSection.style.display = 'none';
recurringExpenseSection.style.display = 'none';
expenseReminderSection.style.display = 'none';

if (incomeRecordButton) {
    incomeRecordButton.parentNode.insertBefore(incomeReminderSection, incomeRecordButton);
    incomeRecordButton.parentNode.insertBefore(recurringIncomeSection, incomeRecordButton);
}

if (expenseRecordButton) {
    expenseRecordButton.parentNode.insertBefore(expenseReminderSection, expenseRecordButton);
    expenseRecordButton.parentNode.insertBefore(recurringExpenseSection, expenseRecordButton);
    expenseRecordButton.parentNode.insertBefore(loanSection, expenseRecordButton);
}

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

if (loanLink) {
    loanLink.addEventListener('click', function(event) {
        event.preventDefault();
        // Open the loan offcanvas modal
        const loanOffcanvas = document.getElementById('offcanvasLoan');
        if (loanOffcanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
            const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(loanOffcanvas);
            bsOffcanvas.show();
        }
        // Set default due date to next month
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

if (document.getElementById('incomeForm')) {
    document.getElementById('incomeForm').addEventListener('submit', function(event) {
        event.preventDefault();
        
        const amountInput = document.getElementById('amountInput');
        const titleInput = this.querySelector('input[placeholder="Title"]');
        const categoryButton = document.getElementById('categoryDropdown');
        const descriptionTextarea = this.querySelector('textarea[placeholder="Description"]');
        const contactInput = this.querySelector('input[type="text"]:not([placeholder="Title"])');
        const branchButton = document.getElementById('branchDropdown');
        const paymentMethodButtons = this.querySelectorAll('.dropdown .btn.text-success');
        
        const incomeData = {
            amount: amountInput ? amountInput.value : '',
            title: titleInput ? titleInput.value : '',
            category: categoryButton ? categoryButton.textContent.trim() : '',
            description: descriptionTextarea ? descriptionTextarea.value : '',
            contact: contactInput ? contactInput.value : '',
            branch: branchButton ? branchButton.textContent.trim() : '',
            paymentMethod: paymentMethodButtons.length > 0 ? paymentMethodButtons[0].textContent.trim() : '',
            currency: paymentMethodButtons.length > 1 ? paymentMethodButtons[1].textContent.trim() : '',
            isRecurring: recurringIncomeSection.style.display === 'block',
            hasReminder: incomeReminderSection.style.display === 'block',
            files: fileInput ? Array.from(fileInput.files) : []
        };
        
        const errors = validateForm(incomeData);
        if (errors.length > 0) {
            Swal.fire({
                icon: 'error',
                title: 'Validation Error',
                html: errors.join('<br>'),
                confirmButtonColor: '#009788'
            });
            return;
        }
        
        if (incomeData.isRecurring) {
            const repeatInput = recurringIncomeSection.querySelector('input[type="number"]');
            const periodButton = recurringIncomeSection.querySelector('.dropdown-toggle');
            const fromDateInput = document.getElementById('incomeFromDate');
            const toDateInput = document.getElementById('incomeToDate');
            
            incomeData.recurringSettings = {
                repeatEvery: repeatInput ? repeatInput.value : '1',
                period: periodButton ? periodButton.textContent.trim() : 'Day(s)',
                fromDate: fromDateInput ? fromDateInput.value : '',
                toDate: toDateInput ? toDateInput.value : ''
            };
        }
        
        if (incomeData.hasReminder) {
            const reminderDateInput = document.getElementById('incomeReminderDate');
            incomeData.reminderDate = reminderDateInput ? reminderDateInput.value : '';
        }
        
        console.log('Income recorded:', incomeData);
        saveToLocalStorage('income', incomeData);
        
        Swal.fire({
            icon: 'success',
            title: 'Income recorded successfully!',
            confirmButtonColor: '#009788'
        });
        this.reset();
        if (attachmentArea) resetAttachmentArea(attachmentArea, 'attachmentArea');
        recurringIncomeSection.style.display = 'none';
        incomeReminderSection.style.display = 'none';
        
        resetToggleLinks();
    });
}

if (document.getElementById('expenseForm')) {
    document.getElementById('expenseForm').addEventListener('submit', function(event) {
        event.preventDefault();
        
        const amountInput = document.getElementById('amountInputExpense');
        const titleInput = this.querySelector('input[placeholder="Title"]');
        const categoryButtons = this.querySelectorAll('.btn.btn-outline-secondary.dropdown-toggle');
        const descriptionTextarea = this.querySelector('textarea[placeholder="Description"]');
        const contactInput = this.querySelector('input[type="text"]:not([placeholder="Title"])');
        const branchButton = categoryButtons.length > 1 ? categoryButtons[1] : null;
        const paymentMethodButtons = this.querySelectorAll('.dropdown .btn.text-danger');
        
        const expenseData = {
            amount: amountInput ? amountInput.value : '',
            title: titleInput ? titleInput.value : '',
            category: categoryButtons.length > 0 ? categoryButtons[0].textContent.trim() : '',
            description: descriptionTextarea ? descriptionTextarea.value : '',
            contact: contactInput ? contactInput.value : '',
            branch: branchButton ? branchButton.textContent.trim() : '',
            paymentMethod: paymentMethodButtons.length > 0 ? paymentMethodButtons[0].textContent.trim() : '',
            currency: paymentMethodButtons.length > 1 ? paymentMethodButtons[1].textContent.trim() : '',
            isLoan: loanSection.style.display === 'block',
            isRecurring: recurringExpenseSection.style.display === 'block',
            hasReminder: expenseReminderSection.style.display === 'block',
            files: fileInputExpense ? Array.from(fileInputExpense.files) : []
        };
        
        const errors = validateForm(expenseData);
        if (errors.length > 0) {
            Swal.fire({
                icon: 'error',
                title: 'Validation Error',
                html: errors.join('<br>'),
                confirmButtonColor: '#e57373'
            });
            return;
        }
        
        if (expenseData.isLoan) {
            const interestRateInput = loanSection.querySelector('input[type="number"]');
            const loanTermButton = loanSection.querySelector('.dropdown-toggle');
            const dueDateInput = document.getElementById('loanDueDate');
            
            expenseData.loanDetails = {
                interestRate: interestRateInput ? interestRateInput.value : '',
                loanTerm: loanTermButton ? loanTermButton.textContent.trim() : 'Month(s)',
                dueDate: dueDateInput ? dueDateInput.value : ''
            };
        }
        
        if (expenseData.isRecurring) {
            const repeatInput = recurringExpenseSection.querySelector('input[type="number"]');
            const periodButton = recurringExpenseSection.querySelector('.dropdown-toggle');
            const fromDateInput = document.getElementById('expenseFromDate');
            const toDateInput = document.getElementById('expenseToDate');
            
            expenseData.recurringSettings = {
                repeatEvery: repeatInput ? repeatInput.value : '1',
                period: periodButton ? periodButton.textContent.trim() : 'Month(s)',
                fromDate: fromDateInput ? fromDateInput.value : '',
                toDate: toDateInput ? toDateInput.value : ''
            };
        }
        
        if (expenseData.hasReminder) {
            const reminderDateInput = document.getElementById('expenseReminderDate');
            expenseData.reminderDate = reminderDateInput ? reminderDateInput.value : '';
        }
        
        console.log('Expense recorded:', expenseData);
        saveToLocalStorage('expense', expenseData);
        
        Swal.fire({
            icon: 'success',
            title: 'Expense recorded successfully!',
            confirmButtonColor: '#e57373'
        });
        this.reset();
        if (attachmentAreaExpense) resetAttachmentArea(attachmentAreaExpense, 'attachment-Area');
        loanSection.style.display = 'none';
        recurringExpenseSection.style.display = 'none';
        expenseReminderSection.style.display = 'none';
        
        resetToggleLinks();
    });
}

if (document.getElementById('transferForm')) {
    document.getElementById('transferForm').addEventListener('submit', function(event) {
        event.preventDefault();
        
        const amountInput = this.querySelector('input[placeholder="Enter Amount"]');
        const dropdownButtons = this.querySelectorAll('.dropdown-toggle');
        
        const transferData = {
            amount: amountInput ? amountInput.value : '',
            fromBranch: dropdownButtons.length > 0 ? dropdownButtons[0].textContent.trim() : '',
            fromAccount: dropdownButtons.length > 1 ? dropdownButtons[1].textContent.trim() : '',
            toAccount: dropdownButtons.length > 2 ? dropdownButtons[2].textContent.trim() : '',
            toUser: dropdownButtons.length > 3 ? dropdownButtons[3].textContent.trim() : ''
        };
        
        if (!transferData.amount || parseFloat(transferData.amount) <= 0) {
            Swal.fire({
                icon: 'error',
                title: 'Please enter a valid transfer amount',
                confirmButtonColor: '#009788'
            });
            return;
        }
        
        console.log('Transfer submitted:', transferData);
        saveToLocalStorage('transfer', transferData);
        
        Swal.fire({
            icon: 'success',
            title: 'Transfer completed successfully!',
            confirmButtonColor: '#009788'
        });
        this.reset();
        resetDropdowns();
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const transferBtn = document.querySelector('[data-bs-target="#offcanvasTransfer"]');
    const transferCanvas = document.getElementById('offcanvasTransfer');
    if (transferBtn && transferCanvas && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
        transferBtn.addEventListener('click', function(e) {
            try {
                const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(transferCanvas);
                offcanvas.show();
                console.log('DEBUG: Transfer offcanvas forced to show.');
            } catch (err) {
                console.error('DEBUG: Error showing transfer offcanvas:', err);
            }
        });
    } else {
        console.warn('DEBUG: Transfer button or canvas not found, or Bootstrap not loaded.');
    }
});
setDefaultDates();
initializeDropdowns();
initializeCategories();

function resetDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        const defaultText = dropdown.getAttribute('data-default-text');
        if (defaultText) {
            dropdown.textContent = defaultText;
        }
    });
}

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

function initializeCategories() {
    const categoryDropdowns = document.querySelectorAll('#categoryDropdown');
    categoryDropdowns.forEach(dropdown => {
        const addCategoryItem = dropdown.parentElement.querySelector('.dropdown-menu li:last-child a');
        if (addCategoryItem && addCategoryItem.querySelector('i.bx-plus') && !addCategoryItem.hasAttribute('data-listener-added')) {
            addCategoryItem.addEventListener('click', function(e) {
                e.preventDefault();
                const categoryName = prompt('Enter new category name:');
                if (categoryName && categoryName.trim()) {
                    const newCategoryItem = document.createElement('li');
                    newCategoryItem.innerHTML = `<a class="dropdown-item" href="#">${categoryName.trim()}</a>`;
                    this.parentElement.parentElement.insertBefore(newCategoryItem, this.parentElement.previousElementSibling);
                    dropdown.textContent = categoryName.trim();
                    
                    newCategoryItem.querySelector('a').addEventListener('click', function(e) {
                        e.preventDefault();
                        dropdown.textContent = this.textContent;
                        
                        if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                            const dropdownInstance = bootstrap.Dropdown.getInstance(dropdown);
                            if (dropdownInstance) {
                                dropdownInstance.hide();
                            }
                        }
                    });
                }
            });
            addCategoryItem.setAttribute('data-listener-added', 'true');
        }
    });
}

function formatCurrency(amount, currency = 'USD') {
    const numAmount = parseFloat(amount) || 0;
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    }).format(numAmount);
}

function validateForm(formData) {
    const errors = [];
    
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
        errors.push('Amount must be greater than 0');
    }
    
    if (!formData.title || formData.title.trim() === '') {
        errors.push('Title is required');
    }
    
    return errors;
}

function resetDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        const originalText = dropdown.getAttribute('data-original-text');
        if (originalText) {
            dropdown.textContent = originalText;
        } else {
            const text = dropdown.textContent;
            if (text.includes('CASH')) dropdown.textContent = 'CASH';
            else if (text.includes('USD')) dropdown.textContent = 'USD';
            else if (text.includes('Branch')) dropdown.textContent = 'Branch';
            else if (text.includes('Select')) {
                const parts = text.split(' ');
                if (parts.length >= 2) {
                    dropdown.textContent = parts[0] + ' ' + parts[1];
                }
            }
            else if (text.includes('category')) dropdown.textContent = 'Select or add category';
            else if (text.includes('User Account')) dropdown.textContent = 'User Account';
        }
    });
}

function initializeOriginalTexts() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        if (!dropdown.getAttribute('data-original-text')) {
            dropdown.setAttribute('data-original-text', dropdown.textContent.trim());
        }
    });
}

function handleAmountInput() {
    const amountInputs = document.querySelectorAll('#amountInput, #amountInputExpense, input[placeholder="Enter Amount"]');
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

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing financial management system...');
    
    try {
        setDefaultDates();
        initializeOriginalTexts();
        initializeDropdowns();
        initializeCategories();
        handleAmountInput();
        initializeSearchFunctionality();
        
        console.log('Financial management system initialized successfully');
    } catch (error) {
        console.error('Error initializing system:', error);
    }
    
    setTimeout(() => {
        try {
            initializeDropdowns();
            initializeCategories();
            handleAmountInput();
            initializeSearchFunctionality();
        } catch (error) {
            console.error('Error in delayed initialization:', error);
        }
    }, 500);
});

document.addEventListener('click', function(event) {
    if (event.target.matches('.dropdown-item:not([data-listener-added])')) {
        const dropdown = event.target.closest('.dropdown');
        const button = dropdown ? dropdown.querySelector('.dropdown-toggle') : null;
        
        if (button && !event.target.querySelector('i.bx-plus')) {
            event.preventDefault();
            button.textContent = event.target.textContent;
            
            if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                const dropdownInstance = bootstrap.Dropdown.getInstance(button);
                if (dropdownInstance) {
                    dropdownInstance.hide();
                }
            }
        }
        
        event.target.setAttribute('data-listener-added', 'true');
    }
});

window.addEventListener('error', function(event) {
    console.error('JavaScript error:', event.error);
});

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

 document.getElementById('principalAmount').addEventListener('input', function() {
            const principal = parseFloat(this.value) || 0;
            const rate = parseFloat(document.getElementById('defaultRate').value) || 0;
            const duration = parseFloat(document.getElementById('defaultDuration').value) || 0;
            
            // Simple flat rate calculation
            const repayment = principal + (principal * rate / 100 * duration / 12);
            document.getElementById('repaymentDisplay').textContent = repayment.toFixed(2);
        });