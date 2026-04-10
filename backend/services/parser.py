def extract_candidate_data(json_tokens):
    """
    Extracts name and pdf_url from parsed JSON tokens
    """

    name = None
    pdf_url = None

    # Case 1: direct keys
    if isinstance(json_tokens, dict):
        name = json_tokens.get("name")
        pdf_url = json_tokens.get("pdf_url")

    # Case 2: list of tokens (common in NLP parsing)
    elif isinstance(json_tokens, list):
        for token in json_tokens:
            key = token.get("key", "").lower()
            value = token.get("value")

            if "name" in key and not name:
                name = value

            if ("pdf" in key or "url" in key) and not pdf_url:
                pdf_url = value

    return {
        "name": name,
        "pdf_url": pdf_url
    }