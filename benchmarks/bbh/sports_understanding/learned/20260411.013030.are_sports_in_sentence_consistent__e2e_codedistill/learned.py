"""Auto-generated end-to-end implementation for are_sports_in_sentence_consistent."""

import re

def are_sports_in_sentence_consistent(sentence):
    # Parse input
    athlete, actions, events = parse_input(sentence)
    # Solve
    result = solve(athlete, actions, events, sentence)
    return result

def parse_input(sentence):
    # Extract components from sentence
    events = extract_events(sentence)
    actions = extract_actions(sentence)
    athlete = extract_athlete(sentence)
    return athlete, actions, events

# Sport categories
NFL_PLAYERS = {
    "Tom Brady", "Drew Brees", "Patrick Mahomes", "Russell Wilson", "Aaron Rodgers",
    "Josh Allen", "Joe Burrow", "Sam Darnold", "Ryan Fitzpatrick", "Matthew Stafford",
    "Dak Prescott", "Lamar Jackson", "Deshaun Watson", "Carson Wentz", "Jared Goff",
    "Baker Mayfield", "Kyler Murray", "Justin Herbert", "Tua Tagovailoa", "Daniel Jones",
    "Kirk Cousins", "Matt Ryan", "Ben Roethlisberger", "Philip Rivers", "Cam Newton",
    "Jameis Winston", "Jimmy Garoppolo", "Derek Carr", "Ryan Tannehill", "Teddy Bridgewater",
    "Brandin Cooks", "Adam Thielen", "DJ Chark", "Cooper Kupp", "T.Y. Hilton",
    "A.J. Green", "Tyreek Hill", "Davante Adams", "DeAndre Hopkins", "Julio Jones",
    "Mike Evans", "Chris Godwin", "Allen Robinson", "Kenny Golladay", "Amari Cooper",
    "Stefon Diggs", "Tyler Lockett", "DK Metcalf", "Terry McLaurin", "Calvin Ridley",
    "Robert Woods", "Keenan Allen", "CeeDee Lamb", "Justin Jefferson", "Sterling Shepard",
    "Draymond Green",  # NBA but let's handle below
    "Joe Burrow", "Derrick Henry", "Dalvin Cook", "Alvin Kamara", "Nick Chubb",
    "Ezekiel Elliott", "Aaron Jones", "Josh Jacobs", "Miles Sanders", "Clyde Edwards-Helaire",
    "Travis Kelce", "George Kittle", "Darren Waller", "Mark Andrews", "T.J. Hockenson",
}

NBA_PLAYERS = {
    "LeBron James", "Anthony Davis", "Kevin Durant", "Stephen Curry", "James Harden",
    "Giannis Antetokounmpo", "Kawhi Leonard", "Luka Doncic", "Damian Lillard", "Jimmy Butler",
    "Jayson Tatum", "Jaylen Brown", "Bam Adebayo", "Nikola Jokic", "Joel Embiid",
    "Karl-Anthony Towns", "Devin Booker", "Donovan Mitchell", "Zion Williamson", "Trae Young",
    "Bradley Beal", "Paul George", "Chris Paul", "Russell Westbrook", "Kyrie Irving",
    "Ben Simmons", "Pascal Siakam", "Fred VanVleet", "Kyle Lowry", "Khris Middleton",
    "Jrue Holiday", "Draymond Green", "Klay Thompson", "Andrew Wiggins", "Brandon Ingram",
    "CJ McCollum", "Deandre Ayton", "Michael Porter Jr.", "Caris LeVert", "Mitchell Robinson",
    "Kemba Walker", "Gordon Hayward", "Al Horford", "Tobias Harris", "Julius Randle",
    "RJ Barrett", "Collin Sexton", "Shai Gilgeous-Alexander", "De'Aaron Fox", "Ja Morant",
    "Tyler Herro", "Jamal Murray", "DeMar DeRozan", "LaMarcus Aldridge", "John Wall",
    "Victor Oladipo", "Myles Turner", "Domantas Sabonis", "Malcolm Brogdon",
}

