"""
CSE310 Cloud Database Workshop

This program will allow you to manage inventory in a firestore Cloud
database.

Note that the add_new_item, add_inventory, and use_inventory functions are 
not currently protected by multiple users changing the database at the same time 
for the same item.  Transactions should be used as described here:

https://firebase.google.com/docs/firestore/manage-data/transactions

"""

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os

def initialize_firestore():
    """
    Create database connection
    """

    # Setup Google Cloud Key - The json file is obtained by going to 
    # Project Settings, Service Accounts, Create Service Account, and then
    # Generate New Private Key
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]  = "FirestoreKey.json"

    # Use the application default credentials.  The projectID is obtianed 
    # by going to Project Settings and then General.
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': 'firebasics-e0c4f',
    })

    # Get reference to database
    db = firestore.client()
    return db

def add_new_item(db):
    '''
    Prompt the user for a new item to add to the inventory database.  The
    item name must be unique (firestore document id).  
    '''

    name = input("Item Name: ")
    price = float(input("Price: "))
    popular = input("Is it popular (Y/N): ") in ['Y','y']
    qty = int(input("Initial Quantity: "))

    # Check for an already existing item by the same name.
    # The document ID must be unique in Firestore.
    result = db.collection("inventory").document(name).get()
    if result.exists:
      print("ERROR: Item alreay exists.")
      return
  
    # Build a dictionary to hold the contents of the firestore document.
    data = {"popular": popular, "price": price, "qty": qty}
    db.collection("inventory").document(name).set(data)
    # Save this in the log collection in Firestore       
    log_transaction(db, f"Added {name} with initial quantity {qty}")


def add_inventory(db):
    '''
    Prompt the user to add quantity to an already existing item in the
    inventory database.  
    '''

    name = input("Item Name: ")
    add_qty = int(input("Add Quantity: "))

    # Check for an already existing item by the same name.
    # The document ID must be unique in Firestore.
    result = db.collection("inventory").document(name).get()
    if not result.exists:
      print('ERROR: Item does not exist')
      return
    # Convert data read from the firestore document to a dictionary
    # db.collection("inventory").document(name).set() NOT USEFUL
    data = result.to_dict()
      
    # Update the dictionary with the new quanity and then save the 
    # updated dictionary to Firestore.
    data["qty"] += add_qty
    db.collection("inventory").document(name).set(data)
  
    # Save this in the log collection in Firestore
    log_transaction(db, f"Added {add_qty} {name}")


def use_inventory(db):
    '''
    Prompt the user to use quantity from an already existing item in the
    inventory database.  An error will be given if the requested amount
    exceeds the quanity in the database.
    '''

    name = input("Item Name: ")

    # Check for an already existing item by the same name.
    # The document ID must be unique in Firestore.
    result = db.collection("inventory").document(name).get()
    if not result.exists:
      print(f"{name} doesn't exist in the inventory")
      return

    use_qty = int(input("Use Quantity: "))

    # Convert data read from the firestore document to a dictionary
    data = result.to_dict()
    # Check for sufficient quantity.
    if use_qty > data["qty"]:
      print("You have an insufficient ammount for this")
      return

    # Update the dictionary with the new quanity and then save the 
    # updated dictionary to Firestore.
    data["qty"] -= use_qty
    db.collection("inventory").document(name).set(data)

    # Save this in the log collection in Firestore
    log_transaction(db, f"Used {use_qty} {name}")



def search_inventory(db):
    '''
    Search the database in multiple ways.
    '''

    print("Select Query")
    print("1) Show All Inventory")        
    print("2) Show Unstocked Inventory")
    print("3) Show Popular Inventory with Low Inventory")
    choice = input("> ")
    print()

    # Build and execute the query based on the request made
    if choice == "1":
        results = db.collection("inventory").get()
    elif choice == "2":
        results = db.collection("inventory").where("qty", "==", 0).get()
    elif choice == "3":
        results = db.collection("inventory").where("popular","==",True).where("qty","<",10).get()
    else:
        print("Invalid Selection")
        return
    
    # Display all the results from any of the queries
    print("")
    print("Search Results")
    print(f"{'Name':<20}  {'Price':<10}  {'Popular':<10}  {'Qty':<10}")
    for result in results:
        data = result.to_dict()
        try:
          print(f"{result.id:<20}  {data['price']:<10}  {data['popular']:<10}  {data['qty']:<10}")
        except:
          pass
    print()    

def log_transaction(db, message):
    '''
    Save a message with current timestamp to the log collection in the
    Firestore database.
    '''
    data = {"message": message, "timestampt": firestore.SERVER_TIMESTAMP}
    db.collection("log").add(data)

def notify_stock_alert(results, changes, read_time):
    '''
    If the query of out of stock items changes, then display the changes.
    ADDED = New out of stock item added to the list since registration
    MODIFIED = An out of stock item was modified but still out of stock
    REMOVED = An out of stock item is no longer out of stock
    '''
    for change in changes:
      if change.type.name == "REMOVED":
        print()
        print(f"OUT OF STOCK ALERT!! ORDER MORE: {change.document.id}")
        print()
      elif change.type.name == "ADDED":
        print()
        print(f"ITEM HAS BEEN RE-STOCKED!! READY TO USE: {change.document.id}")
        print()
      elif change.type.name == "MODIFIED":
        print()
        print(f"ITEM IS STILL OUT OF STOCK!! NONE LEFT: {change.document.id}")
        print()
        
    
def register_out_of_stock(db):
    '''
    Request a query to be monitored.  If the query changes, then the
    notify_stock_alert will be called.
    '''
    db.collection("inventory").where("qty", "==", 0).on_snapshot(notify_stock_alert)

def delete_document(db):
    #Get product name to delete
    name = input("What product would you like to delete?: ")

    # Check for an already existing item by the same name.
    # The document ID must be unique in Firestore.
    result = db.collection("inventory").document(name).get()
    if not result.exists:
      print('ERROR: Item does not exist')
      return

    #Delete item from the database
    try:
      db.collection("inventory").document(name).delete()
      print('Item succesfully removed from the Database!')
    except:
      print(f"Error: Cannot perform this action")

    #add action log to the database
    log_transaction(db, f"Removed {name} from inventory database")
    return
  


def main():
    db = initialize_firestore()
    register_out_of_stock(db)
    choice = None
    while choice != "0":
        print()
        print("0) Exit")
        print("1) Add New Item")
        print("2) Add Quantity")
        print("3) Use Quantity")
        print("4) Search Inventory")
        print("5) Remove Item")
        choice = input(f"> ")
        print()
        if choice == "1":
            add_new_item(db)
        elif choice == "2":
            add_inventory(db)
        elif choice == "3":
            use_inventory(db)
        elif choice == "4":
            search_inventory(db)             
        elif choice == "5":
            delete_document(db)

if __name__ == "__main__":
    main() 