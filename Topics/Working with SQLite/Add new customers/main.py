# Put your code here
import sys

input_data = sys.stdin.read().strip()

customers = []
for line in input_data.split('\n'):
    CustomerName, Address, City, PostalCode, Country = line.split(';')
    customers.append((CustomerName, Address, City, PostalCode, Country))

cursor.executemany('INSERT INTO customers(CustomerName, Address, City, PostalCode, Country) VALUES (?,?,?,?,?)', customers)
con.commit()