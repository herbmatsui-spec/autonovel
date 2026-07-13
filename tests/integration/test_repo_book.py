
import pytest


@pytest.mark.asyncio
async def test_create_and_get_book(real_uow):
    async with real_uow as uow:
        # Create
        book_id = await uow.books.create_book(
            title="Test Book",
            genre="Fantasy",
            concept="Test Concept",
            synopsis="Test Synopsis",
            target_eps=10,
            style_dna={"tone": "dark"},
            marketing_data={"tags": ["action"]}
        )
        assert book_id > 0

        # Get
        book = await uow.books.get_book(book_id)
        assert book is not None
        assert book.title == "Test Book"
        assert book.genre == "Fantasy"
        assert book.target_eps == 10
        assert isinstance(book.style_dna, dict)
        assert book.style_dna.get("tone") == "dark"

@pytest.mark.asyncio
async def test_update_book_marketing_data(real_uow):
    async with real_uow as uow:
        book_id = await uow.books.create_book(
            title="Old Title",
            genre="Sci-Fi",
            concept="C",
            synopsis="S",
            target_eps=5,
            style_dna={},
            marketing_data={"old_tag": 1}
        )

        await uow.books.update_book_marketing_data(
            book_id=book_id,
            title="New Title",
            marketing_data={"new_tag": 2}
        )

        book = await uow.books.get_book(book_id)
        assert book.title == "New Title"
        assert book.marketing_data.get("old_tag") == 1
        assert book.marketing_data.get("new_tag") == 2

@pytest.mark.asyncio
async def test_delete_book(real_uow):
    async with real_uow as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 1, {}, {})

        book = await uow.books.get_book(book_id)
        assert book is not None

        await uow.books.delete_book(book_id)

        book_deleted = await uow.books.get_book(book_id)
        assert book_deleted is None

@pytest.mark.asyncio
async def test_recalculate_book_tension(real_uow):
    async with real_uow as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 1, {}, {})
        # Note: actually creating chapters to test recalculation requires ChapterRepository
        # We will just verify it runs and returns 0 when there are no chapters.
        tension = await uow.books.recalculate_book_tension(book_id, branch_id=1)
        assert tension == 0

        book = await uow.books.get_book(book_id)
        assert book.cumulative_tension == 0
