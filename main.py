from email_message import email_message
import api_util as au
import csv
import os

def manage_csv_file(path: str, email_list: list):

    if os.path.exists(path):
        # Check if the file is empty
        if os.path.getsize(path) == 0:
            # If the file is empty, write the records from the list to it
            with open(path, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(['ID', 'Subject', 'Name', 'Email','Message','Label'])  # Write header
                for email in email_list:
                    if isinstance(email, email_message):
                        csv_writer.writerow([email.id, email.subject, email.by_name, email.by_email, email.message, email.label])
            return "Added registers correctly"
        else:
            # If the file is not empty, append records that are not repeated from the list to the csv
            existing_records = []
            with open(path, 'r', newline='') as csv_file:
                csv_reader = csv.reader(csv_file)
                next(csv_reader)
                for row in csv_reader:
                    id_num, subject, name, name_e, message, label = row
                    by = f"{name} <{name_e}>"
                    message = email_message(id_num, subject, by, message, label)
                    existing_records.append(message)
                    
            add_records = []
            repeated = False
            for email in email_list:
                for record in existing_records:
                    if record == email:
                        repeated = True
                        
                if not repeated:
                    add_records.append(email)
            
            if add_records:
                with open(path, 'a', newline='') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    for email in add_records:
                        csv_writer.writerow([email.id, email.subject, email.by_name, email.by_email, email.message, email.label])
                        
                return f"Added {len(add_records)} registers correctly"
            else:
                return "No records were added"
                
    else:
       # If the file doesn't exist, create it and print a message
        with open(path, 'w', newline='') as csv_file:
            
            return manage_csv_file(path, email_list)

    
if __name__ == '__main__':
    PATH = 'train_database.csv'
    email_number = input('Ingrese la cantidad de mensajes que quiere revisar (MAX: 200, MIN: 1)')
    user = au.gmail_credentials('credentials-unimed.json')
    emails = au.get_messages(user, int(email_number))
    print(manage_csv_file(PATH, emails))