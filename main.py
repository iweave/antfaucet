import logging
from flask import Flask,render_template,request,send_from_directory
from dotenv import load_dotenv
import time, datetime
import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import HTTPProvider, Web3
from web3.middleware import construct_sign_and_send_raw_middleware

from eth_defi.abi import get_deployed_contract
from eth_defi.token import fetch_erc20_details
from eth_defi.confirmation import wait_transactions_to_complete

from urllib.parse import urlencode
import requests, json, re
import sqlite3

logging.basicConfig(level=logging.INFO)

load_dotenv()

TOKEN_CHAIN_ID=421614
ERC_20_TOKEN_ADDRESS = "0xBE1802c27C324a28aeBcd7eeC7D734246C807194"
DEBUG_DRIP = 0.00000001
ETH_DRIP = .001
ANT_DRIP = .25

# What date to start checking for faucet drips
# Allows to report total ant/eth awarded without penalizing early tests
TIME_HORIZON = 1738085919

# Rate informaion in seconds
RATE_WINDOW = 60 * 60
RATE_LIMIT = 6

# Read and setup a local private key
private_key = os.environ.get("PRIVATE_KEY")
assert private_key is not None, "You must set PRIVATE_KEY environment variable"
assert private_key.startswith("0x"), "Private key must start with 0x hex prefix"

HCAPTCHA_KEY = os.environ.get('HCAPTCHA_KEY')
assert HCAPTCHA_KEY is not None, "You must set HCAPTCHA_KEY environment variable"
HCAPTCHA_SITEKEY = os.environ.get('HCAPTCHA_SITEKEY')
assert HCAPTCHA_SITEKEY is not None, "You must set HCAPTCHA_SITEKEY environment variable"


ALCHEMY_KEY = os.environ.get('API_KEY')
assert ALCHEMY_KEY is not None, "You must set API_KEY environment variable"

v2_url = "https://arb-sepolia.g.alchemy.com/v2/" + ALCHEMY_KEY
web3 = Web3(HTTPProvider(v2_url))
#print(f"Connected to blockchain, chain id is {web3.eth.chain_id}. the latest block is {web3.eth.block_number:,}")

# Connect to or create a SQLite3 database
faucetdb = sqlite3.connect('faucet.db', check_same_thread=False)

# Make sure Faucet Database is ready to store data
def prepare_faucet_database():

    # Get a cursor
    cur = faucetdb.cursor()

    # Check if we have a proper database
    try:
        cur.execute("SELECT * FROM faucet LIMIT 1")
     
        # storing the data in a list
        data_list = cur.fetchall() 
        # we survived, and ready roll
        return True       
    # Nope, lets try to set one up
    except sqlite3.OperationalError:
        try:
            # Try to create our table
            cur.execute("""CREATE TABLE IF NOT EXISTS faucet(
                        timestamp INTEGER,
                        wallet TEXT,
                        eth REAL,
                        ant REAL,
                        eth_tx TEXT,
                        ant_tx TEXT,
                        PRIMARY KEY (timestamp, wallet));""")
            # Insert a record
            cur.execute('''INSERT INTO faucet VALUES( 
                        0,'0xdead',0,0,'0xinit','0xinit')''') 
            # Save the changes
            faucetdb.commit()
            return True
        except sqlite3.Error as e:
            app.logger.info("And error occured with the db: " + str(e.args[0]))
            return False
 

# Drip coins to wallet
def drip_coins(wallet):
    #return {'status': True, 'eth_tx': '0xtest_harness', 'ant_tx': '0xtest_harness'}

    web3 = Web3(HTTPProvider(v2_url))

    account: LocalAccount = Account.from_key(private_key)
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))

    if not web3.is_checksum_address(wallet):
        return { "status": False, "reason": "value provided is not a valid wallet" }
    # We successfully connected to the Token chain
    if TOKEN_CHAIN_ID == web3.eth.chain_id:
        # Get users current status of token and their address
        erc_20 = get_deployed_contract(web3, "ERC20MockDecimals.json", ERC_20_TOKEN_ADDRESS)
        token_details = fetch_erc20_details(web3, ERC_20_TOKEN_ADDRESS)
        ant_balance = erc_20.functions.balanceOf(account.address).call()
        eth_balance = web3.eth.get_balance(account.address)
        decimal_eth_balance = eth_balance/(10**18)
        decimal_ant_balance = token_details.convert_to_decimals(ant_balance)
        # Make sure we have a balance to send
        if decimal_eth_balance < ETH_DRIP:
            return { "status": False, "reason": "Out of ETH"}
        if decimal_ant_balance < ANT_DRIP:
            return { "status": False, "reason": "Out of ANT"}
        #return { "status": True, "ant": ant_balance, "eth": eth_balance }
        # Convert a human-readable number to fixed decimal with 18 decimal places
        eth_amount = token_details.convert_to_raw(ETH_DRIP)
        eth_tx_hash = web3.eth.send_transaction({
                        "to": wallet,
                        "from": account.address,
                        "value": eth_amount,
                    })
        
        ant_amount = token_details.convert_to_raw(ANT_DRIP)
        ant_tx_hash = erc_20.functions.transfer(wallet, ant_amount).transact({"from": account.address})
        
        # Wait for the transactions to complete
        complete = wait_transactions_to_complete(web3, [eth_tx_hash, ant_tx_hash], max_timeout=datetime.timedelta(minutes=5))

        # Check our results
        for receipt in complete.values():
            if receipt.status != 1:
                return { "status": False, "reason": "transactions did not confirm" }
         
        return { "status": True, "eth_tx": eth_tx_hash.hex(), "ant_tx": ant_tx_hash.hex() }
    else:
        return { "status": False, "reason": "token is: "+web3.eth.chain_id}

