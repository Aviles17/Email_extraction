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
                #Añadir registros al diccionario
                message_dict['ID'] = message_id
                message_dict['Subject'] = asunto
                message_dict['From'] = remitente
                message_dict['Snippet'] = content['snippet']
                message_dict['Message'] = clean_string(str(body[0]))
                #Añadir registro de correo a lista
                message_list.append(message_dict)
                
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


def forwarded_message(message: dict):
    word_bag = message['Message']
    for word in word_bag:
        if word == 'Forwarded':
            return True
    return False
    
    
def clean_messages(messages: list):
    for index, message in enumerate(messages):
        if forwarded_message(message):
            #Call function to update the state of the message params
            message = update_forwarded_message(message)
        #Crear directorios con strings predeterminados para limpiar
        text_symbols = ['+', '-', '*', '/', '%','==', '!=', '<', '>', '<=', '>=','=', '+=', '-=', 
                        '*=', '/=', '%=','&', '|', '^', '~', '<<', '>>',',', ':', ';', '.', '(', ')'
                        '[',']', '{', '}', ':']
            
        #Crear nueva lista de palabras
        new_word_bag = []
        for word in message['Message']:
            delete_word = False
            #Revise stopwords with nltk
            if not delete_word:
                stopwords = get_stopwords('spanish')
                
                for stopword in stopwords:
                    if str(stopword) == word:
                        delete_word = True
                        break
            #Revise text symbols i unitary form
            if not delete_word:
                for symbol in text_symbols:
                    if symbol == word:
                        delete_word = True
                        break
            #If it passes all filters add to the new bag of words
            if not delete_word:
                new_word_bag.append(word.lower())
                
        message['Message'] = clean_word_regex(new_word_bag, text_symbols)
        messages[index] = message
        
    return messages
            
     
def update_forwarded_message(message: dict):
    
    #Create list with the order of the message
    order = [('De:','From:'), ('Date:', 'Dia:'), ('Subject:', 'Asunto:'), ('To:', 'Para:')]
    specific_symbols = ('----------','---------','------------------------------','Forwarded', 'message')
    new_Message = []
    index = 0
    forwarded_part = False
    while index < len(message['Message']):
        if message['Message'][index] in order[0]:
            new_Message.clear()
            new_index = index + 1
            new_from = ""
            while message['Message'][new_index] not in order[1]:
                new_from += message['Message'][new_index] + " "
                new_index += 1
                
            new_index += 1
            new_Date = ""
            while message['Message'][new_index] not in order[2]:
                new_Date += message['Message'][new_index] + " "
                new_index += 1
                
            new_index += 1
            new_Subject = ""
            while message['Message'][new_index] not in order[3]:
                new_Subject += message['Message'][new_index] + " "
                new_index += 1
                
            index = new_index + 1
        else:
            if message['Message'][index] in specific_symbols:
                forwarded_part = True
            else:
                if forwarded_part:
                    new_Message.append(message['Message'][index].lower())
            index += 1
    
    message['Subject'] = new_Subject.strip()
    #Call function to standarize the from message
    message['From'] = from_standarization(new_from.strip())
    message['Message'] = new_Message
    
    new_snippet = ""
    for index, word in enumerate(new_Message):
        if index >= 9:
            break
        new_snippet += word + " "
    
    message['Snippet'] = new_snippet.strip()
    
    return message


def clean_word_regex(word_bag: list, special_characters: list):
    
    new_word_bag = []
    for word in word_bag:
        first = word[0]
        last = word[-1]
        if first in special_characters:
            word = word[1:]
        if last in special_characters:
            word = word[:-1]
        new_word_bag.append(word)         
    
    if len(new_word_bag) != 0:
        return new_word_bag
    else:
        raise ValueError 


def from_standarization(working_string: str):
    
    if ';' in working_string:
        parts = working_string.split(';')
        return f"{parts[0]} <{parts[1].strip()}>"
    else:
        return working_string
    
if __name__ == '__main__':
    print("This is a functional file, it shouldn't have any output")
        