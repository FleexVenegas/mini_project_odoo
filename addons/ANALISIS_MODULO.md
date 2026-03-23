# 📊 Análisis Profundo del Módulo: Costo Promedio Ponderado

**Fecha de análisis**: 4 de marzo de 2026  
**Autor**: Ing. Christian Padilla  
**Versión del módulo**: 17.0.1.0

---

## 🎯 Visión General

El módulo **modulo_costo_ponderado_stock** es un sistema sofisticado de gestión de precios que calcula y mantiene el costo unitario ponderado por producto basado en compras, con funcionalidades avanzadas de cálculo de precios de venta para múltiples listas de precios.

### Propósito Principal

- Calcular el costo unitario ponderado de cada producto basado en las compras confirmadas
- Actualizar automáticamente en cada entrada de compra
- Permitir regenerar los costos desde el histórico de compras
- Calcular precios de venta para 13+ listas de precios diferentes

---

## 🏗️ Arquitectura y Componentes Principales

### **1. Modelos Núcleo**

#### **stock.weighted** - Corazón del sistema

**Ubicación**: `models/stock_weighted.py`

**Campos principales**:

- `product_id`: Producto al que corresponde el costo
- `unit_weighted_cost`: Costo ponderado calculado
- `current_stock`: Stock actual del producto
- `currency_id`: Moneda de última compra (USD/MXN)
- `ultimo_tipo_cambio`: Tipo de cambio usado en el último cálculo
- `ultimo_calculo_date`: Fecha de última ponderación
- `order_id`: Orden de compra que originó el último cálculo

**Responsabilidades**:

- Almacenar el costo ponderado por producto
- Manejar conversiones de moneda (USD/MXN)
- Actualizarse automáticamente con cada entrada de compra
- Registrar tipo de cambio y fecha de última ponderación

---

#### **stock.move** (heredado)

**Ubicación**: `models/stock_weighted.py`

**Hook principal**: método `_action_done()`

**Flujo de ejecución**:

1. Intercepta movimientos de inventario de tipo 'incoming'
2. Verifica si el movimiento tiene una línea de compra asociada
3. Determina la moneda (USD o MXN) según el campo `es_dollar` de la orden
4. Llama a `_update_weighted_cost()` para recalcular el costo ponderado
5. Aplica automáticamente precios a todas las listas

**Escenarios de conversión soportados**:

- USD → USD: Mantiene USD como moneda base
- USD → MXN: Convierte a MXN si la nueva compra es mayor
- MXN → MXN: Promedio ponderado directo en MXN
- MXN → USD: Convierte todo a USD

---

#### **\_update_weighted_cost()** - Algoritmo de Ponderación

**Ubicación**: `models/stock_weighted.py` (líneas 63-164)

**Lógica principal**:

```python
# Caso 1: Sin stock anterior (empate_cantidades == 0)
# → Usar el costo de la compra directamente

# Caso 2: Con stock anterior
# → Calcular promedio ponderado según monedas:

# USD anterior → MXN nueva:
if cantidad_nueva < cantidad_anterior:
    # Mantener USD
else:
    # Convertir todo a MXN
    ponderado = ((cantidad_anterior * costo_anterior_en_mxn) +
                 (cantidad_nueva * costo_nuevo)) / total_qty

# MXN anterior → USD nueva:
# Convertir todo a USD
ponderado = ((cantidad_anterior * costo_anterior_en_usd) +
             (cantidad_nueva * costo_nuevo)) / total_qty

# Misma moneda:
ponderado = ((cantidad_anterior * costo_anterior) +
             (cantidad_nueva * costo_nuevo)) / total_qty
```

**Características**:

- Calcula stock actual consultando `stock.quant` en "ALMACEN CENTRAL"
- Compara cantidad recibida vs stock anterior
- Decide moneda resultante según predominancia de cantidades
- Redondea resultado a 2 decimales

---

#### **purchase.order** (heredado)

**Ubicación**: `models/purchase_order_dollar.py`

**Campos agregados**:

- `es_dollar`: Boolean que indica si la compra es en USD
- `valor_dollar`: Tipo de cambio al momento de la compra
- `precio_original`: Precio original (readonly)
- `valor_dolar_actual`: Valor del dólar de configuración global

**Hook**: `button_confirm()`

- Guarda histórico en `purchase.product.usd.history` o `purchase.product.mxn.history`
- Separa registros según moneda de compra
- Almacena usuario, proveedor, fecha, cantidad y precio unitario

---

### **2. Sistema de Pricing**

#### **pricing_tools.py** - Motor de cálculo

**Ubicación**: `models/pricing_tools.py`

**Funciones principales**:

##### `calcular_precio_debug(env, product, pricelist)`

Para productos comprados en **USD** o con cálculo estándar.

**Fórmula base**:

```python
if currency == 'USD':
    costo_val = ((base_cost * multiplicador + flete) * valor_dollar + cargo)
else:
    costo_val = (base_cost * multiplicador + flete + cargo)
```

**Variantes de fórmula por lista** (6 tipos):

1. **VAR_0 - HIGH RUNNER**:

   ```
   (costo * facturación * prima_riesgo) / denominador_785 / IVA
   ```

2. **VAR_1 - Listas corporativas** (EF, DSW, LMS, MLG, SOJ, ROFERI, PUBLI):

   ```
   (costo * facturación * prima_riesgo) / margen_bruto / IVA
   ```

3. **VAR_2 - PROMOLOGISTICS**:

   ```
   (costo * prima_riesgo) / margen_bruto / IVA
   ```

4. **VAR_3 - E-commerce** (Mercado Libre A/B, Walmart, Coppel, Liverpool):

   ```
   (costo * prima_riesgo) / margen_específico + envío
   ```

5. **VAR_4 - Mayoreo/Foráneo**:
   ```
   (costo / denominador_específico) / IVA
   ```

**Redondeo al 9**:
Aplica `redondeo_para_precios_finales()` que:

1. Multiplica por IVA (1.16)
2. Redondea hacia arriba al siguiente número terminado en 9
3. Divide por IVA para obtener el precio sin IVA

---

##### `calcular_precio_mxn_debug(env, product, pricelist)`

Para productos comprados en **MXN**.

**Fórmula**:

```python
precio_antes_redondeo = (base_cost / denominador_mxn) * IVA

# Aplicar redondeo al 9
precio_redondeado = redondear_a_9(precio_antes_redondeo)

# Volver a precio sin IVA
resultado = precio_redondeado / IVA
```

**Características**:

- Usa `denominador_pesos_mxn` (típicamente 0.9106)
- Siempre aplica redondeo al 9
- Más simple que la fórmula USD

---

#### **pricelist.ponderada**

**Ubicación**: `models/pricelist_ponderada.py`

Tabla intermedia que almacena precios calculados antes de aplicarlos.

**Campos principales**:

- `product_id`, `pricelist_id`: Relación producto-lista
- `price_calculated`: Precio calculado en MXN
- `base_cost`: Costo ponderado base (USD o MXN)
- `currency_id`: Moneda del costo
- `date_calculated`: Fecha de cálculo
- `date_applied`: Fecha de aplicación real
- `application_status`: Estado computado
- `designer`: Diseñador extraído del nombre
- `product_description_fixed`: Descripción corta
- `stock_central`, `stock_plaza_bonita`, etc.: Stocks por almacén (computados)

**Método principal**: `calcular_precios()`

1. Elimina todos los registros existentes
2. Itera sobre todos los productos con costo ponderado
3. Para cada producto, calcula precio en TODAS las listas
4. Guarda resultado en `pricelist.ponderada`
5. NO aplica a las listas automáticamente (solo calcula y muestra)

**Extracción de datos del nombre**:

```python
# De: "[REF] DESIGNER - Descripción corta"
# Extrae: designer = "DESIGNER", descripcion_corta = "Descripción corta"
match = re.search(r'\]\s*(.*?)\s*-\s*(.*)', name)
```

---

### **3. Configuración Global** (global.config)

**Ubicación**: `models/global_config.py`

**Patrón**: Singleton (solo puede existir un registro)

**Categorías de configuración**:

#### Costos y Conversiones:

- `valor_dollar`: Tipo de cambio USD/MXN (default: 22.0)
- `multiplicador_gral`: Multiplicador general (default: 1.1)
- `flete_americano`: Costo de flete (default: 0.25)
- `costo_importacion`: Factor de importación (default: 1.2)
- `costo_facturacion`: Factor de facturación (default: 1.035)
- `prima_riesgo_nacional`: Prima de riesgo (default: 1.1)

#### Denominadores por Lista:

- `denominador_785`: High Runner (default: 0.785)
- `denominador_pesos_mxn`: Para compras en MXN (default: 0.9106)
- `denominador_aromax_mayoreo`: (default: 0.89)
- `denominador_aromax_contado`: (default: 0.91)
- `denominador_medio_mayoreo`: (default: 0.855)
- `denominador_aromax_foraneo`: (default: 0.87)
- `denominador_ale_diaz`: (default: 0.95)

#### Márgenes:

- `margen_bruto`: (default: 0.7)
- `margen_f2_ml_minimo`: Mercado Libre A (default: 0.675)
- `margen_f3_ml_regular`: Mercado Libre B (default: 0.63)
- `margen_f4_walmart`: (default: 0.66)
- `margen_f5_coppel`: (default: 0.75)
- `margen_f5_liverpool`: (default: 0.55)
- `margen_hr`, `margen_7`, `margen_89`, `margen_95`: Otros márgenes