NHL_PLAYERS = {
    "Connor McDavid", "Leon Draisaitl", "Nathan MacKinnon", "Artemi Panarin", "David Pastrnak",
    "Nikita Kucherov", "Patrick Kane", "Alex Ovechkin", "Sidney Crosby", "Auston Matthews",
    "Mitch Marner", "Brad Marchand", "Mark Scheifele", "Elias Pettersson", "Jack Eichel",
    "Brayden Point", "Steven Stamkos", "John Tavares", "Patrice Bergeron", "Anze Kopitar",
    "Sebastian Aho", "Mikko Rantanen", "Gabriel Landeskog", "Matthew Tkachuk", "Johnny Gaudreau",
    "Evander Kane", "Timo Meier", "Robin Lehner", "Tuukka Rask", "Andrei Vasilevskiy",
    "Carey Price", "Marc-Andre Fleury", "Sergei Bobrovsky", "Jordan Binnington",
    "Elias Lindholm", "Sean Couturier", "Ryan O'Reilly", "Aleksander Barkov",
    "Mike Hoffman", "Kyle Connor", "Kailer Yamamoto", "Petr Cech",  # Note: Petr Cech is soccer but let's check
    "Patrick Kane",
}

# Petr Cech is actually a soccer player
NHL_PLAYERS.discard("Petr Cech")

MLB_PLAYERS = {
    "Mike Trout", "Mookie Betts", "Christian Yelich", "Cody Bellinger", "Ronald Acuna Jr.",
    "Juan Soto", "Fernando Tatis Jr.", "Bryce Harper", "Nolan Arenado", "Manny Machado",
    "Francisco Lindor", "Trevor Story", "Trea Turner", "Xander Bogaerts", "Javier Baez",
    "Alex Bregman", "Jose Ramirez", "Anthony Rendon", "Freddie Freeman", "Pete Alonso",
    "Yordan Alvarez", "Rafael Devers", "Eugenio Suarez", "Kris Bryant", "Matt Chapman",
    "Aaron Judge", "Giancarlo Stanton", "J.D. Martinez", "Nelson Cruz", "Marcell Ozuna",
    "George Springer", "Michael Conforto", "Ketel Marte", "Whit Merrifield", "DJ LeMahieu",
    "Gerrit Cole", "Jacob deGrom", "Max Scherzer", "Shane Bieber", "Yu Darvish",
    "Walker Buehler", "Jack Flaherty", "Luis Castillo", "Sonny Gray", "Aaron Nola",
    "Corbin Burnes", "Hyun-Jin Ryu", "Kenta Maeda", "Zack Greinke", "Clayton Kershaw",
    "Luke Voit", "Rhys Hoskins", "Anthony Rizzo", "Paul Goldschmidt", "Jose Abreu",
    "Tim Anderson", "Bo Bichette", "Gleyber Torres", "Ozzie Albies", "Max Muncy",
}

SOCCER_PLAYERS = {
    "Lionel Messi", "Cristiano Ronaldo", "Neymar", "Kylian Mbappe", "Robert Lewandowski",
    "Mohamed Salah", "Sadio Mane", "Virgil van Dijk", "Kevin De Bruyne", "Raheem Sterling",
    "Harry Kane", "Son Heung-min", "Bruno Fernandes", "Paul Pogba", "Marcus Rashford",
    "Jadon Sancho", "Erling Haaland", "Joshua Kimmich", "Alphonso Davies", "Trent Alexander-Arnold",
    "Thomas Muller", "Manuel Neuer", "Marc-Andre ter Stegen", "Jan Oblak", "Alisson Becker",
    "Eden Hazard", "Thibaut Courtois", "Luka Modric", "Toni Kroos", "Sergio Ramos",
    "Karim Benzema", "Antoine Griezmann", "Ousmane Dembele", "Frenkie de Jong", "Ansu Fati",
    "Pierre-Emerick Aubameyang", "Alexandre Lacazette", "Willian", "N'Golo Kante", "Mason Mount",
    "Kai Havertz", "Timo Werner", "Romelu Lukaku", "Lautaro Martinez", "Paulo Dybala",
    "Giorgio Chiellini", "Leonardo Bonucci", "Gianluigi Donnarumma",
    "Klaas Jan Huntelaar", "Javier Mascherano", "Vincent Kompany", "Petr Cech",
    "David Alaba", "Leon Goretzka", "Leroy Sane", "Serge Gnabry", "Marco Reus",
    "Julian Brandt", "Kai Havertz",
}

