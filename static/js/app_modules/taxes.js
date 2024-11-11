// inclusive tax 
function calculateInclusiveTax(price, taxRate) {
    const taxAmount = price * (taxRate / (1 + taxRate));
    return taxAmount;
}

// exclusive tax 
function calculateExclusiveTax(price, taxRate) {
    const taxAmount = price * taxRate;
    return taxAmount;
}

module.exports = {
    calculateInclusiveTax,
    calculateExclusiveTax
};
