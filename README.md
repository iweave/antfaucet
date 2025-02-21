# antfaucet
Faucet for ERC-20/ETH


This is a sample Flask app to create a cryptocurrency faucet for a ERC-20 Token and ETH.

This faucet transfers ETH to enable the wallet to have gas to use with the ERC-20 tokens

There is a [blog post](https://blog.skillcadet.com/2025/02/02/Writing-a-faucet-dapp.html) that goes through the creation of this script.

### Environment variables

The example is designed to use with [Alchemy](https://alchemy.com) as an endpoint. Any other valid RPC endpoint should work.


The form uses a free [hcaptcha](https://hCaptcha.com/) [referral link](https://hCaptcha.com/?r=fcd32e73c291) to protect the front end.


The faucet also needs the private key of a funded wallet (both token and ETH).


These need to be passed as environment variables or in a .env file, do not commit them to github.

| ENV Variable     | Description                                            |
|------------------|--------------------------------------------------------|
| API_KEY          | Alchemy API Key                                        |
| PRIVATE_KEY      | The private key for a source wallet, starting with '0x'|
| HCAPTCHA_KEY     | hCaptcha backend API key                               |
| HCAPTCHA_SITEKEY | hCaptcha Web API key                                   |

The remaining configuration can be turned into environment variables or just changed in your code.

### ERC_TOKEN

ERC_20_TOKEN_ADDRESS is the address of the token we want to transfer.
TOKEN_CHAIN_ID is the chain ID of the Network (In this case Aribtrum Sepolia) that we are trying to connect to

```
TOKEN_CHAIN_ID=421614
ERC_20_TOKEN_ADDRESS = "0xBE1802c27C324a28aeBcd7eeC7D734246C807194"
```

### Faucet Size

ETH_DRIP and ANT_DRIP are the amounts of ETH and ERC-20 token to transfer when we award a drip.

If you set ETH_DRIP and ANT_DRIP to DEBUG_DRIP, you can change DEBUG_DRIP between tests to track your transactions on the blockchain explorer

```
DEBUG_DRIP = 0.00000001
ETH_DRIP = .001
ANT_DRIP = .25
```

### Time Horizon

TIME_HORIZON is the number of seconds since the unix epoch (Since January 1, 1970). Use it to reset the date of the faucet without deleting the database.

```
TIME_HORIZON = 1738085919
```

### Rate limit

These help protect the faucet from being drained all at once.  Initially it is configured to 6 drips per hour.


RATE_WINDOW is the number of seconds to look for transactions.


RATE_LIMIT is the maximum number of transactions in the RATE_WINDOW

```
RATE_WINDOW = 60 * 60
RATE_LIMIT = 6
```

### Other configuration options

v2_url is the Network API you are connecting to (This example uses the Alchemy endpoint which requires a key, which is free for small usage)

faucet.db is the name of the database file to store transactions.

```
v2_url = "https://arb-sepolia.g.alchemy.com/v2/" + ALCHEMY_KEY

faucetdb = sqlite3.connect('faucet.db', check_same_thread=False)
```

### templates/form.html

Modify this file to set the URL for the form submission.