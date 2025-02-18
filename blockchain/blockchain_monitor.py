from web3 import Web3
import time
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def monitor_blockchain_status():
    w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
    
    try:
        # Check connection
        if not w3.is_connected():
            logger.error("Cannot connect to local blockchain")
            return False
            
        # Check latest block
        latest_block = w3.eth.block_number
        logger.info(f"Current block number: {latest_block}")
        
        # Check gas price
        gas_price = w3.eth.gas_price
        logger.info(f"Current gas price: {gas_price}")
        
        return True
        
    except Exception as e:
        logger.error(f"Blockchain monitoring error: {str(e)}")
        return False