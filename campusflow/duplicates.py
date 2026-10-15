def normalize_text(text):
    """Trim, case-fold and collapse repeated whitespace."""
    return " ".join(str(text).casefold().split())


def detect_duplicates(tickets, category, title):
    """Return unresolved tickets with the same normalized title and category.

    Read-only: never modifies the tickets. Resolved tickets are ignored,
    because the problem may have come back.
    """
    wanted_title = normalize_text(title)
    wanted_category = normalize_text(category)
    matches = []
    for ticket in tickets:
        if ticket["status"] == "resolved":
            continue
        same_title = normalize_text(ticket["title"]) == wanted_title
        same_category = normalize_text(ticket["category"]) == wanted_category
        if same_title and same_category:
            matches.append(ticket)
    return matches
