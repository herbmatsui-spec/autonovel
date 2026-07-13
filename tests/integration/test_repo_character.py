
import pytest


@pytest.mark.asyncio
async def test_character_repository(real_uow):
    async with real_uow as uow:
        # Create Book dependency
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})

        # Test create_character
        await uow.characters.create_character(
            book_id=book_id,
            name="Alice",
            role="Protagonist",
            registry_data={"age": 20}
        )
        await uow.characters.create_character(
            book_id=book_id,
            name="Bob",
            role="Antagonist",
            registry_data={"age": 30}
        )

        # Test get_all_characters
        chars = await uow.characters.get_all_characters(book_id)
        assert len(chars) == 2

        alice = next((c for c in chars if c.name == "Alice"), None)
        assert alice is not None
        assert alice.role == "Protagonist"
        assert isinstance(alice.registry_data, dict)
        assert alice.registry_data.get("age") == 20

        # Test update_character_registry
        await uow.characters.update_character_registry(alice.id, {"age": 21, "skill": "magic"})

        chars_updated = await uow.characters.get_all_characters(book_id)
        alice_updated = next((c for c in chars_updated if c.name == "Alice"), None)
        assert alice_updated.registry_data.get("age") == 21
        assert alice_updated.registry_data.get("skill") == "magic"
