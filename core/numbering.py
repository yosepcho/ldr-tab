COL_ORDER = [
    "A", "a",
    "B", "b",
    "C", "c",
    "D", "d",
    "E", "e",
    "F", "f",
    "G"
]


def assign_display_numbers(summary):

    locations = set()

    for info in summary.values():

        locations.add(
            (
                info["col"],
                info["row"]
            )
        )

    locations = sorted(
        locations,
        key=lambda x: (
            -x[1],
            COL_ORDER.index(x[0])
        )
    )

    location_to_display = {}

    for display_no, location in enumerate(
        locations,
        start=1
    ):
        location_to_display[
            location
        ] = display_no

    for info in summary.values():

        info["display_needle"] = (
            location_to_display[
                (
                    info["col"],
                    info["row"]
                )
            ]
        )

    return summary