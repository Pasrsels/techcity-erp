class PurchaseOrderManager {
    constructor() {
        this.items = [];
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        // Form Elements
        this.productSelect = document.getElementById('id_product');
        this.supplierSelect = document.getElementById('id_supplier');
        this.priceInput = document.getElementById('id_p_price');
        this.quantityInput = document.getElementById('id_p_quantity');
        this.taxSelect = document.getElementById('id_tax');
        
        // Cart Elements
        this.cartItemsBody = document.getElementById('cart-items');
        this.subtotalElement = document.getElementById('subtotal');
        this.discountInput = document.getElementById('id_discount');
        this.taxElement = document.getElementById('tax');
        this.totalElement = document.getElementById('id_total');
        
        // Buttons
        this.addToCartButton = document.getElementById('id_add_to_cart');
        this.nextButton = document.getElementById('next_button');
    }

    bindEvents() {
        this.addToCartButton.addEventListener('click', () => this.addItemToCart());
        this.nextButton.addEventListener('click', () => this.proceedToNextStep());
        this.discountInput.addEventListener('input', () => this.calculateTotals());
        
        // Delegate event for dynamically added remove buttons
        this.cartItemsBody.addEventListener('click', (event) => {
            if (event.target.classList.contains('remove-item')) {
                this.removeItemFromCart(event.target.closest('tr'));
            }
        });
    }

    addItemToCart() {
        // Validate inputs
        if (!this.validateInputs()) return;

        const item = {
            productId: this.productSelect.value,
            productName: this.productSelect.options[this.productSelect.selectedIndex].text,
            supplierId: this.supplierSelect.value,
            supplierName: this.supplierSelect.options[this.supplierSelect.selectedIndex].text,
            unitPrice: parseFloat(this.priceInput.value),
            quantity: parseInt(this.quantityInput.value),
            tax: parseFloat(this.taxSelect.value)
        };

        // Check if product already exists in cart
        const existingItemIndex = this.items.findIndex(
            i => i.productId === item.productId && i.supplierId === item.supplierId
        );

        if (existingItemIndex !== -1) {
            // Update existing item
            this.items[existingItemIndex].quantity += item.quantity;
        } else {
            // Add new item
            this.items.push(item);
        }

        this.renderCartItems();
        this.calculateTotals();
        this.clearInputs();
    }

    renderCartItems() {
        this.cartItemsBody.innerHTML = this.items.map((item, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>
                    <button class="btn btn-sm btn-danger remove-item">
                        <i class="bx bx-trash"></i>
                    </button>
                </td>
                <td>${item.productName}</td>
                <td>${item.supplierName}</td>
                <td>${item.quantity}</td>
                <td>${item.unitPrice.toFixed(2)}</td>
                <td class="text-center">${(item.quantity * item.unitPrice).toFixed(2)}</td>
            </tr>
        `).join('');
    }

    removeItemFromCart(row) {
        const index = Array.from(this.cartItemsBody.children).indexOf(row);
        this.items.splice(index, 1);
        this.renderCartItems();
        this.calculateTotals();
    }

    calculateTotals() {
        // Calculate subtotal
        const subtotal = this.items.reduce(
            (total, item) => total + (item.quantity * item.unitPrice), 
            0
        );
        this.subtotalElement.textContent = subtotal.toFixed(2);

        // Calculate tax
        const taxRate = this.taxSelect.value / 100;
        const taxTotal = subtotal * taxRate;
        this.taxElement.textContent = taxTotal.toFixed(2);

        // Calculate discount
        const discount = parseFloat(this.discountInput.value) || 0;

        // Calculate total
        const total = subtotal + taxTotal - discount;
        this.totalElement.textContent = total.toFixed(2);
    }

    validateInputs() {
        const errors = [];

        if (!this.productSelect.value) errors.push('Please select a product');
        if (!this.supplierSelect.value) errors.push('Please select a supplier');
        if (!this.priceInput.value || parseFloat(this.priceInput.value) <= 0) errors.push('Invalid price');
        if (!this.quantityInput.value || parseInt(this.quantityInput.value) <= 0) errors.push('Invalid quantity');

        const errorContainer = document.getElementById('cart_error');
        if (errors.length) {
            errorContainer.textContent = errors.join(', ');
            return false;
        }
        
        errorContainer.textContent = '';
        return true;
    }

    clearInputs() {
        this.productSelect.selectedIndex = 0;
        this.supplierSelect.selectedIndex = 0;
        this.priceInput.value = '';
        this.quantityInput.value = '';
        this.taxSelect.selectedIndex = 0;
    }

    proceedToNextStep() {
        if (this.items.length === 0) {
            alert('Please add items to the purchase order');
            return;
        }

        // Prepare data for backend
        const purchaseOrderData = {
            items: this.items.map(item => ({
                product_id: item.productId,
                supplier_id: item.supplierId,
                quantity: item.quantity,
                unit_price: item.unitPrice,
                tax: item.tax
            })),
            subtotal: parseFloat(this.subtotalElement.textContent),
            tax: parseFloat(this.taxElement.textContent),
            total: parseFloat(this.totalElement.textContent)
        };

        // Send to backend
        this.sendPurchaseOrder(purchaseOrderData);
    }

    async sendPurchaseOrder(data) {
        try {
            const response = await fetch('/purchase-order/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                const result = await response.json();
                this.showSuccessModal(result.purchase_order_id);
            } else {
                throw new Error('Failed to create purchase order');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to create purchase order');
        }
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    showSuccessModal(purchaseOrderId) {
        const modal = new bootstrap.Modal(document.getElementById('poSuccessModal'));
        modal.show();
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    new PurchaseOrderManager();
});