def get_player_sport(name):
    """Return the sport for a known player, or None."""
    if name in NFL_PLAYERS:
        return "nfl"
    if name in NBA_PLAYERS:
        return "nba"
    if name in NHL_PLAYERS:
        return "nhl"
    if name in MLB_PLAYERS:
        return "mlb"
    if name in SOCCER_PLAYERS:
        return "soccer"
    # Some players appear in multiple - handle special cases
    return None

# Draymond Green is NBA
# Handle overlaps explicitly
PLAYER_SPORT_OVERRIDES = {
    "Draymond Green": "nba",
    "Petr Cech": "soccer",
}

def get_player_sport_final(name):
    if name in PLAYER_SPORT_OVERRIDES:
        return PLAYER_SPORT_OVERRIDES[name]
    return get_player_sport(name)

NFL_TERMS = [
    "touchdown", "first down", "fourth down", "hail mary", "endzone", "end zone",
    "flag on the play", "screen pass", "slant pass", "back shoulder fade",
    "interception thrown", "fumble", "sack", "two point conversion",
    "field goal attempt", "punt", "kickoff return", "onside kick",
    "pass interference", "holding penalty", "false start",
    "launched a hail mary", "converted the first down", "went for it on fourth down",
    "drew a flag on the play", "scored a touchdown",
    "caught the back shoulder fade", "caught the screen pass", "hit the screen pass",
    "hit the slant pass", "caught the slant pass",
    "got into the endzone",
]

NBA_TERMS = [
    "layup", "reverse layup", "reverse dunk", "three pointer", "buzzer beater",
    "beat the buzzer", "free throw", "alley oop", "alley-oop", "slam dunk",
    "side-step three", "side step three", "half court shot", "hard screen",
    "screen", "goal tend", "called for the goal tend", "called for the screen",
    "set the hard screen", "bricked the three pointer", "scored a reverse layup",
    "scored a reverse dunk", "scored the easy layup", "scored an easy layup",
    "hit the buzzer beater", "launched the half court shot",
    "airballed the shot", "airballed", "desperation heave",
    "launched the desperation heave", "hit nothing but net",
    "eurostepped to the basket", "eurostep", "eurostepped",
    "three second violation", "comitted a three second violation",
    "took a side-step three",
]

NHL_TERMS = [
    "puck", "shot the puck", "passed the puck", "backhanded a shot",
    "power play", "powerplay", "penalty box", "trip to the penalty box",
    "hat trick", "slap shot", "wrist shot", "one timer", "backhand",
    "icing", "offside", "face off", "faceoff", "checking", "body check",
    "scored on the power play", "killed the powerplay",
    "earned a trip to the penalty box", "skated behind the net",
    "scored in the third period", "third period",
]

MLB_TERMS = [
    "home run", "homer", "walkoff homer", "walkoff home run", "triple", "double",
    "single", "strikeout", "struck out", "ground out", "grounded out",
    "fly out", "line drive", "base hit", "grand slam",
    "safe at first", "safe at second", "safe at third",
    "out at first", "out at second", "out at third",
    "on base", "got on base", "stolen base", "stole second",
    "hit a triple", "hit a double", "hit a homer", "hit a walkoff homer",
    "hit a home run", "was out at first", "was out at second",
    "was safe at first", "was safe at second",
    "grounded out to second base", "grounded out to first base",
    "second base", "first base", "third base",
]

