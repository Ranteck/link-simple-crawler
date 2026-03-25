
# Link Simple Crawler

Scraper simple en Python para recorrer un archivo paginado y generar un listado de artículos en formato Markdown.

## Requisitos

- Python `>=3.12`
- Dependencias definidas en `pyproject.toml`

## Instalación

Si usas `uv`:

```bash
uv sync
```

Si prefieres `pip`, instala al menos:

```bash
pip install requests bs4
```

## Uso básico

El script recibe una URL base de archivo, por ejemplo una sección paginada tipo WordPress:

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/
```

O con `uv`:

```bash
uv run scraper.py https://www.fitnessrevolucionario.com/articulos/
```

## Qué hace

- Recorre la paginación del archivo
- Detecta enlaces que parecen artículos
- Elimina duplicados
- Genera un archivo Markdown con los resultados
- Muestra en consola solo un resumen corto

## Salida

Sin filtros, el archivo generado usa un nombre automático basado en dominio y sección:

```text
fitnessrevolucionario-articulos.md
```

La consola muestra algo así:

```text
Total de artículos únicos encontrados: 391
Archivo generado: /ruta/completa/fitnessrevolucionario-articulos.md
```

## Filtros opcionales

Si no pasas filtros, el comportamiento se mantiene simple y lista todos los artículos encontrados.

### Excluir artículos por keywords

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/ --exclude nutricion dieta suplementos
```

### Incluir solo artículos por keywords

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/ --include fuerza entrenamiento
```

### Combinar include y exclude

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/ --include fuerza entrenamiento --exclude nutricion suplementos
```

## Cómo funcionan los filtros

Los filtros son léxicos y simples. Buscan coincidencias en:

- El título del artículo
- La URL o slug del artículo

Reglas actuales:

- `--exclude` elimina artículos si alguna keyword coincide
- `--include` conserva artículos solo si alguna keyword coincide
- Si usas ambos, primero se aplica `exclude` y luego `include`

Cuando hay filtros activos, el archivo generado usa el sufijo `-filtrado`:

```text
fitnessrevolucionario-articulos-filtrado.md
```

El Markdown generado también deja registradas las keywords usadas.

## Limitaciones actuales

- El patrón de detección de artículos está pensado para URLs tipo `/yyyy/mm/dd/slug/`
- Los filtros no usan semántica, embeddings ni RAG
- Un artículo puede quedar fuera o dentro si la temática no aparece en el título o en la URL
- La lógica de paginación asume rutas tipo `page/N/`

## Estructura principal

- `scraper.py`: script principal
- `pyproject.toml`: dependencias del proyecto
