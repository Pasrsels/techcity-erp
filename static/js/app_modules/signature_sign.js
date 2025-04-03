function getHash(request) {
    return CryptoJS.enc.Base64.stringify(CryptoJS.SHA256(request));
}

function signData(data, privateKeyPem) {
    try {
        var key = KEYUTIL.getKey(privateKeyPem);  
        var sig = new KJUR.crypto.Signature({"alg": "SHA256withRSA"});
        sig.init(key);
        sig.updateString(data);
        var signatureHex = sig.sign();  // Get signature in hex format
        return hextob64(signatureHex);  // Convert hex signature to Base64
    } catch (e) {
        console.error("Signing Error: ", e);
        return null;
    }
}

function run(signature) {
    var stringToSign = signature;
    
    var hash = getHash(stringToSign);
    console.log("Hash:", hash);

    var privateKey = `-----BEGIN PRIVATE KEY-----
    MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDwEH8sSxrJip/A
    j1JtrmPRlIMdqx/qg6W0WM91MaGj876PcFwsIxCBCa4RWSdBH4AX7qfYoVx8UmPP
    Ck8Ni1mt4duCCPEEULxg11rcivy6RY375yNbKJ5LcoXlkVn9nGWJ39p7Oj/Y95nU
    4a5dE2s04ppq4KH72/hQCSkRxS9vUR9hS8Y8ZgNyQ/4buTZmm2TPYRBMDv9pgFm1
    pgYi7+XpC7f/F3yZMoPtouCF3SwscUJ8YSnc4SBjPV6bGQxcqMG3NoaopHNmDmGh
    E2ogjG/I454hDm3rzazKz3sef2HE2hGGm6rNK0GS6FYyfqwYiARvVfs6EcSgz9Vr
    ck6MFEWXAgMBAAECgf9u9zEm8uXEQ0+UsqsSB99xVjSaginpPPEGFrHOeiKSpm3E
    ioC7O3oQK2lKm5Xe2bCxX0o2gwqSbNhghg4Eig/p+tHRnvserjMP5dEaIHoG9XUB
    UNYG97+JIGbEDBaMzr4gp64AnUGQs41n2ZRqHDpx4kzTxQHFvugIwYiPrkCUMwYf
    EysgpY2OT/oMNjJJK/a33P4QVSeFCvCWZ2zIwGcxMHB2a7CKnvRLs6s7MJGT+gU4
    2tNOjCmRTvJixGLIC21m28Cnf7Kxjih384ulK4MyCc/n0W8+chg0kUWmiHln4vex
    qIpoxP72vCn/jUId34FyLEiPrySsYsFEhANw5YECgYEA+PnSvjlVIw5L2CB9nQr8
    M93US0+TK+/qlr/RbCCIaFAkrfS6Tvto09AARAQWUYa6CbJbAd5XjuVof6YlZ7Hm
    9ciGzEKvZPqvO5WxxJUbvnTXPe3as9r7fn5jTRYJrc2IKTPXT7+8MD82pUZyqbHS
    RfdPBE3S6VNRKRXmVz5pb9cCgYEA9tZQBWklCccOEnP5cshvxy0OeiWbFWq8bfIz
    w214ZHrGqims5N1L3Ejs9srqn0vWYL4I8B4uaZScOzOWZAVopXfNrnjiRBZzqTzn
    BlPO0bWmrjQAgyA5SnTQ02us9biFvfaNCtxyhJAhMGrb3C108EHqtG7W7riE9TJY
    4QrMIEECgYEA1YvZMOUV28qATPCZLOBmLspeMvYeofnWeNQveJFyzh2nSDj2r5W9
    dKccAzqKNgTbfkOnATRGXz7u4UWNIaKaGUeULpAnxfGp6O5dGeJWeIXYs7pV8hup
    x/X5j/2N8a+u0MAxNaqba7pcUWfaIyhs1SvobyWc+BlJLHcnKL9USeMCgYBw63fu
    EbzE7VANtwptrS4dgwo1bNC2in6rGXr+syy5YsVRgQE8LdSPcLke6ZNNzmbDGQyD
    tHrtB/Q0zRPGrAbEc7sfTuPL3C2LRXY2mc5qd1xKIzX8xpgO7MO/hGm6e3CLh6fc
    SR8Gb90PBkOQRSdS5gTWCELBMJ56gU7RnJvnQQKBgQDyjPPgVwEmAgCSX2AGacfJ
    yB2GBZsy5NwWUboR+D+eSoD9U3EiggjlmPaHKwVsOm9UZ2WTuQY5+4G3Vo3QJv5p
    99uAWZM476cHo3GMJyofOMSzhP+zoTajsMKVwZreVfSkBP3bkgPv/Pa0Eo6pnQoc
    LSlpirFwsvVBf/SGHszN5Q==
    -----END PRIVATE KEY-----`;

    var signature = signData(stringToSign, privateKey);
    console.log("Signature:", signature);

    return {
        'hash':hash,
        'signature':signature
    }
}

