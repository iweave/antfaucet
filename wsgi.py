from main import app, prepare_faucet_database

if __name__ == "__main__":
    if prepare_faucet_database():
        app.run()
    else:
        print("Program terminated due to issues with faucet database")
