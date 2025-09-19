#!/usr/bin/env python3
"""
Blockchain Service - Interface between API and Smart Contracts
Handles toll payments and blockchain interactions
"""

from web3 import Web3
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockchainService:
    def __init__(self, rpc_url="http://localhost:8545"):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = None
        self.contract_address = None
        self.owner_account = None
        
        # Load contract ABI (simplified)
        self.contract_abi = [
            {
                "inputs": [],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tollId", "type": "uint256"},
                    {"indexed": True, "name": "vehicle", "type": "address"},
                    {"indexed": False, "name": "amount", "type": "uint256"}
                ],
                "name": "TollCreated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tollId", "type": "uint256"},
                    {"indexed": True, "name": "payer", "type": "address"}
                ],
                "name": "TollPaid",
                "type": "event"
            },
            {
                "inputs": [
                    {"name": "vehicle", "type": "address"},
                    {"name": "gantryId", "type": "uint256"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "createToll",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "vehicle", "type": "address"},
                    {"name": "gantryId", "type": "uint256"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "autoPayToll",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tollId", "type": "uint256"}],
                "name": "payToll",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "depositBalance",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [{"name": "", "type": "uint256"}],
                "name": "tollRecords",
                "outputs": [
                    {"name": "vehicle", "type": "address"},
                    {"name": "gantryId", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "paid", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "", "type": "address"}],
                "name": "vehicleBalances",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self._setup_accounts()
    
    def _setup_accounts(self):
        """Setup blockchain accounts"""
        try:
            if self.w3.isConnected():
                accounts = self.w3.eth.accounts
                if accounts:
                    self.owner_account = accounts[0]
                    logger.info(f"✓ Connected to blockchain, owner: {self.owner_account}")
                else:
                    logger.warning("No accounts available")
            else:
                logger.error("Failed to connect to blockchain")
        except Exception as e:
            logger.error(f"Blockchain setup error: {e}")
    
    def deploy_contract(self):
        """Deploy TollManager contract"""
        try:
            # Contract bytecode (simplified - in production use compiled bytecode)
            contract_bytecode = "0x608060405234801561001057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506001600181905550610c8c806100686000396000f3fe"
            
            # Deploy contract
            contract = self.w3.eth.contract(abi=self.contract_abi, bytecode=contract_bytecode)
            
            tx_hash = contract.constructor().transact({'from': self.owner_account})
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            
            self.contract_address = tx_receipt.contractAddress
            self.contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=self.contract_abi
            )
            
            logger.info(f"✓ Contract deployed at: {self.contract_address}")
            return self.contract_address
            
        except Exception as e:
            logger.error(f"Contract deployment error: {e}")
            return None
    
    def connect_to_contract(self, contract_address):
        """Connect to existing contract"""
        try:
            self.contract_address = contract_address
            self.contract = self.w3.eth.contract(
                address=contract_address,
                abi=self.contract_abi
            )
            logger.info(f"✓ Connected to contract: {contract_address}")
            return True
        except Exception as e:
            logger.error(f"Contract connection error: {e}")
            return False
    
    def create_toll_record(self, vehicle_address, gantry_id, amount_eth):
        """Create toll record on blockchain"""
        if not self.contract:
            logger.error("Contract not connected")
            return None
        
        try:
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            tx_hash = self.contract.functions.createToll(
                vehicle_address,
                gantry_id,
                amount_wei
            ).transact({'from': self.owner_account})
            
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            
            # Get toll ID from events
            toll_created_event = self.contract.events.TollCreated().processReceipt(tx_receipt)
            if toll_created_event:
                toll_id = toll_created_event[0]['args']['tollId']
                logger.info(f"✓ Toll record created: ID {toll_id}")
                return {
                    'toll_id': toll_id,
                    'tx_hash': tx_hash.hex(),
                    'block_number': tx_receipt.blockNumber
                }
            
        except Exception as e:
            logger.error(f"Create toll error: {e}")
            return None
    
    def auto_pay_toll(self, vehicle_address, gantry_id, amount_eth):
        """Auto-pay toll using vehicle balance"""
        if not self.contract:
            logger.error("Contract not connected")
            return None
        
        try:
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            tx_hash = self.contract.functions.autoPayToll(
                vehicle_address,
                gantry_id,
                amount_wei
            ).transact({'from': self.owner_account})
            
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            
            # Process events
            events = self.contract.events.TollCreated().processReceipt(tx_receipt)
            paid_events = self.contract.events.TollPaid().processReceipt(tx_receipt)
            
            if events:
                toll_id = events[0]['args']['tollId']
                is_paid = len(paid_events) > 0
                
                logger.info(f"✓ Auto-pay toll: ID {toll_id}, Paid: {is_paid}")
                return {
                    'toll_id': toll_id,
                    'paid': is_paid,
                    'tx_hash': tx_hash.hex(),
                    'block_number': tx_receipt.blockNumber
                }
            
        except Exception as e:
            logger.error(f"Auto-pay toll error: {e}")
            return None
    
    def pay_toll(self, toll_id, payer_address, amount_eth):
        """Pay existing toll"""
        if not self.contract:
            logger.error("Contract not connected")
            return None
        
        try:
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            tx_hash = self.contract.functions.payToll(toll_id).transact({
                'from': payer_address,
                'value': amount_wei
            })
            
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            
            logger.info(f"✓ Toll {toll_id} paid")
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': tx_receipt.blockNumber
            }
            
        except Exception as e:
            logger.error(f"Pay toll error: {e}")
            return None
    
    def get_toll_record(self, toll_id):
        """Get toll record from blockchain"""
        if not self.contract:
            return None
        
        try:
            record = self.contract.functions.tollRecords(toll_id).call()
            return {
                'vehicle': record[0],
                'gantry_id': record[1],
                'timestamp': record[2],
                'amount_wei': record[3],
                'amount_eth': self.w3.fromWei(record[3], 'ether'),
                'paid': record[4]
            }
        except Exception as e:
            logger.error(f"Get toll record error: {e}")
            return None
    
    def get_vehicle_balance(self, vehicle_address):
        """Get vehicle balance from contract"""
        if not self.contract:
            return 0
        
        try:
            balance_wei = self.contract.functions.vehicleBalances(vehicle_address).call()
            return self.w3.fromWei(balance_wei, 'ether')
        except Exception as e:
            logger.error(f"Get balance error: {e}")
            return 0
    
    def deposit_balance(self, vehicle_address, amount_eth):
        """Deposit balance to vehicle account"""
        if not self.contract:
            return None
        
        try:
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            tx_hash = self.contract.functions.depositBalance().transact({
                'from': vehicle_address,
                'value': amount_wei
            })
            
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            
            logger.info(f"✓ Balance deposited: {amount_eth} ETH")
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': tx_receipt.blockNumber
            }
            
        except Exception as e:
            logger.error(f"Deposit balance error: {e}")
            return None

