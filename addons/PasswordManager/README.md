# Password Manager for Odoo

## Descripción

Módulo de Odoo para gestionar y almacenar contraseñas de forma segura con encriptación AES-256 usando la librería Fernet.

## Características

- **Encriptación segura**: Utiliza Fernet (AES-256) para encriptar todas las contraseñas
- **Gestión de servicios**: Organiza contraseñas por servicio (Gmail, GitHub, AWS, etc.)
- **Control de acceso**: Dos niveles de permisos (Usuario y Administrador)
- **Validaciones de seguridad**:
  - Validación de longitud mínima de contraseña
  - Validación de formato de URL
  - Prevención de duplicados (servicio + usuario único)
- **Auditoría**: Registro de cambios y eliminaciones
- **Interfaz intuitiva**: Vistas kanban, lista y formulario
- **Generador de claves**: Genera claves de encriptación desde la configuración

## Instalación

1. Copiar el módulo en el directorio de addons de Odoo
2. Actualizar la lista de aplicaciones
3. Instalar "Password Manager"

### Dependencias

```bash
pip install cryptography
```

## Configuración

### 1. Configurar clave de encriptación (PRIMER PASO)

Después de instalar el módulo:

1. Ir a **Password Manager > Configuration**
2. Abrir la configuración por defecto
3. Hacer clic en **"Generate New Key"** para generar una clave segura automáticamente
4. Guardar la configuración
5. **⚠️ IMPORTANTE**: Hacer backup de esta clave en un lugar seguro. Si se pierde, no se podrán recuperar las contraseñas

### 2. Asignar permisos

Asignar usuarios a los grupos de seguridad:

- **Password Manager User**: Puede crear y gestionar contraseñas
- **Password Manager Administrator**: Puede administrar servicios y configurar la encriptación

## Uso

### Crear un servicio

1. Ir a **Password Manager > Services**
2. Crear un nuevo servicio con:
   - Nombre del servicio (ej: "Gmail Corporativo")
   - URL del servicio (ej: "https://mail.google.com")
   - Descripción opcional

### Agregar una contraseña

1. Ir a **Password Manager > Manage Passwords**
2. Crear un nuevo registro:
   - Seleccionar el servicio
   - Ingresar usuario/email
   - Ingresar contraseña (se encriptará automáticamente)
   - Agregar notas adicionales (opcional)

### Ver contraseñas

- En la vista kanban/lista, hacer clic en "Show password" para ver la contraseña desencriptada
- La contraseña se muestra en una ventana modal temporal

## Seguridad

### Buenas prácticas implementadas

1. **Encriptación**: Todas las contraseñas se encriptan antes de almacenarse
2. **Sin almacenamiento plano**: Nunca se almacenan contraseñas en texto plano
3. **Validación de entrada**: Se validan URLs y longitud de contraseña
4. **Constraints únicos**: Previene duplicados por servicio
5. **Auditoría**: Se registran las eliminaciones de contraseñas
6. **Permisos granulares**: Control de acceso por roles
7. **Prevención de copia**: No se copian contraseñas al duplicar registros

### Advertencias de seguridad

⚠️ **Backup de clave de encriptación**: Guardar la clave en un lugar seguro. Si se pierde, todas las contraseñas serán irrecuperables.

⚠️ **Cambio de clave**: NO cambiar la clave después de tener contraseñas almacenadas, o se perderá el acceso a ellas.

⚠️ **Acceso a base de datos**: Proteger el acceso directo a la base de datos de Odoo.

## Estructura del módulo

```
PasswordManager/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── password_manager_model.py      # Modelo principal
│   ├── password_services_model.py     # Gestión de servicios
│   ├── password_popup_model.py        # Popup para mostrar contraseñas
│   └── res_config_settings_model.py   # Configuración de encriptación
├── views/
│   ├── password_manager_view.xml
│   ├── password_services_view.xml
│   ├── password_popup_view.xml
│   └── res_config_settings_view.xml
├── security/
│   ├── password_manager_groups.xml    # Grupos de seguridad
│   └── ir.model.access.csv           # Permisos de acceso
└── static/
    └── src/
        └── scss/
            └── password_manager_css.scss  # Estilos personalizados
```

## Mejoras implementadas

### Modelos

- ✅ Índices en campos frecuentemente consultados
- ✅ Constraints SQL para prevenir duplicados
- ✅ Validaciones de dominio (@api.constrains)
- ✅ Orden por defecto optimizado
- ✅ Campos relacionados para evitar duplicación
- ✅ Logging de operaciones críticas
- ✅ Traducción con \_() para i18n

### Vistas

- ✅ Filtros de búsqueda avanzados
- ✅ Agrupación por servicio y fecha
- ✅ Widgets especializados (url, relative)
- ✅ Botones estadísticos en servicios
- ✅ Decoraciones visuales en listas
- ✅ Campos opcionales para personalización

### Seguridad

- ✅ Grupos de usuario y administrador
- ✅ Permisos granulares por modelo
- ✅ Validación de formato de clave
- ✅ Generador de claves seguras
- ✅ Prevención de eliminación con datos relacionados

## Licencia

LGPL-3

## Autor

**Ing. Diego Venegas**

GitHub: [FleexVenegas/mini_project_odoo](https://github.com/FleexVenegas/mini_project_odoo)
