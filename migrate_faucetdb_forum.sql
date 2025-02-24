-- Migrate DB
-- Adds transaction hashes to track forum authorized transactions
ALTER TABLE faucet ADD COLUMN author TEXT;
ALTER TABLE faucet ADD COLUMN badges TEXT;

CREATE INDEX IF NOT EXISTS author ON faucet(author);
