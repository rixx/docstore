import datetime
import shutil

import pytest

from docstore.documents import store_new_document
from docstore.tint_colors import (
    choose_tint_color_from_dominant_colors,
    choose_tint_color,
    get_colors_from,
    store_tint_color,
)


def test_get_colors_from_small_image():
    result = get_colors_from("tests/files/cluster_segment.png")
    assert result == [
        (0, 154, 142),
        (0, 128, 128),
        (0, 0, 0),
        (0, 166, 153),
        (0, 154, 143),
        (0, 155, 141),
        (0, 155, 143),
        (0, 161, 148),
        (0, 158, 146),
    ]


def test_get_colors_from_large_image():
    result = get_colors_from("tests/files/cluster.png")
    # 500x325 image => 100x65 thumbnail
    assert len(result) == 100 * 65


def test_get_colors_from_animated_gif():
    result = get_colors_from("tests/files/Newtons_cradle.gif")
    # 480x360 image => 100x75 thumbnail
    # 36 frames, of which 18 are sampled
    assert len(result) == 100 * 75 * 18
    assert result[0:7500] != result[7500 : 7500 * 2]


def test_choose_tint_color():
    tint_color = choose_tint_color(
        paths=["tests/files/Newtons_cradle.gif"], background_color="white"
    )
    assert all(0.4 <= c <= 0.5 for c in tint_color), tint_color


@pytest.mark.parametrize(
    "dominant_color, background_color, expected_tint",
    [
        ((1, 1, 1), (1, 1, 1), (0, 0, 0)),
        ((0.9, 0.9, 0.9), (1, 1, 1), (0, 0, 0)),
        ((0, 0, 0), (0, 0, 0), (1, 1, 1)),
    ],
)
def test_selects_black_or_white_if_unsufficient_contrast(
    dominant_color, background_color, expected_tint
):
    assert (
        choose_tint_color_from_dominant_colors(
            dominant_colors=[dominant_color], background_color=background_color
        )
        == expected_tint
    )


def test_uses_thumbnail_if_cannot_use_file(root, tmpdir):
    shutil.copyfile(src="tests/files/snakes.pdf", dst=tmpdir / "snakes.pdf")

    document = store_new_document(
        root=root,
        path=tmpdir / "snakes.pdf",
        title="Some snakes",
        tags=[],
        source_url="htttps://example.org/snakes.pdf",
        date_saved=datetime.datetime.now(),
    )

    store_tint_color(root, document=document)
