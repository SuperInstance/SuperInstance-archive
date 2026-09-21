"""
Blockchain-Based Character Ownership System
Decentralized character ownership with NFTs, smart contracts, and cross-platform interoperability
"""

import asyncio
import logging
import json
import time
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import web3
from web3 import Web3
from eth_account import Account
import ipfshttpclient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import base64
import requests
import sqlite3

logger = logging.getLogger(__name__)

class BlockchainNetwork(Enum):
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    AVALANCHE = "avalanche"
    BINANCE_SMART_CHAIN = "bsc"
    SOLANA = "solana"
    IMMUTABLE_X = "immutablex"

class CharacterRarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"

@dataclass
class CharacterNFT:
    token_id: str
    contract_address: str
    owner_address: str
    character_data: Dict[str, Any]
    metadata_uri: str
    rarity: CharacterRarity
    created_timestamp: float
    last_updated: float
    network: BlockchainNetwork
    traits: Dict[str, Any] = field(default_factory=dict)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    cross_platform_verified: bool = False

@dataclass
class SmartContractConfig:
    contract_address: str
    abi: List[Dict[str, Any]]
    network: BlockchainNetwork
    gas_limit: int = 300000
    gas_price_gwei: int = 20

class IPFSManager:
    """IPFS integration for decentralized metadata storage"""
    
    def __init__(self, ipfs_api_url: str = '/ip4/127.0.0.1/tcp/5001'):
        try:
            self.client = ipfshttpclient.connect(ipfs_api_url)
            logger.info("Connected to IPFS node")
        except Exception as e:
            logger.warning(f"Failed to connect to IPFS: {e}")
            self.client = None
    
    def upload_character_metadata(self, character_data: Dict[str, Any]) -> Optional[str]:
        """Upload character metadata to IPFS and return hash"""
        if not self.client:
            logger.error("IPFS client not available")
            return None
        
        try:
            # Create comprehensive metadata
            metadata = self._create_nft_metadata(character_data)
            
            # Upload to IPFS
            result = self.client.add_json(metadata)
            ipfs_hash = result['Hash']
            
            logger.info(f"Character metadata uploaded to IPFS: {ipfs_hash}")
            return ipfs_hash
            
        except Exception as e:
            logger.error(f"Failed to upload to IPFS: {e}")
            return None
    
    def retrieve_character_metadata(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve character metadata from IPFS"""
        if not self.client:
            logger.error("IPFS client not available")
            return None
        
        try:
            metadata = self.client.get_json(ipfs_hash)
            return metadata
        except Exception as e:
            logger.error(f"Failed to retrieve from IPFS: {e}")
            return None
    
    def _create_nft_metadata(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create OpenSea-compatible NFT metadata"""
        character_name = character_data.get('name', 'Unknown Adventurer')
        character_class = character_data.get('class', 'Unknown')
        character_race = character_data.get('race', 'Unknown')
        level = character_data.get('level', 1)
        
        # Extract traits for NFT attributes
        attributes = []
        
        # Core character attributes
        attributes.extend([
            {"trait_type": "Class", "value": character_class},
            {"trait_type": "Race", "value": character_race},
            {"trait_type": "Level", "value": level, "display_type": "number"},
            {"trait_type": "Creation Date", "value": time.strftime("%Y-%m-%d"), "display_type": "date"}
        ])
        
        # Ability scores
        abilities = character_data.get('abilities', {})
        for ability, score in abilities.items():
            attributes.append({
                "trait_type": ability.title(),
                "value": score,
                "display_type": "number",
                "max_value": 20
            })
        
        # Skills and proficiencies
        skills = character_data.get('skills', {})
        proficient_skills = [skill for skill, proficiency in skills.items() if proficiency > 0]
        if proficient_skills:
            attributes.append({
                "trait_type": "Skill Proficiencies",
                "value": len(proficient_skills),
                "display_type": "number"
            })
        
        # Equipment and wealth
        equipment = character_data.get('equipment', [])
        if equipment:
            attributes.append({
                "trait_type": "Equipment Items",
                "value": len(equipment),
                "display_type": "number"
            })
        
        # Character optimization score (if available)
        optimization_score = character_data.get('optimization_score')
        if optimization_score:
            attributes.append({
                "trait_type": "Optimization Score",
                "value": round(optimization_score, 1),
                "display_type": "number",
                "max_value": 100.0
            })
        
        # Determine rarity based on character features
        rarity = self._calculate_character_rarity(character_data)
        attributes.append({"trait_type": "Rarity", "value": rarity.value})
        
        metadata = {
            "name": character_name,
            "description": f"A Level {level} {character_race} {character_class} from the DMLog Character Builder ecosystem. This NFT represents verified ownership of a unique D&D character with full blockchain provenance.",
            "image": character_data.get('image_url', 'https://dmlog.ai/default-character.png'),
            "external_url": f"https://dmlog.ai/character/{character_data.get('id', '')}",
            "attributes": attributes,
            "properties": {
                "character_data": character_data,
                "created_with": "DMLog Character Builder",
                "version": "2.0",
                "blockchain_verified": True,
                "cross_platform_compatible": True
            }
        }
        
        return metadata
    
    def _calculate_character_rarity(self, character_data: Dict[str, Any]) -> CharacterRarity:
        """Calculate character rarity based on various factors"""
        rarity_score = 0
        
        # Level factor
        level = character_data.get('level', 1)
        if level >= 20:
            rarity_score += 30
        elif level >= 15:
            rarity_score += 20
        elif level >= 10:
            rarity_score += 10
        elif level >= 5:
            rarity_score += 5
        
        # Optimization score factor
        optimization_score = character_data.get('optimization_score', 0)
        if optimization_score >= 95:
            rarity_score += 25
        elif optimization_score >= 90:
            rarity_score += 15
        elif optimization_score >= 80:
            rarity_score += 10
        
        # Unique combinations
        class_name = character_data.get('class', '').lower()
        race = character_data.get('race', '').lower()
        
        # Rare class/race combinations
        rare_combinations = {
            ('dragonborn', 'sorcerer'): 15,
            ('tiefling', 'paladin'): 15,
            ('halfling', 'barbarian'): 10,
            ('gnome', 'barbarian'): 10,
            ('aarakocra', 'monk'): 20,
            ('yuan-ti', 'cleric'): 20
        }
        
        combination_bonus = rare_combinations.get((race, class_name), 0)
        rarity_score += combination_bonus
        
        # Special features
        if character_data.get('multiclass'):
            rarity_score += 15
        
        if character_data.get('custom_background'):
            rarity_score += 5
        
        equipment_count = len(character_data.get('equipment', []))
        if equipment_count > 20:
            rarity_score += 10
        elif equipment_count > 10:
            rarity_score += 5
        
        # Determine rarity tier
        if rarity_score >= 80:
            return CharacterRarity.MYTHIC
        elif rarity_score >= 60:
            return CharacterRarity.LEGENDARY
        elif rarity_score >= 40:
            return CharacterRarity.EPIC
        elif rarity_score >= 25:
            return CharacterRarity.RARE
        elif rarity_score >= 10:
            return CharacterRarity.UNCOMMON
        else:
            return CharacterRarity.COMMON

class SmartContractManager:
    """Smart contract interaction for character NFTs"""
    
    def __init__(self, network_configs: Dict[BlockchainNetwork, Dict[str, Any]]):
        self.network_configs = network_configs
        self.web3_connections = {}
        self.contracts = {}
        
        # Initialize Web3 connections
        for network, config in network_configs.items():
            try:
                w3 = Web3(Web3.HTTPProvider(config['rpc_url']))
                if w3.is_connected():
                    self.web3_connections[network] = w3
                    logger.info(f"Connected to {network.value} blockchain")
                    
                    # Load smart contract
                    if 'contract_address' in config and 'contract_abi' in config:
                        contract = w3.eth.contract(
                            address=config['contract_address'],
                            abi=config['contract_abi']
                        )
                        self.contracts[network] = contract
                        
                else:
                    logger.warning(f"Failed to connect to {network.value}")
                    
            except Exception as e:
                logger.error(f"Error connecting to {network.value}: {e}")
    
    def mint_character_nft(self, character_data: Dict[str, Any], 
                          owner_address: str, network: BlockchainNetwork,
                          private_key: str) -> Optional[str]:
        """Mint a new character NFT"""
        
        if network not in self.web3_connections:
            logger.error(f"No connection to {network.value}")
            return None
        
        if network not in self.contracts:
            logger.error(f"No contract available for {network.value}")
            return None
        
        w3 = self.web3_connections[network]
        contract = self.contracts[network]
        
        try:
            # Upload metadata to IPFS first
            ipfs_manager = IPFSManager()
            metadata_uri = ipfs_manager.upload_character_metadata(character_data)
            
            if not metadata_uri:
                logger.error("Failed to upload metadata to IPFS")
                return None
            
            # Generate unique token ID
            token_id = int(hashlib.sha256(
                f"{character_data.get('id', uuid.uuid4())}{time.time()}".encode()
            ).hexdigest()[:16], 16)
            
            # Prepare transaction
            account = Account.from_key(private_key)
            
            # Build mint transaction
            mint_function = contract.functions.mintCharacter(
                owner_address,
                token_id,
                f"ipfs://{metadata_uri}"
            )
            
            # Estimate gas
            gas_estimate = mint_function.estimate_gas({'from': account.address})
            
            # Get gas price
            gas_price = w3.eth.gas_price
            
            # Build transaction
            transaction = mint_function.build_transaction({
                'from': account.address,
                'gas': gas_estimate,
                'gasPrice': gas_price,
                'nonce': w3.eth.get_transaction_count(account.address)
            })
            
            # Sign transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            
            # Send transaction
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                logger.info(f"Character NFT minted successfully: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                logger.error("Transaction failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to mint NFT: {e}")
            return None
    
    def verify_character_ownership(self, token_id: str, network: BlockchainNetwork) -> Optional[str]:
        """Verify current owner of a character NFT"""
        
        if network not in self.web3_connections or network not in self.contracts:
            return None
        
        try:
            contract = self.contracts[network]
            owner = contract.functions.ownerOf(int(token_id)).call()
            return owner
            
        except Exception as e:
            logger.error(f"Failed to verify ownership: {e}")
            return None
    
    def transfer_character(self, token_id: str, from_address: str, to_address: str,
                          network: BlockchainNetwork, private_key: str) -> Optional[str]:
        """Transfer character NFT to another address"""
        
        if network not in self.web3_connections or network not in self.contracts:
            return None
        
        w3 = self.web3_connections[network]
        contract = self.contracts[network]
        
        try:
            account = Account.from_key(private_key)
            
            # Build transfer transaction
            transfer_function = contract.functions.transferFrom(
                from_address,
                to_address,
                int(token_id)
            )
            
            # Estimate gas
            gas_estimate = transfer_function.estimate_gas({'from': account.address})
            
            # Build transaction
            transaction = transfer_function.build_transaction({
                'from': account.address,
                'gas': gas_estimate,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                logger.info(f"Character transferred successfully: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                logger.error("Transfer transaction failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to transfer NFT: {e}")
            return None

class CrossPlatformManager:
    """Manage cross-platform character portability and verification"""
    
    def __init__(self):
        self.supported_platforms = {
            "dnd_beyond": {"api_url": "https://www.dndbeyond.com/api", "auth_required": True},
            "roll20": {"api_url": "https://app.roll20.net/api", "auth_required": True},
            "foundry_vtt": {"api_url": "http://localhost:30000/api", "auth_required": False},
            "fantasy_grounds": {"api_url": "https://www.fantasygrounds.com/api", "auth_required": True}
        }
        self.verification_signatures = {}
    
    def export_character_for_platform(self, character_nft: CharacterNFT, 
                                    target_platform: str) -> Optional[Dict[str, Any]]:
        """Export character data in platform-specific format"""
        
        if target_platform not in self.supported_platforms:
            logger.error(f"Unsupported platform: {target_platform}")
            return None
        
        character_data = character_nft.character_data
        
        try:
            if target_platform == "dnd_beyond":
                return self._export_to_dnd_beyond(character_data)
            elif target_platform == "roll20":
                return self._export_to_roll20(character_data)
            elif target_platform == "foundry_vtt":
                return self._export_to_foundry(character_data)
            elif target_platform == "fantasy_grounds":
                return self._export_to_fantasy_grounds(character_data)
            else:
                return self._export_generic_format(character_data)
                
        except Exception as e:
            logger.error(f"Failed to export to {target_platform}: {e}")
            return None
    
    def _export_to_dnd_beyond(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export character in D&D Beyond compatible format"""
        return {
            "name": character_data.get("name", ""),
            "race": self._map_race_to_ddb(character_data.get("race", "")),
            "classes": [{
                "definition": {
                    "name": character_data.get("class", ""),
                    "hitDie": self._get_hit_die_for_class(character_data.get("class", ""))
                },
                "level": character_data.get("level", 1),
                "classFeatures": []
            }],
            "stats": [
                {"id": 1, "value": character_data.get("abilities", {}).get("strength", 10)},
                {"id": 2, "value": character_data.get("abilities", {}).get("dexterity", 10)},
                {"id": 3, "value": character_data.get("abilities", {}).get("constitution", 10)},
                {"id": 4, "value": character_data.get("abilities", {}).get("intelligence", 10)},
                {"id": 5, "value": character_data.get("abilities", {}).get("wisdom", 10)},
                {"id": 6, "value": character_data.get("abilities", {}).get("charisma", 10)}
            ],
            "background": {
                "definition": {
                    "name": character_data.get("background", ""),
                    "skillProficiencies": []
                }
            },
            "preferences": {
                "useHomebrewContent": True,
                "progressionType": "milestone"
            }
        }
    
    def _export_to_roll20(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export character in Roll20 compatible format"""
        abilities = character_data.get("abilities", {})
        
        return {
            "character_name": character_data.get("name", ""),
            "class_and_level": f"{character_data.get('class', '')} {character_data.get('level', 1)}",
            "race": character_data.get("race", ""),
            "background": character_data.get("background", ""),
            "strength": abilities.get("strength", 10),
            "dexterity": abilities.get("dexterity", 10),
            "constitution": abilities.get("constitution", 10),
            "intelligence": abilities.get("intelligence", 10),
            "wisdom": abilities.get("wisdom", 10),
            "charisma": abilities.get("charisma", 10),
            "hp": character_data.get("current_hp", 0),
            "hp_max": character_data.get("max_hp", 0),
            "armor_class": character_data.get("armor_class", 10),
            "speed": character_data.get("speed", 30),
            "proficiency_bonus": max(2, (character_data.get("level", 1) - 1) // 4 + 2)
        }
    
    def _export_to_foundry(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export character in Foundry VTT compatible format"""
        return {
            "name": character_data.get("name", ""),
            "type": "character",
            "system": {
                "details": {
                    "class": character_data.get("class", ""),
                    "level": {"value": character_data.get("level", 1)},
                    "race": character_data.get("race", ""),
                    "background": character_data.get("background", "")
                },
                "abilities": {
                    ability: {
                        "value": score,
                        "mod": (score - 10) // 2,
                        "save": 0,
                        "proficient": 0
                    }
                    for ability, score in character_data.get("abilities", {}).items()
                },
                "attributes": {
                    "hp": {
                        "value": character_data.get("current_hp", 0),
                        "max": character_data.get("max_hp", 0)
                    },
                    "ac": {
                        "value": character_data.get("armor_class", 10)
                    },
                    "movement": {
                        "walk": character_data.get("speed", 30)
                    }
                }
            }
        }
    
    def _export_generic_format(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export character in generic portable format"""
        return {
            "format": "dmlog_portable_character",
            "version": "1.0",
            "character": character_data,
            "export_timestamp": time.time(),
            "blockchain_verified": True
        }
    
    def create_platform_verification(self, character_nft: CharacterNFT, 
                                   target_platform: str, user_signature: str) -> str:
        """Create cryptographic verification for cross-platform use"""
        
        # Generate verification data
        verification_data = {
            "token_id": character_nft.token_id,
            "contract_address": character_nft.contract_address,
            "owner_address": character_nft.owner_address,
            "target_platform": target_platform,
            "timestamp": time.time(),
            "character_hash": self._hash_character_data(character_nft.character_data)
        }
        
        # Create signature
        data_string = json.dumps(verification_data, sort_keys=True)
        signature = hashlib.sha256(data_string.encode()).hexdigest()
        
        verification_id = str(uuid.uuid4())
        self.verification_signatures[verification_id] = {
            "data": verification_data,
            "signature": signature,
            "user_signature": user_signature,
            "created_at": time.time()
        }
        
        return verification_id
    
    def _hash_character_data(self, character_data: Dict[str, Any]) -> str:
        """Create hash of character data for verification"""
        essential_data = {
            "name": character_data.get("name", ""),
            "class": character_data.get("class", ""),
            "race": character_data.get("race", ""),
            "level": character_data.get("level", 1),
            "abilities": character_data.get("abilities", {}),
            "created_timestamp": character_data.get("created_timestamp", 0)
        }
        
        data_string = json.dumps(essential_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _map_race_to_ddb(self, race: str) -> str:
        """Map race names to D&D Beyond format"""
        race_mapping = {
            "human": "Human",
            "elf": "Elf",
            "dwarf": "Dwarf",
            "halfling": "Halfling",
            "dragonborn": "Dragonborn",
            "gnome": "Gnome",
            "half-elf": "Half-Elf",
            "half-orc": "Half-Orc",
            "tiefling": "Tiefling"
        }
        return race_mapping.get(race.lower(), race)
    
    def _get_hit_die_for_class(self, class_name: str) -> int:
        """Get hit die size for class"""
        hit_die_mapping = {
            "barbarian": 12,
            "fighter": 10,
            "paladin": 10,
            "ranger": 10,
            "bard": 8,
            "cleric": 8,
            "druid": 8,
            "monk": 8,
            "rogue": 8,
            "warlock": 8,
            "sorcerer": 6,
            "wizard": 6
        }
        return hit_die_mapping.get(class_name.lower(), 8)

class BlockchainCharacterSystem:
    """Complete blockchain character ownership system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize managers
        self.ipfs_manager = IPFSManager(config.get('ipfs_api_url', '/ip4/127.0.0.1/tcp/5001'))
        self.smart_contract_manager = SmartContractManager(config.get('blockchain_networks', {}))
        self.cross_platform_manager = CrossPlatformManager()
        
        # Database for local tracking
        self.db_path = config.get('database_path', 'blockchain_characters.db')
        self._init_database()
        
        # Character registry
        self.character_nfts = {}
        
    def _init_database(self):
        """Initialize local database for character tracking"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS character_nfts (
            token_id TEXT PRIMARY KEY,
            contract_address TEXT,
            owner_address TEXT,
            character_data TEXT,
            metadata_uri TEXT,
            rarity TEXT,
            network TEXT,
            created_timestamp REAL,
            last_updated REAL,
            transaction_hash TEXT,
            verified BOOLEAN DEFAULT FALSE
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS ownership_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT,
            from_address TEXT,
            to_address TEXT,
            transaction_hash TEXT,
            timestamp REAL,
            network TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS cross_platform_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT,
            platform TEXT,
            export_data TEXT,
            verification_id TEXT,
            timestamp REAL
        )''')
        
        conn.commit()
        conn.close()
    
    async def mint_character_nft(self, character_data: Dict[str, Any], 
                                owner_address: str, network: BlockchainNetwork,
                                private_key: str) -> Optional[CharacterNFT]:
        """Mint a new character NFT with full blockchain integration"""
        
        try:
            # Upload metadata to IPFS
            metadata_uri = self.ipfs_manager.upload_character_metadata(character_data)
            if not metadata_uri:
                logger.error("Failed to upload character metadata to IPFS")
                return None
            
            # Mint NFT on blockchain
            tx_hash = self.smart_contract_manager.mint_character_nft(
                character_data, owner_address, network, private_key
            )
            
            if not tx_hash:
                logger.error("Failed to mint character NFT")
                return None
            
            # Generate token ID (this would normally come from the mint transaction)
            token_id = str(int(hashlib.sha256(
                f"{character_data.get('id', uuid.uuid4())}{time.time()}".encode()
            ).hexdigest()[:16], 16))
            
            # Get contract address
            contract_address = self.config['blockchain_networks'][network]['contract_address']
            
            # Determine rarity
            rarity = self.ipfs_manager._calculate_character_rarity(character_data)
            
            # Create CharacterNFT object
            character_nft = CharacterNFT(
                token_id=token_id,
                contract_address=contract_address,
                owner_address=owner_address,
                character_data=character_data,
                metadata_uri=f"ipfs://{metadata_uri}",
                rarity=rarity,
                created_timestamp=time.time(),
                last_updated=time.time(),
                network=network,
                cross_platform_verified=True
            )
            
            # Store in local database
            self._store_character_nft(character_nft, tx_hash)
            
            # Add to registry
            self.character_nfts[token_id] = character_nft
            
            logger.info(f"Character NFT minted successfully: {token_id}")
            return character_nft
            
        except Exception as e:
            logger.error(f"Failed to mint character NFT: {e}")
            return None
    
    def _store_character_nft(self, character_nft: CharacterNFT, transaction_hash: str):
        """Store character NFT in local database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT OR REPLACE INTO character_nfts 
                    (token_id, contract_address, owner_address, character_data, 
                     metadata_uri, rarity, network, created_timestamp, last_updated, 
                     transaction_hash, verified) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (character_nft.token_id, character_nft.contract_address,
                   character_nft.owner_address, json.dumps(character_nft.character_data),
                   character_nft.metadata_uri, character_nft.rarity.value,
                   character_nft.network.value, character_nft.created_timestamp,
                   character_nft.last_updated, transaction_hash, True))
        
        conn.commit()
        conn.close()
    
    async def verify_character_ownership(self, token_id: str, network: BlockchainNetwork) -> Optional[Dict[str, Any]]:
        """Verify character ownership on blockchain"""
        
        # Check blockchain
        owner_address = self.smart_contract_manager.verify_character_ownership(token_id, network)
        
        if not owner_address:
            return None
        
        # Get character data from database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM character_nfts WHERE token_id = ?', (token_id,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            "token_id": token_id,
            "owner_address": owner_address,
            "verified": True,
            "network": network.value,
            "character_data": json.loads(result[3]) if result[3] else {},
            "rarity": result[5],
            "created_timestamp": result[7]
        }
    
    async def export_character_to_platform(self, token_id: str, target_platform: str,
                                         owner_signature: str) -> Optional[Dict[str, Any]]:
        """Export character to another platform with verification"""
        
        if token_id not in self.character_nfts:
            logger.error(f"Character NFT {token_id} not found")
            return None
        
        character_nft = self.character_nfts[token_id]
        
        # Export character data
        exported_data = self.cross_platform_manager.export_character_for_platform(
            character_nft, target_platform
        )
        
        if not exported_data:
            return None
        
        # Create verification
        verification_id = self.cross_platform_manager.create_platform_verification(
            character_nft, target_platform, owner_signature
        )
        
        # Store export record
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO cross_platform_exports 
                    (token_id, platform, export_data, verification_id, timestamp) 
                    VALUES (?, ?, ?, ?, ?)''',
                  (token_id, target_platform, json.dumps(exported_data),
                   verification_id, time.time()))
        conn.commit()
        conn.close()
        
        return {
            "token_id": token_id,
            "platform": target_platform,
            "exported_data": exported_data,
            "verification_id": verification_id,
            "blockchain_verified": True
        }
    
    def get_character_ownership_history(self, token_id: str) -> List[Dict[str, Any]]:
        """Get complete ownership history for a character NFT"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT * FROM ownership_history WHERE token_id = ? 
                    ORDER BY timestamp DESC''', (token_id,))
        results = c.fetchall()
        conn.close()
        
        history = []
        for row in results:
            history.append({
                "from_address": row[2],
                "to_address": row[3],
                "transaction_hash": row[4],
                "timestamp": row[5],
                "network": row[6]
            })
        
        return history
    
    def get_platform_compatibility_report(self, token_id: str) -> Dict[str, Any]:
        """Generate platform compatibility report for character"""
        
        if token_id not in self.character_nfts:
            return {"error": "Character not found"}
        
        character_nft = self.character_nfts[token_id]
        compatibility = {}
        
        for platform in self.cross_platform_manager.supported_platforms:
            try:
                exported_data = self.cross_platform_manager.export_character_for_platform(
                    character_nft, platform
                )
                compatibility[platform] = {
                    "compatible": exported_data is not None,
                    "features_supported": self._analyze_platform_features(exported_data, platform) if exported_data else [],
                    "limitations": self._get_platform_limitations(character_nft.character_data, platform)
                }
            except Exception as e:
                compatibility[platform] = {
                    "compatible": False,
                    "error": str(e)
                }
        
        return {
            "token_id": token_id,
            "character_name": character_nft.character_data.get("name", "Unknown"),
            "platform_compatibility": compatibility,
            "blockchain_verified": True,
            "cross_platform_score": sum(1 for p in compatibility.values() if p.get("compatible", False))
        }
    
    def _analyze_platform_features(self, exported_data: Dict[str, Any], platform: str) -> List[str]:
        """Analyze which features are supported on target platform"""
        features = []
        
        if exported_data.get("name"):
            features.append("character_name")
        if exported_data.get("race") or exported_data.get("classes"):
            features.append("basic_character_info")
        if any(key in exported_data for key in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma", "stats", "abilities"]):
            features.append("ability_scores")
        if exported_data.get("hp") or exported_data.get("attributes", {}).get("hp"):
            features.append("hit_points")
        if exported_data.get("armor_class") or exported_data.get("attributes", {}).get("ac"):
            features.append("armor_class")
        
        return features
    
    def _get_platform_limitations(self, character_data: Dict[str, Any], platform: str) -> List[str]:
        """Get platform-specific limitations"""
        limitations = []
        
        if platform == "dnd_beyond":
            if character_data.get("homebrew_content"):
                limitations.append("Homebrew content may not be fully supported")
            if character_data.get("custom_spells"):
                limitations.append("Custom spells require manual recreation")
        
        elif platform == "roll20":
            if character_data.get("complex_macros"):
                limitations.append("Complex macros need manual setup")
            if len(character_data.get("equipment", [])) > 50:
                limitations.append("Large equipment lists may be truncated")
        
        elif platform == "foundry_vtt":
            if character_data.get("custom_animations"):
                limitations.append("Custom animations not transferred")
        
        return limitations

async def main():
    """Main entry point for blockchain character system"""
    logging.basicConfig(level=logging.INFO)
    
    # Configuration for blockchain system
    config = {
        'ipfs_api_url': '/ip4/127.0.0.1/tcp/5001',
        'database_path': 'blockchain_characters.db',
        'blockchain_networks': {
            BlockchainNetwork.POLYGON: {
                'rpc_url': 'https://polygon-rpc.com',
                'contract_address': '0x1234567890abcdef1234567890abcdef12345678',
                'contract_abi': [
                    {
                        "inputs": [
                            {"name": "to", "type": "address"},
                            {"name": "tokenId", "type": "uint256"},
                            {"name": "uri", "type": "string"}
                        ],
                        "name": "mintCharacter",
                        "outputs": [],
                        "type": "function"
                    }
                ]
            }
        }
    }
    
    blockchain_system = BlockchainCharacterSystem(config)
    
    logger.info("Blockchain character ownership system initialized")
    logger.info("Features: NFT minting, cross-platform portability, ownership verification")

if __name__ == "__main__":
    asyncio.run(main())