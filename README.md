
# Link Simple Crawler

Scraper simple en Python para recorrer una pagina y generar un listado de artículos en formato Markdown.

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

### Extraer solo URLs

Si necesitas copiar y pegar las URLs rápidamente, usa `--urls-only` para generar un archivo `.txt` plano en lugar de un Markdown con descripciones:

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/ --urls-only
```

Se puede combinar con cualquier filtro y para dividir en partes:

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/ --exclude nutricion --urls-only --batch-size 50
```

### Dividir resultados en partes (Batching)

Si vas a importar los links a herramientas como NotebookLM (que tienen un tope de 50 fuentes por cuaderno), usa `--batch-size` para que el scraper divida automáticamente los resultados en varios archivos (ej. `part1`, `part2`, etc.):

```bash
python scraper.py https://www.fitnessrevolucionario.com/articulos/ --batch-size 50
```

## Cómo funcionan los filtros

Los filtros siguen siendo léxicos y deterministas, pero ahora hacen un matching un poco más robusto. Buscan coincidencias en:

- El título del artículo
- La URL o slug del artículo

Reglas actuales:

- El texto y las keywords se normalizan en minúsculas y sin tildes
- Si una keyword tiene varias palabras, se trata como frase
- Si una keyword tiene una sola palabra, se compara como token y no solo como substring bruto
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
