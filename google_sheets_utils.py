import gspread
from oauth2client.service_account import ServiceAccountCredentials

def conectar_google_sheet(nombre_hoja, ruta_credenciales="credenciales.json"):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(ruta_credenciales, scope)
    client = gspread.authorize(credentials)
    return client.open(nombre_hoja).sheet1
