from model.gestionar_db import HandleDB
from werkzeug.security import check_password_hash

def check_user(username, passw):
    user = HandleDB()
    filter_user = user.get_only(username)
    
    if filter_user:
        if filter_user[5] == 0:  # Verifica si el estado es inactivo
            return False, None, None  # Usuario inactivo

        same_passw = check_password_hash(filter_user[5], passw)
        if same_passw:
            nombres = filter_user[1]
            apellidos = filter_user[2]
            return True, nombres, apellidos
    
    return False, None, None