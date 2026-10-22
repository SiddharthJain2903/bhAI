import markdown as _markdown
import nh3

# Only these tags/attributes survive. Everything else (scripts, iframes,
# inline event handlers, javascript: links...) is stripped, so a model reply
# or an uploaded document can never inject anything into the page.
ALLOWED_TAGS = {
    "p", "br", "strong", "em", "b", "i", "del",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "hr",
    "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td",
    "a",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}


def render_markdown(text):
    """Converts a model reply from Markdown to sanitized HTML for display."""
    html = _markdown.markdown(
        text or "",
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
        set_tag_attribute_values={"a": {"target": "_blank"}},
    )
