"""
My poker bot!

Run it (the organiser will tell you the host and port):
    python3 my_bot.py --host 192.168.1.20 --port 8000

Practise against copies of itself on your own computer:
    python3 my_bot.py --port 8000 --count 4 --quiet

On Windows, type `python` (or `py`) instead of `python3`.
"""
import random

from pokerbot import all_in, call, check, fold, raise_to, run
from pokerbot.cards import hand_strength, is_pair, is_suited, rank

BOT_NAME = "underdog 2467"   # change this to your team's name!

BIG_BLIND = 20


# ----------------------------------------------------------------------
# Helpers

def preflop_score(cards):
    """Rate a starting hand from 0 (worst) to 1 (pocket aces)."""
    hi = max(rank(cards[0]), rank(cards[1]))
    lo = min(rank(cards[0]), rank(cards[1]))
    if is_pair(cards):
        return 0.5 + (hi - 2) / 12 * 0.5          # 22 -> 0.50, AA -> 1.00
    score = (hi - 2) / 12 * 0.45 + (lo - 2) / 12 * 0.25
    if is_suited(cards):
        score += 0.06
    gap = hi - lo
    if gap == 1:
        score += 0.05
    elif gap == 2:
        score += 0.02
    return score


def position(state):
    """0.0 = acting first (bad), 1.0 = on the button (best)."""
    try:
        n = len(state.opponents) + 1
        if n <= 1:
            return 0.5
        dist = (state.my_seat - state.button) % n     # 0 = button
        return 1.0 - dist / (n - 1) if dist else 1.0
    except Exception:
        return 0.5


def desperation(state):
    """Loosen up late in the match if we're behind the starting stack."""
    hands_left = state.hands_in_match - state.hand_number
    if hands_left <= 4 and state.my_stack < 1000:
        return 0.06
    return 0.0


def bet_pot_fraction(state, fraction):
    """Raise by `fraction` of the pot (after calling), kept within limits."""
    target = state.my_bet + state.to_call + fraction * (state.pot + state.to_call)
    target = max(state.min_raise, min(int(target), state.max_raise))
    if target >= state.max_raise:
        return all_in()
    return raise_to(target)


def safe_raise(state, fraction):
    if not state.can_raise:
        return check() if state.can_check else call()
    return bet_pot_fraction(state, fraction)


# ----------------------------------------------------------------------
# Main decision

def decide(state):
    opps = max(1, len(state.opponents_in_hand))
    pos = position(state)
    loosen = desperation(state)
    facing_bet = state.to_call > 0

    # ---------------- PREFLOP ----------------
    if state.street == "preflop":
        score = preflop_score(state.my_cards) + loosen
        # Late position and fewer opponents -> play more hands
        score += 0.05 * pos - 0.015 * (opps - 1)

        big_raise = state.to_call > 3 * BIG_BLIND

        # Monsters: raise big, re-raise, or shove
        if score >= 0.85:
            return safe_raise(state, 1.0)

        # Strong hands: raise if not facing a big raise, otherwise call
        if score >= 0.68:
            if not big_raise:
                return safe_raise(state, 0.75)
            return call()

        # Playable hands
        if score >= 0.45:
            if not facing_bet:
                # Open-raise sometimes from late position
                if pos >= 0.6 and random.random() < 0.6:
                    return safe_raise(state, 0.6)
                return check()
            if not big_raise:
                return call()
            return fold()

        # Weak hands: check if free, steal the blinds now and then,
        # call tiny bets, otherwise fold
        if state.can_check:
            if pos >= 0.8 and opps <= 2 and random.random() < 0.25:
                return safe_raise(state, 0.6)
            return check()
        if state.to_call <= BIG_BLIND and score >= 0.35:
            return call()
        return fold()

    # ---------------- POSTFLOP ----------------
    s = hand_strength(state.my_cards, state.board) + loosen
    # More opponents -> same hand is worth less
    s_adj = s ** (1 + 0.15 * (opps - 1))

    # Very strong: build the pot. Commit if we're already deep in.
    if s_adj >= 0.85:
        if state.my_stack <= state.pot:
            return all_in() if state.can_raise else call()
        return safe_raise(state, 0.9)

    # Good hand: bet for value, call raises
    if s_adj >= 0.62:
        if not facing_bet:
            return safe_raise(state, 0.6)
        if state.pot_odds <= 0.45:
            return safe_raise(state, 0.6) if random.random() < 0.3 else call()
        return call()

    # Medium hand: small bet or cheap call
    if s_adj >= 0.42:
        if not facing_bet:
            if random.random() < 0.6:
                return safe_raise(state, 0.4)
            return check()
        if s_adj >= state.pot_odds + 0.1:
            return call()
        return fold()

    # Weak hand
    if not facing_bet:
        # Bluff sometimes when few opponents are in and we act late
        if opps <= 2 and pos >= 0.6 and random.random() < 0.25:
            return safe_raise(state, 0.6)
        return check()

    # Facing a bet with a weak hand: only call if the price is right
    if s_adj >= state.pot_odds + 0.15:
        return call()
    # Occasional bluff-raise against a single opponent
    if opps == 1 and state.street != "river" and random.random() < 0.07:
        return safe_raise(state, 0.9)
    return fold()


# ----------------------------------------------------------------------
# You don't need to change anything below this line.
if __name__ == "__main__":
    run(decide, name=BOT_NAME)