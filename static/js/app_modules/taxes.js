// inclusive tax 
export function calculateInclusiveTax(price, taxRate) {
    const taxAmount = price * (taxRate / (1 + taxRate));
    return taxAmount;
}
// exclusive tax 
 export function calculateExclusiveTax(price, taxRate) {
    const taxAmount = price * taxRate;
    return taxAmount;
}