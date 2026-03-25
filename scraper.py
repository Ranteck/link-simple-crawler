import argparse
import re
import unicodedata
from pathlib import Path
from typing import cast
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from requests import Response, Session
from requests.exceptions import RequestException

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrae enlaces de artículos desde un archivo paginado.")
    _ = parser.add_argument(
        "link_base",
        help="URL base del archivo, por ejemplo https://www.fitnessrevolucionario.com/articulos/",
    )
    _ = parser.add_argument(
        "--include",
        nargs="+",
        default=[],
        help="Conserva solo artículos cuyo título o URL coincidan con alguna de estas palabras o frases.",
    )
    _ = parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Excluye artículos cuyo título o URL coincidan con alguna de estas palabras o frases.",
    )
    return parser.parse_args()


def normalize_base_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    if not parts.scheme or not parts.netloc:
        raise ValueError("Debes indicar una URL completa, por ejemplo: https://www.fitnessrevolucionario.com/articulos/")

    normalized_path = parts.path.rstrip("/") + "/"
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, "", ""))


def build_site_root(base_url: str) -> str:
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def build_article_url_re(site_root: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(site_root.rstrip('/'))}/\d{{4}}/\d{{2}}/\d{{2}}/[^/#?]+/?$")


def build_page_url(base_url: str, page_number: int) -> str:
    if page_number == 1:
        return base_url
    return urljoin(base_url, f"page/{page_number}/")


def normalize_url(url: str, site_root: str) -> str:
    absolute_url = urljoin(site_root, url)
    parts = urlsplit(absolute_url)
    normalized_path = parts.path.rstrip("/") + "/"
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, "", ""))


def build_output_path(base_url: str, filters_active: bool = False) -> Path:
    parts = urlsplit(base_url)
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    domain_parts = [part for part in netloc.split(".") if part]
    if len(domain_parts) > 1:
        domain_label = "-".join(domain_parts[:-1])
    elif domain_parts:
        domain_label = domain_parts[0]
    else:
        domain_label = "output"

    path_segments = [segment for segment in parts.path.split("/") if segment]
    section_label = re.sub(r"[^a-z0-9]+", "-", path_segments[0].lower()).strip("-") if path_segments else "links"
    suffix = "-filtrado" if filters_active else ""
    return Path(f"{domain_label}-{section_label}{suffix}.md")


def normalize_keywords(keywords: list[str]) -> list[str]:
    normalized_keywords: list[str] = []
    normalized_signatures: set[str] = set()

    for keyword in keywords:
        normalized_keyword = " ".join(keyword.strip().lower().split())
        keyword_signature = normalize_text(normalized_keyword)

        if keyword_signature and keyword_signature not in normalized_signatures:
            normalized_signatures.add(keyword_signature)
            normalized_keywords.append(normalized_keyword)

    return normalized_keywords


def normalize_text(text: str) -> str:
    normalized_text = unicodedata.normalize("NFKD", text.lower())
    without_marks = "".join(character for character in normalized_text if not unicodedata.combining(character))
    cleaned_text = re.sub(r"[^a-z0-9]+", " ", without_marks)
    return " ".join(cleaned_text.split())


def build_searchable_text(article_url: str, title: str) -> str:
    article_path = unquote(urlsplit(article_url).path)
    return normalize_text(f"{title} {article_path}")


def article_matches_keywords(article_url: str, title: str, keywords: list[str]) -> bool:
    searchable_text = build_searchable_text(article_url, title)
    searchable_tokens = set(searchable_text.split())

    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue

        if " " in normalized_keyword:
            if normalized_keyword in searchable_text:
                return True
            continue

        if normalized_keyword in searchable_tokens:
            return True

    return False


