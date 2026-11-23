import re
from pathlib import Path

from bs4 import BeautifulSoup
from mkdocs import plugins
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation
from mkdocs.structure.pages import Page


regex = re.compile(r'(///([a-zA-Z_@\(\)]+)///)')
INLINE_CODE = (
    r'<code style="background-color: var(--md-code-bg-color);color: var(--md-code-fg-color);'
    r'padding: 0 .2941176471em;">\2</code>'
)


@plugins.event_priority(-100)
def on_post_page(output_content: str, page: Page, config: MkDocsConfig) -> str:
    soup = BeautifulSoup(output_content, 'html.parser')
    aria_tags = soup.find_all(lambda tag: 'aria-label' in tag.attrs)
    for at in aria_tags:
        at.attrs['aria-label'] = re.sub(
            regex,
            r'\2',
            at.attrs['aria-label'],
        )

    # The theme's search overlay is a dialog without a name, which screen readers announce as "dialog".
    for dialog in soup.find_all(attrs={'role': 'dialog', 'data-md-component': 'search'}):
        dialog.attrs.setdefault('aria-label', 'Search')

    output_content = str(soup)
    # The head holds the title, the share tags and the JSON-LD block. Markup there shows up as text in
    # search results and breaks the JSON, so the markers become plain text in the head and code in the body.
    head, closing_tag, body = output_content.partition('</head>')
    if not closing_tag:
        return re.sub(regex, INLINE_CODE, output_content)
    return re.sub(regex, r'\2', head) + closing_tag + re.sub(regex, INLINE_CODE, body)


MAX_DESCRIPTION = 160
_SKIPPED_LINE = re.compile(r'^(#|<|>|!|\||```|~~~|---|\{%|///|[-*+] |\d+\. |\s{4,})')
_descriptions: dict[str, str] = {}
_nav: list[Navigation] = []


def _plain(text: str) -> str:
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(regex, r'\2', text)
    text = re.sub(r'[*`]|(?<!\w)_+|_+(?!\w)', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _first_paragraph(markdown: str) -> str:
    """Return the first prose paragraph of a page, cut to a length search engines show."""
    in_fence = False
    paragraph: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(('```', '~~~')):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped or _SKIPPED_LINE.match(line):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    text = _plain(' '.join(paragraph))
    if len(text) <= MAX_DESCRIPTION:
        return text
    cut = text[: MAX_DESCRIPTION - 1]
    sentence_end = max(cut.rfind('. '), cut.rfind('? '), cut.rfind('! '))
    if sentence_end > 60:
        return cut[: sentence_end + 1]
    return cut[: cut.rfind(' ')].rstrip(',;:') + '…'


def on_page_markdown(markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:
    """Give every page its own meta description, taken from its first paragraph."""
    if not page.meta.get('description'):
        description = _first_paragraph(markdown)
        if description:
            page.meta['description'] = description
    _descriptions[page.file.src_uri] = page.meta.get('description') or config.site_description or ''
    return markdown


def on_post_build(config: MkDocsConfig) -> None:
    """Write llms.txt: an index of the documentation for language models."""
    nav = _nav[-1]
    lines = [f'# {config.site_name}', '', f'> {config.site_description}', '']
    for item in nav.items:
        pages = [item] if item.is_page else [p for p in _walk(item) if p.is_page]
        lines += [f'## {_plain(item.title or "")}', '']
        for page in pages:
            title = _plain(page.title or '')
            lines.append(f'- [{title}]({page.canonical_url}): {_descriptions.get(page.file.src_uri, "")}')
        lines.append('')
    lines += ['## Optional', '', f'- [Full documentation on one page]({config.site_url}llm-full/)', '']
    Path(config.site_dir, 'llms.txt').write_text('\n'.join(lines), encoding='utf-8')


def _walk(section):
    for child in section.children:
        if child.is_page:
            yield child
        elif child.is_section:
            yield from _walk(child)


def on_nav(nav: Navigation, config: MkDocsConfig, files: Files) -> Navigation:
    _nav.append(nav)
    return nav
