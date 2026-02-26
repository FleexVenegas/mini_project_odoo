# Fill Rate - Módulo de Evaluación de Proveedores

## 🎯 Objetivo

Módulo de Odoo 17 que mide automáticamente el cumplimiento de proveedores comparando las **cantidades ordenadas** en Órdenes de Compra vs las **cantidades realmente recibidas** en Almacén.

## ¿Qué es el Fill Rate?

**Fill Rate = (Cantidad Recibida / Cantidad Ordenada) × 100**

Es el porcentaje que indica qué tan bien un proveedor cumple con lo que se le solicita.

### Ejemplo:

- **Ordenado**: 100 unidades
- **Recibido**: 92 unidades
- **Fill Rate**: 92%

## 🌟 Características Principales

### 1. Cálculo Automático

- Se crea un registro cuando se **confirma una Orden de Compra**
- Se actualiza automáticamente cuando se **valida una Recepción** en almacén
- No requiere entrada manual de datos

### 2. Clasificación ABC de Proveedores

Cada proveedor se clasifica automáticamente:

| Clasificación | Fill Rate | Descripción                       |
| ------------- | --------- | --------------------------------- |
| **A**         | ≥ 95%     | Excelente cumplimiento            |
| **B**         | 85% - 94% | Buen cumplimiento                 |
| **C**         | < 85%     | Cumplimiento deficiente           |
| **Nuevo**     | Sin datos | Proveedor sin órdenes completadas |

### 3. Historial Completo

- Registro detallado por cada línea de orden de compra
- Seguimiento de cantidades ordenadas vs recibidas
- Detección de origen (Manual, Bot, Sistema)

### 4. Integración Total

- **Módulo de Compras**: Lee órdenes automáticamente
- **Módulo de Almacén**: Actualiza con recepciones validadas
- **Ficha de Proveedor**: Muestra métricas directamente

## 📊 Vistas Disponibles

### En Contactos/Proveedores:

- **Botón de Fill Rate**: Muestra el porcentaje en la parte superior
- **Pestaña "Fill Rate"**: Estadísticas completas y clasificación
- **Historial integrado**: Últimas 10 órdenes en la ficha

### Menú "Fill Rate" (bajo Compras):

1. **Historial**: Todas las líneas de órdenes con su cumplimiento
2. **Clasificación de Proveedores**: Ranking de proveedores por desempeño

### Reportes:

- Vista Pivot para análisis multidimensional
- Gráficas de cumplimiento por proveedor
- Filtros por clasificación (A, B, C)

## 🔄 Flujo de Funcionamiento

```
1. Usuario crea Orden de Compra
   └─> Sistema registra: 100 unidades ordenadas

2. Orden se confirma
   └─> Se crea registro en fill.rate.line

3. Llega la mercancía
   └─> Usuario valida recepción: 92 unidades

4. Sistema actualiza automáticamente:
   ├─> Fill Rate de esa orden: 92%
   ├─> Fill Rate promedio del proveedor
   └─> Clasificación del proveedor (A/B/C)
```

## 🛠️ Modelos Técnicos

### `fill.rate.line`

Historial de cada línea de orden de compra:

- Proveedor, Orden, Producto
- Cantidades: ordenada, recibida
- Fill Rate calculado
- Estado y fechas

### `res.partner` (extendido)

Campos agregados:

- `fill_rate`: Porcentaje promedio
- `supplier_class`: Clasificación A/B/C
- `fill_rate_history_ids`: Relación con historial

### Hooks en:

- `purchase.order`: Al confirmar, crea registros
- `stock.picking`: Al validar recepción, actualiza cantidades

## ⚠️ Consideraciones

### Casos Especiales Manejados:

- ✅ Recepciones parciales (múltiples entregas)
- ✅ Órdenes canceladas (no se consideran)
- ✅ Diferentes unidades de medida
- ✅ Backorders automáticos

### Recálculo Automático:

- **Cron diario**: Recalcula fill rate de todos los proveedores
- **Manual**: Botón "Recalcular" en la ficha del proveedor

## 📈 Casos de Uso

1. **Evaluación de Proveedores**: Identificar quiénes cumplen mejor
2. **Negociaciones**: Datos objetivos para renegociar condiciones
3. **Selección de Proveedores**: Priorizar proveedores clase A
4. **Alertas**: Detectar proveedores con bajo desempeño (C)
5. **Auditorías**: Historial completo de cumplimiento

## 🚀 Instalación

1. El módulo ya está en la carpeta addons
2. Actualizar lista de módulos en Odoo
3. Instalar "Fill Rate - Supplier Performance"
4. El módulo se integra automáticamente con Compras

## 👥 Permisos

- **Usuario de Compras**: Lectura, escritura, creación
- **Gerente de Compras**: Todos los permisos
- **Usuario de Almacén**: Solo lectura

## 📝 Configuración

### Personalizar Umbrales (futuro):

Los umbrales de clasificación (95%, 85%) están actualmente en código.
En versiones futuras se podrán configurar desde Ajustes.

---

**Autor**: Diego Venegas  
**Versión**: 1.0  
**Odoo**: 17.0  
**Licencia**: LGPL-3
