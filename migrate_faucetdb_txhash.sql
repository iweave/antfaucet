-- Migrate DB
-- Adds transaction hashes to track hotwired transactions
ALTER TABLE faucet ADD COLUMN eth_tx TEXT;
ALTER TABLE faucet ADD COLUMN ant_tx TEXT;