# See if wallet has already received payments
def check_db_for_wallet(wallet):
    #return False
    # Get a cursor
    cur = faucetdb.cursor()
    
    # See if we get a cached record
    cur.execute("SELECT timestamp FROM faucet WHERE wallet = ? AND timestamp > ? LIMIT 1", [ wallet, str(TIME_HORIZON) ])
    cached_result = cur.fetchall()
    if cached_result:
        return True

# Check for volume of drips
def check_db_for_drips():
    #return False
    # Get a cursor
    cur = faucetdb.cursor()
    
    # Count successful drips
    cur.execute("SELECT count(timestamp) AS drips FROM faucet;")
    drips_result = cur.fetchall()
    if drips_result:
        #return { "status": False, "reason": drips_result }
        if int(drips_result[0][0]):
            # Return the number of records minus the inital test
            return { "status": True, "reason": drips_result[0][0]-1 }
    return { "status": False, "reason": "no results" }

# Check for velocity of drips
def check_db_for_rate():
    #return False
    # Get a cursor
    cur = faucetdb.cursor()
    
    # See if we get a cached record
    #cur.execute("SELECT count(timestamp) FROM faucet WHERE timestamp > ( unixepoch() - " + str(RATE_WINDOW) + ")")
    cur.execute("SELECT count(timestamp) AS drips FROM faucet WHERE timestamp > ( unixepoch() - ? )", [str(RATE_WINDOW)])
    cached_result = cur.fetchall()
    if cached_result:
        if int(cached_result[0][0]) >= int(RATE_LIMIT):
            return cached_result[0][0]
    return False

# Save wallet in db
def add_db(wallet,ant_tx,eth_tx):
    # Get a cursor
    cur = faucetdb.cursor()

    at = int(time.time())
    ant_drip = ANT_DRIP if ant_tx != '0xtest_harness' else 0.0
    eth_drip = ETH_DRIP if eth_tx != '0xtest_harness' else 0.0

    app.logger.info("Inserting: "+str(at)+" "+wallet)
    cur.execute("INSERT INTO faucet VALUES ( ?, ?, ?, ?, ?, ? );",
                [ at, wallet, eth_drip, ant_drip, eth_tx, ant_tx ])
    faucetdb.commit()

# Validate a h-captcha-response
def check_hcaptcha(captcha):
    #return True
    payload =  { "secret": HCAPTCHA_KEY,
                 "site-key": HCAPTCHA_SITEKEY,
                 "response": captcha }
    
    #return urlencode(payload)
    
    response = requests.post("https://api.hcaptcha.com/siteverify", 
                             data = payload )
    
    # Parse the json response
    #return(response.text)
    results = json.loads(response.text)

    if isinstance(results,dict) and \
        "success" in results and \
        results["success"]:
        return True
    else:
        return False

# Validate our form
def validate_request(form_data):

    # Did we get a hcaptcha to test?
    if "h-captcha-response" in form_data:
        captcha = check_hcaptcha(form_data["h-captcha-response"])
        if not captcha:
            return { "status": "fail", "reason": "Failed captcha" }
        #else:
        #    return [{ "captcha": captcha }]
    else:
        return { "status": "fail", "reason": "No captcha provided"}
    
    if "wallet" in form_data and \
        len(form_data["wallet"]) > 0 and \
        len(form_data["wallet"]) <= 42:
        # Sanitize input data
        wallet = re.sub(r"[^A-Fa-fXx0-9]+", '', form_data["wallet"])

        # See if this wallet has already suceeded
        if check_db_for_wallet(wallet):
            return { "status": "fail", "reason": "already received payout" }
        
        # Check for rate limit
        rate_limit = check_db_for_rate()
        if rate_limit:
            #return { "status": "fail", "reason": rate_limit }
            return { "status": "fail", "reason": "rate limit exceeded" }

        # OK let's drip
        results = drip_coins(wallet)
        app.logger.info("Returned from drip" + str(results))
        # What did we get back?
        if results and \
           isinstance(results, dict) and \
           "status" in results:
            # If we got a failure, just return the results
            if results["status"] != True:
                return results
            
            # Let's store our success
            add_db(wallet,results['ant_tx'],results['eth_tx'])
            results["Wallet"]=wallet
            #return { "status": "fail", "reason": "Always fail" }
            return results
        else:
            return { "status": "fail", "reason": "Drip crashed" }
    else:
        return { "status": "fail", "reason": "Invalid Wallet" }

app = Flask(__name__)

# Set a content length to protect from overflows
app.config['MAX_CONTENT_LENGTH'] = 1 * 1000 * 1000

@app.route('/')
def home():
    return render_template('form.html',sitekey=HCAPTCHA_SITEKEY)

@app.route('/form')
def form():
    return render_template('form.html',sitekey=HCAPTCHA_SITEKEY)

@app.route('/drips')
def drips():
        # Verify the request looks ok
        my_data = check_db_for_drips()

        if my_data["status"]!=True:
            return render_template('fail.html', results = my_data["reason"])
        else:
            return render_template('drips.html', results = my_data["reason"])
        
@app.route('/data/', methods = ['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is accessed directly. Try going to '/form' to submit form"
    if request.method == 'POST':
        # Get the form data
        form_data = request.form

        # Verify the request looks ok
        my_data = validate_request(form_data)

        if my_data["status"]!=True:
            return render_template('fail.html', results=my_data["reason"])

        return render_template('success.html', my_data = my_data)

# Load Browser Favorite Icon if accessed directly
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')
    
if __name__ == '__main__':
    # Initialize database
    if prepare_faucet_database():
        app.run(debug=True, host='0.0.0.0', port=5010)
    else:
        print("Program terminated due to issues with faucet database")
