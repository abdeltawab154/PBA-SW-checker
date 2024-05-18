import tkinter as tk
from tkinter import ttk, messagebox
import pymysql
import re
import configparser
from datetime import datetime, timedelta, date
import os

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the config file
config_file_path = os.path.join(current_dir, 'config.ini')

# Function to read configurations from config.ini
def read_config():
    config = configparser.ConfigParser()
    config.read(config_file_path)
    return config

config = read_config()

# Database connection details
DB_HOST = config['Database']['host']
DB_USER = config['Database']['user']
DB_PASSWORD = config['Database']['password']
DB_NAME = config['Database']['database']

# Table names
SW_VERSIONS_TABLE = config['Tables']['sw_versions_table']
TOP_MODELS_TABLE = config['Tables']['top_models_table']
PRODUCT_DETAILS_TABLE = config['Tables']['product_details_table']
PRODUCT_INFO_TABLE = config['Tables']['product_info_table']

# Column names
SW_COLUMNS = {
    'serial_number': config['Columns']['sw_versions_columns_serial_number'],
    'sw1': config['Columns']['sw_versions_columns_sw1'],
    'sw2': config['Columns']['sw_versions_columns_sw2'],
    'sw3': config['Columns']['sw_versions_columns_sw3'],
    'sw4': config['Columns']['sw_versions_columns_sw4'],
    'sw5': config['Columns']['sw_versions_columns_sw5'],
    'sw6': config['Columns']['sw_versions_columns_sw6'],
    'date_added': config['Columns']['sw_versions_columns_date_added']
}

TOP_MODELS_COLUMNS = {
    'serial_number': config['Columns']['top_models_columns_serial_number'],
    'top_model': config['Columns']['top_models_columns_top_model']
}

PRODUCT_DETAILS_COLUMNS = {
    'micom_code': config['Columns']['product_details_columns_micom_code'],
    'sw_version': config['Columns']['product_details_columns_sw_version'],
    'date': config['Columns']['product_details_columns_date']
}

PRODUCT_INFO_COLUMNS = {
    'top_model': config['Columns']['product_info_columns_top_model'],
    'sw_versions': config['Columns']['product_info_columns_sw_versions'],
    'micom_code': config['Columns']['product_info_columns_micom_code']
}

# Read the path of the text file from the configuration
text_file_path = config['File']['text_file_path']

