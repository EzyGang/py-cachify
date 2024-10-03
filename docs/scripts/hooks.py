import re

from bs4 import BeautifulSoup
from mkdocs import plugins
from mkdocs.config.defaults import MkDocsConfig
from paginate import Page


regex = re.compile(r'(///([a-zA-Z_@\(\)]+)///)')


@plugins.event_priority(-100)
def on_post_page(output_content: str, page: Page, config: MkDocsConfig) -> str:
    soup = BeautifulSoup(output_content, 'html.parser')
    aria_tags = soup.findAll(lambda tag: 'aria-label' in tag.attrs)
    for at in aria_tags:
        at.attrs['aria-label'] = re.sub(
            regex,
            r'\2',
            at.attrs['aria-label'],
        )

    output_content = str(soup)
    return re.sub(
        regex,
        r'<code style="background-color: var(--md-code-bg-color);padding: 0 .2941176471em;">\2</code>',
        output_content,
    )
