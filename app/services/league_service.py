from sqlalchemy.orm import Session
from app.models.league import LeagueStanding, LeagueMatch, LeagueFixture, LeagueEvent
from datetime import datetime

def update_league_standings(db: Session, league_id: int, user_id: int, score: int, opponent_score: int, result: str):
    """
    result: 'win', 'loss', or 'draw'
    """
    standing = db.query(LeagueStanding).filter_by(league_id=league_id, user_id=user_id).first()
    if not standing:
        standing = LeagueStanding(
            league_id=league_id,
            user_id=user_id,
            matches_played=0,
            wins=0,
            losses=0,
            draws=0,
            points=0,
            goals_for=0,
            goals_against=0,
            created_at=datetime.utcnow()
        )
        db.add(standing)

    standing.matches_played += 1
    standing.goals_for += score
    standing.goals_against += opponent_score

    if result == 'win':
        standing.wins += 1
        standing.points += 3
    elif result == 'loss':
        standing.losses += 1
    elif result == 'draw':
        standing.draws += 1
        standing.points += 1

    db.add(standing)
    db.commit()

def process_match_completion(db: Session, match: LeagueMatch):
    fixture = db.query(LeagueFixture).filter_by(id=match.fixture_id).first()
    if not fixture:
        return

    # Only process if both have played OR it's being force-closed
    if match.player1_score is not None and match.player2_score is not None:
        # Determine winner
        if match.player1_score > match.player2_score:
            match.winner_id = fixture.player1_id
            update_league_standings(db, fixture.league_id, fixture.player1_id, match.player1_score, match.player2_score, 'win')
            update_league_standings(db, fixture.league_id, fixture.player2_id, match.player2_score, match.player1_score, 'loss')
        elif match.player2_score > match.player1_score:
            match.winner_id = fixture.player2_id
            update_league_standings(db, fixture.league_id, fixture.player1_id, match.player1_score, match.player2_score, 'loss')
            update_league_standings(db, fixture.league_id, fixture.player2_id, match.player2_score, match.player1_score, 'win')
        else:
            # Draw
            match.winner_id = None
            update_league_standings(db, fixture.league_id, fixture.player1_id, match.player1_score, match.player2_score, 'draw')
            update_league_standings(db, fixture.league_id, fixture.player2_id, match.player2_score, match.player1_score, 'draw')

        match.played_at = datetime.utcnow()
        fixture.result_submitted = True
        db.add(match)
        db.add(fixture)
        db.commit()

def force_complete_match(db: Session, match_id: int, winner_id: int = None):
    """
    Force a match to complete, potentially awarding a win to one player if the other didn't play.
    """
    match = db.query(LeagueMatch).filter_by(id=match_id).first()
    if not match:
        return None

    fixture = db.query(LeagueFixture).filter_by(id=match.fixture_id).first()
    if not fixture:
        return None

    if winner_id:
        match.winner_id = winner_id
        # We assign scores if missing to allow standing updates
        if match.player1_score is None: match.player1_score = 0
        if match.player2_score is None: match.player2_score = 0

        # Award points
        p1_res = 'win' if winner_id == fixture.player1_id else 'loss'
        p2_res = 'win' if winner_id == fixture.player2_id else 'loss'

        update_league_standings(db, fixture.league_id, fixture.player1_id, match.player1_score, match.player2_score, p1_res)
        update_league_standings(db, fixture.league_id, fixture.player2_id, match.player2_score, match.player1_score, p2_res)
    else:
        # It's a draw by default
        if match.player1_score is None: match.player1_score = 0
        if match.player2_score is None: match.player2_score = 0
        update_league_standings(db, fixture.league_id, fixture.player1_id, match.player1_score, match.player2_score, 'draw')
        update_league_standings(db, fixture.league_id, fixture.player2_id, match.player2_score, match.player1_score, 'draw')

    match.played_at = datetime.utcnow()
    fixture.result_submitted = True
    db.add(match)
    db.add(fixture)
    db.commit()
    return match

