from web3 import Web3
from eth_account import Account
from django.conf import settings
import logging
import time
from decimal import Decimal

logger = logging.getLogger(__name__)

def get_ethereum_account():
    """Get the Ethereum account for transactions"""
    w3 = get_web3_connection()
    if not w3.is_connected():
        raise Exception("Could not connect to Ethereum network")
    
    # Use the first account from Ganache
    if not w3.eth.accounts:
        raise Exception("No accounts available in Ganache")
    
    return w3.eth.accounts[0]

def get_web3_connection():
    """Establish Web3 connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
            if not w3.is_connected():
                raise Exception("Could not connect to Ethereum network")
            return w3
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Ethereum network: {str(e)}")
                raise
            time.sleep(2 ** attempt)

def estimate_gas_price():
    """Estimate current gas price with safety margin"""
    try:
        w3 = get_web3_connection()
        base_gas_price = w3.eth.gas_price
        # Add 10% safety margin
        return int(base_gas_price * Decimal('1.1'))
    except Exception as e:
        logger.error(f"Error estimating gas price: {str(e)}")
        raise

def send_blockchain_transaction(contract_function, account):
    """Send a blockchain transaction with proper gas estimation"""
    try:
        w3 = get_web3_connection()
        gas_price = estimate_gas_price()
        
        # Estimate gas for the transaction
        gas_estimate = contract_function.estimate_gas({'from': account.address})
        gas_with_margin = int(gas_estimate * Decimal('1.2'))  # Add 20% margin
        
        # Build transaction
        transaction = contract_function.build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': gas_with_margin,
            'gasPrice': gas_price,
            'chainId': w3.eth.chain_id  # Add chainId
        })
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(
            transaction,
            private_key=settings.ETHEREUM_PRIVATE_KEY
        )
        
        # Send raw transaction using hexbytes
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        return w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        logger.error(f"Error sending blockchain transaction: {str(e)}")
        raise

def store_certificate_with_retry(order_id, certificate_hash, max_retries=3):
    """Store certificate with retry logic"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            w3 = get_web3_connection()
            account = get_ethereum_account()
            
            # Check balance
            balance = w3.eth.get_balance(account.address)
            gas_price = estimate_gas_price()
            estimated_gas = 200000  # Base gas estimate for certificate storage
            required_balance = gas_price * estimated_gas
            
            if balance < required_balance:
                raise Exception(f"Insufficient balance. Required: {required_balance}, Available: {balance}")
            
            # Get contract instance
            contract = w3.eth.contract(
                address=settings.CERTIFICATE_CONTRACT_ADDRESS,
                abi=settings.CERTIFICATE_CONTRACT_ABI
            )
            
            # Prepare contract function
            store_function = contract.functions.storeCertificate(
                str(order_id),
                certificate_hash
            )
            
            # Send transaction
            receipt = send_blockchain_transaction(store_function, account)
            return receipt['transactionHash'].hex()
            
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time} seconds: {str(e)}")
                time.sleep(wait_time)
            else:
                logger.error(f"All attempts failed for order {order_id}: {str(e)}")
                raise last_error

def store_certificate_on_blockchain(order_id, certificate_hash):
    """Store certificate hash on blockchain"""
    try:
        w3 = get_web3_connection()
        account = get_ethereum_account()
        
        contract = w3.eth.contract(
            address=settings.CERTIFICATE_CONTRACT_ADDRESS,
            abi=settings.CERTIFICATE_CONTRACT_ABI
        )
        
        # Store hash on blockchain
        tx_hash = contract.functions.storeCertificate(
            str(order_id),
            certificate_hash
        ).transact({'from': account})
        
        # Wait for transaction receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt['transactionHash'].hex()
        
    except Exception as e:
        logger.error(f"Error storing certificate on blockchain: {str(e)}")
        raise

def verify_certificate_on_blockchain(order_id, certificate_hash):
    """Verify certificate hash on blockchain"""
    try:
        w3 = get_web3_connection()
        contract = w3.eth.contract(
            address=settings.CERTIFICATE_CONTRACT_ADDRESS,
            abi=settings.CERTIFICATE_CONTRACT_ABI
        )
        
        # Get stored certificate with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                stored_hash = contract.functions.getCertificate(str(order_id)).call()
                return stored_hash == certificate_hash
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                
    except Exception as e:
        logger.error(f"Error verifying certificate on blockchain: {str(e)}")
        raise

def test_blockchain_connection():
    """Test blockchain connection and account setup"""
    try:
        w3 = get_web3_connection()
        account = get_ethereum_account()
        
        # Test connection
        if not w3.is_connected():
            return False, "Could not connect to Ethereum network"
            
        # Test account
        balance = w3.eth.get_balance(account.address)
        if balance == 0:
            return False, f"Account {account.address} has no balance"
            
        # Test contract
        contract = w3.eth.contract(
            address=settings.CERTIFICATE_CONTRACT_ADDRESS,
            abi=settings.CERTIFICATE_CONTRACT_ABI
        )
        
        # Try to call a view function
        try:
            contract.functions.getCertificate("test").call()
        except Exception as e:
            if "revert" not in str(e):  # Revert is ok as it means contract exists
                return False, f"Contract call failed: {str(e)}"
        
        return True, "Blockchain connection successful"
        
    except Exception as e:
        return False, f"Setup test failed: {str(e)}"