#### Costos de Envío E-commerce:

- `envio_ecommerce_h1`: (default: 140.00)
- `envio_ecommerce_h2`: (default: 99.00)
- `envio_ecommerce_h3`: (default: 83.00)
- `envio_ecommerce_h4`: (default: 105.00)

#### Cargos por Tipo:

- `kit_hr`: Valor importación kit (default: 45.0)
- `normal_hr`: Valor importación normal (default: 15.0)

#### IVA y Otros:

- `desgloce_iva`: Factor de IVA (default: 1.16)

#### Configuraciones de Negocio:

- `purchase_superusers`: Usuarios con permisos especiales
- `warehouse_id`: Almacén para ajustes
- `equipos_venta_excluidos`: Equipos excluidos de reportes
- Configuración de licitaciones (horarios, correos, fechas)

#### Herramientas:

- `sku_finder`: Campo para buscar SKU
- `input_refs`: Órdenes de compra para procesar

**Métodos útiles**:

- `get_solo_config()`: Obtiene o crea la configuración singleton
- `get_valor_dollar()`, `get_denominador_785()`, etc.: Getters individuales
- `action_calcular_precios_ponderada()`: Recalcula todas las listas
- `action_buscar_sku()`: Búsqueda de productos

---

### **4. Herramientas Complementarias**

#### **price_calculation_test** - Simulador

**Ubicación**: `models/price_calculation_test.py`

Wizard transient para simular cálculos.

**Campos de entrada**:

- `product_id`: Producto a probar
- `pricelist_id`: Lista de precios a calcular

**Campos de salida** (readonly):

- Todos los parámetros de la fórmula (A, B, C, D, E, F, G, H1)
- `resultado`: Precio calculado
- `formula_utilizada`: Identificador de variante
- `formula_completa`: Fórmula con valores sustituidos
- `error`: Si hubo algún error

**Método**: `ejecutar_prueba()`

- Llama a `calcular_precio_debug()` o `calcular_precio_mxn_debug()`
- Muestra todos los pasos del cálculo
- Permite ver exactamente cómo se calculó un precio

**Método**: `actualiza_lista()`

- Permite aplicar el precio calculado directamente a la lista
- Útil para correcciones manuales

---

#### **purchase_order_sku_cost_search** - Buscador de Costos

**Ubicación**: `models/purchase_order_sku_cost_search.py`

Wizard para buscar costos de productos en órdenes específicas.

**Funcionalidad**:

1. Seleccionar múltiples órdenes de compra confirmadas
2. Hacer clic en "Buscar"
3. Ver tabla con: Orden, Producto, SKU, Costo, Moneda
4. Exportar a Excel

**Líneas de resultado**:
Modelo `purchase.order.sku.cost.line` con:

- `search_id`: Referencia al wizard
- `order_id`: Orden de compra
- `product_id`: Producto
- `sku`: Código interno
- `cost`: Costo unitario
- `currency`: Moneda (USD/MXN)

---

#### **historico.calculo.precio** - Auditoría

**Ubicación**: `models/history_pricelist_calculate.py`

Modelo permanente que guarda cada cálculo de precio.

**Campos**:

- `product_id`, `pricelist_id`: Qué se calculó
- `costo`: Costo base usado
- `resultado`: Precio resultante
- `formula_utilizada`: Variante aplicada
- `formula_completa`: Fórmula con valores
- `valor_dollar`: Tipo de cambio usado
- `currency_name`: Moneda del costo
- `error`: Si hubo error
- `usuario_id`: Quién lo ejecutó
- `fecha`: Cuándo se ejecutó
- `order_id`: Orden de compra origen

**Utilidad**:

- Trazabilidad completa
- Debugging de cálculos pasados
- Auditoría de cambios de precios
- Análisis histórico de márgenes

---

#### **Wizards de Aplicación**

##### **pricelist_ponderada_set_price_wizard**

**Ubicación**: `models/wizard/pricelist_ponderada_set_price_wizard.py`

Permite establecer un precio igualitario a múltiples productos/listas.

**Uso**:

1. Seleccionar varios registros de `pricelist.ponderada`
2. Abrir wizard
3. Ingresar precio deseado
4. Aplicar → Todos los registros seleccionados tendrán ese precio

##### **pricelist_ponderada_apply_pricelist_wizard**

Aplica los precios calculados a las listas de precios reales.

##### **stock_weighted_manual_wizard**

Permite ajustar manualmente costos ponderados (casos especiales).

---

### **5. Controladores HTTP**

#### **PurchaseOrderSkuCostController**

**Ubicación**: `controllers/main.py`

**Ruta**: `/web/content/purchase.order.sku.cost.search/export_file/<int:search_id>`

**Función**:

- Descarga del archivo Excel generado por el wizard de búsqueda
- Responde con tipo MIME correcto
- Content-Disposition para forzar descarga

---

### **6. Vistas XML**

**Archivos en `views/`**:

- `purchase_order_views.xml`: Campos adicionales en órden de compra
- `stock_weighted_views.xml`: Vista de costos ponderados
- `global_config_views.xml`: Formulario de configuración
- `purchase_order_sku_cost_search_views.xml`: Wizard de búsqueda
- `pricelist_ponderada_views.xml`: Vista principal de precios calculados
- `pricelist_ponderada_set_price_wizard_views.xml`: Wizard de precio igualitario
- `pricelist_ponderada_apply_pricelist_wizard_views.xml`: Wizard de aplicación
- `price_calculation_test_views.xml`: Simulador de cálculos
- `stock_weighted_manual_wizard_views.xml`: Ajuste manual
- `history_pricelist_calculate.xml`: Histórico de cálculos

---

### **7. Seguridad**

**Archivo**: `security/ir.model.access.csv`

**Permisos actuales**:

- Todos los modelos principales: acceso total sin restricción de grupos
- Wizards: lectura/escritura/creación (sin eliminación)
- Histórico: usuarios normales solo lectura/creación, administradores todo

---

## ⚙️ Flujo de Funcionamiento Detallado

