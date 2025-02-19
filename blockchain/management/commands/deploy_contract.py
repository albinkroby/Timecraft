from django.core.management.base import BaseCommand
from django.conf import settings
from web3 import Web3
from solcx import compile_standard, install_solc
import json
import os

class Command(BaseCommand):
    help = 'Deploy smart contract to local blockchain'

    def handle(self, *args, **kwargs):
        try:
            # Install specific solidity version
            install_solc('0.8.0')
            
            # Connect to local blockchain
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
            
            if not w3.is_connected():
                self.stdout.write(self.style.ERROR('Could not connect to local blockchain'))
                return
            
            # Get the absolute path to the contract file
            contract_path = os.path.join(settings.BASE_DIR, 'smart contract', 'WatchCertificateVerification.sol')
            
            # Compile the contract
            with open(contract_path, 'r') as file:
                contract_source = file.read()
                
            compiled_sol = compile_standard({
                "language": "Solidity",
                "sources": {
                    "WatchCertificateVerification.sol": {
                        "content": contract_source
                    }
                },
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                        }
                    }
                }
            }, solc_version="0.8.0")
            
            # Get contract data
            contract_data = compiled_sol['contracts']['WatchCertificateVerification.sol']['WatchCertificateVerification']
            contract_bytecode = contract_data['evm']['bytecode']['object']
            contract_abi = contract_data['abi']
            
            # Deploy contract
            Contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
            account = w3.eth.accounts[0]
            
            # Build and send transaction
            tx_hash = Contract.constructor().transact({'from': account})
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Save contract data
            contract_data = {
                'address': tx_receipt.contractAddress,
                'abi': contract_abi
            }
            
            output_path = os.path.join(settings.BASE_DIR, 'smart contract', 'contract_data.json')
            with open(output_path, 'w') as f:
                json.dump(contract_data, f, indent=2)
                
            self.stdout.write(self.style.SUCCESS(f'Contract deployed at: {tx_receipt.contractAddress}'))
            
            # Update settings
            self.stdout.write(self.style.SUCCESS(
                f'\nAdd these settings to your .env file:\n'
                f'CERTIFICATE_CONTRACT_ADDRESS={tx_receipt.contractAddress}\n'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error deploying contract: {str(e)}'))