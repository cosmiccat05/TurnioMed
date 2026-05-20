#Voy a trasladar y dividir las vistas de view.py aqui, para mejor modularidad y manejo de codigo
#y pq es muy extenso y pesado, me pierdo teniendolo en un solo archivo.

#Aqui se importan todos los views :p
from .auth import landing, signin, signout
from .home import home
from .turnos import turnos
from .solicitudes import solicitudes
from .vacaciones import vacaciones
from .reportes import reportes