### **Flujo Principal: Recepción de Compra**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CONFIRMACIÓN DE ORDEN DE COMPRA                              │
│    purchase.order.button_confirm()                              │
│    ├─ Si es_dollar = True:                                      │
│    │   └─ Guardar en purchase.product.usd.history               │
│    └─ Si es_dollar = False:                                     │
│        └─ Guardar en purchase.product.mxn.history               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. RECEPCIÓN DE MERCANCÍA                                       │
│    Usuario valida picking de entrada                            │
│    └─ stock.picking.button_validate()                           │
│        └─ stock.move._action_done() se ejecuta                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. HOOK AUTOMÁTICO                                              │
│    stock.move._action_done() (OVERRIDE)                         │
│    ├─ Filtrar movimientos con picking_code = 'incoming'         │
│    ├─ Verificar que tenga purchase_line_id                      │
│    ├─ Obtener global.config.valor_dollar                        │
│    ├─ Determinar moneda (USD o MXN según es_dollar)             │
│    └─ Llamar _update_weighted_cost() por cada producto          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. CÁLCULO DE PONDERACIÓN                                       │
│    _update_weighted_cost(product, costo, cantidad, ...)         │
│    ├─ Consultar stock actual en ALMACEN CENTRAL                 │
│    ├─ Buscar registro stock.weighted existente                  │
│    │                                                             │
│    ├─ CASO A: No existe weighted                                │
│    │   └─ Crear nuevo con costo actual                          │
│    │                                                             │
│    ├─ CASO B: Stock anterior = 0 (empate_cantidades = 0)        │
│    │   └─ Reemplazar con costo actual                           │
│    │                                                             │
│    └─ CASO C: Hay stock anterior                                │
│        ├─ Obtener: costo_anterior, moneda_anterior, tc_anterior │
│        │                                                         │
│        ├─ ESCENARIO 1: USD anterior → MXN nueva                 │
│        │   ├─ Si nueva cantidad < cantidad anterior:            │
│        │   │   └─ Mantener USD y costo anterior                 │
│        │   └─ Si nueva cantidad >= cantidad anterior:           │
│        │       ├─ Convertir costo anterior a MXN                │
│        │       ├─ Promedio ponderado en MXN                     │
│        │       └─ Ajustar si resultado < costo nuevo            │
│        │                                                         │
│        ├─ ESCENARIO 2: MXN anterior → USD nueva                 │
│        │   ├─ Convertir costo anterior a USD                    │
│        │   ├─ Promedio ponderado en USD                         │
│        │   └─ Resultado final en USD                            │
│        │                                                         │
│        ├─ ESCENARIO 3: MXN anterior → MXN nueva                 │
│        │   ├─ Si nueva cantidad < cantidad anterior:            │
│        │   │   └─ Mantener costo anterior                       │
│        │   └─ Si nueva cantidad >= cantidad anterior:           │
│        │       └─ Promedio ponderado directo en MXN             │
│        │                                                         │
│        └─ ESCENARIO 4: USD anterior → USD nueva                 │
│            └─ Promedio ponderado directo en USD                 │
│                                                                  │
│    ├─ Redondear resultado a 2 decimales                         │
│    ├─ Actualizar stock.weighted:                                │
│    │   - unit_weighted_cost = ponderado                         │
│    │   - currency_id = moneda resultante                        │
│    │   - current_stock = total_qty                              │
│    │   - ultimo_tipo_cambio = tc_ponderado                      │
│    │   - ultimo_calculo_date = ahora                            │
│    │   - order_id = orden actual                                │
│    └─ Ajustar current_stock al valor real del sistema           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. APLICACIÓN AUTOMÁTICA A LISTAS                               │
│    _calculate_and_apply_new_price_to_pricelist(product, order)  │
│    ├─ Obtener stock.weighted del producto                       │
│    ├─ Buscar TODAS las product.pricelist                        │
│    └─ Para cada lista:                                          │
│        ├─ Si moneda = MXN:                                      │
│        │   └─ calcular_precio_mxn_debug()                       │
│        └─ Si moneda = USD:                                      │
│            └─ calcular_precio_debug()                           │
│        ├─ Agregar order_id a valores                            │
│        ├─ Guardar en historico.calculo.precio                   │
│        └─ Llamar _apply_price_to_pricelist()                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. ACTUALIZACIÓN DE PRODUCT.PRICELIST.ITEM                      │
│    _apply_price_to_pricelist(product, valores)                  │
│    ├─ Extraer pricelist_id y precio_final                       │
│    ├─ Buscar product.pricelist.item existente                   │
│    ├─ Si existe:                                                │
│    │   └─ Actualizar fixed_price                                │
│    └─ Si no existe:                                             │
│        └─ Crear nuevo item con:                                 │
│            - applied_on = '1_product'                            │
│            - compute_price = 'fixed'                             │
│            - fixed_price = precio_final                          │
└─────────────────────────────────────────────────────────────────┘
```

---

### **Flujo Alternativo: Cálculo Manual desde Interfaz**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USUARIO ACCEDE A CONFIGURACIÓN GLOBAL                        │
│    └─ Clic en botón "Calcular Precios Ponderada"                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. pricelist.ponderada.calcular_precios()                       │
│    ├─ Eliminar todos los registros de pricelist.ponderada       │
│    ├─ Obtener todos los stock.weighted                          │
│    ├─ Obtener todas las product.pricelist                       │
│    └─ Para cada weighted:                                       │
│        └─ Para cada pricelist:                                  │
│            ├─ Calcular precio (debug o mxn_debug)               │
│            ├─ Extraer diseñador y descripción del nombre        │
│            └─ Crear registro en pricelist.ponderada             │
│                (NO aplica a las listas reales)                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. USUARIO REVISA PRECIOS CALCULADOS                            │
│    ├─ Ve tabla con precios de todas las combinaciones           │
│    ├─ Puede filtrar, buscar, ordenar                            │
│    ├─ Ve stocks por almacén                                     │
│    └─ Ve diseñador y descripción                                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. APLICACIÓN MANUAL (OPCIONAL)                                 │
│    Usuario selecciona registros y usa wizard para aplicar       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💪 Puntos Fuertes

### **1. Automatización Completa** ⭐⭐⭐⭐⭐

- ✅ **Cálculo automático al recibir productos**: No requiere intervención manual
- ✅ **Actualización instantánea de todas las listas**: Un solo evento actualiza todo
- ✅ **Sin intervención manual requerida**: El flujo es completamente automático
- ✅ **Integración perfecta con Odoo**: Usa hooks nativos de stock.move

**Impacto**: Elimina errores humanos y garantiza consistencia en precios.

---

### **2. Manejo Multi-moneda Robusto** ⭐⭐⭐⭐⭐

- ✅ **Soporta USD y MXN nativamente**: Diseñado para operación binacional
- ✅ **Conversiones bidireccionales con lógica de negocio**: No solo convierte, aplica reglas
- ✅ **Registro del tipo de cambio histórico**: Trazabilidad del TC usado
- ✅ **Decisión inteligente de moneda predominante**: No fuerza una moneda arbitrariamente

**Ejemplo de lógica inteligente**:

```python
# Si la nueva compra es pequeña comparada con stock anterior,
# mantiene la moneda anterior para no distorsionar el costo
if cantidad_nueva < cantidad_anterior:
    mantener_moneda_anterior()
```

**Impacto**: Refleja la realidad del negocio con compras en múltiples monedas.

---

### **3. Trazabilidad Excepcional** ⭐⭐⭐⭐⭐

- ✅ **Histórico completo de cálculos**: Cada cálculo se guarda en `historico.calculo.precio`
- ✅ **Fórmulas detalladas guardadas**: No solo el resultado, sino cómo se llegó a él
- ✅ **Tracking de orden de compra origen**: Saber qué compra cambió el precio
- ✅ **Fecha y usuario de cada operación**: Auditoría completa
- ✅ **Valores de todos los parámetros**: A, B, C, D, E, F, etc. guardados

**Ejemplo de fórmula guardada**:

```
((5.50 * 1.1 + 0.25) * 22 + 15) = 148.15
(((148.15 * 1.035 * 1.1) / 0.785 / 1.16) = 185.37)
[REDONDEO] Precio con IVA actual: 215.03, ajustado a: 219, nuevo costo sin IVA: 188.79
```

**Impacto**: Permite debugging, auditoría y comprensión del sistema.

---

### **4. Flexibilidad de Configuración** ⭐⭐⭐⭐⭐

- ✅ **Todos los parámetros centralizados**: Un solo lugar de configuración
- ✅ **Sin código duro de márgenes**: Todo configurable desde interfaz
- ✅ **Fácil ajuste sin programación**: Usuario de negocio puede modificar
- ✅ **Patrón Singleton seguro**: No puede haber conflictos de configuración
- ✅ **40+ parámetros configurables**: Cubre todos los casos de negocio

**Ventaja competitiva**: El negocio puede ajustar márgenes en minutos, no días.

---

### **5. Herramientas de Diagnóstico** ⭐⭐⭐⭐⭐

- ✅ **Wizard de prueba con fórmulas visibles**: Ver exactamente cómo se calcula
- ✅ **Búsqueda de costos por orden**: Análisis rápido de compras
- ✅ **Exportación a Excel**: Reportes para análisis externo
- ✅ **Vista de simulación antes de aplicar**: Revisión previa a cambios

**Herramientas incluidas**:

1. **price.calculation.test**: Simulador paso a paso
2. **purchase.order.sku.cost.search**: Buscador de costos
3. **pricelist.ponderada**: Vista previa de precios calculados
4. **historico.calculo.precio**: Trazabilidad histórica

**Impacto**: Reduce tiempo de debugging de horas a minutos.

---

### **6. Redondeo Inteligente (Psicología de Precios)** ⭐⭐⭐⭐

- ✅ **Terminación en 9 para precios al público**: $189, $299, $449
- ✅ **Psicología de precios aplicada**: Percibido como más barato
- ✅ **Preserva márgenes tras redondeo**: Siempre redondea hacia arriba
- ✅ **Aplicado solo en paso final**: No distorsiona cálculos intermedios

**Algoritmo**:

```python
precio_con_iva = precio * 1.16  # Ej: 188.79 * 1.16 = 219.00
entero = int(precio_con_iva)     # 219
if entero % 10 != 9:
    precio_final = entero + (9 - entero % 10)  # 219 + 0 = 219
    # Pero si fuera 215, sería 215 + 4 = 219
```

**Impacto**: Precios más atractivos sin sacrificar márgenes.

---

### **7. Soporte Multi-lista Extensivo** ⭐⭐⭐⭐⭐

Soporta **13+ listas de precios** con fórmulas específicas:

**Categorías**:

- **Corporativas**: EF, DSW, LMS, MLG, SOJ, ROFERI, PUBLI
- **E-commerce**: Mercado Libre A/B, Walmart, Coppel, Liverpool
- **Mayoreo**: Obregón, Medio Mayoreo, Foráneo, Contado
- **Especiales**: High Runner, Promologistics, Ale Diaz

Cada una con:

- Denominador específico
- Márgenes diferenciados
- Costos de envío (para e-commerce)
- Lógica de facturación propia

**Impacto**: Un solo sistema maneja toda la complejidad de pricing.

---

### **8. Separación de Históricos USD/MXN** ⭐⭐⭐⭐

- ✅ **Tablas separadas**: `purchase.product.usd.history` y `purchase.product.mxn.history`
- ✅ **Consultas más eficientes**: No mezclar monedas en búsquedas
- ✅ **Reportes especializados**: Análisis por moneda más claros
- ✅ **Integridad de datos**: Campos específicos por moneda

**Impacto**: Mejora performance y claridad en reportes.

---

### **9. Campos Computados de Stock por Almacén** ⭐⭐⭐⭐

En `pricelist.ponderada`:

```python
stock_central = fields.Float(compute="_compute_stock_central")
stock_plaza_bonita = fields.Float(compute="_compute_stock_plaza_bonita")
stock_gran_patio = fields.Float(compute="_compute_stock_gran_patio")
stock_showroom_central = fields.Float(compute="_compute_stock_showroom_central")
stock_showroom_obregon = fields.Float(compute="_compute_stock_showroom_obregon")
```

**Ventaja**: Ver disponibilidad sin cambiar de vista, decisiones más informadas.

---

### **10. Diseño Modular y Extensible** ⭐⭐⭐⭐

- ✅ **pricing_tools.py separado**: Lógica de negocio reutilizable
- ✅ **Funciones puras**: `calcular_precio_debug()` no modifica estado
- ✅ **Fácil agregar nuevas listas**: Solo agregar elif en pricing_tools
- ✅ **Wizards separados**: Cada herramienta es independiente

**Impacto**: Fácil de extender y mantener.

---

## ⚠️ Puntos Críticos

### **1. Dependencia de "ALMACEN CENTRAL" Hardcodeado** 🔴

**Ubicación**: `models/stock_weighted.py:72`

```python
warehouse = self.env['stock.warehouse'].search([('name', '=', 'ALMACEN CENTRAL')], limit=1)
if not warehouse:
    raise UserError("No se encontró el almacén ALMACEN CENTRAL")
