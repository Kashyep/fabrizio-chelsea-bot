import pytest

from chelsea_bot.filtering import ChelseaMatcher


@pytest.mark.parametrize(
    "text",
    [
        "Chelsea have submitted a new bid.",
        "CHELSEA are in talks.",
        "Update for #ChelseaFC supporters.",
        "News from @ChelseaFC today.",
        "Chelsea FC remain interested.",
    ],
)
def test_matches_supported_chelsea_variants(text: str) -> None:
    matcher = ChelseaMatcher(("chelsea", "chelsea fc", "chelseafc", "@chelseafc", "#chelseafc"))
    assert matcher.matches(text)


@pytest.mark.parametrize(
    "text",
    [
        "Arsenal have submitted a new bid.",
        "A fictional chelseafcacademy opened today.",
        "The word prechelseaexample is not a club mention.",
    ],
)
def test_rejects_non_matches_and_partial_words(text: str) -> None:
    matcher = ChelseaMatcher(("chelsea", "chelseafc"))
    assert not matcher.matches(text)


def test_requires_a_term() -> None:
    with pytest.raises(ValueError, match="At least one"):
        ChelseaMatcher(())
