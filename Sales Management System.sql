CREATE TABLE branches (
branch_id INT PRIMARY KEY,
branch_name VARCHAR (100),
branch_admin_name VARCHAR (100)
);


CREATE TABLE customer_sales (
sale_id INT PRIMARY KEY,
branch_id INT,
date DATE,
name VARCHAR(100),
mobile_number VARCHAR(15),
product_name VARCHAR(30),
gross_sales DECIMAL(12,2),
received_amount DECIMAL(12,2) DEFAULT 0,
pending_amount DECIMAL(12,2) GENERATED ALWAYS AS (gross_sales - received_amount) STORED,
staus VARCHAR(10) CHECK (staus in ('Open','Closed')),

CONSTRAINT F_Cust FOREIGN KEY (branch_id) REFERENCES branches (branch_id)
);



CREATE TABLE users(
user_id INT PRIMARY KEY,
username VARCHAR(100),
password VARCHAR(255),
branch_id INT,
role  VARCHAR(20) CHECK (role in ('Super Admin', 'Admin')),
email VARCHAR(255) UNIQUE,
CONSTRAINT F_User FOREIGN KEY (branch_id) REFERENCES branches (branch_id)
);




CREATE TABLE payment_splits(
payment_id SERIAL PRIMARY KEY,
sale_id INT,
payment_date DATE,
amount_paid DECIMAL(12,2),
payment_method VARCHAR(50),
CONSTRAINT F_Pay FOREIGN KEY (sale_id) REFERENCES customer_sales (sale_id)
);


CREATE OR REPLACE FUNCTION update_received_amount()
RETURNS TRIGGER AS pay
BEGIN
    UPDATE customer_sales
    SET received_amount = (
        SELECT SUM(amount_paid)
        FROM payment_splits
        WHERE sale_id = NEW.sale_id
    )
    WHERE sale_id = NEW.sale_id;

    RETURN NEW;
END;

CREATE TRIGGER payment_update
AFTER INSERT ON payment_splits
FOR EACH ROW
BEGIN
UPDATE customer_sales
SET received_amount = (
        SELECT sum(amount_paid)
FROM payment_splits
WHERE sale_id = NEW.sale_id
)
    WHERE sale_id = NEW.sale_id;
END














































