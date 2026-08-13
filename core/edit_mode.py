def add_manual_needle(
    summary,
    real_needle,
    col,
    row,
    seeds
):

    summary[real_needle] = {
        "real_needle": real_needle,
        "display_needle": None,
        "is_extra": True,
        "is_removed": False,
        "highlight": False,
        "col": col,
        "row": row,
        "retraction": None,
        "actual_count": seeds,
        "expected_count": seeds
    }

    return summary


def find_needle_at(summary, col, row):

    for needle, info in summary.items():

        if (
            info["col"] == col and
            info["row"] == row
        ):
            return needle

    return None

def find_extra_needle_at(summary, col, row):

    for needle, info in summary.items():

        if not info["is_extra"]:
            continue

        if (
            info["col"] == col and
            info["row"] == row
        ):
            return needle

    return None

def get_next_real_needle(
    summary,
    original_needle_count,
    seeds
):

    if seeds == 2:

        candidates = [
            original_needle_count + 1,
            original_needle_count + 2
        ]

    elif seeds == 3:

        candidates = [
            original_needle_count + 3,
            original_needle_count + 4
        ]

    else:
        return None

    used = {
        info["real_needle"]
        for info in summary.values()
        if info["is_extra"]
    }

    for needle in candidates:

        if needle not in used:
            return needle

    return None

def get_retraction_choices(nop):

    max_retraction = (
        (nop - 3) * 0.5
    )

    values = [-0.5]

    r = 0.0

    while r <= max_retraction:

        values.append(r)

        r += 0.5

    return values

def get_extra_needles(extra_seed):

    mapping = {
        2: [2],
        3: [3],
        4: [2, 2],
        5: [2, 3]
    }

    return mapping.get(extra_seed, [])

def count_extra_at(summary, col, row):

    count = 0

    for info in summary.values():

        if not info["is_extra"]:
            continue

        if (
            info["col"] == col and
            info["row"] == row
        ):
            count += 1

    return count

def set_retraction(
    summary,
    real_needle,
    value
):

    summary[
        real_needle
    ]["retraction"] = value

    return summary