// Calculator functionality for amount fields
document.addEventListener('DOMContentLoaded', function() {
    // Find all amount input fields
    const amountInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    
    amountInputs.forEach(input => {
        // Create calculator container
        const container = document.createElement('div');
        container.className = 'calculator-container';
        
        // Create calculator button
        const calcBtn = document.createElement('button');
        calcBtn.type = 'button';
        calcBtn.className = 'calculator-btn';
        calcBtn.innerHTML = '<i class="bx bx-calculator"></i>';
        
        // Create calculator popup
        const calcPopup = document.createElement('div');
        calcPopup.className = 'calculator-popup';
        calcPopup.innerHTML = `
            <div class="calculator-display">0</div>
            <div class="calculator-buttons">
                <button type="button">7</button>
                <button type="button">8</button>
                <button type="button">9</button>
                <button type="button">÷</button>
                <button type="button">4</button>
                <button type="button">5</button>
                <button type="button">6</button>
                <button type="button">×</button>
                <button type="button">1</button>
                <button type="button">2</button>
                <button type="button">3</button>
                <button type="button">-</button>
                <button type="button">0</button>
                <button type="button">.</button>
                <button type="button">=</button>
                <button type="button">+</button>
            </div>
        `;
        
        // Wrap input in container
        input.parentNode.insertBefore(container, input);
        container.appendChild(input);
        container.appendChild(calcBtn);
        container.appendChild(calcPopup);
        
        // Initialize calculator
        initializeCalculator(calcPopup, input);
    });
});

function initializeCalculator(calculator, inputField) {
    const display = calculator.querySelector('.calculator-display');
    const buttons = calculator.querySelectorAll('.calculator-buttons button');
    let currentValue = '0';
    let previousValue = null;
    let operation = null;

    // Toggle calculator visibility
    calculator.parentElement.querySelector('.calculator-btn').addEventListener('click', () => {
        calculator.classList.toggle('show');
    });

    // Close calculator when clicking outside
    document.addEventListener('click', (e) => {
        if (!calculator.contains(e.target) && !e.target.classList.contains('calculator-btn')) {
            calculator.classList.remove('show');
        }
    });

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const value = button.textContent;

            if (value >= '0' && value <= '9' || value === '.') {
                if (currentValue === '0' && value !== '.') {
                    currentValue = value;
                } else {
                    currentValue += value;
                }
            } else if (value === '=') {
                if (previousValue !== null && operation !== null) {
                    currentValue = calculate(previousValue, currentValue, operation);
                    previousValue = null;
                    operation = null;
                }
            } else {
                if (previousValue === null) {
                    previousValue = currentValue;
                    currentValue = '0';
                } else {
                    currentValue = calculate(previousValue, currentValue, operation);
                    previousValue = currentValue;
                    currentValue = '0';
                }
                operation = value;
            }

            display.textContent = currentValue;
            inputField.value = currentValue;
            
            // Trigger input event to update any dependent calculations
            inputField.dispatchEvent(new Event('input', { bubbles: true }));
        });
    });
}

function calculate(a, b, operation) {
    a = parseFloat(a);
    b = parseFloat(b);
    switch (operation) {
        case '+': return (a + b).toString();
        case '-': return (a - b).toString();
        case '×': return (a * b).toString();
        case '÷': return (a / b).toString();
        default: return b.toString();
    }
} 