```

**Problemas**:

- Si renombran el almacén, el módulo deja de funcionar
- No hay configuración para cambiar el almacén
- Busca por nombre en vez de por ID o XML ID

**Impacto**: Fallo total del módulo si cambia el nombre del almacén.

**Solución propuesta**:

```python
# En global.config agregar:
warehouse_id = fields.Many2one('stock.warehouse', string='Almacén de Cálculo', required=True)

# En _update_weighted_cost():
config = self.env['global.config'].get_solo_config()
warehouse = config.warehouse_id
```

---

### **2. Método \_update_weighted_cost() Excesivamente Largo** 🔴

**Ubicación**: `models/stock_weighted.py:63-164` (101 líneas)

**Problemas**:

- Lógica compleja con anidamiento profundo
- Difícil de mantener y testear
- 4 escenarios de conversión mezclados
- Variables reutilizadas con significados diferentes

**Ejemplo de complejidad**:

```python
if moneda_anterior == 'USD' and currency.name == 'MXN':
    if(cantidad < cantidad_anterior - cantidad):  # ⚠️ Lógica confusa
        currency = self.env.ref('base.USD')
        ponderado = costo_anterior
        tipo_de_cambio_ponderado = tc_anterior
    else:
        costo_anterior = costo_anterior / tc_anterior  # Modifica variable
        ponderado = (cantidad_anterior * costo_anterior) + (cantidad * costo)
        ponderado = ponderado / total_qty
        currency = self.env.ref('base.MXN')
        if ponderado < costo:  # ⚠️ Ajuste no documentado
            ponderado = costo
        tipo_de_cambio_ponderado = 1.0
```

**Impacto**: Alto riesgo de bugs, difícil de debuggear.

**Solución propuesta**:

```python
def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar, order):
    """Método principal que delega según escenario"""
    weighted = self._get_or_create_weighted(product, costo, cantidad, currency, valor_dollar, order)

    if not weighted.unit_weighted_cost:
        return self._set_initial_cost(weighted, costo, currency, valor_dollar)

    if self._is_stock_empty(product):
        return self._replace_cost(weighted, costo, currency, valor_dollar)

    escenario = self._determinar_escenario(weighted.currency_id, currency)
    return self._calcular_segun_escenario(weighted, escenario, costo, cantidad, valor_dollar)

def _calcular_ponderado_usd_to_mxn(self, weighted, cantidad, costo, valor_dollar):
    """Lógica específica para conversión USD → MXN"""
    ...

def _calcular_ponderado_mxn_to_usd(self, weighted, cantidad, costo, valor_dollar):
    """Lógica específica para conversión MXN → USD"""
    ...

def _calcular_ponderado_misma_moneda(self, weighted, cantidad, costo):
    """Lógica para misma moneda"""
    ...
```

---

### **3. Nombres de Listas de Precios Hardcodeados** 🔴

**Ubicación**: `models/pricing_tools.py:64-130`

```python
if "HIGH RUNNER" in nombre_lista:
    resultado = (costo_val * D * E) / denominador_785 / G
elif nombre_lista in ["LISTA EF", "GRUPO COMERCIAL DSW", "LISTA LMS", ...]:
    resultado = (costo_val * D * E) / F1 / G
elif nombre_lista == "PROMOLOGISTICS":
    resultado = (costo_val * E) / F1 / G
elif nombre_lista in ["MERCADO LIBRE A", "MERCADO LIBRE B", ...]:
    ...
```

**Problemas**:

- Si renombran una lista, deja de calcular correctamente
- Difícil agregar nuevas listas (requiere código)
- No hay configuración visual de qué fórmula usa cada lista
- Case sensitive: "high runner" vs "HIGH RUNNER"

**Impacto**: Precios incorrectos si cambian nombres de listas.

**Solución propuesta**:
Crear modelo `pricelist.formula.config`:

```python
class PricelistFormulaConfig(models.Model):
    _name = 'pricelist.formula.config'

    pricelist_id = fields.Many2one('product.pricelist', required=True)
    formula_type = fields.Selection([
        ('var_0', 'HIGH RUNNER'),
        ('var_1', 'Corporativas'),
        ('var_2', 'PROMOLOGISTICS'),
        ('var_3', 'E-commerce'),
        ('var_4', 'Mayoreo/Foráneo'),
    ])
    denominador = fields.Float()
    margen = fields.Float()
    envio = fields.Float()
```

---

### **4. Sin Validación de Configuración Global** 🟡

**Problema**: No valida que exista global.config antes de usarla en varios lugares.

**Ejemplos**:

```python
# En stock.move._action_done():
global_config = self.env['global.config'].search([], limit=1)
if not global_config:
    raise UserError("No hay configuración global definida.")
```

Pero en otros lugares:

```python
# En pricing_tools.py:
global_config = env['global.config'].search([], limit=1)
# Usa global_config.valor_dollar sin verificar si existe
```

**Impacto**: Posibles errores crípticos si no existe configuración.

**Solución**:

```python
# Método centralizado en global.config:
@api.model
def get_solo_config(self):
    config = self.search([], limit=1)
    if not config:
        raise UserError("Configure el módulo desde Configuración Global")
    return config

# Usar en todos lados:
config = self.env['global.config'].get_solo_config()
```

---

### **5. Aplicación Automática Sin Control** 🟡

**Ubicación**: `models/stock_weighted.py:164`

```python
def _action_done(self, *args, **kwargs):
    res = super()._action_done(*args, **kwargs)
    # ...
    for move in self.filtered(lambda m: m.product_id):
        # ...
        self._calculate_and_apply_new_price_to_pricelist(product, order)
    return res
```

**Problemas**:

- Al recibir **cualquier** producto, recalcula **todas** las listas
- No hay opción de desactivar temporalmente
- No hay confirmación de usuario
- Podría causar recálculos no deseados durante importación masiva

**Impacto**: Posibles actualizaciones no deseadas, performance en importaciones.

**Solución propuesta**:

```python
# En global.config:
auto_calculate_prices = fields.Boolean(
    string='Calcular precios automáticamente',
    default=True,
    help='Si está activo, los precios se calculan al recibir productos'
)

# En _update_weighted_cost():
config = self.env['global.config'].get_solo_config()
if config.auto_calculate_prices:
    self._calculate_and_apply_new_price_to_pricelist(product, order)
```

---

### **6. Seguridad Permisiva** 🟡

**Ubicación**: `security/ir.model.access.csv`

```csv
access_stock_weighted,access_stock_weighted,model_stock_weighted,,1,1,1,1
access_pricelist_ponderada,access_pricelist_ponderada,model_pricelist_ponderada,,1,1,1,1
access_global_config,access_global_config,model_global_config,,1,1,1,1
```

**Problemas**:

- Todos los usuarios tienen permisos completos (read, write, create, unlink)
- No hay restricción por grupos
- Cualquiera puede modificar configuración global
- Cualquiera puede eliminar costos ponderados

**Impacto**: Riesgo de modificaciones o eliminaciones no autorizadas.

**Solución propuesta**:

```csv
# Usuario normal: solo lectura
access_stock_weighted_user,stock.weighted.user,model_stock_weighted,base.group_user,1,0,0,0
access_pricelist_ponderada_user,pricelist.ponderada.user,model_pricelist_ponderada,base.group_user,1,0,0,0

# Manager de inventario: read/write
access_stock_weighted_manager,stock.weighted.manager,model_stock_weighted,stock.group_stock_manager,1,1,1,0

# Administrador: todo
access_stock_weighted_admin,stock.weighted.admin,model_stock_weighted,base.group_system,1,1,1,1
access_global_config_admin,global.config.admin,model_global_config,base.group_system,1,1,1,1
```

---

### **7. Consultas SQL Directas No Utilizadas** 🟢

**Ubicación**: `models/pricelist_ponderada.py:87-103`

```python
# Se consultan compras de Itzel Partida
self.env.cr.execute("""
    SELECT pol.price_unit, po.date_order
    FROM purchase_order_line pol
    ...
    WHERE ... AND rp.name = %s
""", (product.id, 'Itzel Partida'))
last_purchase_itzel = self.env.cr.fetchone()

# Se consultan compras de Ricardo Partida
self.env.cr.execute("""
    ...
""", (product.id, 'Ricardo Partida'))
last_purchase_ricardo = self.env.cr.fetchone()

# ⚠️ NUNCA SE USAN estas variables
```

**Problemas**:

- Código muerto que confunde
- Queries ejecutándose innecesariamente
- Pérdida de performance leve
- Mantenimiento de código innecesario

**Impacto**: Confusión y performance levemente reducido.

**Solución**: Eliminar estas líneas o documentar por qué existen.

---

### **8. Falta de Manejo de Errores en Cálculos** 🟡

**Ubicación**: `models/stock_weighted.py:175-181`

```python
try:
    if weighted.currency_id.name == 'MXN':
        valores = calcular_precio_mxn_debug(self.env, product, pricelist)
    else:
        valores = calcular_precio_debug(self.env, product, pricelist)
    # ...
