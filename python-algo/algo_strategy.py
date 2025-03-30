import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 3)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Next, build offense
        self.offensive_strategy(game_state)
        # Now build reactive defenses based on where the enemy scored and then update your defences
        self.build_reactive_defense(game_state)
        # Now update the defence based on points
        self.update_defence(game_state)


    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[11, 11], [16, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        
        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13]]
        game_state.attempt_spawn(WALL, wall_locations)

        # # Place supports to heal our turrets and walls
        # leftEnemyDefences = game_state.analyze_enemy_defences([1,11])
        # rightEnemyDefences = game_state.analyze_enemy_defences([22, 11])

        # # Default to placing support on left side if analysis fails
        # if leftEnemyDefences is None or rightEnemyDefences is None:
        #     support_location = [[3, 11]] 
        # elif leftEnemyDefences['TOTAL'] < rightEnemyDefences['TOTAL']:
        #     support_location = [[3, 11]]
        # else:
        #     support_location = [[24, 11]]

        game_state.attempt_spawn(SUPPORT, [[3, 11]])


    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0] + 2, location[1] + 2]
            game_state.attempt_spawn(TURRET, build_location)

    def update_defence(self, game_state):
        structPoints = game_state.get_resource(0)
        # Update_defence based on points
        if (structPoints  <  12):
            if (game_state.can_spawn(TURRET, [12, 11])):
                game_state.attempt_spawn(TURRET, [12, 11])
            if (game_state.can_spawn(TURRET, [15, 11])):
                game_state.attempt_spawn(TURRET, [12, 11])
            if (game_state.can_spawn(TURRET, [5, 11])):
                game_state.attempt_spawn(TURRET, [5, 11])
            if (game_state.can_spawn(TURRET, [22, 11])):
                game_state.attempt_spawn(TURRET, [22, 11])
            for i in range(1, 10):
                if (game_state.can_spawn(WALL, [i, 13])):
                    game_state.attempt_spawn(WALL, [i, 13])
            for i in range(17, 27):
                if (game_state.can_spawn(WALL, [i, 13])):
                    game_state.attempt_spawn(WALL, [i, 13])
            for i in range(1, 4):
                if (game_state.can_spawn(SUPPORT, [i, 12])):
                    game_state.attempt_spawn(SUPPORT, [i, 12])
            for i in range(24, 27):
                if (game_state.can_spawn(SUPPORT, [i, 12])):
                    game_state.attempt_spawn(SUPPORT, [i, 12])
        else:
            if (game_state.can_spawn(TURRET, [12, 11])):
                game_state.attempt_spawn(TURRET, [12, 11])
            else:
                game_state.attempt_upgrade([12, 11])
            if (game_state.can_spawn(TURRET, [15, 11])):
                game_state.attempt_spawn(TURRET, [15, 11])
            else:
                game_state.attempt_upgrade([15, 11]) 
            if (game_state.can_spawn(TURRET, [5, 11])):
                game_state.attempt_spawn(TURRET, [5, 11])
            else:
                game_state.attempt_upgrade([5, 11])
            if (game_state.can_spawn(TURRET, [22, 11])):
                game_state.attempt_spawn(TURRET, [22, 11])
            else:
                game_state.attempt_upgrade([22, 11])                                      
            for i in range(1, 10):
                if (game_state.can_spawn(WALL, [i, 13])):
                    game_state.attempt_spawn(WALL, [i, 13])
            for i in range(17, 27):
                if (game_state.can_spawn(WALL, [i, 13])):
                    game_state.attempt_spawn(WALL, [i, 13])
            for i in range(1, 4):
                if (game_state.can_spawn(SUPPORT, [i, 12])):
                    game_state.attempt_spawn(SUPPORT, [i, 12])
            for i in range(24, 27):
                if (game_state.can_spawn(SUPPORT, [i, 12])):
                    game_state.attempt_spawn(SUPPORT, [i, 12])
    
    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

    def offensive_strategy(self, game_state):
        interceptors = [[0, 13], [27, 13]]
        game_state.attempt_spawn(INTERCEPTOR, interceptors)
        scouts = [[6,7], [7, 6]]
        game_state.attempt_spawn(SCOUT, scouts)

    
if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()