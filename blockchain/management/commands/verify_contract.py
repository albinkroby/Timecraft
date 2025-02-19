# blockchain/management/commands/verify_contract.py
from django.core.management.base import BaseCommand
from django.conf import settings
from web3 import Web3

class Command(BaseCommand):
    help = 'Verify smart contract deployment'

    def handle(self, *args, **kwargs):
        try:
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
            
            if not w3.is_connected():
                self.stdout.write(self.style.ERROR('Could not connect to blockchain'))
                return
                
            contract = w3.eth.contract(
                address=settings.CERTIFICATE_CONTRACT_ADDRESS,
                abi=settings.CERTIFICATE_CONTRACT_ABI
            )
            
            # Test contract by storing and retrieving a test certificate
            test_order_id = "TEST123"
            test_hash = "0x" + "0" * 64
            
            # Store test certificate
            tx_hash = contract.functions.storeCertificate(
                test_order_id,
                test_hash
            ).transact({'from': w3.eth.accounts[0]})
            
            # Wait for transaction
            w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Verify storage
            stored_hash = contract.functions.getCertificate(test_order_id).call()
            
            if stored_hash == test_hash:
                self.stdout.write(self.style.SUCCESS('Contract verified successfully'))
            else:
                self.stdout.write(self.style.ERROR('Contract verification failed'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error verifying contract: {str(e)}'))