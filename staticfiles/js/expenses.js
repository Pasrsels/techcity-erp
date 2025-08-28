let tableRows = document.querySelectorAll('#expense_table tbody, tr');
        let runningBalance = 0;
        new DataTable('#expense_table')

        $(document).ready(function() {
            calculateTotal();

            function calculateTotal() {
                let total = 0;
                $('#expense_table .amount').each(function() {
                    const amount = parseFloat($(this).text().trim().replace(/,/g, ''));
                    if (!isNaN(amount)) {
                        total += amount;
                    }
                });
                $('#total').text(total.toFixed(2));
            }
        });

        tableRows.forEach((row, index) => {
            if (index === 0) return;

            let totalAmountCell = document.getElementById('total')
            let amountCell = row.querySelector(".amount");
            
            if (amountCell){
                let amount = parseFloat(amountCell.textContent) || 0;
            }else{
                amount = 0;
            }
            runningBalance = runningBalance + amount;
            
            totalAmountCell.textContent = runningBalance.toFixed(2);
        });

        function updateExpenseStatus(expenseId) {
            const checkbox = document.querySelector(`input[onchange="updateExpenseStatus(${expenseId})"]`);
            const status = checkbox.checked;

            fetch(`/finance/update_expense_status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({id: expenseId, status: status}),
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    Swal.fire({
                        title: 'Error!',
                        text: data.message,
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                }
            })
            .catch(error => {
                Swal.fire({
                    title: 'Error!',
                    text: 'An error occurred while updating the status.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            });
        }

        const addModal = new bootstrap.Modal(document.getElementById('AddExpenseModal'))
        const categoryModal = new bootstrap.Modal(document.getElementById('AddCategoryModal'))

        function categorySubmit(){
        
            const data = {name:$('#id_name').val()}
            console.log(data)
              
            fetch("{% url 'finance:add_expense_category' %}", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "X-CSRFToken": getCookie("csrftoken"), 
                },
                body: JSON.stringify(data),
              })
              .then(response => response.json())
              .then(data => {
                  if (data.success) {
                    fetchCategories()
                    categoryModal.hide()
                    addModal.show()
                  } else {
                    Swal.fire({
                        title: "Error",
                        text: data.message,
                        icon: "error"
                    });
                  }
                })
                .catch((error) => {
                  console.error("Error:", error);
                });
            }
      
        async function fetchCategories(){
            try {
                const response = await fetch('{% url "finance:add_expense_category" %}');
    
                if (!response.ok) {
                    throw new Error('Network response was not ok.');
                }
                const data = await response.json();
                updateCategory(data);
                console.log(data)
            } catch (error) {
                console.error('Error fetching categories:', error);
            } 
        }
    
        fetchCategories()
    
        function updateCategory(data){
            const catElement = document.querySelector('#id_category')
            const editCatElement = document.getElementById('id_e_category')

            while(catElement.options.length > 1){
                catElement.remove(1)
            }
            data.forEach((category)=>{
                catElement.innerHTML += `<option value=${category.id}>${category.name}</option>`
            })

            while(editCatElement.options.length > 1){
                editCatElement.remove(1)
            }
            data.forEach((category)=>{
                editCatElement.innerHTML += `<option value=${category.id}>${category.name}</option>`
            })
        }

    //edit modal data
    function openEditModal(expenseId) {
        const url = `/finance/get_expense/${expenseId}/`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const expense = data.data;
                    document.getElementById('id_e_category').value = expense.category;
                    document.getElementById('id_e_amount').value = expense.amount;
                    document.getElementById('id_e_description').value = expense.description;
                    document.getElementById('saveExpenseBtn').setAttribute('data-expense-id', expense.id);
                    $('#editExpenseModal').modal('show');
                } else {
                    Swal.fire({
                        title: 'Error!',
                        text: data.message,
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                }
            })
            .catch(error => {
                Swal.fire({
                    title: 'Error!',
                    text: 'An error occurred while fetching expense data.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            });
    }

    document.getElementById('saveExpenseBtn').addEventListener('click', function() {
        const expenseId = this.getAttribute('data-expense-id');
        const url = "{% url 'finance:add_or_edit_expense' %}";

        const expenseData = {
            id: expenseId,
            category: document.getElementById('id_e_category').value,
            amount: document.getElementById('id_e_amount').value,
            description: document.getElementById('id_e_description').value,
            currency: document.getElementById('id_currency').value,
            payment_method: document.getElementById('id_payment_method').value
        };

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(expenseData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    title: 'Success!',
                    text: data.message,
                    icon: 'success',
                    confirmButtonText: 'OK'
                }).then((result) => {
                    if (result.isConfirmed) {
                        location.reload();
                    }
                });
            } else {
                Swal.fire({
                    title: 'Error!',
                    text: data.message,
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        })
        .catch(error => {
            Swal.fire({
                title: 'Error!',
                text: 'An error occurred while saving the expense.',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        });
    });

    // submit expenses

    function submitExpenseForm() {
        const category = document.getElementById('id_category').value;
        const amount = document.getElementById('id_amount').value;
        const description = document.getElementById('id_description').value;
        const currency = document.getElementById('id_currency').value;
        const payment_method = document.getElementById('id_payment_method').value;

        const data = {
            category: category,
            amount: amount,
            description: description,
            currency: currency,
            payment_method: payment_method
        };

        console.log(data)

        const url = "{% url 'finance:expenses' %}";

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    title: 'Success!',
                    text: 'Expense successfully saved.',
                    icon: 'success',
                    confirmButtonText: 'OK'
                }).then((result) => {
                    if (result.isConfirmed) {
                        location.reload();
                    }
                });
            } else {
                Swal.fire({
                    title: 'Error!',
                    text: data.message || 'An error occurred while adding the expense category.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        })
        .catch(error => {
            Swal.fire({
                title: 'Error!',
                text: 'An error occurred while processing your request.',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        });
    }

    // delete expense
    function deleteExpense(expenseId) {
        Swal.fire({
            title: 'Are you sure?',
            text: "You want to cancel this expense!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Yes, cancel it!'
        }).then((result) => {
            if (result.isConfirmed) {
                const url = `/finance/delete_expense/${expenseId}/`;

                fetch(url, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({
                            title: 'Deleted!',
                            text: data.message,
                            icon: 'success',
                            confirmButtonText: 'OK'
                        }).then((result) => {
                            if (result.isConfirmed) {
                                location.reload();
                            }
                        });
                    } else {
                        Swal.fire({
                            title: 'Error!',
                            text: data.message,
                            icon: 'error',
                            confirmButtonText: 'OK'
                        });
                    }
                })
                .catch(error => {
                    Swal.fire({
                        title: 'Error!',
                        text: 'An error occurred while deleting the expense.',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                });
            }
        }
    )}
    
    function filterCashBook() {
        const filter = document.getElementById('filterSelect').value;
        window.location.href = `?filter=${filter}`;
    }


    function applyCustomFilter() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        if (startDate && endDate) {
            window.location.href = `?filter=custom&start_date=${startDate}&end_date=${endDate}`;
        } else {
            Swal.fire({
                title: "Error",
                text: "Please select both start and end dates.",
                icon: "error"
            });
        }
    }

    function downloadReport() {
        const filter = document.getElementById('filterSelect').value;
        let url = `?filter=${filter}&download=${true}/`;

        if (filter === 'custom') {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }

        window.location.href = url;
    }

    

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }