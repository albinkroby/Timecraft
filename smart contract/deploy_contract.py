from web3 import Web3
import json
from eth_account import Account
import os
from dotenv import load_dotenv
from solcx import compile_standard, install_solc

def deploy_contract():
    # Install specific solidity version
    install_solc('0.8.0')
    
    # Connect to local Ganache blockchain
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    
    # Use one of the pre-funded Ganache accounts
    private_key = '0xb03619af738458129a27e4f6f871d2f84dcac34de26eb6b715362a3f57257e88'  # First Ganache account private key
    account = Account.from_key(private_key)
    w3.eth.default_account = account.address
    
    # Read contract source
    with open('../contract/WatchCertificateVerification.sol', 'r') as file:
        contract_source = file.read()
    
    # Rest of your existing compilation code...
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
    
    Contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    
    # Check balance
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance_wei, 'ether')
    print(f"Account balance: {balance_eth} ETH")
    
    # Estimate gas
    gas_price = w3.eth.gas_price
    estimated_gas = w3.eth.estimate_gas({
        'from': account.address,
        'data': Contract.bytecode
    })
    
    # Deploy contract
    construct_txn = Contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': estimated_gas,
        'gasPrice': gas_price
    })
    
    signed = account.sign_transaction(construct_txn)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Save contract data
    contract_data = {
        'address': tx_receipt.contractAddress,
        'abi': contract_abi
    }
    
    with open('contract_data.json', 'w') as f:
        json.dump(contract_data, f)
    
    print(f'Contract deployed at: {tx_receipt.contractAddress}')
    return contract_data

if __name__ == '__main__':
    contract_data = deploy_contract()