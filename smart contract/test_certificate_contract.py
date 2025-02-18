from web3 import Web3
import pytest
from eth_account import Account
import json
import time

from blockchain.blockchain_utils import store_certificate_on_blockchain

def test_certificate_contract():
    # Connect to local Ganache
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    
    # Load contract data
    with open('contract_data.json', 'r') as f:
        contract_data = json.load(f)
    
    # Create test account
    test_account = Account.create()
    
    # Get contract instance
    contract = w3.eth.contract(
        address=contract_data['address'],
        abi=contract_data['abi']
    )
    
    # Test certificate storage
    order_id = "TEST123"
    certificate_hash = "0x" + "a" * 64
    
    tx_hash = contract.functions.storeCertificate(
        order_id,
        certificate_hash
    ).transact({'from': w3.eth.accounts[0]})
    
    # Wait for transaction
    w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Verify certificate
    stored_hash = contract.functions.getCertificate(order_id).call()
    assert stored_hash == certificate_hash

def store_certificate_with_retry(order_id, certificate_hash, max_retries=3):
    """Store certificate with retry mechanism"""
    for attempt in range(max_retries):
        try:
            tx_hash = store_certificate_on_blockchain(order_id, certificate_hash)
            return tx_hash
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))  # Exponential backoff