except Exception as e:
    _logger.warning(f"Error al calcular precio para {pricelist.name} - {product.name}: {str(e)}")
    continue  # 👈 Solo loguea y continúa
```

**Problemas**:

- Errores silenciosos sin notificación al usuario
- No se guarda en ningún lado que falló el cálculo
- Usuario no sabe que algunos precios no se actualizaron
- Difícil identificar qué productos tienen problemas

**Impacto**: Precios desactualizados sin que nadie lo sepa.

**Solución propuesta**:

```python
# Crear modelo de errores
class PriceCalculationError(models.Model):
    _name = 'price.calculation.error'

    product_id = fields.Many2one('product.product')
    pricelist_id = fields.Many2one('product.pricelist')
    error_message = fields.Text()
    date = fields.Datetime(default=fields.Datetime.now)
    resolved = fields.Boolean(default=False)

# En el try/except:
except Exception as e:
    self.env['price.calculation.error'].create({
        'product_id': product.id,
        'pricelist_id': pricelist.id,
        'error_message': str(e),
    })
    _logger.error(f"Error calculando precio: {str(e)}")
```

---

### **9. Sin Validación de Valores Negativos** 🟡

No hay constraints para evitar:

- Costos negativos en `stock.weighted`
- Precios negativos en `pricelist.ponderada`
- Cantidades negativas en cálculos

**Impacto**: Posibles datos inconsistentes.

**Solución**:

```python
@api.constrains('unit_weighted_cost')
def _check_cost_positive(self):
    for rec in self:
        if rec.unit_weighted_cost < 0:
            raise ValidationError("El costo ponderado no puede ser negativo")

@api.constrains('price_calculated')
def _check_price_positive(self):
    for rec in self:
        if rec.price_calculated < 0:
            raise ValidationError("El precio calculado no puede ser negativo")
```

---

### **10. Falta de Índices en Búsquedas Frecuentes** 🟢

Búsquedas frecuentes sin índices explícitos:

```python
weighted = Weighted.search([('product_id', '=', product.id)], limit=1)
```

Aunque `product_id` tiene `index=True`, otras búsquedas podrían beneficiarse:

```python
# En historico.calculo.precio:
product_id = fields.Many2one('product.product', index=True)  # ✅ Agregar índice
pricelist_id = fields.Many2one('product.pricelist', index=True)  # ✅ Agregar índice
order_id = fields.Many2one('purchase.order', index=True)  # ✅ Agregar índice
```

**Impacto**: Performance levemente reducida en búsquedas.

---

## 🚀 Oportunidades de Mejora

### **Prioridad Alta 🔴 (Impacto inmediato)**

#### **1. Externalizar Configuración de Almacén**

**Beneficio**: Flexibilidad, no rompe si renombran almacén.

```python
# En models/global_config.py:
warehouse_id = fields.Many2one(
    'stock.warehouse',
    string='Almacén de Cálculo de Costos',
    required=True,
    help='Almacén usado para calcular stock en costo ponderado'
)

# En models/stock_weighted.py:
def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar, order):
    config = self.env['global.config'].get_solo_config()
    warehouse = config.warehouse_id

    if not warehouse:
        raise UserError("Configure el Almacén de Cálculo en Configuración Global")

    location = warehouse.lot_stock_id
    # ... resto del código
```

---

#### **2. Refactorizar \_update_weighted_cost()**

**Beneficio**: Código más mantenible, testeable y claro.

```python
def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar, order):
    """Punto de entrada principal para actualización de costo ponderado"""
    weighted = self._get_or_create_weighted_record(product)
    stock_info = self._get_stock_info(product)

    if self._should_replace_cost(stock_info):
        ponderado, final_currency, tc = self._calculate_replacement_cost(
            costo, currency, valor_dollar
        )
    else:
        ponderado, final_currency, tc = self._calculate_weighted_average(
            weighted, costo, cantidad, currency, valor_dollar, stock_info
        )

    self._update_weighted_record(weighted, ponderado, final_currency, tc, stock_info, order)
    self._calculate_and_apply_new_price_to_pricelist(product, order)

def _get_stock_info(self, product):
    """Obtiene información de stock actual"""
    config = self.env['global.config'].get_solo_config()
    warehouse = config.warehouse_id
    location = warehouse.lot_stock_id

    quants = self.env['stock.quant'].search([
        ('product_id', '=', product.id),
        ('location_id', 'child_of', location.id)
    ])

    return {
        'available_qty': sum(quants.mapped('quantity')),
        'warehouse': warehouse,
        'location': location,
    }

def _should_replace_cost(self, stock_info):
    """Determina si debe reemplazar el costo en vez de promediar"""
    return stock_info['available_qty'] == 0

def _calculate_weighted_average(self, weighted, costo_nuevo, cantidad_nueva,
                                 currency_nueva, valor_dollar, stock_info):
    """Calcula promedio ponderado según monedas"""
    escenario = self._get_conversion_scenario(weighted.currency_id, currency_nueva)

    strategies = {
        'usd_to_mxn': self._calculate_usd_to_mxn,
        'mxn_to_usd': self._calculate_mxn_to_usd,
        'same_currency': self._calculate_same_currency,
    }

    return strategies[escenario](weighted, costo_nuevo, cantidad_nueva,
                                  currency_nueva, valor_dollar, stock_info)

def _calculate_usd_to_mxn(self, weighted, costo_nuevo, cantidad_nueva,
                          currency_nueva, valor_dollar, stock_info):
    """Lógica específica para conversión USD → MXN"""
    cantidad_anterior = stock_info['available_qty']
    costo_anterior = weighted.unit_weighted_cost
    tc_anterior = weighted.ultimo_tipo_cambio or valor_dollar

    # Si la nueva compra es minoritaria, mantener USD
    if cantidad_nueva < cantidad_anterior:
        return costo_anterior, self.env.ref('base.USD'), tc_anterior

    # Convertir todo a MXN
    costo_anterior_mxn = costo_anterior * tc_anterior
    total_qty = cantidad_anterior + cantidad_nueva
    ponderado = ((cantidad_anterior * costo_anterior_mxn) +
                 (cantidad_nueva * costo_nuevo)) / total_qty

    # No permitir que baje del nuevo costo
    ponderado = max(ponderado, costo_nuevo)

    return round(ponderado, 2), self.env.ref('base.MXN'), 1.0

# Y así para cada escenario...
```

---

#### **3. Externalizar Configuración de Listas**

**Beneficio**: Agregar/modificar listas sin programar.

```python
# Nuevo modelo:
class PricelistFormulaConfig(models.Model):
    _name = 'pricelist.formula.config'
    _description = 'Configuración de Fórmulas por Lista de Precios'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de Precios',
        required=True,
        ondelete='cascade'
    )

    formula_type = fields.Selection([
        ('var_0', 'HIGH RUNNER - (costo * D * E) / denominador_785 / IVA'),
        ('var_1', 'Corporativas - (costo * D * E) / margen_bruto / IVA'),
        ('var_2', 'PROMOLOGISTICS - (costo * E) / margen_bruto / IVA'),
        ('var_3', 'E-commerce - (costo * E) / margen + envío'),
        ('var_4', 'Mayoreo - (costo / denominador) / IVA'),
    ], required=True)

    # Parámetros específicos
    denominador = fields.Float(string='Denominador', digits=(16, 4))
    margen = fields.Float(string='Margen', digits=(16, 4))
    envio = fields.Float(string='Costo de Envío', digits='Product Price')

    # Flags
    aplicar_facturacion = fields.Boolean(string='Aplicar Costo Facturación', default=True)
    aplicar_prima_riesgo = fields.Boolean(string='Aplicar Prima de Riesgo', default=True)
    aplicar_iva = fields.Boolean(string='Dividir por IVA', default=True)

# Modificar pricing_tools.py:
def calcular_precio_debug(env, product, pricelist):
    # ... código inicial ...

    # Buscar configuración de la lista
    formula_config = env['pricelist.formula.config'].search([
        ('pricelist_id', '=', pricelist.id)
    ], limit=1)

    if not formula_config:
        raise UserError(f"No hay configuración de fórmula para {pricelist.name}")

    # Calcular según formula_type
    if formula_config.formula_type == 'var_0':
        resultado = (costo_val * global_config.costo_facturacion *
                    global_config.prima_riesgo_nacional) / formula_config.denominador / valores['G']
    elif formula_config.formula_type == 'var_1':
        resultado = (costo_val * global_config.costo_facturacion *
                    global_config.prima_riesgo_nacional) / formula_config.margen / valores['G']
    # ... etc
```

---

#### **4. Agregar Flag de Activación de Cálculo Automático**

**Beneficio**: Control sobre cuándo actualizar precios.

```python
# En models/global_config.py:
auto_calculate_prices = fields.Boolean(
    string='Calcular Precios Automáticamente',
    default=True,
    help='Si está activo, los precios se recalculan automáticamente al recibir productos. '
         'Desactivar temporalmente para importaciones masivas.'
)

