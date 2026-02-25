"""Wikipedia search workflow demo."""
from thirdlayer_prototype.models.action import navigate, type_text, press, click, extract


def get_wikipedia_workflow():
    """Define Wikipedia search workflow as action sequence."""
    return [
        navigate("https://en.wikipedia.org"),
        type_text("#searchInput", "Artificial Intelligence"),
        press("Enter"),
        click("h1.firstHeading"),
        extract("p.mw-empty-elt + p"),
    ]
