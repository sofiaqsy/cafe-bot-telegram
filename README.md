# Bot de Telegram para Gestión de Café

Un bot de Telegram completo para gestionar operaciones relacionadas con un negocio de café, desde la compra de café en cereza hasta la venta final, incluyendo procesamiento y control de gastos.

![Café Bot](https://img.shields.io/badge/Bot-Telegram-0088cc)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

## 🚀 Características

- ☕ **Gestión de Compras**: Registro detallado de proveedores, cantidad, precio y calidad
- 🔄 **Procesamiento de Café**: Control del flujo desde cereza hasta producto final
- 💰 **Control de Gastos**: Registro categorizado de gastos operativos
- 💼 **Gestión de Ventas**: Registro de clientes, precios y cálculo de utilidades
- 📊 **Reportes Avanzados**: Diarios, semanales y mensuales
- 📦 **Control de Inventario**: Seguimiento del café disponible por estado
- 📱 **Interfaz de Telegram**: Accesible desde cualquier dispositivo

## 📋 Requisitos

- Python 3.9 o superior
- Cuenta de Telegram
- Token de bot (obtenido a través de [@BotFather](https://t.me/botfather))
- Bibliotecas de Python (ver `requirements.txt`)

## 🛠️ Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/sofiaqsy/cafe-bot-telegram.git
cd cafe-bot-telegram
```

2. **Crear un entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar el token**:
   - Copia `.env.example` a `.env`
   - Edita `.env` y añade tu token de bot

5. **Ejecutar el bot**:
```bash
python bot.py
```

## 🤖 Uso

1. **Inicia una conversación** con tu bot en Telegram
2. Usa el comando `/start` para comenzar
3. Sigue las instrucciones para cada operación:
   - `/compra` - Registrar compra de café
   - `/proceso` - Registrar procesamiento
   - `/gasto` - Registrar gastos
   - `/venta` - Registrar venta
   - `/reporte` - Ver reportes

## 📁 Estructura del Proyecto

```
cafe_bot/
├── bot.py                 # Archivo principal
├── config.py              # Configuraciones
├── handlers/              # Manejadores de comandos
│   ├── compras.py
│   ├── proceso.py
│   ├── gastos.py
│   ├── ventas.py
│   └── reportes.py
├── utils/                 # Utilidades
│   ├── db.py              # Manejo de CSV
│   ├── helpers.py         # Funciones auxiliares
│   └── validators.py      # Validadores
└── data/                  # Datos almacenados
    ├── compras.csv
    ├── proceso.csv
    ├── gastos.csv
    └── ventas.csv
```

## 🔄 Flujo de Trabajo

1. **Compra** → 2. **Procesamiento** → 3. **Venta**
   (Con registro de gastos en cualquier momento)

## 📊 Reportes Disponibles

- **General**: Histórico completo
- **Diario**: Operaciones del día
- **Semanal**: Últimos 7 días 
- **Mensual**: Últimos 30 días

## 🛡️ Control de Inventario

El sistema mantiene un control detallado del café:
- **Pendiente**: Café disponible para procesar
- **Procesado parcialmente**: Parte del lote procesado
- **Procesado completamente**: Lote agotado

## 📃 Documentación

Consulta la carpeta `/docs` para documentación completa del proyecto.

## 🤝 Contribuir

Las contribuciones son bienvenidas. Si quieres mejorar este proyecto:
1. Haz un fork del repositorio
2. Crea una rama para tu función: `git checkout -b nueva-funcion`
3. Realiza tus cambios y haz commit: `git commit -m 'Añadir nueva función'`
4. Envía tus cambios: `git push origin nueva-funcion`
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

## 🙋 Soporte

Si tienes preguntas o problemas, abre un issue en este repositorio.

---

Desarrollado con ☕ y 💙