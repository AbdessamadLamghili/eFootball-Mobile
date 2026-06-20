def generate_round_robin(participants):
    """
    Standard round-robin schedule.
    Returns a list of rounds; each round is a list of (home, away) LeagueParticipant tuples.
    Handles odd number of participants by adding a bye slot.
    """
    teams = list(participants)
    n = len(teams)
    if n < 2:
        return []

    if n % 2 == 1:
        teams.append(None)  # bye slot
        n += 1

    rounds = []
    for _ in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if home is not None and away is not None:
                round_matches.append((home, away))
        if round_matches:
            rounds.append(round_matches)
        # Rotate: keep teams[0] fixed, rotate the rest right
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    return rounds
