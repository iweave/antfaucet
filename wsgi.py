from main import app

if __name__ == '__main__':
    # Initialize database
    if prepare_faucet_database(faucetdb):
        app.run()
    else:
        print("Program terminated due to issues with price database")
