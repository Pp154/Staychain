"""services/blockchain.py — web3.py smart contract interactions"""
import os, json
from web3 import Web3
from eth_account import Account
from datetime import datetime
from pathlib import Path

POLYGON_RPC         = os.getenv("POLYGON_MUMBAI_RPC","https://rpc-mumbai.maticvigil.com")
CONTRACT_ADDRESS    = os.getenv("CONTRACT_ADDRESS","")
BACKEND_PRIVATE_KEY = os.getenv("BACKEND_WALLET_PRIVATE_KEY","")
DEFAULT_HOST_WALLET = os.getenv("DEFAULT_HOST_WALLET","")
CHAIN_ID            = 80001

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

def _load_contract():
    if not CONTRACT_ADDRESS or not BACKEND_PRIVATE_KEY:
        return None
    try:
        abi_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "contracts" / "StayChainEscrow.json"
        if not abi_path.exists():
            # Try NextHome contract
            abi_path = Path(__file__).parent.parent.parent / "blockchain" / "artifacts" / "contracts" / "BookingEscrow.sol" / "BookingEscrow.json"
        if not abi_path.exists():
            print("⚠️  Contract ABI not found. Deploy first.")
            return None
        with open(abi_path) as f:
            data = json.load(f)
        abi = data.get("abi") or data
        return w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)
    except Exception as e:
        print(f"⚠️  Contract load failed: {e}")
        return None

contract = _load_contract()

async def create_blockchain_escrow(booking_id: str, booking_data: dict):
    from routes.booking import _bookings
    if not contract or not BACKEND_PRIVATE_KEY:
        print(f"⚠️  Blockchain not configured — skipping escrow for {booking_id}")
        if booking_id in _bookings:
            _bookings[booking_id]["blockchain_status"] = "skipped_not_configured"
        return
    try:
        account   = Account.from_key(BACKEND_PRIVATE_KEY)
        host      = Web3.to_checksum_address(DEFAULT_HOST_WALLET or account.address)
        checkin_ts  = int(datetime(*[int(x) for x in booking_data.get("checkin","2025-01-01").split('-')]).timestamp())
        checkout_ts = int(datetime(*[int(x) for x in booking_data.get("checkout","2025-01-02").split('-')]).timestamp())
        ipfs_cid  = booking_data.get("ipfs_cid","")
        amount_wei = w3.to_wei(0.01,"ether")  # testnet demo amount
        nonce = w3.eth.get_transaction_count(account.address)

        txn = contract.functions.createBooking(host, checkin_ts, checkout_ts, ipfs_cid).build_transaction({
            "from": account.address, "value": amount_wei,
            "gas": 300000, "gasPrice": w3.eth.gas_price, "nonce": nonce, "chainId": CHAIN_ID
        })
        signed  = w3.eth.account.sign_transaction(txn, BACKEND_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        onchain_id = None
        try:
            logs = contract.events.BookingCreated().process_receipt(receipt)
            if logs: onchain_id = int(logs[0]["args"]["bookingId"])
        except Exception: pass

        if booking_id in _bookings:
            _bookings[booking_id].update({
                "blockchain_status": "confirmed",
                "tx_hash": tx_hash.hex(),
                "onchain_booking_id": onchain_id,
                "block_number": receipt.blockNumber,
                "polygonscan_url": f"https://mumbai.polygonscan.com/tx/{tx_hash.hex()}"
            })
        print(f"✅ Escrow created: {tx_hash.hex()}")
    except Exception as e:
        print(f"❌ Blockchain escrow failed for {booking_id}: {e}")
        if booking_id in _bookings:
            _bookings[booking_id]["blockchain_status"] = f"failed:{str(e)[:80]}"

async def cancel_onchain_booking(booking_id: str, onchain_id: int):
    if not contract or not BACKEND_PRIVATE_KEY: return
    try:
        account = Account.from_key(BACKEND_PRIVATE_KEY)
        nonce   = w3.eth.get_transaction_count(account.address)
        txn = contract.functions.cancelBooking(onchain_id).build_transaction({
            "from": account.address, "gas": 200000,
            "gasPrice": w3.eth.gas_price, "nonce": nonce, "chainId": CHAIN_ID
        })
        signed  = w3.eth.account.sign_transaction(txn, BACKEND_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        from routes.booking import _bookings
        if booking_id in _bookings:
            _bookings[booking_id]["cancel_tx_hash"] = tx_hash.hex()
            _bookings[booking_id]["blockchain_status"] = "cancelled_onchain"
        print(f"✅ On-chain cancel: {tx_hash.hex()}")
    except Exception as e:
        print(f"❌ On-chain cancel failed: {e}")

async def get_onchain_booking(onchain_id: int):
    if not contract:
        raise Exception("Contract not configured")
    STATUS = ["PENDING","CONFIRMED","CHECKED_IN","CANCELLED","COMPLETED"]
    b = contract.functions.getBooking(onchain_id).call()
    return {"bookingId": str(b[0]), "guest": b[1], "host": b[2],
            "amountMatic": float(w3.from_wei(b[3],"ether")),
            "checkin": datetime.fromtimestamp(b[4]).isoformat(),
            "checkout": datetime.fromtimestamp(b[5]).isoformat(),
            "status": STATUS[b[6]], "ipfsCid": b[7],
            "createdAt": datetime.fromtimestamp(b[8]).isoformat()}

async def release_funds(onchain_id: int):
    if not contract or not BACKEND_PRIVATE_KEY:
        raise Exception("Contract not configured")
    account = Account.from_key(BACKEND_PRIVATE_KEY)
    nonce   = w3.eth.get_transaction_count(account.address)
    txn = contract.functions.releaseFunds(onchain_id).build_transaction({
        "from": account.address, "gas": 150000,
        "gasPrice": w3.eth.gas_price, "nonce": nonce, "chainId": CHAIN_ID
    })
    signed  = w3.eth.account.sign_transaction(txn, BACKEND_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return {"tx_hash": tx_hash.hex(), "block_number": receipt.blockNumber}
