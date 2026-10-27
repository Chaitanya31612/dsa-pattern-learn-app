import json

with open('frontend/public/lld-db.json', 'r') as f:
    data = json.load(f)

snake_ladder = {
    "id": "snake-and-ladder",
    "number": 2,
    "title": "Snake and Ladder",
    "difficulty": "Easy",
    "tags": ["Game Loop", "Strategy", "Board Modeling"],
    "duration": { "guided": 60, "interview": 45 },
    "category": "Turn-Based Games",
    "description": "Design the board game engine for Snake and Ladder with players, dice, snakes/ladders as jump mappings, win detection, and clean turn loop.",
    "framework": {
        "requirements": {
            "must_have": [
                "Board of size N x N (typically 10x10 = 100 cells)",
                "Multiple players take turns",
                "Dice roll determines movement (1-6)",
                "Snakes move player DOWN (head → tail)",
                "Ladders move player UP (bottom → top)",
                "Player must land exactly on 100 to win (or overshoot handling)",
                "Game ends when a player reaches the last cell"
            ],
            "nice_to_have": [
                "Multiple dice",
                "Crooked dice (always returns even number — for testing)",
                "Multiple snakes/ladders with no overlap",
                "Undo last move"
            ],
            "out_of_scope": [
                "UI/Frontend rendering",
                "Multiplayer over network",
                "Database persistence"
            ],
            "clarifying_questions": [
                "What happens if a player is at 98 and rolls a 5? Do they stay at 98, bounce back? (Assume they stay in place for V1)",
                "Can multiple players be on the same cell?",
                "Can a ladder lead to a snake's head?"
            ]
        },
        "entities": {
            "classes": [
                {
                    "name": "Game",
                    "responsibility": "Orchestrates the game loop, maintains player queue, and checks for game ends. Does not contain board physics.",
                    "fields": ["Board board", "Queue<Player> players", "Dice dice", "boolean isOver"],
                    "methods": ["play()", "isOver() : boolean"],
                    "design_notes": "Maintains the state machine of the game and the turn loop. Belongs at the top level."
                },
                {
                    "name": "Board",
                    "responsibility": "Holds jump mappings (snakes and ladders) and validates moves. Does NOT hold players.",
                    "fields": ["int size", "Map<Integer, Integer> jumpMap"],
                    "methods": ["getNewPosition(int start, int moves) : int", "hasWon(int position) : boolean"],
                    "design_notes": "Use a jumpMap (hashmap) instead of individual Snake/Ladder classes if they only serve as jumps. Or model Snake/Ladder entities composed in the map. Keeps physics separate from players."
                },
                {
                    "name": "Player",
                    "responsibility": "Maintains player state like name and current position.",
                    "fields": ["String id", "String name", "int position"],
                    "methods": ["getPosition() : int", "setPosition(int newPos)"],
                    "design_notes": "A dumb entity. Does not roll the dice or move itself by reaching into the board; Game coordinates this."
                },
                {
                    "name": "Dice (Interface)",
                    "responsibility": "Simulates random dice roll.",
                    "fields": [],
                    "methods": ["roll() : int"],
                    "design_notes": "Interface allows NormalDice and CrookedDice (for testing/variation)."
                }
            ],
            "relationships": [
                "Game 1..1 Board (composition)",
                "Game 1..* Player (composition/aggregation)",
                "Game 1..1 Dice (strategy injection)",
                "Board 1..* Jump (Snake/Ladder entities or simple Map)"
            ]
        },
        "design_patterns": [
            {
                "name": "Strategy",
                "applied_to": "Dice",
                "why": "Allows swapping out NormalDice with a CrookedDice (always throws even numbers) for easy unit testing.",
                "signal_phrase": "I'll make Dice an interface to implement the Strategy pattern. This allows us to inject a deterministic CrookedDice later for testing without mocking."
            }
        ],
        "uml_ascii": "┌─────────────┐     ┌───────────┐\n│    Game     │1───1│   Board   │\n├─────────────┤     ├───────────┤\n│ -board      │     │ -size     │\n│ -players    │     │ -jumpMap  │\n│ -dice       │     ├───────────┤\n├─────────────┤     │+getNewPos()│\n│ +play()     │     └───────────┘\n└──────┬──────┘\n       │ depends on (inject)\n       ▼\n┌─────────────┐     ┌───────────┐\n│ <<interface>>│    │  Player   │\n│    Dice     │     ├───────────┤\n├─────────────┤     │ -name     │\n│ +roll()     │     │ -position │\n└──────▲──────┘     └───────────┘\n       │\n┌──────┴──────┐\n│ NormalDice  │\n└─────────────┘",
        "implementation_order": [
            "1. Player class (simple POJO)",
            "2. Dice interface + NormalDice (Random 1-6)",
            "3. Board class (setup jump map, move logic)",
            "4. Game class (queue logic, play loop)",
            "5. Demo driver"
        ],
        "key_phrases": [
            "I'm keeping Players out of the Board to satisfy Single Responsibility. The Board handles physics, the Player handles identity, and the Game orchestrates.",
            "Instead of treating Snake and Ladder as separate domain classes with logic, I'll model them as a simple Map of start -> end positions to keep O(1) jump lookups.",
            "I'll use a Queue for players to handle turn logic simply by polling and appending until a win is detected."
        ],
        "gotchas": [
            "SOLID violation: Adding `rollDice()` inside `Player`. Player shouldn't hold the random generator logic.",
            "Bug: Unbounded jumps — what if a ladder leads to a snake? Make sure jumps are computed correctly without infinite loops.",
            "Edge case: Dice rolls 5 when player is at 98 (needs 2 to win). Ensure logic clearly skips or handles overshoot safely."
        ],
        "extensibility_test": "Interviewer says: 'We want multiple dice'. Candidate: 'Since Dice is an interface, I can create a MultipleDiceStrategy that rolls N times and sums the result. Game doesn't change.'"
    },
    "guided": {
        "phase_hints": {
            "clarify": ["Ask what happens on overshoot (e.g., at 98, rolls 4).", "Ask if multiple players can occupy the same spot."],
            "model": ["Jump mappings can just be a HashMap<Integer, Integer> where key=start, value=end. No need for complex objects.", "Use a Queue for round-robin turn management."],
            "design": ["Make Dice an interface. It shows you think about testability.", "Separate Board limits from turn orchestration."],
            "implement": ["Start with small entities: Player, Dice.", "In Game play(), use a while loop until isOver."],
            "review": ["Check 100 overshoot logic.", "Mention how the Dice interface makes unit testing deterministic."]
        },
        "starter_code": "// ========== MODELS ==========\nclass Player {\n    private String id;\n    private String name;\n    private int position;\n    // Constructors, getters, setters\n}\n\n// ========== STRATEGY ==========\ninterface Dice {\n    int roll();\n}\nclass NormalDice implements Dice {\n    public int roll() { return (int)(Math.random() * 6) + 1; }\n}\n\n// ========== LOGIC ==========\nclass Board {\n    private int size;\n    private Map<Integer, Integer> jumpMap = new HashMap<>();\n\n    public Board(int size) {\n        this.size = size;\n    }\n    public void addJump(int start, int end) {\n        jumpMap.put(start, end);\n    }\n    public int getNewPosition(int startPos, int diceValue) {\n        // TODO: Ensure it doesn't overshoot size\n        // TODO: Check if new pos is in jumpMap\n        return 0;\n    }\n}\n\nclass Game {\n    private Board board;\n    private Queue<Player> players = new LinkedList<>();\n    private Dice dice;\n    private boolean isOver = false;\n\n    public Game(Board b, Dice d, List<Player> pls) {\n        this.board = b;\n        this.dice = d;\n        players.addAll(pls);\n    }\n    public void play() {\n        // TODO: while round-robin queue, roll dice, move player, check win\n    }\n}\n",
        "checkpoints": [
            "Clarified target exact win vs overshoot rules.",
            "Modeled jumps efficiently (e.g., HashMap).",
            "Dice abstracted as interface/strategy.",
            "Game loop uses a Queue for robust turns."
        ]
    },
    "interview": {
        "opening_prompt": "Design the classic Snake and Ladder game. Focus on the core mechanics and game loop. What are the key entities and how do they interact?",
        "evaluation_rubric": [
            "Does the candidate separate game orchestration from board topography?",
            "Are jumps modeled efficiently (O(1) lookup vs O(N) iteration)?",
            "Is the turn mechanism simple (like a Queue) instead of messy index tracking?",
            "Can they articulate how to test it without random flaky tests?"
        ],
        "probing_questions": [
            "How would you handle a scenario where a ladder takes you directly into a snake's mouth?",
            "If I asked you to write a unit test for a player winning, how does your Dice design enforce a predictable test?"
        ]
    },
    "deep_dive": {
        "concept_map": {
            "title": "Snake & Ladder Core Concepts",
            "sections": [
                {
                    "heading": "Why Jump Maps?",
                    "content": "Beginners often create `Snake` and `Ladder` classes. While purely OOP, traversing a List<Snake> to check if a cell has a snake is O(S). A simple `Map<Integer, Integer>` where key is start cell (head of snake or bottom of ladder) and value is end cell, handles both instantly in O(1) and simplifies `Board`."
                },
                {
                    "heading": "Queue for Turns",
                    "content": "Managing turns with `currentPlayerIndex = (currentPlayerIndex + 1) % players.size()` works but is brittle if players are removed. Using a `Queue` where you `poll()` the current player and `offer()` them back at the end of their turn is much cleaner."
                },
                {
                    "heading": "Testability with Dice Strategy",
                    "content": "Testing games of chance is notoriously hard. If `Dice` is hardcoded to `Math.random()`, you can't assert a win sequence reliably. Extracting `Dice` interface allows injecting a `CrookedDice` or `MockDice` that returns exact sequences [4, 6, 2] in tests."
                }
            ]
        },
        "common_interview_dialogues": [
            {
                "interviewer": "Where shouldn't the roll dice logic go?",
                "ideal_response": "It shouldn't be inside the `Player` class. The player is a state holder. Pushing action dependencies like `Dice` into `Player` violates SRP. The `Game` orchestrator should roll the dice and then tell the player where they landed based on the board."
            }
        ],
        "complexity_analysis": {
            "move_time": "O(1) to map dice roll and jump lookup.",
            "space": "O(S + L + P) for Snakes, Ladders, and Players."
        }
    }
}