calculate_on_products = fields.Many2many(
    'product.product',
    string='Calcular Solo para Productos',
    help='Si está vacío, calcula para todos. Si tiene productos, solo para esos.'
)

# En models/stock_weighted.py:
def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar, order):
    # ... cálculo del ponderado ...

    config = self.env['global.config'].get_solo_config()

    # Verificar si debe calcular automáticamente
    if not config.auto_calculate_prices:
        _logger.info(f"Cálculo automático desactivado, solo actualizando weighted para {product.display_name}")
        return

    # Verificar si está en la lista de productos permitidos
    if config.calculate_on_products and product not in config.calculate_on_products:
        _logger.info(f"Producto {product.display_name} no está en lista de cálculo automático")
        return

    self._calculate_and_apply_new_price_to_pricelist(product, order)
```

---

### **Prioridad Media 🟡 (Mejoras significativas)**

#### **5. Implementar ACLs Adecuadas**

**Beneficio**: Seguridad y control de acceso apropiados.

```xml
<!-- En security/security.xml (crear): -->
<odoo>
    <record id="group_stock_weighted_user" model="res.groups">
        <field name="name">Costo Ponderado - Usuario</field>
        <field name="category_id" ref="base.module_category_inventory"/>
    </record>

    <record id="group_stock_weighted_manager" model="res.groups">
        <field name="name">Costo Ponderado - Manager</field>
        <field name="category_id" ref="base.module_category_inventory"/>
        <field name="implied_ids" eval="[(4, ref('group_stock_weighted_user'))]"/>
    </record>
</odoo>
```

```csv
# En security/ir.model.access.csv:
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink

# Usuario: solo lectura
access_stock_weighted_user,stock.weighted.user,model_stock_weighted,group_stock_weighted_user,1,0,0,0
access_pricelist_ponderada_user,pricelist.ponderada.user,model_pricelist_ponderada,group_stock_weighted_user,1,0,0,0

# Manager: edición y creación
access_stock_weighted_manager,stock.weighted.manager,model_stock_weighted,group_stock_weighted_manager,1,1,1,0
access_pricelist_ponderada_manager,pricelist.ponderada.manager,model_pricelist_ponderada,group_stock_weighted_manager,1,1,1,0

# Administrador: todo
access_stock_weighted_admin,stock.weighted.admin,model_stock_weighted,base.group_system,1,1,1,1
access_global_config_admin,global.config.admin,model_global_config,base.group_system,1,1,1,1
```

---

#### **6. Agregar Validaciones de Datos**

**Beneficio**: Integridad de datos garantizada.

```python
# En models/stock_weighted.py:
@api.constrains('unit_weighted_cost')
def _check_cost_positive(self):
    for rec in self:
        if rec.unit_weighted_cost < 0:
            raise ValidationError(
                f"El costo ponderado no puede ser negativo. "
                f"Producto: {rec.product_id.display_name}, Costo: {rec.unit_weighted_cost}"
            )

@api.constrains('ultimo_tipo_cambio')
def _check_exchange_rate_positive(self):
    for rec in self:
        if rec.ultimo_tipo_cambio and rec.ultimo_tipo_cambio <= 0:
            raise ValidationError(
                f"El tipo de cambio debe ser positivo. "
                f"Producto: {rec.product_id.display_name}, TC: {rec.ultimo_tipo_cambio}"
            )

# En models/pricelist_ponderada.py:
@api.constrains('price_calculated')
def _check_price_positive(self):
    for rec in self:
        if rec.price_calculated < 0:
            raise ValidationError(
                f"El precio calculado no puede ser negativo. "
                f"Producto: {rec.product_id.display_name}, "
                f"Lista: {rec.pricelist_id.name}, "
                f"Precio: {rec.price_calculated}"
            )

# En models/global_config.py:
@api.constrains('valor_dollar')
def _check_dollar_rate(self):
    for rec in self:
        if rec.valor_dollar <= 0:
            raise ValidationError("El valor del dólar debe ser mayor a 0")

@api.constrains('denominador_785', 'denominador_pesos_mxn', /*all denominadores*/)
def _check_denominadores(self):
    for rec in self:
        denominadores = [
            ('denominador_785', rec.denominador_785),
            ('denominador_pesos_mxn', rec.denominador_pesos_mxn),
            ('denominador_aromax_mayoreo', rec.denominador_aromax_mayoreo),
            # ... todos los denominadores
        ]

        for nombre, valor in denominadores:
            if valor <= 0 or valor > 1:
                raise ValidationError(
                    f"{nombre} debe estar entre 0 y 1. Valor actual: {valor}"
                )
```

---

#### **7. Sistema de Notificaciones**

**Beneficio**: Visibilidad de cambios importantes y errores.

```python
# Nuevo modelo:
class StockWeightedAlert(models.Model):
    _name = 'stock.weighted.alert'
    _description = 'Alertas de Costo Ponderado'
    _order = 'create_date desc'

    product_id = fields.Many2one('product.product', required=True)
    alert_type = fields.Selection([
        ('cost_increase', 'Aumento Significativo de Costo'),
        ('cost_decrease', 'Disminución Significativa de Costo'),
        ('calculation_error', 'Error en Cálculo'),
        ('currency_change', 'Cambio de Moneda'),
    ], required=True)

    old_value = fields.Float(string='Valor Anterior')
    new_value = fields.Float(string='Valor Nuevo')
    percentage_change = fields.Float(string='% Cambio')
    message = fields.Text(string='Mensaje')
    order_id = fields.Many2one('purchase.order', string='Orden Origen')
    reviewed = fields.Boolean(string='Revisado', default=False)
    reviewed_by = fields.Many2one('res.users', string='Revisado Por')
    reviewed_date = fields.Datetime(string='Fecha Revisión')

# En models/stock_weighted.py, al actualizar costo:
def _create_alert_if_needed(self, product, old_cost, new_cost, order):
    """Crea alerta si el cambio es significativo"""
    config = self.env['global.config'].get_solo_config()
    threshold = 0.15  # 15% de cambio

    if not old_cost or old_cost == 0:
        return

    change = abs(new_cost - old_cost) / old_cost

    if change > threshold:
        alert_type = 'cost_increase' if new_cost > old_cost else 'cost_decrease'

        self.env['stock.weighted.alert'].create({
            'product_id': product.id,
            'alert_type': alert_type,
            'old_value': old_cost,
            'new_value': new_cost,
            'percentage_change': change * 100,
            'message': f'El costo cambió de {old_cost:.2f} a {new_cost:.2f} ({change*100:.1f}%)',
            'order_id': order,
        })

        # Notificar por correo
        self._send_alert_email(product, old_cost, new_cost, change, order)

# En _update_weighted_cost(), antes de actualizar:
old_cost = weighted.unit_weighted_cost if weighted else 0.0
# ... cálculo del nuevo costo ...
self._create_alert_if_needed(product, old_cost, ponderado, order)
```

---

#### **8. Logging Estructurado**

**Beneficio**: Debugging más eficiente, auditoría detallada.

```python
# En models/stock_weighted.py:
import logging
import json

_logger = logging.getLogger(__name__)

def _log_cost_update(self, product, old_cost, new_cost, currency, order, details):
    """Logueo estructurado de actualización de costo"""
    log_data = {
        'event': 'cost_update',
        'product_id': product.id,
        'product_code': product.default_code,
        'product_name': product.name,
        'old_cost': old_cost,
        'new_cost': new_cost,
        'currency': currency.name if currency else 'N/A',
        'order_ref': order.name if isinstance(order, models.Model) else str(order),
        'user': self.env.user.name,
        'timestamp': fields.Datetime.now().isoformat(),
        **details
    }

    _logger.info(f"COSTO_ACTUALIZADO: {json.dumps(log_data)}")

# Uso:
def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar, order):
    old_cost = weighted.unit_weighted_cost if weighted else 0.0

    # ... cálculos ...

    self._log_cost_update(
        product, old_cost, ponderado, currency, order,
        details={
            'cantidad_recibida': cantidad,
            'cantidad_anterior': cantidad_anterior,
            'tipo_cambio': valor_dollar,
            'escenario': escenario_conversion,
        }
    )
