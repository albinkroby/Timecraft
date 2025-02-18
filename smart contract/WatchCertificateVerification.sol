// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract WatchCertificateVerification {
    // Mapping from order ID to certificate hash
    mapping(string => string) private certificates;
    
    // Event to emit when a certificate is stored
    event CertificateStored(string orderId, string certificateHash);
    
    // Store a new certificate
    function storeCertificate(string memory orderId, string memory certificateHash) public {
        certificates[orderId] = certificateHash;
        emit CertificateStored(orderId, certificateHash);
    }
    
    // Get a certificate by order ID
    function getCertificate(string memory orderId) public view returns (string memory) {
        return certificates[orderId];
    }
    
    // Verify if a certificate exists and matches
    function verifyCertificate(string memory orderId, string memory certificateHash) public view returns (bool) {
        return keccak256(abi.encodePacked(certificates[orderId])) == keccak256(abi.encodePacked(certificateHash));
    }
} 