tic_tac_toe = {
    "id": "tic-tac-toe",
    "number": 3,
    "title": "Tic Tac Toe",
    "difficulty": "Easy",
    "tags": ["Board Game", "Strategy", "Validation"],
    "duration": { "guided": 60, "interview": 45 },
    "category": "Turn-Based Games",
    "description": "Design a reusable Tic Tac Toe engine with configurable board size, player strategies, move validation, and efficient win detection anchored on last move.",
    "framework": {
        "requirements": {
            "must_have": [
                "N x N board (default 3x3)",
                "Two players with distinct symbols (X and O)",
                "Players take turns placing symbols",
                "Win detection — row, column, or diagonal filled by same symbol",
                "Draw detection — board full with no winner",
                "Input validation — cell must be empty and within bounds"
            ],
            "nice_to_have": [
                "N x N board with configurable win condition",
                "AI player (random or minimax)",
                "Undo last move",
                "Multiple game rounds with score tracking"
            ],
            "out_of_scope": [
                "GUI rendering",
                "Network multiplayer"
            ],
            "clarifying_questions": [
                "Is the board strictly 3x3 or should it scale to NxN?",
                "Is the win condition always filling the entire row/col, or K-in-a-row?",
                "Do we need bot players, or just human vs human?"
            ]
        },
        "entities": {
            "classes": [
                {
                    "name": "Game",
                    "responsibility": "Orchestrates players and board, manages turn state, and checks win status.",
                    "fields": ["Board board", "Deque<Player> players", "GameState state"],
                    "methods": ["play()"],
                    "design_notes": "Similar to Snake and Ladder, the Game loop is the orchestrator."
                },
                {
                    "name": "Board",
                    "responsibility": "Holds grid state, sets symbols, and validates bounds.",
                    "fields": ["int size", "Symbol[][] grid"],
                    "methods": ["placeSymbol(row, col, Symbol) : boolean", "isFull() : boolean", "checkWin(int, int, Symbol) : boolean"],
                    "design_notes": "Board manages spatial data but arguably win detection can live here or in an external RuleEngine."
                },
                {
                    "name": "Player",
                    "responsibility": "Represents a participant, holding their symbol and name.",
                    "fields": ["String name", "Symbol symbol", "PlayerStrategy strategy"],
                    "methods": ["makeMove(Board board) : Move"],
                    "design_notes": "If bot support is required, Player acts as context for a PlayerStrategy."
                },
                {
                    "name": "PlayerStrategy (Interface)",
                    "responsibility": "Decides the next move.",
                    "fields": [],
                    "methods": ["getMove(Board board) : Move"],
                    "design_notes": "HumanStrategy reads from console; BotStrategy computes."
                }
            ],
            "relationships": [
                "Game 1..1 Board",
                "Game 1..* Player",
                "Player 1..1 PlayerStrategy",
                "Player 1..1 Symbol"
            ]
        },
        "design_patterns": [
            {
                "name": "Strategy",
                "applied_to": "Player moves (Human vs Bot)",
                "why": "Allows treating human input and bot algorithms uniformly in the game loop.",
                "signal_phrase": "I will extract move generation into a PlayerStrategy interface so the Game doesn't need 'if bot then... else...' logic."
            }
        ],
        "uml_ascii": "┌─────────────┐     ┌───────────┐\n│    Game     │1───1│   Board   │\n├─────────────┤     ├───────────┤\n│ -board      │     │ -grid[][] │\n│ -players    │     │ -size     │\n├─────────────┤     ├───────────┤\n│ +play()     │     │+place()   │\n└──────┬──────┘     └───────────┘\n       │\n       ▼\n┌─────────────┐     ┌────────────────┐\n│   Player    │1───1│ <<interface>>  │\n├─────────────┤     │ PlayerStrategy │\n│ -name       │     ├────────────────┤\n│ -symbol     │     │ +getMove()     │\n│ -strategy   │     └───────▲────────┘\n└─────────────┘             │\n                    ┌───────┴──────┐\n                    │ HumanStrategy│\n                    └──────────────┘",
        "implementation_order": [
            "1. Enums: Symbol (X, O, EMPTY)",
            "2. Board: setup grid, print method, boundary checks",
            "3. PlayerStrategy & Player: Move data object, Human entry",
            "4. Game: The turn loop",
            "5. Win/Draw detection logic"
        ],
        "key_phrases": [
            "Checking the whole board on every turn is O(N^2). I will implement a localized win check that only scans the row, column, and diagonals anchored to the last placed symbol, bringing it to O(N).",
            "By associating the move selection with a Strategy, adding a Minimax bot later requires zero changes to the Game class."
        ],
        "gotchas": [
            "Performance detail: Standard check is O(N^2). Optimized check is O(N).",
            "Bug: Not checking if a cell is already occupied before placing.",
            "SOLID Violation: Putting `Scanner` or `System.in` directly inside `Player` or `Game`."
        ],
        "extensibility_test": "Interviewer says: 'Add a computer player.' Candidate: 'I implement a BotStrategy (perhaps picking random empty cells or Minimax). I initialize a Player with BotStrategy. Game loop just calls `player.makeMove(board)` — it works automatically.'"
    },
    "guided": {
        "phase_hints": {
            "clarify": ["Ask if the board is strictly 3x3 or scalable.", "Clarify draw conditions (board full)."],
            "model": ["Entities: Game, Board, Player, Move.", "Make Symbol an Enum, not strings/chars."],
            "design": ["Keep I/O (Scanner) out of Game core. Abstract it via HumanStrategy."],
            "implement": ["Start with Board array initialization.", "Write `checkWin(row, col, symbol)` optimally (O(N))."],
            "review": ["Walk through the last-move win optimization.", "Discuss bot injection."]
        },
        "starter_code": "// ========== ENUMS & DATA ==========\nenum Symbol { X, O, EMPTY }\nclass Move { int row, col; Move(int r, int c){row=r;col=c;} }\n\n// ========== STRATEGY ==========\ninterface PlayerStrategy {\n    Move getMove(Board board);\n}\nclass HumanStrategy implements PlayerStrategy {\n    // reads from console\n    public Move getMove(Board board) { return new Move(0,0); }\n}\n\n// ========== MODELS ==========\nclass Player {\n    String name; Symbol symbol; PlayerStrategy strategy;\n    public Move makeMove(Board b) { return strategy.getMove(b); }\n}\n\nclass Board {\n    int size; Symbol[][] grid;\n    public Board(int sz) { size = sz; /* init EMPTY */ }\n    public boolean isFull() { return false; }\n    public boolean place(int r, int c, Symbol s) { return false; }\n    public boolean checkWin(int lastR, int lastC, Symbol s) {\n        // TODO: O(N) check only row `lastR`, col `lastC`, and diagonals\n        return false;\n    }\n}\n\n// ========== ORCHESTRATOR ==========\nclass Game {\n    Board board;\n    Queue<Player> players;\n    public void play() {\n        // TODO: loop while not over and not drawn\n    }\n}",
        "checkpoints": [
            "Symbols are represented via Enum.",
            "Win Check is O(N), not O(N^2).",
            "Move fetching is abstracted into a Strategy."
        ]
    },
    "interview": {
        "opening_prompt": "Let's design Tic Tac Toe. Before jumping into code, tell me how you will represent players to easily support computer opponents in the future, and how you will check for a winner efficiently.",
        "evaluation_rubric": [
            "Strategy Pattern: Is move selection cleanly separated from player data?",
            "Optimized validation: Is win detection O(N) relying on the last placed piece?",
            "Extensibility: Does Game rely on hardcoded I/O?"
        ],
        "probing_questions": [
            "Scanning the whole board takes O(N^2) time. How can you verify a win after a move in O(N) time?",
            "What if we want an online matchmaking system later where moves come from an HTTP hook? How will this design adapt?"
        ]
    },
    "deep_dive": {
        "concept_map": {
            "title": "Tic Tac Toe Concepts",
            "sections": [
                {
                    "heading": "Optimizing Win Detection",
                    "content": "A naive win check scans the entire board. But a win can only happen if the *last placed symbol* completes a line. By passing `lastRow` and `lastCol` to `checkWin`, we only check `board[lastRow][...]`, `board[...][lastCol]`, and the two diagonals if the piece is on them. This reduces validation from O(N^2) to O(N)."
                },
                {
                    "heading": "Strategy for Moves",
                    "content": "Using a `PlayerStrategy` for move fetching allows us to completely decouple the game rules from the I/O. `HumanStrategy` reads from standard input. `BotStrategy` runs minimax. `NetworkStrategy` waits for JSON socket data. The `Game` loop remains `player.makeMove()`."
                }
            ]
        },
        "common_interview_dialogues": [
            {
                "interviewer": "Can you do win detection in O(1)?",
                "ideal_response": "Yes, by maintaining running arrays. We keep a `rowCount[N]`, `colCount[N]`, `diag`, and `antiDiag`. When Player X moves at (r,c), we do `rowCount[r]++`. If any count reaches N, Player X wins. For Player O, we decrement. This makes win checks O(1) space O(N)."
            }
        ],
        "complexity_analysis": {
            "win_check": "O(N) normal, O(1) with running row/col sums.",
            "space": "O(N^2) for the board."
        }
    }
}

for i, p in enumerate(data['problems']):
    if p['id'] == 'snake-and-ladder':
        data['problems'][i] = snake_ladder
    elif p['id'] == 'tic-tac-toe':
        data['problems'][i] = tic_tac_toe

with open('frontend/public/lld-db.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Updated lld-db.json")
