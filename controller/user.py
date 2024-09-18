from model.gestionar_db import HandleDB
from werkzeug.security import generate_password_hash

class User():
  data_user = {}

  def __init__(self, data_user):
    self.db = HandleDB()
    self.data_user = data_user

  def create_user(self):
    # Verifica si el username ya existe
    existing_user = self.db.get_only(self.data_user["username"])
    if existing_user:
       return {"success": False, "message": "El usuario ya está creado en la base de datos"}
    
    # Añade ID y encripta contraseña
    self._add_id()
    self._passw_encrypt() # encrypt password
    self.db.insert(self.data_user) # Escribe en BD el nuevo usuario
    
    # Retorna True indicando éxito en la creación del usuario
    return {"success": True, "message": "Usuario creado exitosamente"}
    
  def _add_id(self):
    user = self.db.get_all()
    if user:
        one_user = user[-1]
        id_user = int(one_user[0])
        self.data_user["id"] = str(id_user + 1)
    else:
        # Si no hay usuarios en la base de datos, asigna el primer id como "1"
        self.data_user["id"] = "1"

  def _passw_encrypt(self):
    self.data_user["password_user"] = generate_password_hash(self.data_user["password_user"], "pbkdf2:sha256:30", 30)