```

---

#### **9. Dashboard de Costos**

**Beneficio**: Visibilidad ejecutiva de cambios de costos.

```python
# Nuevo modelo:
class StockWeightedDashboard(models.Model):
    _name = 'stock.weighted.dashboard'
    _description = 'Dashboard de Costos Ponderados'
    _auto = False  # Vista SQL

    product_id = fields.Many2one('product.product', readonly=True)
    current_cost = fields.Float(readonly=True)
    previous_cost = fields.Float(readonly=True)
    cost_change_pct = fields.Float(string='% Cambio', readonly=True)
    last_update = fields.Datetime(readonly=True)
    currency_name = fields.Char(readonly=True)
    total_stock = fields.Float(readonly=True)
    stock_value = fields.Float(string='Valor de Inventario', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'stock_weighted_dashboard')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW stock_weighted_dashboard AS (
                SELECT
                    sw.id,
                    sw.product_id,
                    sw.unit_weighted_cost as current_cost,
                    LAG(sw.unit_weighted_cost) OVER (
                        PARTITION BY sw.product_id
                        ORDER BY sw.ultimo_calculo_date
                    ) as previous_cost,
                    ((sw.unit_weighted_cost / NULLIF(
                        LAG(sw.unit_weighted_cost) OVER (
                            PARTITION BY sw.product_id
                            ORDER BY sw.ultimo_calculo_date
                        ), 0
                    )) - 1) * 100 as cost_change_pct,
                    sw.ultimo_calculo_date as last_update,
                    rc.name as currency_name,
                    sw.current_stock as total_stock,
                    sw.unit_weighted_cost * sw.current_stock as stock_value
                FROM stock_weighted sw
                LEFT JOIN res_currency rc ON sw.currency_id = rc.id
            )
        """)
```

---

### **Prioridad Baja 🟢 (Mejoras incrementales)**

#### **10. Tests Unitarios**

**Beneficio**: Confianza en refactorizaciones futuras.

```python
# tests/test_stock_weighted.py
from odoo.tests import TransactionCase
from odoo.exceptions import UserError

class TestStockWeighted(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'TEST001',
        })
        self.config = self.env['global.config'].get_solo_config()
        self.config.valor_dollar = 20.0

    def test_01_initial_cost_usd(self):
        """Prueba costo inicial en USD"""
        weighted = self.env['stock.weighted'].create({
            'product_id': self.product.id,
            'unit_weighted_cost': 10.0,
            'currency_id': self.env.ref('base.USD').id,
            'current_stock': 100,
        })

        self.assertEqual(weighted.unit_weighted_cost, 10.0)
        self.assertEqual(weighted.currency_id.name, 'USD')

    def test_02_weighted_average_same_currency(self):
        """Prueba promedio ponderado en misma moneda"""
        # Stock inicial: 100 unidades @ $10 USD
        weighted = self._create_weighted(100, 10.0, 'USD')

        # Nueva compra: 50 unidades @ $12 USD
        self._simulate_purchase(50, 12.0, 'USD')

        # Esperado: (100*10 + 50*12) / 150 = 10.67
        self.assertAlmostEqual(weighted.unit_weighted_cost, 10.67, places=2)

    def test_03_conversion_usd_to_mxn(self):
        """Prueba conversión USD → MXN"""
        # Stock inicial: 100 @ $10 USD (= $200 MXN con TC=20)
        weighted = self._create_weighted(100, 10.0, 'USD')

        # Nueva compra grande: 200 @ $180 MXN
        self._simulate_purchase(200, 180.0, 'MXN')

        # Debe convertir a MXN
        self.assertEqual(weighted.currency_id.name, 'MXN')

        # Costo debe ser promedio ponderado en MXN
        # (100*200 + 200*180) / 300 = 186.67 MXN
        self.assertAlmostEqual(weighted.unit_weighted_cost, 186.67, places=2)

    def test_04_redondeo_al_9(self):
        """Prueba redondeo de precios al 9"""
        from odoo.addons.modulo_costo_ponderado_stock.models.pricing_tools import \
            redondeo_para_precios_finales

        # Precio sin IVA: 162.78
        # Con IVA: 188.82
        # Redondeado: 189
        # Sin IVA nuevamente: 162.93
        precio, _ = redondeo_para_precios_finales(162.78, "")
        self.assertEqual(precio, 162.93)

    def _create_weighted(self, stock, cost, currency_code):
        currency = self.env['res.currency'].search([('name', '=', currency_code)])
        return self.env['stock.weighted'].create({
            'product_id': self.product.id,
            'unit_weighted_cost': cost,
            'currency_id': currency.id,
            'current_stock': stock,
        })

    def _simulate_purchase(self, qty, price, currency_code):
        # Simular recepción de compra
        # (implementación depende de la estructura de pruebas)
        pass
```

---

#### **11. Optimización de Performance**

**Cache de Configuración Global**:

```python
# En models/global_config.py:
@tools.ormcache()
def _get_cached_config_values(self):
    """Cachea valores de configuración para evitar búsquedas repetidas"""
    config = self.get_solo_config()
    return {
        'valor_dollar': config.valor_dollar,
        'denominador_785': config.denominador_785,
        'margen_bruto': config.margen_bruto,
        # ... todos los valores frecuentemente usados
    }

@api.model
def get_valor_dollar(self):
    return self._get_cached_config_values()['valor_dollar']

# Invalidar cache cuando cambie la configuración:
def write(self, vals):
    res = super().write(vals)
    self.clear_caches()
    return res
```

**Batch Processing**:

```python
# En models/stock_weighted.py:
def _action_done(self, *args, **kwargs):
    res = super()._action_done(*args, **kwargs)

    # Agrupar productos para batch processing
    products_to_update = {}
    for move in self.filtered(lambda m: m.product_id and m.picking_code == 'incoming'):
        product = move.product_id
        if product not in products_to_update:
            products_to_update[product] = []
        products_to_update[product].append(move)

    # Procesar en batch
    for product, moves in products_to_update.items():
        # Calcular una sola vez por producto, no por cada movimiento
        self._update_weighted_cost_batch(product, moves)

    return res
```

**Índices adicionales**:

```python
# En models/historico_calculo_precio.py:
product_id = fields.Many2one('product.product', index=True)
pricelist_id = fields.Many2one('product.pricelist', index=True)
order_id = fields.Many2one('purchase.order', index=True)
fecha = fields.Datetime(index=True)  # Para búsquedas por rango de fechas
```

---

#### **12. Interfaz de Usuario Mejorada**

**Vista Kanban con Estados Visuales**:

```xml
<record id="view_stock_weighted_kanban" model="ir.ui.view">
    <field name="name">stock.weighted.kanban</field>
    <field name="model">stock.weighted</field>
    <field name="arch" type="xml">
        <kanban>
            <field name="product_id"/>
            <field name="unit_weighted_cost"/>
            <field name="currency_id"/>
            <field name="ultimo_calculo_date"/>
            <templates>
                <t t-name="kanban-box">
                    <div class="oe_kanban_global_click">
                        <div class="o_kanban_image">
                            <img t-att-src="kanban_image('product.product', 'image_128', record.product_id.raw_value)"/>
                        </div>
                        <div class="oe_kanban_details">
                            <strong class="o_kanban_record_title">
                                <field name="product_id"/>
                            </strong>
                            <div class="o_kanban_tags_section">
                                <span class="badge badge-pill"
                                      t-att-class="record.currency_id.value == 'USD' ? 'badge-info' : 'badge-success'">
                                    <field name="currency_id"/>
                                </span>
                            </div>
                            <div>
                                Costo: $<field name="unit_weighted_cost"/>
                            </div>
                            <div>
                                Stock: <field name="current_stock"/>
                            </div>
                            <div class="text-muted">
                                Actualizado: <field name="ultimo_calculo_date"/>
                            </div>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

**Gráfico de Evolución de Costos**:

```xml
<record id="view_stock_weighted_graph" model="ir.ui.view">
    <field name="name">stock.weighted.graph</field>
    <field name="model">historico.calculo.precio</field>
    <field name="arch" type="xml">
        <graph string="Evolución de Costos" type="line">
            <field name="product_id"/>
            <field name="fecha" type="row"/>
            <field name="costo" type="measure"/>
        </graph>
    </field>
</record>
```

---

#### **13. Eliminar Código Muerto**

```python
# En models/pricelist_ponderada.py, ELIMINAR líneas 87-103:

# ❌ ELIMINAR ESTO:
self.env.cr.execute("""
    SELECT pol.price_unit, po.date_order
    FROM purchase_order_line pol
    JOIN purchase_order po ON pol.order_id = po.id
    JOIN res_users ru ON po.create_uid = ru.id
    JOIN res_partner rp ON ru.partner_id = rp.id
    WHERE pol.product_id = %s
    AND po.state IN ('purchase', 'done')
    AND rp.name = %s
    ORDER BY po.date_order DESC
    LIMIT 1
""", (product.id, 'Itzel Partida'))
last_purchase_itzel = self.env.cr.fetchone()

self.env.cr.execute("""
    SELECT pol.price_unit, po.date_order, po.es_dollar
    FROM purchase_order_line pol
    JOIN purchase_order po ON pol.order_id = po.id
    JOIN res_users ru ON po.create_uid = ru.id
    JOIN res_partner rp ON ru.partner_id = rp.id
    WHERE pol.product_id = %s
    AND po.state IN ('purchase', 'done')
    AND rp.name = %s
    ORDER BY po.date_order DESC
    LIMIT 1