# Function to fetch SW versions for a given serial number
def fetch_sw(serial_number):
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {SW_COLUMNS['sw1']}, {SW_COLUMNS['sw2']}, {SW_COLUMNS['sw3']}, {SW_COLUMNS['sw4']}, {SW_COLUMNS['sw5']}, {SW_COLUMNS['sw6']}
        FROM {SW_VERSIONS_TABLE} 
        WHERE {SW_COLUMNS['serial_number']} = %s
        ORDER BY {SW_COLUMNS['date_added']} DESC 
        LIMIT 1
    """, (serial_number,))
    result = cursor.fetchone()
    conn.close()
    return result

# Function to fetch top model for a given serial number
def extract_pba_code(serial_number):
    # Extract PBA code from serial number
    pba_code_match = re.search(r'^.{4}(.{10})', serial_number)
    if pba_code_match:
        pba_code = pba_code_match.group(1)
        formatted_pba_code = pba_code[:4] + "-" + pba_code[4:]
        print("Extracted PBA Code:", formatted_pba_code)
        return formatted_pba_code
    else:
        print("Failed to extract PBA code from the serial number.")
        return None


def fetch_top_model(serial_number):
    serial_number = extract_pba_code(serial_number)
    if serial_number:
        # Check if the top model exists in the database
        top_model = fetch_from_database(serial_number)
        if top_model:
            return top_model
        else:
            # If not found in the database, try fetching from text file
            top_model = fetch_from_text_file(serial_number)
            return top_model
    else:
        return None

def fetch_from_database(serial_number):
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    cursor.execute(f"SELECT {TOP_MODELS_COLUMNS['top_model']} FROM {TOP_MODELS_TABLE} WHERE {TOP_MODELS_COLUMNS['serial_number']}=%s", (serial_number,))
    result = cursor.fetchone()
    conn.close()
    return result

def fetch_from_text_file(serial_number):
    top_models_file = config['File']['top_models_file']
    # Assuming the text file has the format: serial_number,top_model
    with open(top_models_file, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            if parts[0] == serial_number:
                return parts[1:15]                 
    return None


# Function to check the validity of SW versions from a text file
def check_sw_validity_from_file(file_path, top_model, sw_versions):
    today = datetime.now().date()
    with open(file_path, 'r') as file:
        for line in file:
            row = line.strip().split(',')
            if len(row) == 6:  # Check if the row has all the expected columns
                if row[0] == top_model and row[2] in sw_versions:  # Check if the top model and SW version match
                    end_date_str = row[-1]  # Get the expiration date from the last column of the row
                    if end_date_str != "EXPIRY DATE":
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                        if end_date == date(9999, 12, 31) or (end_date - timedelta(days=3)) >= today:
                            return row[2], "Not Expired", end_date.strftime("%Y-%m-%d")
                        else:
                            return row[2], "Expired", end_date.strftime("%Y-%m-%d")
                    else:
                        return row[2], "No Expiration Date", ""
    return None, "Not Found", ""

# Function to get information and display SW dates, SW versions, and MICOM codes
def get_info():
    # Clear previous entries in the tables
 

    serial_number = entry_serial.get()
    if not serial_number:
        messagebox.showerror("Error", "Please enter a serial number")
        return
    
    sw_versions = fetch_sw(serial_number)
    if sw_versions:
        sw1_var.set(sw_versions[0])
        sw2_var.set(sw_versions[1])
        sw3_var.set(sw_versions[2])
        sw4_var.set(sw_versions[3])
        sw5_var.set(sw_versions[4])
        sw6_var.set(sw_versions[5])  


        top_model = fetch_top_model(serial_number)
        if top_model:
            top_model_var.set(top_model[0])

            # Check validity of SW versions from the text file
            valid_sw_versions = []
            for sw_version in sw_versions:
                version, expiration_status, end_date = check_sw_validity_from_file(text_file_path, top_model[0], sw_version)
                valid_sw_versions.append((expiration_status, end_date))
                if expiration_status == "Not Found":
                    check_labels[sw_versions.index(sw_version)].config(text=f"SW{sw_versions.index(sw_version) + 1}: {sw_version} - Incorrect or expire check with PIC", foreground="#FF9999")  # Light yellow text color
                elif expiration_status == "Not Expired":
                    check_labels[sw_versions.index(sw_version)].config(text=f"SW{sw_versions.index(sw_version) + 1}: {sw_version} (End Date: {end_date}) - Not Expired", foreground="#99FF99")  # Light green text color
                elif expiration_status == "Expired":
                    check_labels[sw_versions.index(sw_version)].config(text=f"SW{sw_versions.index(sw_version) + 1}: {sw_version} (End Date: {end_date}) - Expired", foreground="#FF9999")  # Light red text color
                else:
                    check_labels[sw_versions.index(sw_version)].config(text=f"SW{sw_versions.index(sw_version) + 1}: {sw_version} (End Date: {end_date}) - {expiration_status}", foreground="#FFFF99")  # Light yellow text color

            # Display SW versions for the fetched top model from the text file
            with open(text_file_path, 'r') as file:
                for line in file:
                    row = line.strip().split(',')
                    if len(row) == 6 and row[0] == top_model[0]:  # Check if the row has all the expected columns and matches the top model
                        tree_sw_versions.insert('', 'end', values=(row[2], row[4], row[5]))  # Insert SW version, start date, and end date into the treeview
        else:
            top_model_var.set("No top model found")
            for label in check_labels:
                label.config(text="")
    else:
        messagebox.showerror("Error", "Serial number not found")

# Create main window
root = tk.Tk()
root.title("PBA SW CHECKER")
root.configure(background="#282C34")

# Create labels, entry, and button widgets
label_header = tk.Label(root, text="PBA SW CHECKER", font=("Helvetica", 16, "bold"))
label_header.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky=tk.W+tk.E)
label_header.configure(foreground="#FFFFFF", background="#282C34")

label_serial = tk.Label(root, text="Enter Serial Number:", font=("Helvetica", 12))
label_serial.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
label_serial.configure(foreground="#C3DAE4", background="#282C34")

entry_serial = tk.Entry(root, font=("Helvetica", 12))
entry_serial.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
entry_serial.configure(foreground="#C3DAE4", background="#3E4452")

btn_get_info = tk.Button(root, text="Check", command=get_info, font=("Helvetica", 12))
btn_get_info.grid(row=1, column=2, padx=10, pady=10)
btn_get_info.configure(foreground="#FFFFFF", background="#007ACC")
btn_get_info.config(activebackground="#005F9E")

sw1_var = tk.StringVar()
sw2_var = tk.StringVar()
sw3_var = tk.StringVar()
sw4_var = tk.StringVar()
sw5_var = tk.StringVar() 
sw6_var = tk.StringVar() # Add sw5 variable

label_sw1 = tk.Label(root, text="Main Micom:", font=("Helvetica", 12))
label_sw1.grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
label_sw1_value = tk.Label(root, textvariable=sw1_var, font=("Helvetica", 12))
label_sw1_value.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)

label_sw2 = tk.Label(root, text="SUB MICOM:", font=("Helvetica", 12))
label_sw2.grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
label_sw2_value = tk.Label(root, textvariable=sw2_var, font=("Helvetica", 12))
label_sw2_value.grid(row=3, column=1, padx=10, pady=5, sticky=tk.W)

label_sw3 = tk.Label(root, text="OC SUB MICOM:", font=("Helvetica", 12))
label_sw3.grid(row=4, column=0, padx=10, pady=5, sticky=tk.W)
label_sw3_value = tk.Label(root, textvariable=sw3_var, font=("Helvetica", 12))
label_sw3_value.grid(row=4, column=1, padx=10, pady=5, sticky=tk.W)

label_sw4 = tk.Label(root, text="SUB OTP:", font=("Helvetica", 12))
label_sw4.grid(row=5, column=0, padx=10, pady=5, sticky=tk.W)
label_sw4_value = tk.Label(root, textvariable=sw4_var, font=("Helvetica", 12))
label_sw4_value.grid(row=5, column=1, padx=10, pady=5, sticky=tk.W)

label_sw5 = tk.Label(root, text="TCON DATA:", font=("Helvetica", 12))  # Add label for SW5
label_sw5.grid(row=6, column=0, padx=10, pady=5, sticky=tk.W)
label_sw5_value = tk.Label(root, textvariable=sw5_var, font=("Helvetica", 12))  # Add label for SW5
label_sw5_value.grid(row=6, column=1, padx=10, pady=5, sticky=tk.W)

label_sw6 = tk.Label(root, text="FW:", font=("Helvetica", 12))
label_sw6.grid(row=7, column=0, padx=10, pady=5, sticky=tk.W)
label_sw6_value = tk.Label(root, textvariable=sw6_var, font=("Helvetica", 12))
label_sw6_value.grid(row=7, column=1, padx=10, pady=5, sticky=tk.W)

top_model_var = tk.StringVar()
label_top_model = tk.Label(root, text="Top Model:", font=("Helvetica", 12))
label_top_model.grid(row=8, column=0, padx=10, pady=5, sticky=tk.W)
label_top_model_value = tk.Label(root, textvariable=top_model_var, font=("Helvetica", 12))
label_top_model_value.grid(row=8, column=1, padx=10, pady=5, sticky=tk.W)

check_labels = []
for i in range(6):  # Update the range to 5 for SW1-SW5
    label = tk.Label(root, text="", font=("Helvetica", 12), padx=10, pady=5)
    label.grid(row=11+i, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)
    label.configure(foreground="#99FF99", background="#282C34")  # Light green text color
    check_labels.append(label)

# Create Treeview widget for displaying SW dates, SW versions, and MICOM codes


# Define the style for the Treeview widget
style = ttk.Style()
style.theme_use("default")
style.configure("Treeview.Heading", foreground="#FFFFFF", background="#282C34", font=("Helvetica", 10, "bold"))
style.configure("Treeview", background="#353C48", foreground="#99FF99", rowheight=25, fieldbackground="#353C48", font=("Helvetica", 10))

# Create another Treeview widget for displaying SW versions for the fetched top model
tree_sw_versions = ttk.Treeview(root, columns=('SW Version', 'Start Date', 'End Date'), show='headings', height=10)
tree_sw_versions.heading('SW Version', text='SW Version')
tree_sw_versions.heading('Start Date', text='Start Date')
tree_sw_versions.heading('End Date', text='End Date')
tree_sw_versions.grid(row=18, column=0, columnspan=3, padx=10, pady=5, sticky=tk.W+tk.E)

# Define the style for the Treeview widget for SW versions
style_sw_versions = ttk.Style()
style_sw_versions.theme_use("default")
style_sw_versions.configure("Treeview.Heading", foreground="#FFFFFF", background="#282C34", font=("Helvetica", 10, "bold"))
style_sw_versions.configure("Treeview", background="#353C48", foreground="#99FF99", rowheight=25, fieldbackground="#353C48", font=("Helvetica", 10))

label_developer = tk.Label(root, text="SW Developer: Mohamed Abd EL-Tawab", font=("Helvetica", 12))
label_developer.grid(row=20, column=0, columnspan=3, padx=10, pady=10, sticky=tk.W)
label_developer.configure(foreground="#FFFFFF", background="#282C34")

# Run the application
root.mainloop()