# Flask API for blockchain service
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize blockchain service
blockchain = BlockchainService()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'blockchain',
        'connected': blockchain.w3.isConnected() if blockchain.w3 else False
    })

@app.route('/deploy', methods=['POST'])
def deploy_contract():
    """Deploy smart contract"""
    address = blockchain.deploy_contract()
    if address:
        return jsonify({'contract_address': address})
    else:
        return jsonify({'error': 'Deployment failed'}), 500

@app.route('/connect', methods=['POST'])
def connect_contract():
    """Connect to existing contract"""
    data = request.get_json()
    address = data.get('contract_address')
    
    if blockchain.connect_to_contract(address):
        return jsonify({'status': 'connected'})
    else:
        return jsonify({'error': 'Connection failed'}), 500

@app.route('/toll/create', methods=['POST'])
def create_toll():
    """Create toll record"""
    data = request.get_json()
    result = blockchain.create_toll_record(
        data.get('vehicle_address'),
        data.get('gantry_id'),
        data.get('amount')
    )
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to create toll'}), 500

@app.route('/toll/autopay', methods=['POST'])
def auto_pay_toll():
    """Auto-pay toll"""
    data = request.get_json()
    result = blockchain.auto_pay_toll(
        data.get('vehicle_address'),
        data.get('gantry_id'),
        data.get('amount')
    )
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to auto-pay toll'}), 500

@app.route('/toll/<int:toll_id>', methods=['GET'])
def get_toll(toll_id):
    """Get toll record"""
    record = blockchain.get_toll_record(toll_id)
    if record:
        return jsonify(record)
    else:
        return jsonify({'error': 'Toll record not found'}), 404

@app.route('/balance/<vehicle_address>', methods=['GET'])
def get_balance(vehicle_address):
    """Get vehicle balance"""
    balance = blockchain.get_vehicle_balance(vehicle_address)
    return jsonify({'balance': float(balance)})

if __name__ == "__main__":
    # Try to connect to existing contract or deploy new one
    contract_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"  # Default Ganache address
    if not blockchain.connect_to_contract(contract_address):
        logger.info("Deploying new contract...")
        blockchain.deploy_contract()
    
    app.run(host='0.0.0.0', port=5002, debug=True)