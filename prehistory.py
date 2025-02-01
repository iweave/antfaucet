import sqlite3


tablet = [[1738051770,
           '0x9C1b147e73A46DDd1a59E3E00A2A88DFFA67e63e',
           0.00000001,
           0.00000001],
           [1738056280,
            '0x9C1b147e73A46DDd1a59E3E00A2A88DFFA67e63e',
           0.00000001,
           0.00000001],
           [1738056408,
            '0x9C1b147e73A46DDd1a59E3E00A2A88DFFA67e63e',
           0.00000001,
           0.00000001],
           [1738056785,
            '0x9C1b147e73A46DDd1a59E3E00A2A88DFFA67e63e',
           0.00000001,
           0.00000001],
           [1738059818,
            '0xBFB1Ef5fBEE8FB0538032b388ae8078e632d1fbc',
           0.00000001,
           0.00000001],
           [1738082794,
            '0x42f672872cB698998997C7e4fdd8F7Ec4549055b',
           0.00000001,
           0.00000001],
            [1738085919,
            '0x809E8F786dfbc17Ba7e6b7cc77c0B0f6B01505a0',
           0.00000001,
           0.00000001],
           ]

# Connect to or create a SQLite3 database
faucetdb = sqlite3.connect('faucet.db', check_same_thread=False)

# Compilable prepared statement
scribe = "INSERT INTO faucet VALUES ( ?, ?, ?, ?)"

# Get a cursor
cur = faucetdb.cursor()

# Iterate through the old data and write it to the database
for args in tablet:
    print(args)
    cur.execute(scribe, args)

faucetdb.commit()