""", (product.id, 'Ricardo Partida'))
last_purchase_ricardo = self.env.cr.fetchone()

# Estas variables nunca se usan después
```

---

#### **14. Documentación Inline Mejorada**

```python
# En models/stock_weighted.py:
def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar, order):
    """
    Calcula y actualiza el costo unitario ponderado de un producto.

    Este método implementa la lógica de promedio ponderado considerando:
    - Conversiones de moneda (USD ↔ MXN)
    - Stock anterior vs cantidad nueva
    - Tipo de cambio histórico vs actual

    Algoritmo:
    1. Consultar stock actual en almacén configurado
    2. Buscar registro weighted existente
    3. Determinar escenario de cálculo:
       - Sin stock anterior → usar costo nuevo directamente
       - Con stock anterior, misma moneda → promedio ponderado directo
       - Con stock anterior, monedas diferentes → convertir y promediar
    4. Decidir moneda resultante según predominancia de cantidades
    5. Aplicar redondeo a 2 decimales
    6. Actualizar registro weighted
    7. Calcular y aplicar precios a todas las listas

    Args:
        product (product.product): Producto a actualizar
        costo (float): Costo unitario de la nueva compra
        cantidad (float): Cantidad recibida
        currency (res.currency): Moneda de la nueva compra
        valor_dollar (float): Tipo de cambio USD/MXN actual
        order (int|purchase.order): Orden de compra origen

    Returns:
        None

    Raises:
        UserError: Si no encuentra almacén configurado o configuración global

    Examples:
        # Caso 1: Primera compra
        >>> _update_weighted_cost(product, 10.0, 100, USD, 20.0, 123)
        # Resultado: costo = 10.0 USD

        # Caso 2: Segunda compra, misma moneda
        >>> # Stock anterior: 100 @ $10 USD
        >>> _update_weighted_cost(product, 12.0, 50, USD, 20.0, 124)
        # Resultado: costo = (100*10 + 50*12)/150 = 10.67 USD

        # Caso 3: Compra en otra moneda (predominante)
        >>> # Stock anterior: 100 @ $10 USD
        >>> _update_weighted_cost(product, 180.0, 200, MXN, 20.0, 125)
        # Resultado: costo = (100*200 + 200*180)/300 = 186.67 MXN

    Notes:
        - Si la nueva cantidad es menor que el stock anterior al cambiar de moneda,
          se mantiene la moneda anterior para evitar distorsiones
        - En conversión USD→MXN, si el promedio resulta menor que el nuevo costo,
          se ajusta al nuevo costo (protección de márgenes)
        - El método dispara automáticamente el cálculo de precios para todas
          las listas configuradas

    See Also:
        - _calculate_and_apply_new_price_to_pricelist()
        - pricing_tools.calcular_precio_debug()
    """
    # ... implementación ...
```

---

#### **15. Reporte de Cambios de Costos**

```python
# Nuevo modelo:
class StockWeightedReport(models.TransientModel):
    _name = 'stock.weighted.report.wizard'
    _description = 'Reporte de Cambios de Costos'

    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True, default=fields.Date.today)
    product_ids = fields.Many2many('product.product', string='Productos')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    min_change_pct = fields.Float(string='% Cambio Mínimo', default=5.0)

    def generate_report(self):
        """Genera reporte Excel de cambios de costos"""
        # Buscar registros de histórico en el rango
        domain = [
            ('fecha', '>=', self.date_from),
            ('fecha', '<=', self.date_to),
        ]

        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))

        if self.currency_id:
            domain.append(('currency_name', '=', self.currency_id.name))

        historico = self.env['historico.calculo.precio'].search(domain, order='fecha')

        # Generar Excel con cambios significativos
        # ... implementación ...
```

---

## 📈 Métricas de Calidad del Código

| Aspecto            | Calificación   | Detalles                                                                            | Mejoras Sugeridas                                                         |
| ------------------ | -------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Funcionalidad**  | ⭐⭐⭐⭐⭐ 5/5 | Cumple perfectamente todos los requisitos de negocio. Sistema completo y operativo. | Agregar más casos edge                                                    |
| **Mantenibilidad** | ⭐⭐⭐ 3/5     | Métodos largos (100+ líneas), lógica compleja anidada, nombres hardcodeados         | Refactorizar \_update_weighted_cost, externalizar configuración de listas |
| **Seguridad**      | ⭐⭐ 2/5       | Permisos demasiado abiertos, sin restricción de grupos                              | Implementar ACLs apropiadas por roles                                     |
| **Escalabilidad**  | ⭐⭐⭐ 3/5     | Funcionará con más productos pero más lento. Sin optimización de queries.           | Batch processing, cacheo, índices adicionales                             |
| **Documentación**  | ⭐⭐ 2/5       | Poca documentación inline, nombres de variables no siempre claros                   | Agregar docstrings detallados, comentarios en lógica compleja             |
| **Robustez**       | ⭐⭐⭐ 3/5     | Depende de nombres hardcodeados, errores silenciosos                                | Externalizar configuración, sistema de alertas                            |
| **Testabilidad**   | ⭐⭐ 2/5       | Sin tests unitarios, lógica difícil de probar                                       | Agregar suite de tests, refactorizar para testear                         |
| **Performance**    | ⭐⭐⭐ 3/5     | Funciona bien pero sin optimizaciones. Calcula todas las listas siempre.            | Cacheo, batch processing, cálculo selectivo                               |
| **UX**             | ⭐⭐⭐⭐ 4/5   | Herramientas de diagnóstico excelentes, interfaz funcional                          | Mejorar vistas con gráficos, kanban, dashboard                            |
| **Arquitectura**   | ⭐⭐⭐⭐ 4/5   | Diseño modular, separación de concerns, patrón singleton                            | Mejor separación de lógica de negocio                                     |

**Calificación General: ⭐⭐⭐⭐ 4/5**

---

## 🎯 Roadmap de Mejora Sugerido

### **Sprint 1 (1-2 semanas): Estabilidad y Seguridad**

1. ✅ Externalizar configuración de almacén
2. ✅ Implementar ACLs apropiadas
3. ✅ Agregar validaciones de datos
4. ✅ Flag de activación de cálculo automático

### **Sprint 2 (2-3 semanas): Refactorización**

5. ✅ Refactorizar \_update_weighted_cost() en métodos más pequeños
6. ✅ Eliminar código muerto
7. ✅ Agregar logging estructurado
8. ✅ Documentación inline mejorada

### **Sprint 3 (2-3 semanas): Configurabilidad**

9. ✅ Externalizar configuración de listas de precios
10. ✅ Sistema de notificaciones y alertas
11. ✅ Manejo de errores con registro

### **Sprint 4 (1-2 semanas): UI/UX**

12. ✅ Dashboard de costos
13. ✅ Vistas Kanban y gráficos
14. ✅ Reportes de cambios de costos

### **Sprint 5 (2-3 semanas): Performance y Testing**

15. ✅ Optimizaciones de performance
16. ✅ Tests unitarios completos
17. ✅ Índices adicionales
18. ✅ Batch processing

---

## 🎓 Conclusión

### **Fortalezas Principales**

Este módulo es una **solución robusta y bien pensada** que resuelve un problema complejo de pricing multi-lista con diferentes fórmulas. Su mayor fortaleza es la **automatización completa** del flujo de cálculo de costos ponderados y precios de venta.

**Características destacadas**:

- ✨ Automatización end-to-end sin intervención manual
- ✨ Manejo inteligente de multi-moneda con conversiones bidireccionales
- ✨ Trazabilidad excepcional con histórico completo
- ✨ Herramientas de diagnóstico y simulación
- ✨ Configuración centralizada de 40+ parámetros
- ✨ Redondeo psicológico de precios (terminación en 9)
- ✨ Soporte para 13+ listas con fórmulas específicas

### **Áreas de Oportunidad**

Si bien el módulo funciona excelente en producción, tiene **deuda técnica** en:

- 🔧 Hardcodeo de nombres de almacenes y listas
- 🔧 Métodos excesivamente largos y complejos
- 🔧 Falta de configurabilidad avanzada (requiere código)
- 🔧 Seguridad básica sin restricción de grupos
- 🔧 Sin tests unitarios
- 🔧 Optimizaciones de performance pendientes

### **Recomendación Final**

El módulo **funciona excelente en su estado actual** y no requiere cambios urgentes. Sin embargo, **dedicar 2-3 sprints a mejoras técnicas** aumentaría significativamente:

- 📈 Mantenibilidad a largo plazo
- 📈 Facilidad de extensión
- 📈 Seguridad y control de acceso
- 📈 Performance con gran volumen de datos
- 📈 Confianza al hacer cambios (con tests)

### **Valor de Negocio**

El módulo aporta **valor significativo** al negocio:

- 💰 Elimina errores humanos en cálculo de precios
- 💰 Reduce tiempo de actualización de horas a segundos
- 💰 Mantiene márgenes consistentes en 13+ canales
- 💰 Proporciona visibilidad y trazabilidad completa
- 💰 Flexible para ajustar estrategia de pricing rápidamente

---

**Calificación General**: ⭐⭐⭐⭐ **4 de 5 estrellas**

**Veredicto**: Excelente funcionalidad, mejorable en estructura técnica.

---

## 📚 Referencias

### **Modelos Principales**

- `stock.weighted`: [models/stock_weighted.py](models/stock_weighted.py)
- `pricelist.ponderada`: [models/pricelist_ponderada.py](models/pricelist_ponderada.py)
- `global.config`: [models/global_config.py](models/global_config.py)
- `purchase.order`: [models/purchase_order_dollar.py](models/purchase_order_dollar.py)

### **Lógica de Negocio**

- `pricing_tools`: [models/pricing_tools.py](models/pricing_tools.py)

### **Herramientas**

- `price.calculation.test`: [models/price_calculation_test.py](models/price_calculation_test.py)
- `purchase.order.sku.cost.search`: [models/purchase_order_sku_cost_search.py](models/purchase_order_sku_cost_search.py)
- `historico.calculo.precio`: [models/history_pricelist_calculate.py](models/history_pricelist_calculate.py)

### **Configuración**

- Manifest: [**manifest**.py](__manifest__.py)
- Seguridad: [security/ir.model.access.csv](security/ir.model.access.csv)

---

**Documento generado el**: 4 de marzo de 2026  
**Última actualización**: 4 de marzo de 2026  
**Versión del análisis**: 1.0