def filter_articles(
    articles: dict[str, str],
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> dict[str, str]:
    if not include_keywords and not exclude_keywords:
        return dict(articles)

    filtered_articles: dict[str, str] = {}

    for article_url, title in articles.items():
        if exclude_keywords and article_matches_keywords(article_url, title, exclude_keywords):
            continue

        if include_keywords and not article_matches_keywords(article_url, title, include_keywords):
            continue

        filtered_articles[article_url] = title

    return filtered_articles


def fetch_soup(session: Session, url: str) -> BeautifulSoup:
    response: Response = session.get(url, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_article_links(soup: BeautifulSoup, site_root: str, article_url_re: re.Pattern[str]) -> dict[str, str]:
    article_links: dict[str, str] = {}

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue

        normalized_url = normalize_url(href, site_root)
        if not article_url_re.match(normalized_url):
            continue

        title = " ".join(anchor.get_text(" ", strip=True).split())
        if normalized_url not in article_links or (not article_links[normalized_url] and title):
            article_links[normalized_url] = title

    return article_links


def extract_known_pages(soup: BeautifulSoup, site_root: str, base_path: str) -> set[int]:
    pages = {1}

    title_text = soup.title.get_text(" ", strip=True) if soup.title else ""
    title_match = re.search(r"Page\s+\d+\s+of\s+(\d+)", title_text, re.IGNORECASE)
    if title_match:
        pages.add(int(title_match.group(1)))

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue

        normalized_url = normalize_url(href, site_root)
        normalized_path = urlsplit(normalized_url).path
        page_match = re.search(rf"^{re.escape(base_path)}page/(\d+)/$", normalized_path)
        if page_match:
            pages.add(int(page_match.group(1)))

    return pages


def collect_all_article_links(base_url: str) -> dict[str, str]:
    normalized_base_url = normalize_base_url(base_url)
    site_root = build_site_root(normalized_base_url)
    base_path = urlsplit(normalized_base_url).path
    article_url_re = build_article_url_re(site_root)

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        collected_articles: dict[str, str] = {}
        current_page = 1
        last_known_page = 1

        while current_page <= last_known_page:
            soup = fetch_soup(session, build_page_url(normalized_base_url, current_page))

            for article_url, title in extract_article_links(soup, site_root, article_url_re).items():
                if article_url not in collected_articles or (not collected_articles[article_url] and title):
                    collected_articles[article_url] = title

            last_known_page = max(last_known_page, *extract_known_pages(soup, site_root, base_path))
            current_page += 1

    return collected_articles


def render_markdown(
    base_url: str,
    articles: dict[str, str],
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> str:
    lines = [
        "# Links encontrados",
        "",
        f"- URL base: `{base_url}`",
        f"- Total de artículos únicos: `{len(articles)}`",
    ]

    if include_keywords:
        lines.append(f"- Include: `{', '.join(include_keywords)}`")

    if exclude_keywords:
        lines.append(f"- Exclude: `{', '.join(exclude_keywords)}`")

    lines.extend(
        [
            "",
            "## Artículos",
            "",
        ]
    )

    for article_url, title in articles.items():
        if title:
            escaped_title = title.replace("[", r"\[").replace("]", r"\]")
            lines.append(f"- [{escaped_title}]({article_url})")
        else:
            lines.append(f"- <{article_url}>")

    lines.append("")
    return "\n".join(lines)


def write_markdown_output(
    base_url: str,
    articles: dict[str, str],
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> Path:
    filters_active = bool(include_keywords or exclude_keywords)
    output_path = build_output_path(base_url, filters_active=filters_active)
    _ = output_path.write_text(
        render_markdown(base_url, articles, include_keywords, exclude_keywords),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    args = parse_args()
    link_base = cast(str, args.link_base)
    include_keywords = normalize_keywords(cast(list[str], args.include))
    exclude_keywords = normalize_keywords(cast(list[str], args.exclude))

    try:
        base_url = normalize_base_url(link_base)
        articles = collect_all_article_links(base_url)
        filtered_articles = filter_articles(articles, include_keywords, exclude_keywords)
        output_path = write_markdown_output(base_url, filtered_articles, include_keywords, exclude_keywords)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    except RequestException as exc:
        raise SystemExit(f"Error al obtener el archivo de artículos: {exc}") from exc

    if include_keywords or exclude_keywords:
        print(f"Total de artículos únicos encontrados: {len(articles)}")
        print(f"Total de artículos tras filtrar: {len(filtered_articles)}")
    else:
        print(f"Total de artículos únicos encontrados: {len(filtered_articles)}")
    print(f"Archivo generado: {output_path.resolve()}")


if __name__ == "__main__":
    main()