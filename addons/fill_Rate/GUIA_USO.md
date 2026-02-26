# 🚀 Guía Rápida - módulo Fill Rate

## ✅ Instalación completada

El módulo **Fill Rate - Supplier Performance** ha sido instalado y actualizado correctamente en tu instancia de Odoo.

---

## 📍 Cómo acceder

### Opción 1: Desde el menú Compras

1. Ve a **Compras** en el menú principal
2. Verás una nueva sección: **Fill Rate**
3. Dentro encontrarás:
   - **Historial**: Todas las líneas de órdenes con su cumplimiento
   - **Clasificación de Proveedores**: Ranking de proveedores

### Opción 2: Desde la ficha del Proveedor

1. Ve a **Contactos** > Selecciona un proveedor
2. En la parte superior verás botones estadísticos con:
   - **Fill Rate %**: Porcentaje de cumplimiento
   - **Órdenes**: Contador de líneas evaluadas
3. Nueva pestaña: **Fill Rate** con toda la información

---

## 🎯 Flujo de Uso Normal

### Paso 1: Crear Orden de Compra (como siempre)

```
Compras > Órdenes de Compra > Crear
- Seleccionar proveedor
- Agregar productos y cantidades
- Confirmar orden
```

**Automático**: El sistema crea registros de Fill Rate para cada línea.

### Paso 2: Recibir Mercancía (como siempre)

```
Almacén > Operaciones > Recepciones
- Abrir la recepción relacionada
- Validar cantidades recibidas
- Hacer clic en "Validar"
```

**Automático**: El sistema actualiza:

- Cantidad recibida
- Fill Rate de esa orden
- Fill Rate del proveedor
- Clasificación del proveedor (A/B/C)

### Paso 3: Ver Resultados

```
Opción A: Compras > Fill Rate > Clasificación de Proveedores
Opción B: En la ficha de cada proveedor
```

---

## 📊 Interpretación de Clasificaciones

| Clase        | Fill Rate | Significado                       |
| ------------ | --------- | --------------------------------- |
| **A** 🟢     | ≥ 95%     | Proveedor excelente - Priorizar   |
| **B** 🟡     | 85-94%    | Buen proveedor - Confiable        |
| **C** 🔴     | < 85%     | Cumplimiento deficiente - Revisar |
| **Nuevo** ⚪ | Sin datos | Aún no hay órdenes completadas    |

---

## 🔍 Casos de Uso Prácticos

### 1. Evaluar un Proveedor antes de Comprar

```
1. Buscar el proveedor en: Compras > Fill Rate > Clasificación
2. Ver su Fill Rate histórico
3. Revisar su historial de órdenes
4. Tomar decisión informada
```

### 2. Identificar Proveedores Problemáticos

```
1. Compras > Fill Rate > Clasificación de Proveedores
2. Filtrar por "Clase C"
3. Ver lista de proveedores con bajo cumplimiento
4. Tomar acciones: negociar, cambiar proveedor, etc.
```

### 3. Reportes para Gerencia

```
1. Compras > Fill Rate > Historial
2. Cambiar a vista "Pivot" o "Gráfica"
3. Agrupar por proveedor, mes, etc.
4. Exportar o imprimir
```

### 4. Revisar Orden Específica

```
1. Abrir la Orden de Compra
2. Botón inteligente "Fill Rate" (se verá después de recepción)
3. Ver detalle de cumplimiento por producto
```

---

## ⚙️ Funciones Avanzadas

### Recalcular Fill Rate Manualmente

Si necesitas recalcular por alguna corrección:

```
1. Ir al proveedor
2. Pestaña "Fill Rate"
3. Botón "Recalcular Fill Rate"
```

### Tarea Programada

El sistema recalcula automáticamente el Fill Rate de todos los proveedores:

- **Frecuencia**: Diaria (1 vez al día)
- **Ubicación**: Configuración > Técnico > Automatización > Acciones Programadas
- **Nombre**: "Fill Rate: Recalcular automáticamente"

---

## 🎨 Colores en las Vistas

- **Verde**: Orden completa (100%)
- **Amarillo**: Orden parcial (< 100%)
- **Azul**: Exceso (> 100%)
- **Gris**: Pendiente de recibir

---

## ⚠️ Notas Importantes

1. **Los registros se crean automáticamente** al confirmar órdenes de compra
2. **Las actualizaciones son automáticas** al validar recepciones
3. **No requiere entrada manual** de datos
4. **Solo afecta órdenes nuevas**: Órdenes anteriores a la instalación no se registran automáticamente
5. **Respeta recepciones parciales**: Si recibes en múltiples veces, suma todas

---

## 🐛 Solución de Problemas

### "No veo Fill Rate en el proveedor"

✅ Asegúrate de que:

- El proveedor tenga al menos una orden de compra confirmada
- Seas usuario del grupo "Usuario de Compras" o superior

### "El Fill Rate no se actualiza"

✅ Verifica:

- Que la recepción esté completamente validada (estado "Hecho")
- Que la recepción esté vinculada a una orden de compra
- Espera la tarea programada o recalcula manualmente

### "El porcentaje parece incorrecto"

✅ Recuerda:

- Es un promedio ponderado de todas las órdenes
- Solo cuenta órdenes en estado "Compra" o "Hecho"
- Usa el botón "Recalcular" en caso de duda

---

## 📞 Soporte

Para consultas adicionales o personalizaciones:

- Revisar el código en `/addons/fill_Rate/`
- Consultar el README.md del módulo
- Contactar al desarrollador: Diego Venegas

---

**¡Listo para usar!** 🎉

El módulo está completamente funcional. Empieza a crear órdenes de compra y recibe mercancía como siempre, el sistema hará el resto automáticamente.
