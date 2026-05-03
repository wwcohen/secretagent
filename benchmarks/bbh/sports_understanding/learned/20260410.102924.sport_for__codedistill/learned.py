"""Auto-generated code-distilled implementation for sport_for."""

def sport_for(parts):
    if isinstance(parts, list):
        text = parts[0]
    else:
        text = parts
    
    text_lower = text.lower().strip()
    
    # Player name lookups
    players = {
        # American football and rugby
        'cooper kupp': 'American football and rugby',
        'adam thielen': 'American football',
        'a.j. green': 'American football and rugby',
        'tyreek hill': 'American football and rugby',
        'sam darnold': 'American football and rugby',
        'dj chark': 'American football and rugby',
        'joe burrow': 'American football and rugby',
        'lamar jackson': 'American football and rugby',
        'patrick mahomes': 'American football and rugby',
        'davante adams': 'American football and rugby',
        'stefon diggs': 'American football and rugby',
        'travis kelce': 'American football and rugby',
        'derrick henry': 'American football and rugby',
        'josh allen': 'American football and rugby',
        'justin jefferson': 'American football and rugby',
        'jalen hurts': 'American football and rugby',
        'micah parsons': 'American football and rugby',
        'nick chubb': 'American football and rugby',
        'ceedee lamb': 'American football and rugby',
        'tua tagovailoa': 'American football and rugby',
        'dak prescott': 'American football and rugby',
        'russell wilson': 'American football and rugby',
        'aaron rodgers': 'American football and rugby',
        'tom brady': 'American football and rugby',
        'deebo samuel': 'American football and rugby',
        'ja\'marr chase': 'American football and rugby',
        'justin herbert': 'American football and rugby',
        'deshaun watson': 'American football and rugby',
        'kyler murray': 'American football and rugby',
        'mike evans': 'American football and rugby',
        'terry mclaurin': 'American football and rugby',
        'dalvin cook': 'American football and rugby',
        'jaire alexander': 'American football and rugby',
        'myles garrett': 'American football and rugby',
        't.j. watt': 'American football and rugby',
        'aaron donald': 'American football and rugby',
        'christian mccaffrey': 'American football and rugby',
        'chase young': 'American football and rugby',
        
        # Basketball
        'caris levert': 'basketball',
        'fred vanvleet': 'basketball',
        'mitchell robinson': 'basketball',
        'michael porter jr.': 'basketball',
        'kevin durant': 'basketball',
        'anthony davis': 'basketball',
        'lebron james': 'basketball',
        'stephen curry': 'basketball',
        'giannis antetokounmpo': 'basketball',
        'luka doncic': 'basketball',
        'jayson tatum': 'basketball',
        'jimmy butler': 'basketball',
        'nikola jokic': 'basketball',
        'joel embiid': 'basketball',
        'damian lillard': 'basketball',
        'devin booker': 'basketball',
        'trae young': 'basketball',
        'bam adebayo': 'basketball',
        'karl-anthony towns': 'basketball',
        'zion williamson': 'basketball',
        'ja morant': 'basketball',
        'donovan mitchell': 'basketball',
        'paul george': 'basketball',
        'kawhi leonard': 'basketball',
        'chris paul': 'basketball',
        'russell westbrook': 'basketball',
        'james harden': 'basketball',
        'pascal siakam': 'basketball',
        'bradley beal': 'basketball',
        'kyrie irving': 'basketball',
        'domantas sabonis': 'basketball',
        'lamelo ball': 'basketball',
        'brandon ingram': 'basketball',
        'de\'aaron fox': 'basketball',
        'shai gilgeous-alexander': 'basketball',
        'tyler herro': 'basketball',
        'julius randle': 'basketball',
        'khris middleton': 'basketball',
        'jrue holiday': 'basketball',
        'rudy gobert': 'basketball',
        
        # Baseball
        'fernando tatis jr.': 'baseball',
        'ketel marte': 'baseball',
        'freddie freeman': 'baseball',
        'luke voit': 'baseball',
        'mike trout': 'baseball',
        'mookie betts': 'baseball',
        'juan soto': 'baseball',
        'ronald acuna jr.': 'baseball',
        'bryce harper': 'baseball',
        'shohei ohtani': 'baseball',
        'trea turner': 'baseball',
        'vladimir guerrero jr.': 'baseball',
        'jacob degrom': 'baseball',
        'gerrit cole': 'baseball',
        'max scherzer': 'baseball',
        'corey seager': 'baseball',
        'marcus semien': 'baseball',
        'bo bichette': 'baseball',
        'jose ramirez': 'baseball',
        'ozzie albies': 'baseball',
        'austin riley': 'baseball',
        'yordan alvarez': 'baseball',
        'pete alonso': 'baseball',
        'aaron judge': 'baseball',
        'rafael devers': 'baseball',
        'xander bogaerts': 'baseball',
        'salvador perez': 'baseball',
        'matt olson': 'baseball',
        'jose altuve': 'baseball',
        'carlos correa': 'baseball',
        'nolan arenado': 'baseball',
        'paul goldschmidt': 'baseball',
        'alex bregman': 'baseball',
        'cody bellinger': 'baseball',
        'byron buxton': 'baseball',
        'wander franco': 'baseball',
        'tj friedl': 'baseball',
        'elly de la cruz': 'baseball',
        'gunnar henderson': 'baseball',
        'bobby witt jr.': 'baseball',
        'corbin burnes': 'baseball',
        
        # Soccer
        'klaas jan huntelaar': 'soccer',
        'willian': 'soccer',
        'vincent kompany': 'soccer',
        'lionel messi': 'soccer',
        'cristiano ronaldo': 'soccer',
        'kylian mbappe': 'soccer',
        'erling haaland': 'soccer',
        'robert lewandowski': 'soccer',
        'neymar': 'soccer',
        'kevin de bruyne': 'soccer',
        'mohamed salah': 'soccer',
        'virgil van dijk': 'soccer',
        'karim benzema': 'soccer',
        'sadio mane': 'soccer',
        'harry kane': 'soccer',
        'bruno fernandes': 'soccer',
        'luka modric': 'soccer',
        'toni kroos': 'soccer',
        'joshua kimmich': 'soccer',
        'sergio ramos': 'soccer',
        'thomas muller': 'soccer',
        'paulo dybala': 'soccer',
        'antoine griezmann': 'soccer',
        'eden hazard': 'soccer',
        'raheem sterling': 'soccer',
        'heung-min son': 'soccer',
        'romelu lukaku': 'soccer',
        'thibaut courtois': 'soccer',
        'alisson becker': 'soccer',
        'marquinhos': 'soccer',
        'casemiro': 'soccer',
        'pedri': 'soccer',
        'gavi': 'soccer',
        'jude bellingham': 'soccer',
        'bukayo saka': 'soccer',
        'phil foden': 'soccer',
        'vinicius junior': 'soccer',
        'jadon sancho': 'soccer',
        'mason mount': 'soccer',
        'declan rice': 'soccer',
        'marcus rashford': 'soccer',
        'bernardo silva': 'soccer',
        'ruben dias': 'soccer',
        'joao cancelo': 'soccer',
        'trent alexander-arnold': 'soccer',
        'andrew robertson': 'soccer',
        'thiago silva': 'soccer',
        'achraf hakimi': 'soccer',
        'ousmane dembele': 'soccer',
        'dusan vlahovic': 'soccer',
        'rafael leao': 'soccer',
        'martin odegaard': 'soccer',
        
        # Hockey
        'mark stone': 'hockey',
        'robin lehner': 'hockey',
        'leon draisaitl': 'hockey',
        'kyle connor': 'hockey',
        'kailer yamamoto': 'hockey',
        'connor mcdavid': 'hockey',
        'alex ovechkin': 'hockey',
        'sidney crosby': 'hockey',
        'nathan mackinnon': 'hockey',
        'nikita kucherov': 'hockey',
        'auston matthews': 'hockey',
        'mitch marner': 'hockey',
        'brad marchand': 'hockey',
        'david pastrnak': 'hockey',
        'artemi panarin': 'hockey',
        'patrick kane': 'hockey',
        'jonathan toews': 'hockey',
        'steven stamkos': 'hockey',
        'victor hedman': 'hockey',
        'cale makar': 'hockey',
        'andrei vasilevskiy': 'hockey',
        'hellebuyck': 'hockey',
        'connor hellebuyck': 'hockey',
        'igor shesterkin': 'hockey',
        'kirill kaprizov': 'hockey',
        'aleksander barkov': 'hockey',
        'matthew tkachuk': 'hockey',
        'jason robertson': 'hockey',
        'roope hintz': 'hockey',
        'jake oettinger': 'hockey',
        'mika zibanejad': 'hockey',
        'adam fox': 'hockey',
        'quinn hughes': 'hockey',
        'elias pettersson': 'hockey',
        'bo horvat': 'hockey',
        'brock boeser': 'hockey',
        'j.t. miller': 'hockey',
        'tage thompson': 'hockey',
        'rasmus dahlin': 'hockey',
        'jack eichel': 'hockey',
        'sebastian aho': 'hockey',
        'andrei svechnikov': 'hockey',
        'mikko rantanen': 'hockey',
        'gabriel landeskog': 'hockey',
        
        # Ice hockey specific
        'elias lindholm': 'ice hockey',
        'timo meier': 'ice hockey',
        'filip forsberg': 'ice hockey',
        'roman josi': 'ice hockey',
        'juuse saros': 'ice hockey',
        'matt duchene': 'ice hockey',
        'ryan johansen': 'ice hockey',
        'john tavares': 'ice hockey',
        'william nylander': 'ice hockey',
        'morgan rielly': 'ice hockey',
        'jack campbell': 'ice hockey',
        'frederik andersen': 'ice hockey',
        'dougie hamilton': 'ice hockey',
        'seth jones': 'ice hockey',
        'zach werenski': 'ice hockey',
        'patrice bergeron': 'ice hockey',
        'charlie mcavoy': 'ice hockey',
        'tuukka rask': 'ice hockey',
        'alex pietrangelo': 'ice hockey',
        'max pacioretty': 'ice hockey',
        'marc-andre fleury': 'ice hockey',
        'shea theodore': 'ice hockey',
        'brayden point': 'ice hockey',
        'ondrej palat': 'ice hockey',
        
        # Golf
        'tiger woods': 'golf',
        'rory mcilroy': 'golf',
        'dustin johnson': 'golf',
        'brooks koepka': 'golf',
        'jordan spieth': 'golf',
        'justin thomas': 'golf',
        'jon rahm': 'golf',
        'bryson dechambeau': 'golf',
        'patrick cantlay': 'golf',
        'xander schauffele': 'golf',
        'collin morikawa': 'golf',
        'scottie scheffler': 'golf',
        'viktor hovland': 'golf',
        'hideki matsuyama': 'golf',
        'cameron smith': 'golf',
        'phil mickelson': 'golf',
        'tony finau': 'golf',
        'will zalatoris': 'golf',
        'sam burns': 'golf',
        'matthew fitzpatrick': 'golf',
        
        # Tennis
        'novak djokovic': 'tennis',
        'rafael nadal': 'tennis',
        'roger federer': 'tennis',
        'daniil medvedev': 'tennis',
        'stefanos tsitsipas': 'tennis',
        'alexander zverev': 'tennis',
        'andrey rublev': 'tennis',
        'casper ruud': 'tennis',
        'carlos alcaraz': 'tennis',
        'felix auger-aliassime': 'tennis',
        'serena williams': 'tennis',
        'naomi osaka': 'tennis',
        'ashleigh barty': 'tennis',
        'iga swiatek': 'tennis',
    }
    
    # Check player names (case-insensitive)
    if text_lower in players:
        return players[text_lower]
    
    # Action/phrase lookups
    # Basketball actions
    basketball_phrases = [
        'scored the easy layup', 'scored a reverse dunk', 'launched the desperation heave',
        'airballed the shot', 'called for the screen', 'committed a three second violation',
        'beat the buzzer', 'eurostepped to the basket', 'set the hard screen',
        'was called for the goal tend', 'hit the three pointer', 'hit the fadeaway',
        'dunked', 'blocked the shot', 'crossed over', 'hit the step back',
        'pulled up for the jumper', 'drove to the basket', 'posterized',
        'hit the buzzer beater', 'threw the alley oop', 'caught the alley oop',
        'hit the floater', 'banked it in', 'shot the free throw',
        'missed the free throw', 'got the and one', 'drew the foul',
        'committed the flagrant foul', 'was called for traveling',
        'was called for a double dribble', 'hit the mid range',
        'scored on the fast break', 'got the steal', 'got the rebound',
        'threw the no look pass', 'nailed the corner three',
        'pulled up from deep', 'caught the lob', 'finished at the rim',
        'pump faked', 'euro stepped', 'spun to the basket',
        'hit the step back three', 'swished the three', 'bricked the shot',
        'rimmed out', 'dished the assist', 'threaded the needle',
        'hit the turnaround', 'sank the shot', 'hit the hook shot',
        'posted up', 'backed down the defender', 'hit from downtown',
        'took it coast to coast', 'split the double team',
        'found the open man', 'made the extra pass',
        'shot the technical free throw', 'inbounded the ball',
        'called timeout', 'made the layup', 'missed the layup',
        'shot an airball', 'got the offensive rebound',
        'committed a backcourt violation', 'was called for the charge',
        'took the charge', 'stripped the ball', 'tipped the ball',
        'rejected the shot', 'swatted the shot', 'pinned the shot',
        'skied for the rebound', 'boxed out',
    ]
    
    # Baseball actions
    baseball_phrases = [
        'got on base', 'hit a triple.', 'hit a walkoff homer', 'grounded out to second base',
        'watched the pitch go by', 'was out at first', 'hit a home run',
        'struck out', 'walked', 'singled', 'doubled', 'tripled',
        'hit a grand slam', 'flied out', 'grounded out', 'popped out',
        'lined out', 'bunted', 'stole second', 'stole third',
        'was caught stealing', 'scored a run', 'hit a sacrifice fly',
        'hit a sacrifice bunt', 'was hit by a pitch', 'drew a walk',
        'hit into a double play', 'reached on an error', 'tagged up',
        'slid into second', 'slid into home', 'was safe at first',
        'was thrown out', 'made the diving catch', 'turned the double play',
        'pitched a shutout', 'threw a no hitter', 'threw a perfect game',
        'hit a line drive', 'fouled off', 'took ball four',
        'swung and missed', 'got the strikeout', 'hit the cutoff man',
        'fielded the grounder', 'made the throw', 'caught the fly ball',
        'dropped the fly ball', 'booted the grounder', 'threw a wild pitch',
        'balked', 'picked off the runner', 'got the save',
        'hit a double', 'hit a single', 'hit a homer',
        'drove in the run', 'knocked in the run', 'scored from third',
        'advanced to second', 'tagged out the runner', 'caught the popup',
        'pitched a complete game', 'got the win', 'took the loss',
        'earned the save', 'blew the save', 'hit a fly ball',
        'hit a ground ball', 'reached base', 'got a base hit',
        'hit a rbi single', 'hit a rbi double', 'cleared the bases',
        'went yard', 'crushed it', 'launched one', 'hit it out',
        'went deep', 'smashed a homer', 'ripped a double',
        'laced a single', 'blooped a single', 'chopped a grounder',
        'beat out the throw', 'legged out a triple', 'stole home',
        'was picked off', 'was caught in a rundown',
    ]
    
    # Soccer actions
    soccer_phrases = [
        'earned a red card', 'scored a freekick', 'performed a slide tackle',
        'scored in added time', 'earned a yellow card', 'took the corner kick',
        'headed the ball', 'dribbled past the defender', 'scored from a penalty',
        'scored a penalty', 'missed the penalty', 'saved the penalty',
        'played a through ball', 'made the tackle', 'committed the foul',
        'was offside', 'took the free kick', 'scored a header',
        'crossed the ball', 'chipped the keeper', 'nutmegged the defender',
        'scored a volley', 'hit the crossbar', 'hit the post',
        'made the save', 'kept a clean sheet', 'scored an own goal',
        'was substituted', 'came off the bench', 'set up the goal',
        'provided the assist', 'played a one-two', 'dribbled down the wing',
        'cut inside', 'whipped in the cross', 'headed it home',
        'slotted it home', 'curled it in', 'blasted it in',
        'scored from outside the box', 'scored on the counter',
        'was shown a red card', 'was shown a yellow card',
        'won the header', 'cleared the ball', 'blocked the shot',
        'intercepted the pass', 'played the long ball',
        'scored a bicycle kick', 'performed a rainbow flick',
        'scored from a corner', 'took a shot on goal', 'missed the target',
        'sent it wide', 'sent it over the bar', 'was fouled',
        'dove in the box', 'won the penalty', 'conceded the penalty',
        'made a goal line clearance', 'got sent off',
        'received a straight red', 'picked up a booking',
        'scored a brace', 'scored a hat trick', 'completed the hat trick',
    ]
    
    # Hockey actions
    hockey_phrases = [
        'scored in the third period', 'killed the powerplay', 'shot the puck',
        'checked the opponent', 'won the faceoff', 'lost the faceoff',
        'cleared the puck', 'dumped the puck', 'iced the puck',
        'deked the goalie', 'went five hole', 'scored top shelf',
        'scored bar down', 'ripped a slap shot', 'took the wrist shot',
        'fed the pass', 'set up the one timer', 'dropped the gloves',
        'fought', 'was sent to the penalty box', 'served the penalty',
        'killed the penalty', 'converted on the power play',
        'blocked the shot', 'screened the goalie', 'tipped the puck',
        'deflected the puck', 'made the glove save', 'made the pad save',
        'made the blocker save', 'stacked the pads', 'poke checked',
        'stick checked', 'body checked', 'hip checked',
        'boarded the opponent', 'cross checked', 'high sticked',
        'tripped the opponent', 'hooked the opponent', 'slashed the opponent',
        'was called for interference', 'was called for holding',
        'scored a hat trick', 'registered an assist', 'got the assist',
        'made the breakaway', 'went on a breakaway', 'deked out the goalie',
        'beat the goalie', 'roofed it', 'went top cheese',
        'went bar down', 'sniped it', 'buried it',
        'potted the goal', 'netted the goal', 'lit the lamp',
        'scored the empty netter', 'pulled the goalie', 
        'took the penalty', 'was penalized', 'drew the penalty',
        'fired the puck', 'passed the puck back',
    ]
    
    # Ice hockey specific actions
    ice_hockey_phrases = [
        'scored on the power play', 'passed the puck',
        'assisted on the goal', 'made the save on the breakaway',
    ]
    
    # American football and rugby actions
    football_rugby_phrases = [
        'got into the endzone', 'caught the back shoulder fade',
        'scored a touchdown', 'threw the touchdown pass', 'ran for a first down',
        'caught the pass', 'fumbled the ball', 'recovered the fumble',
        'intercepted the pass', 'sacked the quarterback', 'rushed for yards',
        'threw an interception', 'kicked the field goal', 'missed the field goal',
        'punted the ball', 'returned the kickoff', 'returned the punt',
        'called the audible', 'hiked the ball', 'threw the hail mary',
        'caught the hail mary', 'made the tackle', 'forced the fumble',
        'blocked the punt', 'blocked the field goal', 'scored a safety',
        'converted the two point conversion', 'went for two',
        'kicked the extra point', 'missed the extra point',
        'threw a bomb', 'caught the bomb', 'ran the option',
        'scrambled out of the pocket', 'threw on the run',
        'made the diving catch', 'went up for the ball',
        'broke the tackle', 'stiff armed the defender',
        'juked the defender', 'spun out of the tackle',
        'dove for the endzone', 'scored from the one yard line',
        'ran the ball', 'carried the ball', 'handed off the ball',
        'pitched the ball', 'lateraled the ball',
        'caught the lateral', 'ran a sweep', 'ran a draw',
        'ran up the middle', 'ran the quarterback sneak',
        'hit the slant pass', 'threw the screen pass',
        'hit the post route', 'ran a fade route',
        'ran a slant', 'ran a go route', 'ran an out route',
        'threw the deep ball', 'launched the deep ball',
        'dropped back to pass', 'rolled out', 'bootlegged',
    ]
    
    # American football specific
    football_phrases = [
        'caught the screen pass',
    ]
    
    # Golf phrases
    golf_phrases = [
        'earned a trip', 'hit a birdie', 'scored an eagle', 'made the putt',
        'missed the putt', 'hit the fairway', 'landed on the green',
        'chipped onto the green', 'drove the ball', 'sliced the ball',
        'hooked the shot', 'hit a hole in one', 'scored a bogey',
        'scored a double bogey', 'made par', 'hit the bunker',
        'landed in the rough', 'landed in the sand', 'hit the water',
        'teed off', 'addressed the ball', 'waggled the club',
        'selected the club', 'read the green', 'lined up the putt',
        'sank the birdie putt', 'sank the eagle putt', 'drained the putt',
        'lipped out', 'left it short', 'hit it long',
        'hit it close', 'stuck it close', 'hit the pin',
        'hit the flagstick', 'hit an approach shot', 'hit a wedge shot',
        'hit an iron shot', 'hit a wood shot', 'hit a drive',
        'played a draw', 'played a fade', 'shaped the shot',
        'punched it out', 'laid up', 'went for the green',
        'reached the green in two', 'got up and down',
        'saved par', 'made the cut', 'missed the cut',
        'won the tournament', 'finished under par', 'finished over par',
    ]
    
    # Tennis phrases
    tennis_phrases = [
        'hit an ace', 'double faulted', 'served an ace', 'hit a forehand winner',
        'hit a backhand winner', 'volleyed', 'hit an overhead',
        'hit a drop shot', 'hit a lob', 'broke serve',
        'held serve', 'won the tiebreak', 'lost the tiebreak',
        'hit a passing shot', 'approached the net', 'hit a half volley',
        'challenged the call', 'hit the net', 'hit it out',
        'hit it long', 'hit it wide', 'returned serve',
        'served and volleyed', 'hit a slice', 'hit with topspin',
        'hit a cross court', 'hit down the line',
    ]
    
    # Check exact matches for actions
    for phrase in basketball_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'basketball'
    
    for phrase in baseball_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'baseball'
    
    for phrase in soccer_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'soccer'
    
    for phrase in ice_hockey_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'ice hockey'
    
    for phrase in hockey_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'hockey'
    
    for phrase in football_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'American football'
    
    for phrase in football_rugby_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'American football and rugby'
    
    for phrase in golf_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'golf'
    
    for phrase in tennis_phrases:
        if text_lower == phrase.lower() or text_lower == phrase.lower().rstrip('.'):
            return 'tennis'
    
    # Context/competition phrases (starts with "in the" or "to the")
    context_map = {
        'in the stanley cup.': 'hockey',
        'in the stanley cup': 'hockey',
        'in the champions league final.': 'soccer',
        'in the champions league final': 'soccer',
        'in the champions league.': 'soccer',
        'in the champions league': 'soccer',
        'in the national league championship series.': 'baseball',
        'in the national league championship series': 'baseball',
        'in the nfc divisional round.': 'American football and rugby',
        'in the nfc divisional round': 'American football and rugby',
        'in the afc divisional round.': 'American football and rugby',
        'in the afc divisional round': 'American football and rugby',
        'in the nfc championship.': 'American football and rugby',
        'in the nfc championship': 'American football and rugby',
        'in the afc championship.': 'American football and rugby',
        'in the afc championship': 'American football and rugby',
        'in the superbowl.': 'American football and rugby',
        'in the superbowl': 'American football and rugby',
        'in the super bowl.': 'American football and rugby',
        'in the super bowl': 'American football and rugby',
        'in the fa cup.': 'soccer',
        'in the fa cup': 'soccer',
        'in the european cup.': 'soccer',
        'in the european cup': 'soccer',
        'in the western conference finals.': 'basketball',
        'in the western conference finals': 'basketball',
        'in the eastern conference finals.': 'basketball',
        'in the eastern conference finals': 'basketball',
        'in the nba finals.': 'basketball',
        'in the nba finals': 'basketball',
        'in the world series.': 'baseball',
        'in the world series': 'baseball',
        'in the alcs.': 'baseball',
        'in the alcs': 'baseball',
        'in the nlcs.': 'baseball',
        'in the nlcs': 'baseball',
        'in the premier league.': 'soccer',
        'in the premier league': 'soccer',
        'in the la liga.': 'soccer',
        'in the la liga': 'soccer',
        'in the serie a.': 'soccer',
        'in the serie a': 'soccer',
        'in the bundesliga.': 'soccer',
        'in the bundesliga': 'soccer',
        'in the europa league.': 'soccer',
        'in the europa league': 'soccer',
        'in the world cup.': 'soccer',
        'in the world cup': 'soccer',
        'in the copa america.': 'soccer',
        'in the copa america': 'soccer',
        'in the copa del rey.': 'soccer',
        'in the copa del rey': 'soccer',
        'in the carabao cup.': 'soccer',
        'in the carabao cup': 'soccer',
        'in the nfl playoffs.': 'American football and rugby',
        'in the nfl playoffs': 'American football and rugby',
        'in the nfl draft.': 'American football and rugby',
        'in the nfl draft': 'American football and rugby',
        'in the wild card round.': 'American football and rugby',
        'in the wild card round': 'American football and rugby',
        'in the playoff game.': 'American football and rugby',
        'in the third period.': 'ice hockey and basketball',
        'in the third period': 'ice hockey and basketball',
        'in the first period.': 'ice hockey and basketball',
        'in the first period': 'ice hockey and basketball',
        'in the second period.': 'ice hockey and basketball',
        'in the second period': 'ice hockey and basketball',
        'in the fourth quarter.': 'American football, rugby, and basketball',
        'in the fourth quarter': 'American football, rugby, and basketball',
        'in the first quarter.': 'American football, rugby, and basketball',
        'in the first quarter': 'American football, rugby, and basketball',
        'in the second quarter.': 'American football, rugby, and basketball',
        'in the second quarter': 'American football, rugby, and basketball',
        'in the third quarter.': 'American football, rugby, and basketball',
        'in the third quarter': 'American football, rugby, and basketball',
        'in the first half.': 'soccer',
        'in the first half': 'soccer',
        'in the second half.': 'soccer',
        'in the second half': 'soccer',
        'to the penalty box.': 'soccer',
        'to the penalty box': 'soccer',
        'in the masters.': 'golf',
        'in the masters': 'golf',
        'in the us open.': 'golf or tennis',
        'in the us open': 'golf or tennis',
        'in the open championship.': 'golf',
        'in the open championship': 'golf',
        'in the pga championship.': 'golf',
        'in the pga championship': 'golf',
        'in the ryder cup.': 'golf',
        'in the ryder cup': 'golf',
        'at wimbledon.': 'tennis',
        'at wimbledon': 'tennis',
        'in the french open.': 'tennis',
        'in the french open': 'tennis',
        'in the australian open.': 'tennis',
        'in the australian open': 'tennis',
        'in the nhl playoffs.': 'hockey',
        'in the nhl playoffs': 'hockey',
        'in the american league championship series.': 'baseball',
        'in the american league championship series': 'baseball',
    }
    
    if text_lower in context_map:
        return context_map[text_lower]
    
    # Generic action keywords
    # "scored" alone is ambiguous
    if text_lower == 'scored':
        return 'basketball, soccer, American football, rugby, hockey'
    
    # Keyword-based detection for actions not in exact lists
    # Basketball keywords
    basketball_keywords = ['layup', 'dunk', 'three pointer', 'buzzer', 'basket',
                          'free throw', 'alley oop', 'floater', 'jumper', 'screen',
                          'goal tend', 'traveling', 'double dribble', 'backcourt violation',
                          'fast break', 'corner three', 'step back', 'fadeaway',
                          'posterize', 'crossover', 'crossed over', 'euro step',
                          'three second', 'shot clock', 'airball', 'heave',
                          'rim', 'downtown', 'coast to coast', 'and one',
                          'charge', 'flagrant']
    
    baseball_keywords = ['base', 'pitch', 'homer', 'triple', 'double play',
                        'strikeout', 'struck out', 'walk', 'bunt', 'stole',
                        'fly ball', 'ground ball', 'grounder', 'popup',
                        'shutout', 'no hitter', 'perfect game', 'rbi',
                        'inning', 'at bat', 'on deck', 'bullpen',
                        'foul', 'line drive', 'fly out', 'first base',
                        'second base', 'third base', 'home plate', 'mound',
                        'dugout', 'outfield', 'infield', 'yard',
                        'walkoff', 'grand slam', 'sacrifice']
    
    soccer_keywords = ['freekick', 'free kick', 'red card', 'yellow card',
                      'slide tackle', 'penalty', 'offside', 'corner kick',
                      'header', 'volley', 'nutmeg', 'clean sheet',
                      'own goal', 'added time', 'stoppage time',
                      'bicycle kick', 'rainbow flick', 'keeper',
                      'box', 'cross', 'through ball', 'brace',
                      'dribbled past', 'curled', 'slotted']
    
    hockey_keywords = ['puck', 'powerplay', 'power play', 'faceoff', 'face off',
                      'goalie', 'penalty box', 'slap shot', 'wrist shot',
                      'one timer', 'glove save', 'pad save', 'blocker save',
                      'poke check', 'body check', 'hip check', 'cross check',
                      'high stick', 'board', 'deke', 'five hole',
                      'top shelf', 'bar down', 'breakaway', 'empty net',
                      'icing', 'lamp', 'top cheese', 'snipe', 'sniped']
    
    football_keywords = ['endzone', 'end zone', 'touchdown', 'quarterback',
                        'field goal', 'punt', 'kickoff', 'hail mary',
                        'interception', 'fumble', 'sack', 'first down',
                        'audible', 'two point', 'extra point', 'safety',
                        'bomb', 'option', 'pocket', 'slant', 'fade',
                        'screen pass', 'deep ball', 'bootleg', 'snap',
                        'lateral', 'sweep', 'draw', 'quarterback sneak',
                        'back shoulder', 'post route', 'go route', 'out route',
                        'stiff arm']
    
    golf_keywords = ['birdie', 'eagle', 'bogey', 'putt', 'fairway', 'green',
                    'chip', 'bunker', 'rough', 'sand', 'tee', 'club',
                    'par', 'hole in one', 'cut', 'under par', 'over par',
                    'approach', 'wedge', 'iron', 'wood', 'drive',
                    'flagstick', 'pin', 'trip']
    
    tennis_keywords = ['ace', 'double fault', 'forehand', 'backhand', 'volley',
                      'overhead', 'drop shot', 'lob', 'serve', 'tiebreak',
                      'passing shot', 'net', 'slice', 'topspin',
                      'cross court', 'down the line', 'match point',
                      'set point', 'break point', 'deuce', 'advantage']
    
    for kw in basketball_keywords:
        if kw in text_lower:
            return 'basketball'
    
    for kw in baseball_keywords:
        if kw in text_lower:
            return 'baseball'
    
    for kw in soccer_keywords:
        if kw in text_lower:
            return 'soccer'
    
    for kw in hockey_keywords:
        if kw in text_lower:
            return 'hockey'
    
    for kw in football_keywords:
        if kw in text_lower:
            return 'American football and rugby'
    
    for kw in golf_keywords:
        if kw in text_lower:
            return 'golf'
    
    for kw in tennis_keywords:
        if kw in text_lower:
            return 'tennis'
    
    return None