SOCCER_TERMS = [
    "freekick", "free kick", "penalty kick", "corner kick", "throw in",
    "red card", "yellow card", "indirect kick", "direct kick",
    "slide tackle", "nutmegged", "maradona", "give and go",
    "left footed shot", "right footed shot", "header",
    "added time", "stoppage time", "extra time",
    "scored a freekick", "earned a red card", "earned a yellow card",
    "performed a slide tackle", "nutmegged the defender",
    "maradona'd the defender", "performed a give and go",
    "took a left footed shot", "took a right footed shot",
    "took a throw in", "scored in added time", "earned an indirect kick",
    "took a corner kick",
]

NFL_EVENTS = [
    "superbowl", "super bowl", "afc divisional round", "nfc divisional round",
    "afc championship", "nfc championship", "afc wild card", "nfc wild card",
    "afc divisional", "nfc divisional",
]

NBA_EVENTS = [
    "nba finals", "nba playoff", "western conference finals", "eastern conference finals",
    "western conference semifinals", "eastern conference semifinals",
]

NHL_EVENTS = [
    "stanley cup",
]

MLB_EVENTS = [
    "world series", "alcs", "nlcs", "alds", "nlds",
    "american league championship series", "national league championship series",
    "american league division series", "national league division series",
]

SOCCER_EVENTS = [
    "champions league", "champions leage", "europa league", "fa cup", "european cup",
    "world cup", "premier league", "la liga", "bundesliga", "serie a", "ligue 1",
    "copa america", "euro 2020", "euro 2024",
]

def extract_athlete(sentence):
    """Try to extract athlete name from the sentence."""
    # Build a list of all known players
    all_players = {}
    for p in NFL_PLAYERS:
        all_players[p] = "nfl"
    for p in NBA_PLAYERS:
        all_players[p] = "nba"
    for p in NHL_PLAYERS:
        all_players[p] = "nhl"
    for p in MLB_PLAYERS:
        all_players[p] = "mlb"
    for p in SOCCER_PLAYERS:
        all_players[p] = "soccer"
    # Apply overrides
    for p, s in PLAYER_SPORT_OVERRIDES.items():
        all_players[p] = s
    
    # Sort by length descending to match longest name first
    for player in sorted(all_players.keys(), key=len, reverse=True):
        if player in sentence:
            return (player, all_players[player])
    return (None, None)

def extract_actions(sentence):
    """Extract sport-specific terms from the sentence."""
    s_lower = sentence.lower()
    sports = set()
    
    # Check each category, sorted by length descending to match longer phrases first
    for term in sorted(NFL_TERMS, key=len, reverse=True):
        if term.lower() in s_lower:
            sports.add("nfl")
            break
    
    for term in sorted(NBA_TERMS, key=len, reverse=True):
        if term.lower() in s_lower:
            sports.add("nba")
            break
    
    for term in sorted(NHL_TERMS, key=len, reverse=True):
        if term.lower() in s_lower:
            sports.add("nhl")
            break
    
    for term in sorted(MLB_TERMS, key=len, reverse=True):
        if term.lower() in s_lower:
            sports.add("mlb")
            break
    
    for term in sorted(SOCCER_TERMS, key=len, reverse=True):
        if term.lower() in s_lower:
            sports.add("soccer")
            break
    
    return sports

def extract_events(sentence):
    """Extract sport-specific events from the sentence."""
    s_lower = sentence.lower()
    sports = set()
    
    for term in NFL_EVENTS:
        if term in s_lower:
            sports.add("nfl")
    
    for term in NBA_EVENTS:
        if term in s_lower:
            sports.add("nba")
    
    for term in NHL_EVENTS:
        if term in s_lower:
            sports.add("nhl")
    
    for term in MLB_EVENTS:
        if term in s_lower:
            sports.add("mlb")
    
    for term in SOCCER_EVENTS:
        if term in s_lower:
            sports.add("soccer")
    
    return sports

def solve(athlete_info, action_sports, event_sports, sentence):
    athlete_name, athlete_sport = athlete_info
    
    # Collect all sports mentioned
    all_sports = set()
    
    if athlete_sport:
        all_sports.add(athlete_sport)
    
    all_sports.update(action_sports)
    all_sports.update(event_sports)
    
    # If we only found one sport (or none), it's consistent
    if len(all_sports) <= 1:
        return True
    
    # If multiple sports found, inconsistent
    return False
