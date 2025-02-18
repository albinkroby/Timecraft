from web3 import Web3
from eth_account import Account
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_ethereum_account():
    """Get or create Ethereum account from private key"""
    try:
        account = Account.from_key(settings.ETHEREUM_PRIVATE_KEY)
        return account
    except Exception as e:
        logger.error(f"Error creating Ethereum account: {e}")
        raise

def send_blockchain_transaction(contract_function, account):
    """Helper function to send blockchain transactions"""
    try:
        w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
        
        # Get nonce
        nonce = w3.eth.get_transaction_count(account.address)
        
        # Build transaction
        transaction = contract_function.build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, settings.ETHEREUM_PRIVATE_KEY)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt
        
    except Exception as e:
        logger.error(f"Error in send_blockchain_transaction: {str(e)}")
        raise

def store_certificate_on_blockchain(order_id, certificate_hash):
    """Store certificate hash on blockchain"""
    try:
        w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
        account = get_ethereum_account()
        
        # Ensure account has enough balance
        balance = w3.eth.get_balance(account.address)
        if balance == 0:
            raise Exception("Account has no ETH for gas")
        
        contract = w3.eth.contract(
            address=settings.CERTIFICATE_CONTRACT_ADDRESS,
            abi=settings.CERTIFICATE_CONTRACT_ABI
        )
        
        store_function = contract.functions.storeCertificate(
            str(order_id),
            certificate_hash
        )
        
        receipt = send_blockchain_transaction(store_function, account)
        return receipt['transactionHash'].hex()
        
    except Exception as e:
        logger.error(f"Error storing certificate on blockchain: {str(e)}")
        raise