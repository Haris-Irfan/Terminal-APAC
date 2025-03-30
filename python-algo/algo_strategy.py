import gamelib
import random
import math
import time
from copy import deepcopy
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
        # offensive configurations
        self.weights = {
            'health_diff': 10.0,
            'unit_advantage': 2.0,
            'map_control': 1.5,
            'resource_diff': 0.8,
            'burst_potential': 3.5,
            'enemy_econ': -3.0
        }
        self.unit_values = {
            'SCOUT': 0.8,
            'DEMOLISHER': 2.5,
            'INTERCEPTOR': 3.0,
        }
        self.last_offensive_action = None
        self.offensive_push_strength = 1.0
        self.game_phase = "early"
        self.optimal_paths = {}

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
        # initialize optimal paths
        self.optimal_paths = {
            'scout_left': [[13, 0], [13, 1], [12, 1], [12, 2], [11, 2]],
            'scout_right': [[14, 0], [14, 1], [15, 1], [15, 2], [16, 2]],
            'demolisher': [[24, 10], [24, 11], [23, 11], [23, 12]]
        }

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
        # update game phase and weights
        self.update_game_phase(game_state)
        self.adjust_weights_for_phase(game_state)
        # generate and evaluate possible actions
        best_action = self.hill_climbing_search(game_state)
        # execute the best action
        self.execute_action(game_state, best_action)
        # haris actions
        self.starter_strategy(game_state)
        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    
    def update_game_phase(self, game_state):
        """determine current game phase"""
        turn = game_state.turn_number
        if turn < 10:
            self.game_phase = "early"
        elif turn < 25:
            self.game_phase = "mid"
        else:
            self.game_phase = "late"

    def adjust_weights_for_phase(self, game_state):
        """dynamic weight adjustment"""
        if self.game_phase == "early":
            self.weights.update({
                'health_diff': 8.0,
                'burst_potential': 4.0,
                'enemy_econ': -2.0
            })
            self.offensive_push_strength = 1.2
        elif self.game_phase == "mid":
            self.weights.update({
                'health_diff': 10.0,
                'unit_advantage': 2.5,
                'map_control': 1.5
            })
            self.offensive_push_strength = 1.0
        else:  # late game
            self.weights.update({
                'health_diff': 12.0,
                'burst_potential': 5.0,
                'enemy_econ': -4.0
            })
            self.offensive_push_strength = 1.5

    def evaluate_state(self, game_state):
        """comprehensive state evaluation"""
        score = 0
        # health difference (most important)
        health_diff = game_state.my_health - game_state.enemy_health
        score += self.weights['health_diff'] * health_diff
        # unit advantage 
        unit_diff = self.calculate_unit_advantage(game_state)
        score += self.weights['unit_advantage'] * unit_diff
        # map control 
        map_control = self.calculate_map_control(game_state)
        score += self.weights['map_control'] * map_control
        # resource difference
        resource_diff = (game_state.get_resource(MP) - game_state.get_resource(MP, 1)) / 10
        score += self.weights['resource_diff'] * resource_diff
        # burst damage potential
        burst_potential = self.calculate_burst_potential(game_state)
        score += self.weights['burst_potential'] * burst_potential
        # enemy economy penalty
        enemy_resources = game_state.get_resource(MP, 1) + game_state.get_resource(SP, 1)
        score += self.weights['enemy_econ'] * (enemy_resources / 5)
        return score

    def generate_offensive_actions(self, game_state):
        """generate possible offensive moves"""
        actions = []
        mp = game_state.get_resource(MP)
        # scout rush option
        if mp >= 2 and self.game_phase != "late":
            actions.append({
                'type': 'scout_rush',
                'locations': [[13, 0], [14, 0]],
                'count': min(int(mp), 8),
                'priority': 2
            })
        # demolisher push option
        if mp >= 5:
            actions.append({
                'type': 'demolisher_push',
                'locations': [[24, 10]],
                'count': min(int(mp/5), 2),
                'priority': 3
            }) 
        # interceptor tank push 
        if mp >= 4:
            actions.append({
                'type': 'interceptor_push',
                'locations': [[13, 0], [14, 0]],
                'count': min(int(mp/2), 4),
                'follow_up': 'scouts' if mp >= 6 else None,
                'priority': 4
            }) 
        return actions
    
    def execute_offensive_action(self, game_state, action):
        """execute offensive actions"""
        if action['type'] == 'scout_rush':
            count = int(action['count'] * self.offensive_push_strength)
            game_state.attempt_spawn(SCOUT, action['locations'], count)     
        elif action['type'] == 'demolisher_push':
            count = int(action['count'] * self.offensive_push_strength)
            game_state.attempt_spawn(DEMOLISHER, action['locations'], count)     
        elif action['type'] == 'interceptor_push':
            count = int(action['count'] * self.offensive_push_strength)
            game_state.attempt_spawn(INTERCEPTOR, action['locations'], count)
            if action['follow_up']:
                game_state.attempt_spawn(SCOUT, action['locations'], 3)

    def find_best_action(self, game_state):
        """minimax search with alpha-beta pruning"""
        start_time = time.time()
        best_action = None
        best_value = -math.inf
        alpha = -math.inf
        beta = math.inf
        possible_actions = self.generate_actions(game_state)
        for action in possible_actions:
            if time.time() - start_time > self.time_limit:
                break
            new_state = self.simulate_action(game_state, action)
            value = self.minimax_value(new_state, self.search_depth-1, False, alpha, beta)
            if value > best_value:
                best_value = value
                best_action = action
            alpha = max(alpha, best_value)
        return best_action or possible_actions[0]

    def minimax_value(self, game_state, depth, maximizing_player, alpha, beta):
        """recursive minimax evaluation"""
        if depth == 0 or game_state.game_over:
            return self.evaluate_state(game_state)
        if maximizing_player:
            value = -math.inf
            for action in self.generate_actions(game_state):
                new_state = self.simulate_action(game_state, action)
                value = max(value, self.minimax_value(new_state, depth-1, False, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:
            value = math.inf
            for action in self.generate_opponent_actions(game_state):
                new_state = self.simulate_action(game_state, action)
                value = min(value, self.minimax_value(new_state, depth-1, True, alpha, beta))
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value

    def generate_actions(self, game_state):
        """generate offensive actions"""
        actions = []
        offensive_actions = self.generate_offensive_actions(game_state)
        # create actions
        for off_action in offensive_actions[:3]:  
            actions.append({
                'offensive': off_action,
                'priority': off_action.get('priority', 0)
            })     
        return sorted(actions, key=lambda x: -x['priority'])[:self.max_breadth]

    def execute_action(self, game_state, action):
        """execute selected action"""
        if 'offensive' in action:
            self.execute_offensive_action(game_state, action['offensive'])
      
    def calculate_unit_advantage(self, game_state):
        """calculate unit advantage with type weighting"""
        advantage = 0
        for location in game_state.game_map:
            for unit in game_state.game_map[location]:
                if unit.player_index == 0:  # my units
                    advantage += self.unit_values.get(unit.unit_type, 0)
                else:  # enemy units
                    advantage -= self.unit_values.get(unit.unit_type, 0)
        return advantage

    def calculate_map_control(self, game_state):
        """measure territory advancement"""
        total_advance = 0
        unit_count = 0
        for location in game_state.game_map:
            for unit in game_state.game_map[location]:
                if unit.player_index == 0 and unit.unit_type in [SCOUT, DEMOLISHER, INTERCEPTOR]:
                    total_advance += location[1] / 27
                    unit_count += 1
        return total_advance / max(1, unit_count)

    def calculate_burst_potential(self, game_state):
        """estimate immediate damage potential"""
        potential = 0
        for location in game_state.game_map:
            for unit in game_state.game_map[location]:
                if unit.player_index == 0:
                    if unit.unit_type == SCOUT:
                        potential += 1
                    elif unit.unit_type == DEMOLISHER:
                        potential += 4  
                    elif unit.unit_type == INTERCEPTOR:
                        potential += 2 
                    potential += (27 - location[1]) * 0.15      
        return potential

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_interceptors(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our demolishers to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.demolisher_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

                # Only spawn Scouts every other turn
                # Sending more at once is better since attacks can only hit a single scout at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    scout_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
                    game_state.attempt_spawn(SCOUT, best_location, 1000)

                # Lastly, if we have spare SP, let's build some supports
                support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(SUPPORT, support_locations)        


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
        wall_locations = [[5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [18, 13], [19, 13] [20, 13], [21, 13], [22, 13]]
        game_state.attempt_spawn(WALL, wall_locations)

        # Place supports to heal our turrets and walls
        support_location = [[3, 11]] 
        game_state.attempt_spawn(SUPPORT, support_location)    

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def simulate_action(self, game_state, action):
        new_state = deepcopy(game_state)
        if 'offensive' in action:
            off_action = action['offensive']
            if off_action['type'] == 'scout_rush':
                new_state.attempt_spawn(SCOUT, off_action['locations'], off_action['count'])
            elif off_action['type'] == 'demolisher_push':
                new_state.attempt_spawn(DEMOLISHER, off_action['locations'], off_action['count'])
            elif off_action['type'] == 'interceptor_push':
                new_state.attempt_spawn(INTERCEPTOR, off_action['locations'], off_action['count'])
                if off_action['follow_up']:
                    new_state.attempt_spawn(SCOUT, off_action['locations'], 3)
        self.simulate_action_phase(new_state)
        
        return new_state

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

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
