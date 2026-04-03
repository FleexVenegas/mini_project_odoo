# Odoo WooCommerce Sync - Multi-Instance

Módulo de integración entre Odoo 17 y WooCommerce con soporte para múltiples instancias.

## Características

- **Multi-Instance Support**: Conecta múltiples tiendas WooCommerce simultáneamente
- **Sincronización de Órdenes**: Importa pedidos desde WooCommerce a Odoo
- **Gestión Centralizada**: Administra todas tus instancias desde un único panel
- **Tracking y Auditoría**: Seguimiento completo de cambios con chatter
- **Estado de Conexión**: Monitoreo del estado de cada instancia

## Instalación

1. Copia el módulo a tu carpeta de addons de Odoo
2. Actualiza la lista de aplicaciones
3. Instala el módulo "Odoo WordPress Sync"

## Configuración

### Crear una Instancia de WooCommerce

1. Ve a **OdooWpSync → Configuration → WooCommerce Instances**
2. Haz clic en "Crear"
3. Completa la información:
   - **Instance Name**: Nombre descriptivo (ej: "Tienda Principal")
   - **WordPress URL**: URL completa de tu tienda (ej: https://mitienda.com)
   - **Consumer Key**: Clave de consumidor de la API de WooCommerce
   - **Consumer Secret**: Secreto de consumidor de la API de WooCommerce

### Obtener Credenciales de WooCommerce

1. Accede al panel de administración de WordPress
2. Ve a **WooCommerce → Settings → Advanced → REST API**
3. Haz clic en "Add Key"
4. Configura:
   - **Description**: Odoo Integration
   - **User**: Usuario administrador
   - **Permissions**: Read/Write
5. Copia el Consumer Key y Consumer Secret generados

### Probar la Conexión

1. En el formulario de la instancia, haz clic en "Test Connection"
2. Verifica que el estado cambie a "Connected"

## Uso

### Sincronizar Órdenes

1. Ve a **OdooWpSync → Sincronizar Ahora**
2. Las órdenes se importarán automáticamente desde todas las instancias activas
3. Las órdenes se almacenarán con referencia a su instancia de origen

### Ver Órdenes por Instancia

1. Ve a **OdooWpSync → Orders**
2. Usa los filtros para ver órdenes de una instancia específica
3. Agrupa por "Instance" para organizar las órdenes

### Crear Pedidos de Venta en Odoo

1. Selecciona las órdenes de WooCommerce
2. Haz clic en "Crear Pedidos"
3. Se generarán automáticamente los pedidos de venta en Odoo

## Arquitectura

### Modelos Principales

- **woo.instance**: Gestiona las instancias de WooCommerce
- **odoo.wp.sync**: Almacena las órdenes sincronizadas
- **odoo.wp.sync.wc.api**: Servicio de API para comunicación con WooCommerce

### Características Técnicas

- Soporte multi-empresa
- SQL constraints para evitar duplicados por instancia
- API refactorizada para soportar instancias
- Backward compatibility con configuración legacy
- Mail tracking y chatter integration

## Versión

**v17.0.2.0.0** - Multi-Instance Support

## Autor

Diego Venegas - Depsistemas

## Licencia

LGPL-3
