CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
	aadhar_number VARCHAR(20) UNIQUE,
	pan_number VARCHAR(20) UNIQUE,
    date_of_birth DATE NOT NULL,
    address VARCHAR(200) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    country VARCHAR(50) DEFAULT 'India',
    credit_score INTEGER,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$')
);


CREATE INDEX idx_users_name ON users (last_name, first_name);
CREATE INDEX idx_users_location ON users (state, city);



-----Accounts Table -------
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('checking', 'savings', 'money_market', 'cd', 'ira')),
    current_balance DECIMAL(15, 2) DEFAULT 0.00 NOT NULL,
    available_balance DECIMAL(15, 2) DEFAULT 0.00 NOT NULL,
    open_date DATE DEFAULT CURRENT_DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'dormant', 'closed', 'frozen'))
);

CREATE INDEX idx_accounts_user ON accounts (user_id);
CREATE INDEX idx_accounts_type ON accounts (account_type);
CREATE INDEX idx_accounts_status ON accounts (status);

---Transactions Table----
CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    related_transaction_id INTEGER REFERENCES transactions(transaction_id),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal', 'transfer', 'payment', 'fee', 'interest')),
    amount DECIMAL(15, 2) NOT NULL,
    running_balance DECIMAL(15, 2) NOT NULL,
    description VARCHAR(200),
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    posted_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed', 'reversed')),
    merchant_name VARCHAR(100),
    merchant_category VARCHAR(50),
    reference_number VARCHAR(50),
    location VARCHAR(100),
    CONSTRAINT valid_amount CHECK (amount > 0)
);

CREATE INDEX idx_transactions_account ON transactions (account_id);
CREATE INDEX idx_transactions_date ON transactions (posted_date, transaction_date);
CREATE INDEX idx_transactions_type ON transactions (transaction_type);

----Cards Table---
CREATE TABLE cards (
    card_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    card_number VARCHAR(20) UNIQUE NOT NULL, 
    card_type VARCHAR(20) NOT NULL CHECK (card_type IN ('debit', 'credit', 'prepaid')),
    card_network VARCHAR(20) NOT NULL CHECK (card_network IN ('visa', 'mastercard', 'amex', 'discover')),
    expiration_date DATE NOT NULL,
    cvv VARCHAR(4) NOT NULL, 
    issue_date DATE DEFAULT CURRENT_DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'lost', 'stolen', 'expired', 'cancelled')),
    daily_limit DECIMAL(10, 2),
    pin_number VARCHAR(4),
    CONSTRAINT valid_expiry CHECK (expiration_date > CURRENT_DATE)
);

CREATE INDEX idx_cards_user ON cards (user_id);
CREATE INDEX idx_cards_account ON cards (account_id);

---Loans Table--

CREATE TABLE loans (
    loan_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    account_id INTEGER REFERENCES accounts(account_id),
    loan_type VARCHAR(30) NOT NULL CHECK (loan_type IN ('personal', 'mortgage', 'auto', 'student', 'business', 'home_equity')),
    loan_number VARCHAR(20) UNIQUE NOT NULL,
    original_amount DECIMAL(15, 2) NOT NULL,
    current_balance DECIMAL(15, 2) NOT NULL,
    interest_rate DECIMAL(6, 3) NOT NULL,
    term_months INTEGER NOT NULL,
    start_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    payment_frequency VARCHAR(15) DEFAULT 'monthly' CHECK (payment_frequency IN ('weekly', 'biweekly', 'monthly', 'quarterly')),
    next_payment_date DATE,
    next_payment_amount DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paid', 'delinquent', 'default', 'foreclosure')),
    collateral_description TEXT,
    CONSTRAINT valid_dates CHECK (maturity_date > start_date),
    CONSTRAINT valid_term CHECK (term_months > 0)
);

CREATE INDEX idx_loans_user ON loans (user_id);
CREATE INDEX idx_loans_status ON loans (status);
CREATE INDEX idx_loans_type ON loans (loan_type);


---Deposits Table---
CREATE TABLE deposits (
    deposit_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    deposit_type VARCHAR(20) NOT NULL CHECK (deposit_type IN ('cd', 'fixed', 'recurring')),
    deposit_number VARCHAR(20) UNIQUE NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    interest_rate DECIMAL(5, 3) NOT NULL,
    term_months INTEGER NOT NULL,
    start_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    interest_payout VARCHAR(20) DEFAULT 'at_maturity' CHECK (interest_payout IN ('monthly', 'quarterly', 'annually', 'at_maturity')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'matured', 'withdrawn', 'rolled_over')),
    auto_renewal BOOLEAN DEFAULT FALSE,
    early_withdrawal_penalty DECIMAL(5, 2),
    CONSTRAINT valid_deposit_dates CHECK (maturity_date > start_date)
);

CREATE INDEX idx_deposits_user ON deposits (user_id);
CREATE INDEX idx_deposits_account ON deposits (account_id);