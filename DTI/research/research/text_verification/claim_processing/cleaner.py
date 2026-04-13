import re
import string

class ClaimCleaner:

    def __init__(self):
        pass

    def remove_urls(self, text: str) -> str:
        return re.sub(r"http\S+|www\S+|https\S+", "", text)

    def remove_html(self, text: str) -> str:
        return re.sub(r"<.*?>", "", text)

    def remove_punctuation(self, text: str) -> str:
        return text.translate(str.maketrans("", "", string.punctuation))

    def normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def clean(self, claim: str) -> str:
        """
        Main function that processes the claim
        """

        text = claim or ""

        text = self.remove_urls(text)
        text = self.remove_html(text)

        cleaned_text = self.normalize_whitespace(text)

        return cleaned_text