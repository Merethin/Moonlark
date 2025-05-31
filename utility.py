import sans, typing

# Format a NationStates nation name to be compatible with the API.
def format_nation_or_region(name: str) -> str:
    return name.lower().replace(" ", "_")

def check_if_nation_exists(nation: str) -> bool:
    query = sans.Nation(format_nation_or_region(nation), "name")

    response = sans.get(query)
    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        # Should never happen unless something's wrong with your connection to NS, in which case, it will throw an error as we can't connect to NS anyway.
        typing.assert_never(response.status_code)