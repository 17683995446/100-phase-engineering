"""
区块链基础组件
提供区块、链、哈希和基本共识功能
"""
import hashlib
import json
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class Transaction:
    """交易"""
    tx_id: str
    from_addr: str
    to_addr: str
    amount: float
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "from": self.from_addr,
            "to": self.to_addr,
            "amount": self.amount,
            "timestamp": self.timestamp
        }
    
    def hash(self) -> str:
        """计算交易哈希"""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class Block:
    """区块"""
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }
    
    def calculate_hash(self) -> str:
        """计算区块哈希"""
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.hash() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine(self, difficulty: int = 4) -> None:
        """挖矿"""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()


class Blockchain:
    """区块链"""
    
    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = difficulty
        self._lock = threading.RLock()
        self._logger = get_logger("blockchain")
        
        # 创建创世区块
        self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        """创建创世区块"""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            previous_hash="0"
        )
        genesis.hash = genesis.calculate_hash()
        self.chain.append(genesis)
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """添加交易到待处理池"""
        with self._lock:
            self.pending_transactions.append(transaction)
        self._logger.info(f"Transaction added: {transaction.tx_id}")
        return True
    
    def mine_pending_transactions(self, miner_address: str) -> Block:
        """挖矿待处理交易"""
        with self._lock:
            # 添加矿工奖励
            reward_tx = Transaction(
                tx_id=f"reward-{time.time()}",
                from_addr="0",
                to_addr=miner_address,
                amount=1.0
            )
            
            transactions = self.pending_transactions + [reward_tx]
            
            block = Block(
                index=len(self.chain),
                timestamp=time.time(),
                transactions=transactions,
                previous_hash=self.chain[-1].hash
            )
            
            block.mine(self.difficulty)
            self.chain.append(block)
            self.pending_transactions = []
        
        self._logger.info(f"Block mined: {block.index}")
        return block
    
    def get_balance(self, address: str) -> float:
        """获取余额"""
        balance = 0.0
        
        with self._lock:
            for block in self.chain:
                for tx in block.transactions:
                    if tx.from_addr == address:
                        balance -= tx.amount
                    if tx.to_addr == address:
                        balance += tx.amount
        
        return balance
    
    def is_chain_valid(self) -> bool:
        """验证链有效性"""
        with self._lock:
            for i in range(1, len(self.chain)):
                current = self.chain[i]
                previous = self.chain[i - 1]
                
                if current.hash != current.calculate_hash():
                    return False
                
                if current.previous_hash != previous.hash:
                    return False
                
                if not current.hash.startswith("0" * self.difficulty):
                    return False
            
            return True
    
    def get_latest_block(self) -> Block:
        """获取最新区块"""
        with self._lock:
            return self.chain[-1]
    
    def get_block(self, index: int) -> Optional[Block]:
        """获取指定区块"""
        with self._lock:
            if 0 <= index < len(self.chain):
                return self.chain[index]
            return None
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """获取交易"""
        with self._lock:
            for block in self.chain:
                for tx in block.transactions:
                    if tx.tx_id == tx_id:
                        return tx
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "blocks": len(self.chain),
                "pending_transactions": len(self.pending_transactions),
                "difficulty": self.difficulty,
                "is_valid": self.is_chain_valid()
            }


# 全局实例
_blockchain: Optional[Blockchain] = None


def get_blockchain(difficulty: int = 2) -> Blockchain:
    """获取区块链"""
    global _blockchain
    if _blockchain is None:
        _blockchain = Blockchain(difficulty)
    return _blockchain
