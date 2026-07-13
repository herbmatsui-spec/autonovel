
class Book:
    def __init__(self, style_dna):
        self.style_dna = style_dna
        self.genre = "fantasy"

book = Book('{"mode": "test"}')
try:
    print(book.style_dna.get("mode", ""))
except AttributeError as e:
    print(f"Error: {e}")

