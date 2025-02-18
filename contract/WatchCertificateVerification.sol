// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract WatchCertificateVerification {
    address public owner;
    
    // Mapping from order ID to certificate hash
    mapping(string => string) private certificates;
    
    // Events
    event CertificateStored(string orderId, string certificateHash);
    event CertificateRevoked(string orderId);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Store a new certificate hash for an order
     * @param orderId The unique order identifier
     * @param certificateHash The hash of the certificate
     */
    function storeCertificate(string memory orderId, string memory certificateHash) 
        public 
        onlyOwner 
    {
        require(bytes(certificateHash).length == 66, "Invalid certificate hash length");
        require(bytes(certificates[orderId]).length == 0, "Certificate already exists");
        
        certificates[orderId] = certificateHash;
        emit CertificateStored(orderId, certificateHash);
    }

    /**
     * @dev Get the certificate hash for an order
     * @param orderId The unique order identifier
     * @return The certificate hash
     */
    function getCertificate(string memory orderId) 
        public 
        view 
        returns (string memory) 
    {
        require(bytes(certificates[orderId]).length > 0, "Certificate not found");
        return certificates[orderId];
    }

    /**
     * @dev Check if a certificate exists for an order
     * @param orderId The unique order identifier
     * @return bool indicating if certificate exists
     */
    function certificateExists(string memory orderId) 
        public 
        view 
        returns (bool) 
    {
        return bytes(certificates[orderId]).length > 0;
    }

    /**
     * @dev Verify if a provided hash matches the stored certificate
     * @param orderId The unique order identifier
     * @param certificateHash The hash to verify
     * @return bool indicating if the hashes match
     */
    function verifyCertificate(string memory orderId, string memory certificateHash) 
        public 
        view 
        returns (bool) 
    {
        require(bytes(certificates[orderId]).length > 0, "Certificate not found");
        return keccak256(abi.encodePacked(certificates[orderId])) == 
               keccak256(abi.encodePacked(certificateHash));
    }

    /**
     * @dev Revoke a certificate (in case of errors or fraud)
     * @param orderId The unique order identifier
     */
    function revokeCertificate(string memory orderId) 
        public 
        onlyOwner 
    {
        require(bytes(certificates[orderId]).length > 0, "Certificate not found");
        delete certificates[orderId];
        emit CertificateRevoked(orderId);
    }

    /**
     * @dev Transfer ownership of the contract
     * @param newOwner The address of the new owner
     */
    function transferOwnership(address newOwner) 
        public 
        onlyOwner 
    {
        require(newOwner != address(0), "Invalid new owner address");
        owner = newOwner;
    }
}