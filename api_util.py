from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from bs4 import BeautifulSoup
import re
import nltk 
from nltk.corpus import stopwords
from email_message import email_message


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_stopwords(lan : str = 'spanish'):
    
    nltk.download('stopwords', quiet= True)
    stw= stopwords.words(lan)
    
    return stw
    
    
def gmail_credentials(path_credentials: str):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token-unimed.json'):
        creds = Credentials.from_authorized_user_file('token-unimed.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                path_credentials, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token-unimed.json', 'w') as token:
            token.write(creds.to_json())
    # Call the Gmail API
    service = build('gmail', 'v1', credentials=creds)
    return service


def get_messages(service, num_messages: int):
    message_list = []
    try:
        results = service.users().messages().list(userId= 'me', labelIds=['INBOX']).execute()
        #Llamada para conseguir una lista de indices por mensaje, MAX=200
        messages = results.get('messages')
        max_messages = num_messages
        cont = 0
        for msg in messages:
            message_dict = {}
            #Llamada https para conseguir la informacion del mensaje dado el id 
            if cont == max_messages:
                break
            content = service.users().messages().get(userId='me', id=msg['id']).execute()
            message_id = msg['id']
            try:
                #Informacion del encabezado
                email_data = content['payload']['headers']
                asunto = "No Especificado"
                remitente = "No Especificado"
                for d in email_data:
                    if d['name'] == 'Subject':
                        asunto = d['value']
                    elif d['name'] == 'From':
                        remitente = d['value']
                #Información del correo
                temp_part = content['payload']['parts'][0]['body']
                if temp_part.get('size') == 0:
                    temp_part = content['payload']['parts'][0]['parts']
                    part = temp_part[0]['body']['data']
                else:
                    part = temp_part['data']
                    
                data = part.replace("-","+").replace("_","/")
                decoded_data = base64.b64decode(data)
                soup = BeautifulSoup(decoded_data , "lxml")
                body = soup.body()
                
                #Añadir registro de correo a lista
                message = email_message(message_id, asunto, remitente, content['snippet'], clean_string(str(body[0])))
                if forwarded_message(message.message):
                    message = manage_forwarded(message)
                    
                message_list.append(message)
                
            except Exception as e:
                print(e)
         
            cont += 1
            
        return message_list
         
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')
        
        
def clean_string(string: str):
    
    string = re.sub(r'<[^>]*>', '', string)
    
    # Remove links (URLs)
    string= re.sub(r'https?://\S+', '', string)
    
    # Remove double white spaces
    string = re.sub(r'\s+', ' ', string).strip()
    
    return string.split()


def forwarded_message(message_content: list):
    
    for word in message_content:
        if word == 'Forwarded':
            return True
    return False


def manage_forwarded(message: email_message):
    message = clean_forward_message_format(message)
    message = update_email_author(message)
    message.check_data_integrity()
    return message
    
    

def clean_forward_message_format(message: email_message):
        #Create list with the order of the message
    order = [('De:','From:'), ('Date:', 'Dia:'), ('Subject:', 'Asunto:'), ('To:', 'Para:')]
    specific_symbols = ('----------','---------','------------------------------','Forwarded', 'message')
    new_Message = []
    index = 0
    forwarded_part = False
    while index < len(message.message):
        if message.message[index] in order[0]:
            new_Message.clear()
            new_index = index + 1
            new_from = ""
            while message.message[new_index] not in order[1]:
                new_from += message.message[new_index] + " "
                new_index += 1
                
            new_index += 1
            new_Date = ""
            while message.message[new_index] not in order[2]:
                new_Date += message.message[new_index] + " "
                new_index += 1
                
            new_index += 1
            new_Subject = ""
            while message.message[new_index] not in order[3]:
                new_Subject += message.message[new_index] + " "
                new_index += 1
                
            index = new_index + 1
        else:
            if message.message[index] in specific_symbols:
                forwarded_part = True
            else:
                if forwarded_part:
                    new_Message.append(message.message[index].lower())
            index += 1
    
    message.subject = new_Subject.strip()
    #Call function to standarize the from message
    message.by_email = new_from.strip()
    message.by_name = new_from.strip()
    message.message = clean_forwarded_message(new_Message)
    
    return message
    
    
def clean_forwarded_message(message: list):
    #Crear nueva lista de palabras
    new_word_bag = []
    for word in message:
        #Crear directorios con strings predeterminados para limpiar
        text_symbols = ['+', '-', '*', '/', '%','==', '!=', '<', '>', '<=', '>=','=', '+=', '-=', 
                        '*=', '/=', '%=','&', '|', '^', '~', '<<', '>>',',', ':', ';', '.', '(', ')'
                        '[',']', '{', '}', ':']
        delete_word = False
        #Revise stopwords with nltk
        if not delete_word:
            stopwords = get_stopwords('spanish')
                
            for stopword in stopwords:
                if str(stopword) == word:
                    delete_word = True
                    break
        #Revise text symbols in unitary form
        if not delete_word:
            for symbol in text_symbols:
                if symbol == word:
                    delete_word = True
                    break
                
        #Revise if there is a extra email in the word_bag
        if not delete_word:
            if '@' in list(word):
                delete_word = True
            
        #If it passes all filters add to the new bag of words
        if not delete_word:
            new_word_bag.append(delete_extra_symbols(word.lower()))
                
        
    return new_word_bag
            
def delete_extra_symbols(working_string: str):
    pattern = r'^[*,.\-]*([\w\s]+)[*,.\-]*$'
    match = re.match(pattern, working_string)
    
    if match:
        clean_string = match.group(1)
        return clean_string
    else:
        return working_string
    
def update_email_author(message: email_message):
    if message.by_name == message.by_email:
        if ';' in message.by_name:
            try:
                #Manage domain email part
                mail_index = message.by_email.index('@')
                new_mail = message.by_email[mail_index:]
                message.by_email = new_mail[:-1]
                #Manage name part
                name_index = message.by_name.index(';')
                new_name = message.by_name[:name_index]
                message.by_name = new_name
            except ValueError:
                return message
            finally:

                return message
        else:
            #Find if the pattern is hidden in the snipet
            name_split = message.by_name.split()
            try:
                index = message.snippet.index(name_split[-1])
                cont = 0
                new_email = ""
                while cont < 2:
                    if message.snippet[index] == ';':
                        cont += 1
                    if message.snippet[index] != ';' and cont > 0:
                        new_email += message.snippet[index]
                    index += 1
                mail_index = new_email.index('@')
                message.by_email = new_email[mail_index:]
            except ValueError:
                message.by_email = None
                     
            finally:
                return message     
    else:
        return message
    
if __name__ == '__main__':
    print("This file is a module that only provides functionality")
    
        