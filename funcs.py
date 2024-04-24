def normalize_title(title):
    # C'est le pire code que j'ai jamais écrit
    return title.lower().strip().replace(" ", "_").replace("||", "_").replace(":", "").replace("?", "").replace("!", "").replace(".", "").replace(",", "").replace("(", "").replace(")", "").replace("[", "").replace("]", "").replace("{", "").replace("}", "").replace("/", "").replace("\\", "").replace("'", "").replace('"', "")
