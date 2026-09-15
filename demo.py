import pymysql
import sys
from tabulate import tabulate
import pandas as pd

try:
    # Establish the database connection
    connection = pymysql.connect(
        host="localhost",
        user="root",
        password="root",
        database="itemmaster"
    )
    cursor = connection.cursor()

    # List of valid unit names (corresponding to column names)
    unit_names = [
        'MHB1', 'MMB1', 'MWP1', 'MNB1', 'KMC1', 'MDP1', 'MGA1', 'MJP1', 'MSA1', 'MVJ1',
        'MHSR', 'MHVR', 'MHPK', 'MHPB', 'MHYP', 'MHHB', 'MHDB', 'MHMY', 'MHGG', 'MHP1',
        'MHGH', 'MHSL', 'MDHK', 'MSLA', 'MBBS', 'MMKA', 'MHKM', 'MEST', 'MPPP', 'MHNB', 'MHSB'
    ]
    while True:
        print("\nChoose an option:")
        print("T001. Search ITEM DATA(s)")
        print("T002. Insert new ITEM DATA")
        print("T003. Insert Bulk ITEM DATA ")
        print("T004. Delete ITEM DATA")
        print("T005. Update MRP & Purchase Price of ITEM DATA")
        print("T006. Exit")

        choice = input("Enter your choice Tcode: ").strip().upper()

        if choice == 'T001':  # Search ITEM CODE(s)
            print("Enter ITEM CODE(s) (you can paste multiple codes, separated by new lines):")
            item_codes_input = []
            while True:
                line = input()
                if line.strip() == '':  # Empty line to signal the end of input
                    break
                item_codes_input.append(line.strip())

            item_codes = [code.strip() for code in item_codes_input if code.strip()]

            unit_name = input("Enter UNIT NAME: ").strip()
            if unit_name not in unit_names:
                print(f"Invalid UNIT NAME: {unit_name}. Please enter a valid unit name.")
                continue

            placeholders = ', '.join(['%s'] * len(item_codes))
            query = f"""
            SELECT 
                `ITEM CODE`, 
                `HSN NO`, 
                `DESCRIPTION`, 
                `{unit_name}` AS Vendor_Code, 
                `Brand`, 
                `PRODUCT CODE`, 
                `Category`, 
                `MFG`, 
                `MRP_(FY-23-25)`, 
                `PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25)`, 
                `BUOM`, 
                `PACKING`, 
                `PUOM`
            FROM 
                itemdata 
            WHERE 
                `ITEM CODE` IN ({placeholders})
            """

            try:
                cursor.execute(query, item_codes)
                results = cursor.fetchall()

                if results:
                    headers = ["ITEM CODE", "HSN NO", "DESCRIPTION", "Vendor Code", "Brand", "PRODUCT CODE", "Category", "MFG", "MRP (FY-23-25)", "PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25)", "BUOM", "PACKING", "PUOM"]
                    table_data = [list(row) for row in results]
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                else:
                    print(f"No data found for ITEM CODE(s): {', '.join(item_codes)}")
            except pymysql.MySQLError as e:
                print(f"Error executing query: {e}")
        
        elif choice == 'T002':  # Insert new ITEM DATA
            try:
                columns = [
                    "FY","RC effective date from","End date","Type","MFG","ITEM CODE" ,"ARC No","DESCRIPTION","BUOM","PUOM","PACKING","BRAND","PRODUCT CODE", "HSN NO",
                    "MRP-FY-22-23","PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-22-23)","MRP_(FY-23-25)","PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25)",
                     "Category", "MHB1","MMB1","MWP1","MNB1","KMC1","MDP1","MGA1","MJP1","MSA1","MVJ1","MHSR","MHVR","MHPK","MHPB","MHYP","MHHB","MHDB","MHMY",
                     "MHGG","MHP1","MHGH","MHSL","MDHK","MSLA","MBBS","MMKA","MHKM","MEST","MPPP","MHNB","MHSB","CM TEAM HEAD","MHMR"
                ]

                numeric_fields = {
                    "MRP-FY-22-23", "PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-22-23)",
                    "MRP_(FY-23-25)", "PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25)"
                }
                data = {}

                for col in columns:
                    while True:
                        value = input(f"Enter {col}: ").strip()
                        if col in numeric_fields:
                            if value.replace(".", "", 1).isdigit():
                                data[col] = float(value)
                                break
                            else:
                                print(f"⚠️ Invalid input for {col}. Please enter a numeric value.")
                        else:
                            data[col] = value if value else None  # Store None for empty values
                            break
                while True:
            # Display entered data for confirmation
                    print("\n🔹 Please review the entered data:")
                    for col, val in data.items():
                        print(f"{col}: {val}")

                    confirm = input("\n✅ Confirm data? (yes/no/edit): ").strip().lower()
                    if confirm == "yes":
                        insert_query = f"""
                INSERT INTO itemdata ({', '.join(f'`{col}`' for col in columns)}) 
                VALUES ({', '.join(['%s'] * len(columns))})
                """
                        cursor.execute(insert_query, list(data.values()))
                        connection.commit()
                        print("✅ Data inserted successfully!")
                        break
                    elif confirm == "edit":
                        field_to_edit = input("Enter the field name you want to edit: ").strip()
                        if field_to_edit in data:
                            new_value = input(f"Enter new value for {field_to_edit}: ").strip()
                            if field_to_edit in numeric_fields:
                                if new_value.replace(".", "", 1).isdigit():
                                    data[field_to_edit] = float(new_value)
                                else:
                                    print(f"⚠️ Invalid input for {field_to_edit}. Keeping previous value.")
                            else:
                                data[field_to_edit] = new_value if new_value else None
                        else:
                            print("⚠️ Invalid field name. Please try again.")
                    elif confirm == "no":
                        print("❌ Data insertion canceled.")
                        break
                    else:
                        print("⚠️ Invalid choice. Please enter 'yes', 'no', or 'edit'.")

            except pymysql.MySQLError as e:
                print(f"❌ Error inserting data: {e}")

        elif choice == 'T003':
            try:
                columns = [
                     "FY","RC_effective_date_from", "End_date, Type", "MFG, ITEM_CODE", "ARC_No", 
                    "DESCRIPTION", "BUOM", "PUOM", "PACKING", "BRAND", "PRODUCT_CODE", "HSN_NO", 
                    "MRP_FY_22_23", "PURCHASE_PRICE_FY_22_23", "MRP_FY_23_25", "PURCHASE_PRICE_FY_23_25", 
                    "Category", "MHB1", "MMB1", "MWP1", "MNB1", "KMC1", "MDP1", "MGA1", "MJP1", "MSA1", 
                    "MVJ1", "MHSR", "MHVR", "MHPK", "MHPB", "MHYP", "MHHB", "MHDB", "MHMY", "MHGG", "MHP1", 
                    "MHGH", "MHSL", "MDHK", "MSLA", "MBBS", "MMKA", "MHKM", "MEST", "MPPP", "MHNB", "MHSB", 
                    "CM_TEAM_HEAD", "MHMR"
                ]
                numeric_fields = {
                    "MRP_FY_22_23", "PURCHASE_PRICE_FY_22_23", "MRP_FY_23_25", "PURCHASE_PRICE_FY_23_25"
                }

                print("\n Paste your data below (each row on a new line, values separated by TAB or COMMA):")
                print("⚠️ Press ENTER on an empty line to finish input.")

                data_rows = []
                while True:
                    line = input().strip()
                    if line == "":
                        break  
                    values = line.split("\t") if "\t" in line else line.split(",")
                    if len(values) < len(columns):
                        values.extend([""] * (len(columns) - len(values)))
                    elif len(values) > len(columns):
                        print(f"❌ Error: Too many values ({len(values)} instead of {len(columns)}). Please check your input.")
                        continue
                    for i, col in enumerate(columns):
                        if col in numeric_fields:
                            try:
                                values[i] = float(values[i]) if values[i] else None
                            except ValueError:
                                print(f"⚠️ Warning: Invalid numeric value '{values[i]}' in column '{col}'. Setting as NULL.")
                                values[i] = None
                    
                    data_rows.append(values)

                if data_rows:
                    print("\n🔹 Review your data before insertion:")
                    for row in data_rows:
                        print(row)
                    
                    confirm = input("✅ Confirm insert? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        insert_query = f"""
                        INSERT INTO itemdata ({', '.join(f'`{col}`' for col in columns)}) 
                        VALUES ({', '.join(['%s'] * len(columns))})
                        """
                        cursor.executemany(insert_query, data_rows)
                        connection.commit()
                        print("✅ Data inserted successfully!")
                    else:
                        print("❌ Insert operation canceled.")

            except pymysql.MySQLError as e:
                print(f"❌ Error inserting data: {e}")
                

        elif choice == 'T004': 
            try:
                mfg_name = input("Enter MFG name to delete all associated records: ").strip()
                if not mfg_name:
                    print("❌ MFG name cannot be empty.")
                    continue
                confirm = input(f"⚠️ Are you sure you want to delete all records for MFG '{mfg_name}'? (yes/no): ").strip().lower()
                if confirm != "yes":
                    print("❌ Deletion cancelled.")
                    continue
                delete_query = "DELETE FROM itemdata WHERE `MFG` = %s"
                cursor.execute(delete_query, (mfg_name,))
                rows_deleted = cursor.rowcount
                connection.commit()

                if rows_deleted > 0:
                    print(f"✅ Successfully deleted {rows_deleted} record(s) for MFG '{mfg_name}'.")
                else:
                    print(f"⚠️ No records found for MFG '{mfg_name}'.")

            except pymysql.MySQLError as e:
             print(f"❌ Error deleting data: {e}")

        elif choice == 'T005':  # Update MRP and Purchase Price
            try:
                print("\nEnter ITEM CODE for which you want to update values:")
                item_code = input("ITEM CODE: ").strip()

                # Check if ITEM CODE exists
                check_query = "SELECT `MRP_(FY-23-25)`, `PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25)` FROM itemdata WHERE `ITEM CODE` = %s"
                cursor.execute(check_query, (item_code,))
                existing_data = cursor.fetchone()
                if not existing_data:
                    print(f"❌ No data found for ITEM CODE: {item_code}")
                    continue
                print("\n🔹 Existing Values:")
                print(f"MRP_(FY-23-25): {existing_data[0]}")
                print(f"PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25): {existing_data[1]}")

                while True:
                    new_mrp = input("\nEnter new MRP_(FY-23-25): ").strip()
                    if new_mrp.replace(".", "", 1).isdigit():
                        new_mrp = float(new_mrp)
                        break
                    else:
                        print("❌ Invalid input! Please enter a numeric value.")

                while True:
                    new_price = input("Enter new PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25): ").strip()
                    if new_price.replace(".", "", 1).isdigit():
                        new_price = float(new_price)
                        break
                    else:
                        print("❌ Invalid input! Please enter a numeric value.")

                # Confirm update
                print("\n🔹 Updated Values:")
                print(f"MRP_(FY-23-25): {new_mrp}")
                print(f"PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25): {new_price}")

                confirm = input("\n✅ Confirm update? (yes/no): ").strip().lower()
                if confirm == "yes":
                    update_query = """
                    UPDATE itemdata 
                    SET `MRP_(FY-23-25)` = %s, 
                        `PURCHASE PRICE PER UNIT WITHOUT TAX FOR (FY-23-25)` = %s 
                    WHERE `ITEM CODE` = %s
                    """
                    cursor.execute(update_query, (new_mrp, new_price, item_code))
                    connection.commit()
                    print("✅ Data updated successfully!")
                else:
                    print("❌ Update operation canceled.")
            except pymysql.MySQLError as e:
                print(f"❌ Error updating data: {e}")

        
         
        elif choice == 'T006':  # Exit
            print("Exiting the program...")
            break

        else:
            print("Invalid choice. Please select a valid option.")

except pymysql.MySQLError as e:
    print(f"Error connecting to the database: {e}")

finally:
    # Close the connection
    if connection:
        connection.close()





































# # List of valid unit names (corresponding to column names)
# unit_names = [
#     'MHB1', 'MMB1', 'MWP1', 'MNB1', 'KMC1', 'MDP1', 'MGA1', 'MJP1', 'MSA1', 'MVJ1',
#     'MHSR', 'MHVR', 'MHPK', 'MHPB', 'MHYP', 'MHHB', 'MHDB', 'MHMY', 'MHGG', 'MHP1',
#     'MHGH', 'MHSL', 'MDHK', 'MSLA', 'MBBS', 'MMKA', 'MHKM', 'MEST', 'MPPP', 'MHNB', 'MHSB'
# ]

# while True:
#     # Take ITEM CODE input from the user
#     item_code = input("Enter ITEM CODE (or type 'exit' to quit): ")

#     # Exit condition: If the user types 'exit', break the loop
#     if item_code.lower() == 'exit':
#         print("Exiting the program...")
#         break

#     # Take UNIT NAME input from the user
#     unit_name = input("Enter UNIT NAME: ")

#     # Check if the entered unit name is valid
#     if unit_name not in unit_names:
#         print(f"Invalid UNIT NAME: {unit_name}. Please enter a valid unit name.")
#         continue

#     # Prepare the query to search for the entered ITEM CODE
#     query = """
#     SELECT 
#         `HSN NO`,
#         `DESCRIPTION`,
#         `{}`,  # This will dynamically get the column name from the unit name
#         'Category'

#     FROM 
#         itemdata 
#     WHERE 
#         `ITEM CODE` = %s
#     """.format(unit_name)  # Dynamically inserting the unit name into the query

#     # Execute the query with the given ITEM CODE
#     cursor.execute(query, (item_code,))

#     # Fetch the result
#     result = cursor.fetchall()

#     # Check if any result is returned
#     if result:
#         for row in result:
#             hsn_no = row[0]
#             description = row[1]
#             unit_value = row[2]  # Data from the dynamic column (MHB1, MMB1, etc.)
#             category=row[3]


            
#             print("\n--- Search Results ---")
#             print(f"HSN NO: {hsn_no}")
#             print(f"DESCRIPTION: {description}")
#             print(f"{unit_name}: {unit_value}\n")
#             print(f"Category:{category}")
#     else:
#         print(f"No data found for ITEM CODE: {item_code} and UNIT NAME: {unit_name}")

# Close the connection after the loop ends






 
 

 
       

        
       