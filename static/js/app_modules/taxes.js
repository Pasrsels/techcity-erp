export function calculateInclusiveTax(price, taxRate) {
    const taxAmount = price * (taxRate / (1 + taxRate));
    return taxAmount;
}

export function calculateExclusiveTax(price, taxRate) {
    const taxAmount = price * taxRate;
    return taxAmount;
}
