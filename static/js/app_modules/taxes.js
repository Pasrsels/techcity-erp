// // inclusive tax 
// function calculateInclusiveTax(price, taxRate) {
//     const taxAmount = price * (taxRate / (1 + taxRate));
//     return taxAmount;
// }

// // exclusive tax 
// function calculateExclusiveTax(price, taxRate) {
//     const taxAmount = price * taxRate;
//     return taxAmount;
// }

// module.exports = {
//     calculateInclusiveTax,
//     calculateExclusiveTax
// };

///// in pure javascript we dont use, export key work


export function calculateInclusiveTax(price, taxRate) {
    const taxAmount = price * (taxRate / (1 + taxRate));
    return taxAmount;
}

export function calculateExclusiveTax(price, taxRate) {
    const taxAmount = price * taxRate;
    return taxAmount;
}
